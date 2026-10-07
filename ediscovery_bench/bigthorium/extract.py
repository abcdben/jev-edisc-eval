"""Extract the Big Thorium e-mails, the aiR prompt criteria and the demo coding from the RelativityOne ARM archive.

Where things live inside the archive (`data/bigthorium/raw/<workspace>/`):

  StructuredAnalytics/<set>/archive/analytics-set.aset   zip of Spark/Avro parts ("StructuredDocument_1": id, text, meta) —
                                                          the only place that joins control number -> extracted text -> e-mail
                                                          header fields. Codec is the snappy *framing* format, declared as "Snappy".
  Audit/audit_*.txt                                       JSON-lines audit log (~854k rows). Used for: the aiR prompt criteria
                                                          (object aiRforReviewPromptCriteria: "Case Summary" and "Operation
                                                          Configuration" field updates) and the human Responsive coding
                                                          (Document "Update" rows with field Responsive).
  Invariant/Processing/.../SOURCE/*.EML                   the natives (quoted-printable e-mails); INTERMEDIATE/*.TXT the
                                                          processing-side extracted text (UTF-16). Not needed once the Avro is read.
  Database/EDDS11468740.BAK                               compressed SQL Server backup; not readable without SQL Server. The
                                                          aiR relevance results themselves are only in there (not extracted).

Output (data/bigthorium/):
  bigthorium_all.jsonl   {"id": control number, "text", "meta": {from, to, cc, date, subject, human_code, artifact_id}}
  air_criteria.json      every version of the aiR prompt criteria (by artifact id, with timestamps) and the latest one
  human_coding.json      control number -> {"code", "at", "by"}
"""
from __future__ import annotations

import glob
import io
import json
import re
import struct
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "bigthorium" / "raw"
OUT = ROOT / "data" / "bigthorium"
FOOTER_RE = re.compile(r"\s*©\s*20\d\d Relativity ODA LLC\s*$")


def workspace_dir() -> Path:
    cands = [p for p in RAW.iterdir() if p.is_dir() and (p / "ArchiveInformation.xml").exists()] if RAW.exists() else []
    if not cands:
        raise FileNotFoundError(f"no ARM workspace under {RAW}; unzip the Bigthorium_*.zip there first")
    return cands[0]


# ------------------------------------------------------------------------------------------------ Avro (analytics set)

def _rlong(b: bytes, i: int) -> tuple[int, int]:
    shift = n = 0
    while True:
        c = b[i]
        i += 1
        n |= (c & 0x7F) << shift
        shift += 7
        if not c & 0x80:
            break
    return (n >> 1) ^ -(n & 1), i


def _rbytes(b: bytes, i: int) -> tuple[bytes, int]:
    n, i = _rlong(b, i)
    return b[i: i + n], i + n


def read_avro_container(b: bytes) -> list[dict]:
    """Minimal Avro object-container reader for the Relativity analytics-set parts (codec "Snappy" = snappy framing format)."""
    import fastavro  # noqa: PLC0415
    import snappy  # noqa: PLC0415  (python-snappy)

    assert b[:4] == b"Obj\x01", "not an Avro container"
    i, meta = 4, {}
    while True:
        n, i = _rlong(b, i)
        if n == 0:
            break
        for _ in range(abs(n)):
            k, i = _rbytes(b, i)
            v, i = _rbytes(b, i)
            meta[k.decode()] = v
    schema = json.loads(meta["avro.schema"])
    codec = meta.get("avro.codec", b"null").decode().lower()
    i += 16  # sync marker
    out = []
    while i < len(b):
        cnt, i = _rlong(b, i)
        data, i = _rbytes(b, i)
        i += 16
        if codec == "snappy":
            if data[:10] == b"\xff\x06\x00\x00sNaPpY":
                raw = snappy.StreamDecompressor().decompress(data)
            else:
                raw = snappy.decompress(data[:-4])  # standard Avro snappy: CRC32 trailer
        elif codec == "null":
            raw = data
        else:
            raise ValueError(f"codec {codec}")
        bio = io.BytesIO(raw)
        for _ in range(cnt):
            out.append(fastavro.schemaless_reader(bio, schema))
    return out


def read_analytics_set(ws: Path) -> list[dict]:
    asets = list(ws.glob("StructuredAnalytics/*/archive/analytics-set.aset"))
    if not asets:
        raise FileNotFoundError("analytics-set.aset not found")
    recs = []
    blobs: list[bytes] = []
    try:
        with zipfile.ZipFile(asets[0]) as z:
            blobs = [z.read(n) for n in z.namelist()]
    except zipfile.BadZipFile:
        # the .aset carries a non-standard extra field that Python's zipfile rejects; the system unzip reads it
        import subprocess  # noqa: PLC0415
        import tempfile  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["unzip", "-q", "-o", str(asets[0]), "-d", td], check=True)
            blobs = [p.read_bytes() for p in Path(td).glob("blob-*")]
    for data in blobs:
        if data[:4] == b"Obj\x01":
            recs.extend(read_avro_container(data))
    return recs


# ------------------------------------------------------------------------------------------------ audit log

def _fields(r: dict) -> list[dict]:
    d = (r.get("Details") or {}).get("auditElement") or {}
    f = d.get("field", []) if isinstance(d, dict) else []
    return [f] if isinstance(f, dict) else f


def scan_audit(ws: Path, log=print) -> tuple[dict, dict]:
    """Returns (criteria_by_artifact, coding_by_control_number) from the audit JSON lines."""
    criteria: dict[str, dict] = defaultdict(dict)
    coding: dict[str, dict] = {}
    rows = 0
    for f in sorted(glob.glob(str(ws / "Audit" / "audit_*.txt"))):
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                rows += 1
                if '"ObjectType":"aiRforReviewPromptCriteria"' in line:
                    r = json.loads(line)
                    for fl in _fields(r):
                        if "newValue" in fl:
                            prev = criteria[str(r["ArtifactID"])].get(fl["@name"])
                            if prev is None or prev["at"] < r["TimeStamp"]:
                                criteria[str(r["ArtifactID"])][fl["@name"]] = {"at": r["TimeStamp"], "value": fl["newValue"]}
                elif '"ObjectType":"Document"' in line and '"Responsive"' in line:
                    r = json.loads(line)
                    if r.get("ActionName", "").startswith("Update"):
                        for fl in _fields(r):
                            if fl.get("@name") == "Responsive" and fl.get("setChoiceName"):
                                prev = coding.get(r["Name"])
                                if prev is None or prev["at"] < r["TimeStamp"]:
                                    coding[r["Name"]] = {"code": fl["setChoiceName"], "at": r["TimeStamp"], "by": r.get("UserName")}
    log(f"audit: {rows:,} rows; {len(criteria)} prompt-criteria objects; {len(coding)} coded documents")
    return dict(criteria), coding


def latest_criteria(criteria: dict) -> dict:
    """The most recently edited prompt-criteria object with both a case summary and relevance criteria."""
    best = None
    for aid, d in criteria.items():
        if "Case Summary" not in d or "Operation Configuration" not in d:
            continue
        try:
            cs = json.loads(d["Case Summary"]["value"])
            oc = json.loads(d["Operation Configuration"]["value"])
        except Exception:
            continue
        if not (cs.get("matterOverview") and oc.get("criteria")):
            continue
        at = max(d["Case Summary"]["at"], d["Operation Configuration"]["at"])
        if best is None or at > best["at"]:
            best = {"artifact_id": aid, "at": at, "case_summary": cs, "criteria": oc["criteria"]}
    return best


# ------------------------------------------------------------------------------------------------ build

def build(log=print) -> dict:
    ws = workspace_dir()
    OUT.mkdir(parents=True, exist_ok=True)
    recs = read_analytics_set(ws)
    log(f"analytics set: {len(recs):,} records")
    criteria, coding = scan_audit(ws, log)
    rows = []
    for r in sorted(recs, key=lambda r: r["id"]):
        if not r["id"].startswith("aiR"):
            continue  # IMG000001.png … are five images added for a different demo
        text = r["text"].replace("\r\n", "\n").replace("\r", "\n")
        text = FOOTER_RE.sub("", text).rstrip() + "\n"
        m = r.get("meta") or {}
        meta = {k: m.get(k, "") for k in ("from", "to", "cc", "date", "subject")}
        meta["artifact_id"] = m.get("internal-artifact-id")
        meta["human_code"] = (coding.get(r["id"]) or {}).get("code")
        rows.append({"id": r["id"], "text": text, "labels": {}, "gray": [], "meta": meta})
    (OUT / "bigthorium_all.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
    latest = latest_criteria(criteria)
    (OUT / "air_criteria.json").write_text(json.dumps({"latest": latest, "versions": criteria}, indent=1, ensure_ascii=False))
    (OUT / "human_coding.json").write_text(json.dumps(coding, indent=1))
    n_resp = sum(1 for v in coding.values() if v["code"] == "Responsive")
    info = {"docs": len(rows), "empty": sum(1 for x in rows if len(x["text"]) < 200), "coded": len(coding), "coded_responsive": n_resp,
            "criteria_versions": len(criteria), "latest_criteria_at": latest["at"] if latest else None}
    log(f"wrote {OUT / 'bigthorium_all.jsonl'}: {info}")
    return info
