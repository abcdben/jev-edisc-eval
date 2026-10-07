"""
TREC Legal Track 2009 / 2010 corpora: human relevance assessments joined to document text.

Sources (all downloaded into data/legal09/raw and data/legal10/raw):
  NIST   https://trec.nist.gov/data/legal09.html   evalInt09.zip: qrels_{doc,msg}_{pre,post}_all.txt (topics 201-207)
  NIST   https://trec.nist.gov/data/legal10.html   qrel_leg_int_2010_{doc,msg}_{pre,post}.txt (topics 301-304),
                                                   qrels.t10legallearn (Learning task, topics 200-207)
  UMD    https://trec-legal.umiacs.umd.edu/corpora/trec/legal10/  edrmv2txt-v2.tar.bz2: the de-duplicated text
         rendering of EDRM Enron v2 (685,592 documents), kept at EDRM/ in the repo root (git-ignored).

Qrels format (both years): `topic 0 docid judgment p_select`. judgment 1 relevant, 0 not, -1/-2 gray/unjudged.
"pre" is the first-pass assessor's label, "post" the label after the Topic Authority ruled on appeals. p_select is
the document's inclusion probability in the stratified sample, needed for population estimates of recall.

Document ids. 2010 ids are EDRM v2 ids (`3.1007403.DKQY...`, attachments `<msg>.1`, `<msg>.2`, ...) and every
judged 2010 document resolves to a file in the text rendering. 2009 ids (`0.7.47.1000898`) belong to the earlier
Clearwell/UMD build of the collection, which is not public ("available from Doug Oard"); the 2010 coordinators
could only map 2009 assessments onto v2 by approximate text matching (seed.csv, 8,245 documents). So 2009 is
built as an id manifest (labels, no text), 2010 and the Learning task with text.

Record format follows data/trec: {"id", "text", "labels": {<topic_key>: gold}, "gray": [...], "meta": {...}}.
`labels` carries the post-adjudication label (the study's standard); `meta.first_pass` / `meta.adjudicated` keep
both raw judgments, `meta.appealed` marks the documents whose label changed on appeal.
"""
from __future__ import annotations

import gzip
import json
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[2]
EDRM_TAR = ROOT / "EDRM" / "edrmv2txt-v2.tar.bz2"
POS, NEG = "responsive", "not_responsive"

# ZL's licence banner, appended to every message in the text rendering between two rows of asterisks; not part of the
# document. The "Attachment: <name> type=<mime>" lines that follow it are kept.
import re
BANNER_RE = re.compile(r"\*{5,}\s*\r?\nEDRM Enron Email Data Set has been produced.*?\r?\n\*{5,}\s*\r?\n?", re.S)


def _topics(year_dir: Path) -> dict[str, dict]:
    t = json.loads((year_dir / "topics.json").read_text())["topics"]
    return {k: v for k, v in t.items()}


def _read_qrels(path: Path) -> dict[tuple[str, str], tuple[int, float]]:
    """(topic, docid) -> (judgment, p_select)."""
    out: dict[tuple[str, str], tuple[int, float]] = {}
    for line in path.read_text().splitlines():
        p = line.split()
        if len(p) < 4:
            continue
        out[(p[0], p[2])] = (int(p[3]), float(p[4]) if len(p) > 4 else 1.0)
    return out


def _record(docid: str, topic: str, key: str, pre: int | None, post: int, p: float | None, text: str | None, prefix: str, extra: dict | None = None) -> dict:
    labels, gray = {}, []
    if post == 1:
        labels[key] = POS
    elif post == 0:
        labels[key] = NEG
    else:
        gray.append(key)  # gray / unjudged after adjudication: present, not scored
    parts = docid.split(".")
    # EDRM v2 attachments are <n>.<n>.<ZL id>.<k>; the 2009 build's ids are four numbers (0.7.47.1097275) with no family structure we can recover
    is_att = len(parts) == 4 and parts[-1].isdigit() and not parts[2].isdigit()
    msg_id = ".".join(parts[:3]) if is_att else docid
    meta: dict = {
        "docid": docid, "msg_id": msg_id, "is_attachment": is_att, "topic": topic,
        "first_pass": pre, "adjudicated": post, "appealed": (pre is not None and pre != post), "p_select": p,
        "n_chars": len(text) if text is not None else None,
    }
    if extra:
        meta.update(extra)
    rec = {"id": f"{prefix}-{docid}", "labels": labels, "gray": gray, "meta": meta}
    if text is not None:
        rec["text"] = text
    return rec


def _clean(text: str) -> str:
    return BANNER_RE.sub("", text.replace("\r\n", "\n")).rstrip() + "\n"


def extract_texts(docids: set[str], tar_path: Path = EDRM_TAR, log=print) -> dict[str, str]:
    """One streaming pass over the bz2 tar; returns docid -> text for the requested ids."""
    want = set(docids)
    out: dict[str, str] = {}
    log(f"scanning {tar_path.name} for {len(want):,} documents ...")
    with tarfile.open(tar_path, "r:bz2") as tf:
        for n, m in enumerate(tf):
            if not m.isfile():
                continue
            name = m.name.rsplit("/", 1)[-1]
            if not name.endswith(".txt"):
                continue
            did = name[:-4]
            if did in want:
                f = tf.extractfile(m)
                if f is not None:
                    out[did] = _clean(f.read().decode("utf-8", errors="replace"))
                    if len(out) == len(want):
                        break
            if n % 100_000 == 0 and n:
                log(f"  {n:,} entries, {len(out):,} found")
    log(f"  found {len(out):,} / {len(want):,}")
    return out


def _write(path: Path, rows: Iterator[dict] | list[dict]) -> int:
    n = 0
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


# ------------------------------------------------------------------------------------------------ 2010 Interactive

def build_legal10(out_dir: Path = ROOT / "data" / "legal10", unit: str = "doc", log=print) -> Path:
    """data/legal10/legal10.jsonl (unit=doc) or legal10_msg.jsonl (unit=msg): every judged document with text."""
    raw = out_dir / "raw"
    topics = _topics(out_dir)
    pre = _read_qrels(raw / f"qrel_leg_int_2010_{unit}_pre.txt")
    post = _read_qrels(raw / f"qrel_leg_int_2010_{unit}_post.txt")
    assert pre.keys() == post.keys(), "pre/post qrels should cover the same (topic, doc) pairs"
    texts = extract_texts({d for _, d in post}, log=log)
    rows = []
    for (t, d), (j_post, p) in sorted(post.items()):
        j_pre = pre[(t, d)][0]
        rows.append(_record(d, t, topics[t]["key"], j_pre, j_post, p, texts.get(d), "L10", {"unit": unit}))
    missing = sum(1 for r in rows if "text" not in r)
    out = out_dir / ("legal10.jsonl" if unit == "doc" else "legal10_msg.jsonl")
    n = _write(out, rows)
    _summary(rows, log)
    log(f"wrote {out} ({n:,} records, {missing} without text)")
    return out


# ------------------------------------------------------------------------------------------------ 2010 Learning task

def build_legal10_learn(out_dir: Path = ROOT / "data" / "legal10", log=print) -> Path:
    """data/legal10/learn.jsonl: the Learning task's assessed documents (topics 200-207 on EDRM v2), single label."""
    raw = out_dir / "raw"
    topics = _topics(out_dir)
    judged: dict[tuple[str, str], tuple[int, int]] = {}  # (topic, docid) -> (judgment, stratum weight)
    plain, gz = raw / "qrels.t10legallearn", raw / "qrels.t10legallearn.gz"
    if not plain.exists() and not gz.exists():
        raise FileNotFoundError(f"{gz} missing; download from https://trec.nist.gov/data/legal/10/qrels.t10legallearn.gz")
    with (plain.open() if plain.exists() else gzip.open(gz, "rt")) as f:
        for line in f:
            p = line.split()
            if len(p) != 3:
                continue
            t, _, d = p[0].partition(":")
            j = int(p[2])
            if j >= 0:
                judged[(t, d)] = (j, int(p[1]))
    texts = extract_texts({d for _, d in judged}, log=log)
    rows = [
        _record(d, t, topics[t]["key"], None, j, None, texts.get(d), "L10L", {"unit": "doc", "task": "learning", "stratum_weight": w})
        for (t, d), (j, w) in sorted(judged.items())
    ]
    out = out_dir / "learn.jsonl"
    n = _write(out, rows)
    _summary(rows, log)
    log(f"wrote {out} ({n:,} records, {sum(1 for r in rows if 'text' not in r)} without text)")
    return out


# ------------------------------------------------------------------------------------------------ 2009 Interactive (ids only)

def build_legal09_ids(out_dir: Path = ROOT / "data" / "legal09", unit: str = "doc", log=print) -> Path:
    """data/legal09/{doc,msg}_ids.jsonl: 2009 Interactive assessments as an id manifest. No text (collection not public)."""
    raw = out_dir / "raw" / "evalInt09"
    topics = _topics(out_dir)
    pre = _read_qrels(raw / f"qrels_{unit}_pre_all.txt")
    post = _read_qrels(raw / f"qrels_{unit}_post_all.txt")
    assert pre.keys() == post.keys()
    rows = [_record(d, t, topics[t]["key"], pre[(t, d)][0], j, p, None, "L09", {"unit": unit}) for (t, d), (j, p) in sorted(post.items())]
    out = out_dir / f"{unit}_ids.jsonl"
    n = _write(out, rows)
    _summary(rows, log)
    log(f"wrote {out} ({n:,} records, ids only)")
    return out


def _summary(rows: list[dict], log) -> None:
    by: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        m = r["meta"]
        c = by[m["topic"]]
        c["n"] += 1
        c["pos"] += 1 if r["labels"].get(next(iter(r["labels"]), ""), "") == POS else 0
        c["gray"] += 1 if r["gray"] else 0
        c["appealed"] += 1 if m["appealed"] else 0
        c["no_text"] += 1 if "text" not in r else 0
    for t in sorted(by):
        c = by[t]
        log(f"  topic {t}: n={c['n']:,} relevant={c['pos']:,} gray={c['gray']:,} appealed={c['appealed']:,}" + (f" no_text={c['no_text']}" if c["no_text"] else ""))
