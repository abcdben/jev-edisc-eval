"""Population explorer export -> site/public/explore/ (read by site/explore.html).

The explorer shows every judged document of one dataset, cut by who called it responsive: a reference standard, an arm A,
and an optional overlay arm B, each of which can be a human signal or a model. It needs per-document outputs, which the
study aggregates (study.json) do not carry, so this module writes its own small static files:

    explore/index.json                 datasets, their topics, human signals and arms
    explore/<dataset>/rows.json        one row per judgment (document x topic), columnar: ids, topic, family, labels ...
    explore/<dataset>/arms/<arm>.json  one model arm's p(responsive) per row, aligned to rows.json
    explore/<dataset>/arms/<arm>.meta.json  TAR arms only: the simulated reviewer's per-row provenance (_tar_meta), aligned to rows.json

Three kinds of dataset feed it:

  * `judgments`: the TREC Legal corpora, one source row per (document, topic) judgment, human signals in `meta`
    (first_pass / adjudicated), message families via `msg_id` / `is_attachment`;
  * `corpus`: the study corpora (TREC 2016 eval sample, Mallinckrodt, Veridian, CUAD), one source row per document with a
    `labels` map over the task's questions (absent = not responsive, listed in `gray` = gray), one gold signal, no families;
  * `trec-alt`: the TREC 2016 alternate-assessor sample, (topic, document) pairs judged by NIST and three further assessors.

Model arms are read from results/<run dir>/<arm>/<model>.jsonl when a run covers the rows. Datasets flagged `placeholders`
(the TREC Legal ones, not yet scored) get a deterministic placeholder per arm, flagged `planned: true`, so the interface can
be exercised before the runs land; the others list measured arms only. Document text is never exported: `bench serve` reads
it from data/ on demand, locally only.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

from .runner import parse_job_stem
from .study import ARMS

ROOT = Path(__file__).resolve().parents[1]
POS = "responsive"

# ------------------------------------------------------------------------------------------------ datasets

# Human (or gold) signals. `field` is the corpus `meta` key for the judgments datasets; `gold` means the row's label itself.
HUMAN_ARMS = {
    "human@firstpass": dict(name="First-pass reviewer", short="First-pass reviewer", color="var(--ink-3)", field="first_pass",
                            note="The TREC Legal contract reviewers' and volunteers' first-pass judgment, before appeals."),
    "human@authority": dict(name="Topic Authority (adjudicated)", short="Topic Authority", color="var(--ink)", field="adjudicated",
                            note="The first-pass judgment after the Topic Authority ruled on appeals; the track's reference standard."),
    "human@assessor": dict(name="Assessor", short="Assessor", color="var(--ink)", field="adjudicated",
                           note="A single assessment per document, with no appeal process."),
    "human@nist": dict(name="NIST assessor", short="NIST assessor", color="var(--ink)", field="gold",
                       note="The TREC 2016 Total Recall relevance judgments (athome4 qrels); rel 1 or 2 is responsive, judged non-relevant and unjudged are not."),
    "human@alt1": dict(name="Alternate assessor 1", short="Alt assessor 1", color="var(--ink-2)", field="alt1",
                       note="One of three alternate assessors who re-judged a 50-document sample per topic (prels.tr2016.alt1)."),
    "human@alt2": dict(name="Alternate assessor 2", short="Alt assessor 2", color="var(--ink-3)", field="alt2",
                       note="One of three alternate assessors who re-judged a 50-document sample per topic (prels.tr2016.alt2)."),
    "human@alt3": dict(name="Alternate assessor 3", short="Alt assessor 3", color="var(--ink-4)", field="alt3",
                       note="One of three alternate assessors who re-judged a 50-document sample per topic (prels.tr2016.alt3)."),
    "panel@gold": dict(name="Model-panel gold (3 LLMs)", short="Panel gold", color="var(--ink)", field="gold",
                       note="Not a human signal: the corpus gold is a three-LLM panel (bench goldify); unanimous calls are the label, split panels are gray."),
    "human@planner": dict(name="Planner gold (synthetic)", short="Planner gold", color="var(--ink)", field="gold",
                          note="The synthetic matter's intended labels, audited by a model spec-relabel pass; not a human review."),
    "human@cuad": dict(name="CUAD annotators", short="CUAD annotators", color="var(--ink)", field="gold",
                       note="Expert clause annotations from the CUAD contract dataset, mapped to the study's twelve requests."),
}

# TREC 2016 topic numbers for the study's question keys (tasks/trec.yaml), from raw/tr2016-ext-topics.txt.
TREC_NO = {"bottled_water": "403", "eminent_domain": "404", "faith_based": "407", "condominiums": "410", "recount_2000": "412", "medicaid_reform": "414",
           "gw_bush": "415", "marketing": "416", "movie_gallery": "417", "rilya_wilson": "419", "nra_aliens": "422", "nra_rifle": "423"}

# A run counts as covering a dataset when it scores at least this share of the rows; the rest show as unscored (the TAR
# simulations score only the documents the simulated reviewer did not read).
MIN_COVERAGE = 0.2
MEASURED_ARMS = ["jev@base", "jev@choice", "openai-decisions@predicate", "openai-decisions@choice", "claude-sonnet-5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.8-flash", "tar@cal"]
PLACEHOLDER_ARMS = ["jev@base", "openai-decisions@predicate", "claude-sonnet-5", "gpt-5.6-luna", "gemini-3.8-flash", "tar@cal"]

DATASETS: list[dict[str, Any]] = [
    dict(id="legal10", kind="judgments", label="TREC Legal 2010 · Interactive", short="Enron emails (EDRM v2) · first-pass review + Topic Authority appeals",
         src="data/legal10/legal10.jsonl", topics="data/legal10/topics.json", text=True, results="legal10", placeholders=True, inherit_default=True,
         humans=["human@firstpass", "human@authority"], default=dict(standard="human@authority", a="human@firstpass", b="jev@base", topics=["301"])),
    dict(id="legal10-learn", kind="judgments", label="TREC Legal 2010 · Learning", short="Enron emails (EDRM v2) · one assessment per document, 2009 requests",
         src="data/legal10/learn.jsonl", topics="data/legal10/topics.json", text=True, results="legal10-learn", placeholders=True, inherit_default=False,
         humans=["human@assessor"], default=dict(standard="human@assessor", a=None, b=None, topics=["201"])),
    dict(id="legal09", kind="judgments", label="TREC Legal 2009 · Interactive", short="Enron emails (2009 build, text not public) · first-pass review + Topic Authority appeals",
         src="data/legal09/doc_ids.jsonl", topics="data/legal09/topics.json", text=False, results="legal09", placeholders=True, inherit_default=False,
         text_note="The 2009 track used a document build that was never released (available from the track coordinators); its ids do not resolve against the EDRM v2 rendering in EDRM/, so only the judgments are here.",
         humans=["human@firstpass", "human@authority"], default=dict(standard="human@authority", a="human@firstpass", b="jev@base", topics=["201"])),
    dict(id="trec", kind="corpus", label="TREC 2016 Total Recall · eval sample", short="Jeb Bush emails · 3,116-email stratified sample (positives, hard negatives, random) · NIST judgments · measured runs",
         src="data/trec/eval_ids.jsonl", task="tasks/trec.yaml", topic_no=TREC_NO, text=False, results="trec", placeholders=False,
         text_note="The Jeb Bush collection is distributed by NIST under the Total Recall usage agreement (see data/trec/README.md); place it at TREC/Jeb Bush TXT/ and rebuild to read the emails.",
         humans=["human@nist"], default=dict(standard="human@nist", a="jev@base", b="gpt-5.6-luna", topics=["415"])),
    dict(id="trec-alt", kind="trec-alt", label="TREC 2016 Total Recall · alternate assessors", short="Jeb Bush emails · 50 documents per topic re-judged by three alternate assessors · Jev, OpenAI Decisions and TAR scores from the full-collection runs",
         src="data/trec/raw/prels.tr2016.alt1", task="tasks/trec.yaml", topic_no=TREC_NO, text=False, results="trec_full", placeholders=False,
         text_note="The Jeb Bush collection is distributed by NIST under the Total Recall usage agreement (see data/trec/README.md); place it at TREC/Jeb Bush TXT/ and rebuild to read the emails.",
         humans=["human@nist", "human@alt1", "human@alt2", "human@alt3"],
         default=dict(standard="human@nist", a="human@alt1", b="jev@base", topics=[n for k, n in TREC_NO.items() if k != "eminent_domain"])),
    dict(id="mnk", kind="corpus", label="Mallinckrodt opioid emails", short="Opioid Industry Documents Archive emails · eight requests (four broad/narrow pairs) · model-panel gold · measured runs",
         src="data/mallinckrodt/mnk.jsonl", task="tasks/mallinckrodt.yaml", text=True, results="mnk", placeholders=False,
         humans=["panel@gold"], default=dict(standard="panel@gold", a="jev@base", b="gpt-5.6-luna", topics=["som_broad"])),
    dict(id="endo", kind="corpus", label="Endo opioid emails (held-out)", short="Opioid Industry Documents Archive emails, Endo production (published 2024-26) · eight requests (four broad/narrow pairs) · OpenAI-only model-panel gold · measured runs",
         src="data/endo/endo.jsonl", task="tasks/endo.yaml", text=True, results="endo", placeholders=False,
         humans=["panel@gold"], default=dict(standard="panel@gold", a="jev@base", b="gpt-5.6-luna", topics=["som_broad"])),
    dict(id="veridian", kind="corpus", label="Veridian synthetic matter", short="Synthetic medical-device matter · ten requests · planner gold · measured runs",
         src="data/veridian/veridian.jsonl", task="tasks/veridian.yaml", text=True, results="veridian", placeholders=False,
         humans=["human@planner"], default=dict(standard="human@planner", a="jev@base", b="gpt-5.6-luna", topics=["rfp01_recall"])),
    dict(id="cuad", kind="corpus", label="CUAD contract clauses", short="Contract paragraphs · twelve clause requests (six broad/narrow pairs) · expert annotations · measured runs",
         src="data/cuad/cuad.jsonl", task="tasks/cuad.yaml", text=True, results="cuad", placeholders=False,
         humans=["human@cuad"], default=dict(standard="human@cuad", a="jev@base", b="gpt-5.6-luna", topics=["license_grant"])),
]

ARM_BY_ID = {a["id"]: a for a in ARMS}
# Placeholder shape: (exponent on responsive rows, exponent on not-responsive rows). With p = 1 - 0.98 u^k on responsive rows and
# p = 0.98 u^k on the rest, the miss rate is 1 - 0.51^(1/k): the pairs below give roughly 15–30% misses and 4–13% false alarms.
PLACEHOLDER_K = {"jev@base": (4.0, 18.0), "openai-decisions@predicate": (3.5, 15.0), "claude-sonnet-5": (3.0, 12.0), "gpt-5.6-luna": (2.8, 11.0), "gemini-3.8-flash": (2.2, 8.0), "tar@cal": (1.8, 5.0)}


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def _u(*parts: Any) -> float:
    h = hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()
    return int(h[:12], 16) / 16**12


def _topic_kind(t: dict[str, Any]) -> str:
    return "privilege" if t.get("key") == "privilege" or "privilege" in str(t.get("title", "")).lower() else "responsiveness"


def _judgment(meta: dict[str, Any], labels: dict[str, str], gray: list[str], key: str, field: str) -> int:
    """1 / 0 / -1 for a human signal. The adjudicated field is the label itself when meta lacks it (single-assessment corpora)."""
    v = meta.get(field)
    if v is None and field in ("adjudicated", "gold"):
        if key in gray:
            return -1
        return 1 if labels.get(key) == POS else 0 if key in labels else -1
    if v is None:
        return -1
    return 1 if v == 1 else 0 if v == 0 else -1


def _gold(labels: dict[str, str], gray: list[str], key: str) -> int:
    """Study-corpus gold: listed in gray -> gray; labelled responsive -> responsive; otherwise not responsive (absent = negative)."""
    if key in gray:
        return -1
    return 1 if labels.get(key) == POS else 0


def _placeholder_p(arm: str, ds: str, docid: str, topic: str, std: int, contested: bool) -> float:
    """Deterministic, plausible p(responsive): right most of the time, less sure on contested documents, occasionally confidently wrong."""
    k_r, k_nr = PLACEHOLDER_K[arm]
    u = _u("explore", arm, ds, docid, topic)
    e = _u("explore-err", arm, ds, docid, topic)
    if std == 1:
        p = 1 - 0.98 * u**k_r
    elif std == 0:
        p = 0.98 * u**k_nr
    else:
        p = 0.05 + 0.6 * u  # gray: mostly unreadable attachments, the model has little to go on
    if contested:
        p = 0.5 + (p - 0.5) * 0.45
    if e < 0.08 / k_r:
        p = 1 - p
    return round(min(0.999, max(0.001, p)), 3)


def _runs_for(results: Path, run_dir: str, arm: str) -> list[Path]:
    """Prediction files for an arm under results/<run_dir>/: untagged runs first (the study's main runs), `multi` before `single`."""
    base = results / run_dir
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.glob("*/*.jsonl")):
        key, tag = parse_job_stem(p.stem)
        if key == arm:
            out.append((0 if tag == "" else 1, 0 if p.parent.name == "multi" else 1, p))
    return [p for _, _, p in sorted(out, key=lambda x: (x[0], x[1], str(x[2])))]


def _measured(paths: list[Path], prefix_ids: list[str], topic_keys: list[str]) -> tuple[list[float | None], Path] | None:
    """(p_positive per row, the run file) from the first run that covers these rows, keyed by (doc_id, question)."""
    want = set(zip(prefix_ids, topic_keys))
    for path in paths:
        got: dict[tuple[str, str], float] = {}
        for r in _iter_jsonl(path):
            if r.get("error"):
                continue
            k = (r["doc_id"], r["question"])
            if k not in want:
                continue
            p = r.get("p_positive")
            if p is None or (isinstance(p, float) and math.isnan(p)):
                continue
            got[k] = round(float(p), 4)
        vals = [got.get((i, q)) for i, q in zip(prefix_ids, topic_keys)]
        if sum(v is not None for v in vals) >= MIN_COVERAGE * len(vals):
            return vals, path
    return None


def _measured_p(paths: list[Path], prefix_ids: list[str], topic_keys: list[str]) -> list[float | None] | None:
    """p_positive per row from the first run that covers these rows (see _measured)."""
    m = _measured(paths, prefix_ids, topic_keys)
    return None if m is None else m[0]


TAR_SRC = {"clf": 0, "reviewer": 1}  # arms/<tar arm>.meta.json `src` codes; -1 = row not covered by the run


def _tar_meta(path: Path, prefix_ids: list[str], topic_keys: list[str], fpq_map: dict[int, int] | None = None) -> dict[str, Any]:
    """Per-row provenance of a TAR arm from the run's `raw` blocks (tar.py Reviewer.provenance), aligned to rows.json:
    who made the call (src), the uniform behind the simulated reviewer's miscode decision (u), the document's gold
    flag (g), this issue's gold flag (gq) and the over-coded issue index (fpq); plus the run's reviewer rates
    (default.fn miss rate, default.fp over-code rate) from the sidecar, so a front end can re-code the reviewer's
    rows under other rates: gold-positive documents are missed when u < fn, gold-negative ones over-coded on
    issue fpq when u < fp. The reviewer draws fpq over the task set's question order (tar.py Reviewer.code,
    ts.qids); `fpq_map` translates it to rows.json's `topic` index so the front end compares it to a row's topic."""
    raw: dict[tuple[str, str], dict] = {}
    for r in _iter_jsonl(path):
        if r.get("error") or not r.get("raw"):
            continue
        raw[(r["doc_id"], r["question"])] = r["raw"]
    side = path.with_suffix(".tar.json")
    rev = json.loads(side.read_text()).get("reviewer", {}) if side.exists() else {}
    fn = rev.get("miscode_rate")
    fp = rev.get("fp_rate", None if fn is None else round(fn * 0.2, 6))  # tar.NOISE_FP_RATIO for sidecars written before fp_rate existed
    src, u, g, gq, fpq = [], [], [], [], []
    for k in zip(prefix_ids, topic_keys):
        b = raw.get(k)
        src.append(TAR_SRC.get(b.get("src"), -1) if b else -1)
        u.append(b.get("u") if b else None)
        g.append(b.get("g", -1) if b else -1)
        gq.append(b.get("gq", -1) if b else -1)
        q = b.get("fpq", -1) if b else -1
        fpq.append((fpq_map.get(q, -1) if q >= 0 else -1) if fpq_map is not None else q)
    return {"default": {"fn": fn, "fp": fp}, "src": src, "u": u, "g": g, "gq": gq, "fpq": fpq}


# ------------------------------------------------------------------------------------------------ loaders

@dataclass
class Loaded:
    """A dataset flattened to one row per judgment, in source order; topic ids are the display ids (sorted later)."""
    topics_meta: dict[str, dict[str, Any]]  # display id -> {key, title, rfp_text, note}
    docid: list[str] = field(default_factory=list)
    topic: list[str] = field(default_factory=list)
    family: list[str] = field(default_factory=list)
    att: list[int] = field(default_factory=list)
    chars: list[int | None] = field(default_factory=list)
    psel: list[float | None] = field(default_factory=list)
    hum: dict[str, list[int]] = field(default_factory=dict)
    pred_id: list[str] = field(default_factory=list)  # doc_id as the prediction files know it
    pred_q: list[str] = field(default_factory=list)  # question key as the prediction files know it

    def add(self, docid: str, topic: str, family: str, att: int, chars: int | None, psel: float | None, hum: dict[str, int], pred_id: str, pred_q: str) -> None:
        self.docid.append(docid); self.topic.append(topic); self.family.append(family); self.att.append(att); self.chars.append(chars); self.psel.append(psel)
        for h, v in hum.items():
            self.hum.setdefault(h, []).append(v)
        self.pred_id.append(pred_id); self.pred_q.append(pred_q)


def _load_judgments(ds: dict[str, Any]) -> Loaded:
    topics_path = ROOT / ds["topics"]
    topics_meta = json.loads(topics_path.read_text())["topics"]
    for t in topics_meta.values():  # "rfp_text_ref": "../legal09/topics.json#201" -> the request text itself
        ref = t.get("rfp_text_ref")
        if not t.get("rfp_text") and ref:
            path, _, tid = ref.partition("#")
            t["rfp_text"] = json.loads((topics_path.parent / path).resolve().read_text())["topics"].get(tid, {}).get("rfp_text")
    fields = {h: HUMAN_ARMS[h]["field"] for h in ds["humans"]}
    L = Loaded(topics_meta)
    for r in _iter_jsonl(ROOT / ds["src"]):
        m = r["meta"]
        tid = str(m["topic"])
        if tid not in topics_meta:
            continue
        key = topics_meta[tid]["key"]
        L.add(m["docid"], tid, m.get("msg_id") or m["docid"], 1 if m.get("is_attachment") else 0, m.get("n_chars"), m.get("p_select"),
              {h: _judgment(m, r.get("labels", {}), r.get("gray", []), key, fields[h]) for h in ds["humans"]}, r["id"], key)
    return L


def _task_topics(ds: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Display id -> topic meta from the task YAML; TREC questions get their track numbers, the others their keys."""
    task = yaml.safe_load((ROOT / ds["task"]).read_text())
    no = ds.get("topic_no", {})
    out = {}
    for key, q in task["questions"].items():
        tid = no.get(key, key)
        bits = [b for b in (q.get("breadth"), q.get("richness")) if b]
        note = f"{' · '.join(bits)}" if bits else None
        if q.get("pair"):
            note = f"{note or ''}{' · ' if note else ''}pair {q['pair']}"
        out[tid] = dict(key=key, title=q["title"], rfp_text=(q.get("rfp_text") or "").strip() or None, note=note)
    return out


def _load_corpus(ds: dict[str, Any]) -> Loaded:
    topics_meta = _task_topics(ds)
    L = Loaded(topics_meta)
    h = ds["humans"][0]
    for r in _iter_jsonl(ROOT / ds["src"]):
        m = r.get("meta", {})
        chars = m.get("n_chars") or (len(r["text"]) if r.get("text") else None)
        for tid, t in topics_meta.items():
            L.add(r["id"], tid, r["id"], 0, chars, None, {h: _gold(r.get("labels", {}), r.get("gray", []), t["key"])}, r["id"], t["key"])
    return L


def _load_trec_alt(ds: dict[str, Any]) -> Loaded:
    """(topic, document) pairs of the alternate-assessor sample, restricted to the study's topics; NIST label from the athome4 qrels."""
    topics_meta = _task_topics(ds)
    raw = ROOT / "data/trec/raw"
    by_no = {ds["topic_no"][t["key"]]: tid for tid, t in topics_meta.items()}  # TREC number -> display id (the same string here)
    nist: dict[tuple[str, str], int] = {}
    for line in (raw / "athome4.facetsandqrels").read_text().split("\n"):
        if line.strip():
            t, d, rel, _sub = line.split()
            nist[(t, str(int(d)))] = 1 if int(rel) >= 1 else 0
    alts: dict[str, dict[tuple[str, str], tuple[int, float]]] = {}
    for i in (1, 2, 3):
        alts[f"alt{i}"] = {}
        for line in (raw / f"prels.tr2016.alt{i}").read_text().split("\n"):
            if line.strip():
                t, d, rel, p = line.split()
                alts[f"alt{i}"][(t, str(int(d)))] = (1 if int(rel) >= 1 else 0, float(p))
    L = Loaded(topics_meta)
    for (t, d), (_, p) in alts["alt1"].items():
        if t not in by_no:
            continue
        tid = by_no[t]
        hum = {"human@nist": nist.get((t, d), 0)}
        for i in (1, 2, 3):
            v = alts[f"alt{i}"].get((t, d))
            hum[f"human@alt{i}"] = v[0] if v else -1
        L.add(f"JB-{int(d):06d}", tid, f"JB-{int(d):06d}", 0, None, p, hum, f"JB-{int(d):06d}", topics_meta[tid]["key"])
    return L


LOADERS = {"judgments": _load_judgments, "corpus": _load_corpus, "trec-alt": _load_trec_alt}


# ------------------------------------------------------------------------------------------------ export

def export_explore(dest: Path, results: Path = ROOT / "results", only: set[str] | None = None) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index: dict[str, Any] = {"datasets": []}
    for ds in DATASETS:
        if only and ds["id"] not in only:
            continue
        src = ROOT / ds["src"]
        if not src.exists():
            print(f"skip {ds['id']}: {src} missing")
            continue
        L = LOADERS[ds["kind"]](ds)
        n = len(L.docid)
        humans = [dict(id=h, **{k: v for k, v in HUMAN_ARMS[h].items() if k != "field"}) for h in ds["humans"]]

        topic_ids = sorted(set(L.topic), key=lambda t: (not t.isdigit(), int(t) if t.isdigit() else 0, t))
        tpos = {t: i for i, t in enumerate(topic_ids)}
        fam_ids: list[str] = []
        fam_idx: dict[str, int] = {}
        for f in L.family:
            if f not in fam_idx:
                fam_idx[f] = len(fam_ids)
                fam_ids.append(f)
        rows = {"docid": L.docid, "topic": [tpos[t] for t in L.topic], "family": [fam_idx[f] for f in L.family], "att": L.att, "chars": L.chars, "psel": L.psel}

        std = L.hum[ds["default"]["standard"]]
        # contested: any two human signals disagree where both judged
        contested = [False] * n
        if len(ds["humans"]) >= 2:
            cols = [L.hum[h] for h in ds["humans"]]
            contested = [len({c[i] for c in cols if c[i] >= 0}) > 1 for i in range(n)]

        topics_out = []
        for tid in topic_ids:
            t = L.topics_meta[tid]
            idx = [j for j in range(n) if L.topic[j] == tid]
            topics_out.append(dict(id=tid, key=t["key"], title=t["title"], kind=_topic_kind(t), n=len(idx),
                                   n_pos=sum(std[j] == 1 for j in idx), n_gray=sum(std[j] == -1 for j in idx), n_contested=sum(contested[j] for j in idx),
                                   rfp_text=t.get("rfp_text"), note=t.get("note")))

        ds_dir = dest / ds["id"]
        (ds_dir / "arms").mkdir(parents=True, exist_ok=True)
        rows_path = ds_dir / "rows.json"
        rows_path.write_text(json.dumps({"n": n, "topics": topic_ids, "families": fam_ids, **rows, "humans": L.hum}, separators=(",", ":")))
        written.append(rows_path)

        arms_out = []
        for arm in (PLACEHOLDER_ARMS if ds["placeholders"] else MEASURED_ARMS):
            spec = ARM_BY_ID[arm]
            found = _measured(_runs_for(results, ds["results"], arm), L.pred_id, L.pred_q)
            measured, run_path = (None, None) if found is None else found
            if measured is None and not ds["placeholders"]:
                continue
            planned = measured is None
            p = measured or [_placeholder_p(arm, ds["id"], d, t, s, c) for d, t, s, c in zip(L.docid, L.topic, std, contested)]
            path = ds_dir / "arms" / f"{arm.replace('@', '__')}.json"
            path.write_text(json.dumps({"arm": arm, "planned": planned, "p": p}, separators=(",", ":")))
            written.append(path)
            entry = dict(id=arm, name=spec["name"], short=spec["short"], kind=spec["kind"], color=spec["color"], planned=planned,
                         note=spec.get("note") if planned else None, file=path.name,
                         coverage=None if planned else round(sum(v is not None for v in p) / max(1, n), 3))
            if arm.startswith("tar@") and run_path is not None:
                # simulated-reviewer provenance next to the arm file (see _tar_meta); `meta` names it
                meta_path = path.with_name(f"{path.stem}.meta.json")
                # topics_meta is in the task YAML's question order (= TaskSet.qids, the order the reviewer's fpq indexes); rows.json's topic index is tpos
                fpq_map = {i: tpos[tid] for i, tid in enumerate(L.topics_meta) if tid in tpos}
                meta_path.write_text(json.dumps(_tar_meta(run_path, L.pred_id, L.pred_q, fpq_map), separators=(",", ":")))
                written.append(meta_path)
                entry["meta"] = meta_path.name
            arms_out.append(entry)

        default = dict(ds["default"])
        if default.get("b") and not any(a["id"] == default["b"] for a in arms_out):
            default["b"] = None
        if default.get("a") and not any(a["id"] == default["a"] for a in arms_out) and default["a"] not in ds["humans"]:
            default["a"], default["b"] = None, None
        has_att = any(L.att)
        index["datasets"].append(dict(id=ds["id"], kind=ds["kind"], label=ds["label"], short=ds["short"], text=ds["text"], text_note=ds.get("text_note"),
                                      n=n, n_docs=len(set(L.docid)), n_families=len(fam_ids), has_attachments=has_att, inherit_default=bool(ds.get("inherit_default")) and has_att,
                                      placeholders=ds["placeholders"], topics=topics_out, humans=humans, arms=arms_out, default=default))
        print(f"{ds['id']}: {n:,} judgments, {len(set(L.docid)):,} documents, {len(fam_ids):,} families, topics {', '.join(topic_ids)}, "
              f"{sum(1 for a in arms_out if not a['planned'])}/{len(arms_out)} arms measured")

    index_path = dest / "index.json"
    if only and index_path.exists():  # a partial export keeps the other datasets' entries
        done = {d["id"] for d in index["datasets"]}
        kept = [d for d in json.loads(index_path.read_text()).get("datasets", []) if d["id"] not in done]
        order = [d["id"] for d in DATASETS]
        index["datasets"] = sorted(kept + index["datasets"], key=lambda d: order.index(d["id"]) if d["id"] in order else 99)
    index_path.write_text(json.dumps(index, indent=1))
    written.append(index_path)
    return written
