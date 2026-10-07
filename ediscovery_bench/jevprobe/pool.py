"""Unjudged Enron documents for T4: one streaming pass over EDRM/edrmv2txt-v2.tar.bz2.

Keeps a deterministic hash sample of e-mail messages (not attachments) whose EDRM id is in no public TREC Legal qrels
(2010 Learning topics 200-207, 2010 Interactive 301-304). Output: data/jev_probe/enron_unjudged_pool.jsonl.
Slow (~685k entries, bz2); run once in the background. Resumable only in the sense that it is skipped if the output exists.
"""
from __future__ import annotations

import hashlib
import json
import re
import tarfile
import time

from ..legal.build import EDRM_TAR, _clean
from .common import DATA, ROOT, write_jsonl

POOL = DATA / "enron_unjudged_pool.jsonl"
MOD = 250  # keep ~1/250 of messages: ~1,800 candidates before the length filter
MIN_CHARS, MAX_CHARS = 400, 8000
_META_RE = re.compile(r"^X-(?:SDOC|ZLID|FileName|Folder|Origin):.*\n?", re.M)


def judged_ids() -> set[str]:
    ids: set[str] = set()
    for f in ("learn.jsonl", "legal10.jsonl", "legal10_msg.jsonl"):
        p = ROOT / "data" / "legal10" / f
        if p.exists():
            with p.open() as fh:
                for line in fh:
                    if line.strip():
                        r = json.loads(line)
                        ids.add(r["meta"]["docid"])
                        ids.add(r["meta"]["msg_id"])
    return ids


def _keep(docid: str) -> bool:
    return int(hashlib.md5(docid.encode()).hexdigest(), 16) % MOD == 0


def scan(log=print, limit: int | None = None) -> int:
    if POOL.exists():
        log(f"{POOL} exists; skipping EDRM scan")
        return sum(1 for _ in POOL.open())
    if not EDRM_TAR.exists():
        log(f"{EDRM_TAR} not found; T4 (Enron) cannot be built")
        return 0
    judged = judged_ids()
    out: list[dict] = []
    t0 = time.time()
    with tarfile.open(EDRM_TAR, "r:bz2") as tf:
        for n, m in enumerate(tf):
            if not m.isfile() or not m.name.endswith(".txt"):
                continue
            did = m.name.rsplit("/", 1)[-1][:-4]
            parts = did.split(".")
            if len(parts) != 3:  # attachments are <n>.<n>.<ZL id>.<k>
                continue
            if did in judged or not _keep(did):
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            text = _META_RE.sub("", _clean(f.read().decode("utf-8", errors="replace")))
            if MIN_CHARS <= len(text) <= MAX_CHARS:
                out.append({"id": f"L10U-{did}", "text": text, "labels": {}, "gray": [], "meta": {"docid": did, "n_chars": len(text), "judged": False}})
            if n % 100_000 == 0 and n:
                log(f"  {n:,} entries, {len(out):,} kept, {time.time() - t0:.0f}s")
            if limit and len(out) >= limit:
                break
    write_jsonl(POOL, out)
    log(f"wrote {POOL}: {len(out)} unjudged messages in {time.time() - t0:.0f}s")
    return len(out)


if __name__ == "__main__":
    scan()
