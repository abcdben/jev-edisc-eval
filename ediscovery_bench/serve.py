"""Local document server for the population explorer (site/explore.html).

Document text stays on this machine: the explorer's static files carry ids, labels and scores only, and fetch text from
here when the page runs next to a checkout with data/. Binds to 127.0.0.1.

    GET /text/<dataset>/<docid>      -> {"docid", "text", "meta"}
    GET /family/<dataset>/<msgid>    -> {"docs": [{"docid", "is_attachment", "n_chars", "text", "meta"}, ...]}
    GET /health                      -> {"ok": true, "datasets": [...]}

Each dataset's JSONL is indexed once, lazily, by byte offset (ids are read off the start of each line; no JSON parsing).
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from .explore import DATASETS, ROOT

ID_RE = re.compile(rb'^\{"id": "([^"]+)"')
MSG_RE = re.compile(rb'"msg_id": "([^"]+)"')
ATT_RE = re.compile(rb'"is_attachment": (true|false)')


class _Index:
    def __init__(self, path: Path):
        self.path = path
        self.offsets: dict[str, int] = {}
        self.families: dict[str, list[str]] = {}
        with path.open("rb") as f:
            pos = 0
            for line in f:
                m = ID_RE.match(line)
                if m:
                    full = m.group(1).decode()
                    # the explorer asks by the corpus id (study corpora) or by the bare docid behind a "L10-" style prefix (TREC Legal)
                    docid = full.split("-", 1)[1] if "-" in full else full
                    if docid not in self.offsets:
                        self.offsets[docid] = pos
                        mm = MSG_RE.search(line)
                        if mm:
                            self.families.setdefault(mm.group(1).decode(), []).append(docid)
                    self.offsets.setdefault(full, pos)
                pos += len(line)
        # message first, then attachments in id order
        for docs in self.families.values():
            docs.sort(key=lambda d: (d.count(".") , d))

    def read(self, docid: str) -> dict | None:
        off = self.offsets.get(docid)
        if off is None:
            return None
        with self.path.open("rb") as f:
            f.seek(off)
            r = json.loads(f.readline())
        return {"docid": docid, "text": r.get("text", ""), "meta": r.get("meta", {}), "labels": r.get("labels", {}), "gray": r.get("gray", [])}


_INDEXES: dict[str, _Index] = {}
_SOURCES = {d["id"]: ROOT / d["src"] for d in DATASETS if d["text"]}  # datasets whose text is on disk (explore.DATASETS)


def _index(ds: str) -> _Index | None:
    if ds not in _SOURCES or not _SOURCES[ds].exists():
        return None
    if ds not in _INDEXES:
        print(f"indexing {_SOURCES[ds].name} ...", flush=True)
        _INDEXES[ds] = _Index(_SOURCES[ds])
        print(f"  {len(_INDEXES[ds].offsets):,} documents, {len(_INDEXES[ds].families):,} families", flush=True)
    return _INDEXES[ds]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quiet
        pass

    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parts = [unquote(p) for p in self.path.split("?")[0].strip("/").split("/")]
        if parts == ["health"]:
            return self._send(200, {"ok": True, "datasets": [d for d, p in _SOURCES.items() if p.exists()]})
        if len(parts) == 3 and parts[0] in ("text", "family"):
            kind, ds, key = parts
            idx = _index(ds)
            if idx is None:
                return self._send(404, {"error": f"no local text for dataset {ds!r}"})
            if kind == "text":
                doc = idx.read(key)
                return self._send(200, doc) if doc else self._send(404, {"error": "unknown document"})
            docs = [idx.read(d) for d in idx.families.get(key, [])]
            return self._send(200, {"msg_id": key, "docs": [d for d in docs if d]})
        self._send(404, {"error": "unknown route"})


def serve(port: int = 8766, warm: bool = True) -> None:
    if warm:
        for ds in _SOURCES:
            _index(ds)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"document server on http://127.0.0.1:{port}  (Ctrl-C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
