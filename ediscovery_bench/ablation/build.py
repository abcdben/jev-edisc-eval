"""Build the ablation samples and their renamed twins.

  data/ablation/enron_j.jsonl        1,000 docs, TREC Legal 2010 learning task (Complaint J topics 201-207), stratified topic × label
  data/ablation/enron_k.jsonl        1,000 docs, TREC Legal 2010 interactive task (Complaint K topics 301-303)
  data/ablation/veridian.jsonl       1,000 docs from data/veridian/ft_test.jsonl (all ten requests labelled)
  data/ablation/mnk.jsonl            all 1,840 Mallinckrodt docs (copied; the brief arm changes the context, not the text)
  data/ablation/<arm>__renamed.jsonl the same documents with every knowledge-bearing name replaced
  data/ablation/mapping.json         the substitutions (phrases, surnames), with counts
  data/ablation/mnk_brief.md         one-page neutral case brief for the Mallinckrodt arm

Every renamed row carries meta.dose = number of knowledge-bearing substitutions in the original (people, SPEs, code names,
auditors; not the company name itself), for the dose–response analysis.
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from ..tasks import Question, TaskSet
from .names import (COMMON_WORD_SURNAMES, ENRON_FIRST, ENRON_PEOPLE, ENRON_PHRASES, ROLE_WORDS, VERIDIAN_COMMON, VERIDIAN_FORCE_RARE,
                    VERIDIAN_PEOPLE, VERIDIAN_PHRASES, Renamer, fake_surname, header_firstnames, header_surnames)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ablation"
MAX_CHARS = 12000
MIN_CHARS = 200
SEED = 11

ARMS = {
    "enron_j": dict(src="data/legal10/learn.jsonl", task="tasks/enron_j.yaml", n=1000, per_doc_topic=True,
                    topics=["prepay_transactions", "fas140", "financial_forecasts", "document_destruction", "energy_schedules", "financial_analysts", "fantasy_football"]),
    "enron_k": dict(src="data/legal10/legal10.jsonl", task="tasks/enron_k.yaml", n=1000, per_doc_topic=True,
                    topics=["oil_gas_drilling", "spill_response", "lobbying"]),
    "veridian": dict(src="data/veridian/ft_test.jsonl", task="tasks/veridian.yaml", n=1000, per_doc_topic=False, topics=None),
    "mnk": dict(src="data/mallinckrodt/mnk.jsonl", task="tasks/mallinckrodt.yaml", n=None, per_doc_topic=False, topics=None),
}

# knowledge-bearing phrases for the dose count: everything curated except the company's own name, domains and unit abbreviations
_GENERIC = {k for k in ENRON_PHRASES if k.lower().startswith("enron") or k.lower().endswith(".com") or k.lower().endswith(".net")
            or k in ("ECT", "EES", "ENA", "EBS", "EGM", "EWS", "EOTT", "EGF", "ENRON", "PGE")}
KNOWLEDGE_PHRASES = {k: v for k, v in ENRON_PHRASES.items() if k not in _GENERIC}

MNK_BRIEF = """Case brief: the opioid litigation against Mallinckrodt (background a well-informed reviewer would know)

Parties and forum. Mallinckrodt plc (Irish-domiciled since 2013, formerly the pharmaceuticals business of Covidien; U.S. operations
near St. Louis, Missouri) and its subsidiaries Mallinckrodt LLC and SpecGx LLC were defendants in MDL 2804, In re National Prescription
Opiate Litigation (N.D. Ohio, Judge Dan Polster), and in actions by state attorneys general and local governments.

Business. Mallinckrodt was the largest U.S. manufacturer of generic opioid tablets by volume (oxycodone, hydrocodone, methadone;
brands Roxicodone and Methadose) and sold the branded extended-release hydromorphone product Exalgo. The Washington Post's analysis
of DEA ARCOS data attributed roughly 28% of the opioid pills shipped in the United States in 2006-2012 to Mallinckrodt. Non-opioid
products (Acthar Gel, Ofirmev, INOmax, contrast agents) were not at issue in the opioid cases; Acthar was the subject of a separate
Medicaid-rebate matter.

Allegations. (1) Suspicious order monitoring: that the company's SOM program for orders from wholesalers and distributors was
inadequate, that flagged orders were released without adequate review, and that suspicious orders were not reported to DEA.
(2) Downstream visibility: that chargeback and IMS data gave Mallinckrodt visibility into shipments from wholesalers to individual
pharmacies, including Florida "pill mills", and that it did not act on that information. (3) Promotion: that it marketed opioids,
including Exalgo and generics, while minimising addiction and abuse risk. (4) Quota: that it sought ever-larger DEA aggregate
production quota.

Outcome. A 2017 settlement with DEA and DOJ ($35 million) over suspicious-order reporting and record-keeping. In October 2020
Mallinckrodt filed for Chapter 11 to resolve opioid claims through a roughly $1.6-1.7 billion opioid trust; it emerged in 2022 and
filed a second Chapter 11 in 2023. Documents produced in the litigation were made public through the Opioid Industry Documents
Archive (UCSF / Johns Hopkins).
"""


# ------------------------------------------------------------------------------------------------ sampling

def _rows(path: Path):
    for line in (ROOT / path).open():
        line = line.strip()
        if line:
            yield json.loads(line)


def _ok(text: str) -> bool:
    return MIN_CHARS <= len(text or "") <= MAX_CHARS


_META_RE = re.compile(r"^X-(?:SDOC|ZLID|FileName|Folder|Origin):.*\n?", re.M)


def strip_production_meta(text: str) -> str:
    """Remove EDRM production headers (X-SDOC, X-ZLID: zl-edrm-enron-v2-…). They are benchmark artefacts, not document
    content, and the leak check showed models recognise the collection from them. Applied to both conditions."""
    return _META_RE.sub("", text)


def sample_arm(arm: str, rng: random.Random) -> list[dict]:
    spec = ARMS[arm]
    rows = [r for r in _rows(spec["src"]) if _ok(r.get("text"))]
    if arm.startswith("enron"):
        for r in rows:
            r["text"] = strip_production_meta(r["text"])
    if spec["n"] is None:
        return rows
    if not spec["per_doc_topic"]:
        rng.shuffle(rows)
        return sorted(rows[: spec["n"]], key=lambda r: r["id"])
    # one judged topic per document: stratify topic × label, balanced within topic where the positives allow
    by: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        for q, lab in r["labels"].items():
            if q in spec["topics"]:
                by[(q, lab)].append(r)
    per_topic = spec["n"] // len(spec["topics"])
    out: list[dict] = []
    for q in spec["topics"]:
        pos, neg = by[(q, "responsive")], by[(q, "not_responsive")]
        rng.shuffle(pos)
        rng.shuffle(neg)
        n_pos = min(len(pos), per_topic // 2)
        n_neg = min(len(neg), per_topic - n_pos)
        for r in pos[:n_pos] + neg[:n_neg]:
            rr = dict(r)
            rr["labels"] = {q: r["labels"][q]}
            rr["meta"] = {**(r.get("meta") or {}), "topic_key": q}
            out.append(rr)
    return out


# ------------------------------------------------------------------------------------------------ mapping

def build_enron_renamer(texts: list[str], log=print) -> tuple[Renamer, dict]:
    hdr = header_surnames(texts)
    taken = set(ENRON_PEOPLE.values())
    people = {k.rstrip(","): v.rstrip(",") for k, v in ENRON_PEOPLE.items()}
    phrase_words = {w.lower() for k in ENRON_PHRASES for w in k.split()}
    skipped = []
    for s, n in sorted(hdr.items(), key=lambda kv: -kv[1]):
        if s in people or s.lower() in phrase_words or s in ENRON_FIRST:
            continue
        if s in ("Date", "Subject", "Sent", "Mailto", "Re", "Fw", "Fwd", "Original", "Message", "Attachment", "Attachments", "Com", "Www"):
            skipped.append(s)
            continue
        people[s] = fake_surname(s, taken)
    # surnames that are ordinary English words (or first names) are only replaced on header lines / next to a first name;
    # the curated principals (Lay, Skilling, Fastow, Kitchen, Temple...) are knowledge-bearing wherever they are capitalised
    curated = {k.rstrip(",") for k in ENRON_PEOPLE}
    firstlike = {"Mark", "Derrick", "Lynn", "Howard", "Blake", "Buy", "Rogers", "Hughes", "Cooper"}
    common = (set(COMMON_WORD_SURNAMES) | {s for s in people if s.lower() in _ENGLISH_WORDS or s in ENRON_FIRST}) - (curated - firstlike)
    firsts = sorted(set(ENRON_FIRST) | set(header_firstnames(texts)))
    rn = Renamer(ENRON_PHRASES, people, common, firsts)
    rn.catchall = {"enron": "volteron"}
    info = {"phrases": ENRON_PHRASES, "people": people, "common_word_surnames": sorted(common & set(people)), "firsts": firsts, "header_surnames_found": len(hdr),
            "curated_people": len(ENRON_PEOPLE), "skipped_tokens": skipped}
    log(f"enron mapping: {len(ENRON_PHRASES)} phrases, {len(people)} surnames ({len(hdr)} found in headers), {len(common & set(people))} treated as common words")
    return rn, info


def build_veridian_renamer(texts: list[str], log=print) -> tuple[Renamer, dict]:
    hdr = header_surnames(texts)
    taken = set(VERIDIAN_PEOPLE.values())
    people = dict(VERIDIAN_PEOPLE)
    phrase_words = {w.lower() for k in VERIDIAN_PHRASES for w in k.split()}
    for s, n in sorted(hdr.items(), key=lambda kv: -kv[1]):
        if s in people or s.lower() in phrase_words or n < 2:
            continue
        if s in ("Date", "Subject", "Sent", "Re", "Fw", "Fwd", "Employees", "Staff", "Hub", "Managers", "Team", "Services", "Facilities", "Cork", "Warsaw", "Mgmt", "Office"):
            continue
        if s in ROLE_WORDS:  # v2: "General Counsel", "Quality Manager" in From: lines are roles, not people
            continue
        people[s] = fake_surname(s, taken)
    # v2 (2026-10-06 renamer audit): the surgeons named in the requests (Feld, Rao) and Mitchell are replaced wherever they appear;
    # role words are never first names (so "General Counsel" is not a full name); a surname (Kessler) is not a first name either,
    # otherwise the e-mail pass skips it
    common = (set(VERIDIAN_COMMON) | {s for s in people if s.lower() in _ENGLISH_WORDS}) - VERIDIAN_FORCE_RARE
    firsts = {f for f in header_firstnames(texts) if f not in ROLE_WORDS and f not in people and f.lower() not in phrase_words}
    # v2: a capitalised token that is not an English word, standing before a common-word surname in the body ("Melissa Grant",
    # "Raymond Vance"), is a first name too; header parsing alone found 30 and left "Dr. Melissa Grant" untouched
    body_first = re.compile(r"\b([A-Z][a-z]{2,})\s+(?:" + "|".join(sorted(common & set(people), key=len, reverse=True)) + r")\b")
    place_words = {"Metro", "Brooklyn", "Central", "Lake", "State", "National", "City", "County", "Regional", "Memorial", "Warner", "Pike"}
    for t in texts:
        for f in body_first.findall(t):
            if f.lower() not in _ENGLISH_WORDS and f not in ROLE_WORDS and f not in place_words and f not in people and f.lower() not in phrase_words:
                firsts.add(f)
    firsts = sorted(firsts)
    rn = Renamer(VERIDIAN_PHRASES, people, common, firsts)
    info = {"phrases": VERIDIAN_PHRASES, "people": people, "common_word_surnames": sorted(common & set(people)), "firsts": firsts, "header_surnames_found": len(hdr),
            "version": 2, "note": "v2 2026-10-06: bare Apex/Northgate/Meridian/Aegis mapped; Feld, Rao, Mitchell, Barr replaced everywhere; "
                                  "role words excluded; title/initial positions and 3-letter e-mail local parts handled (see renamer_audit.md)"}
    log(f"veridian mapping: {len(VERIDIAN_PHRASES)} phrases, {len(people)} surnames")
    return rn, info


# ordinary English words that are also surnames: the system dictionary (lower-case entries only) plus a few extras
def _system_words() -> set[str]:
    p = Path("/usr/share/dict/words")
    if not p.exists():
        return set()
    return {w.strip().lower() for w in p.read_text(errors="ignore").split("\n") if w and w[0].islower() and len(w) >= 3}


_ENGLISH_WORDS = _system_words() | {w.lower() for w in COMMON_WORD_SURNAMES} | {
    "will", "may", "june", "august", "april", "march", "lane", "ford", "dell", "gates", "wells", "burns", "bills", "hale", "hart",
    "hope", "ivory", "jewel", "kay", "law", "lord", "mills", "nash", "noble", "page", "pace", "post", "ray", "rich", "rock", "sands",
    "sage", "small", "swan", "trim", "vest", "wall", "wells", "wick", "wing", "wise", "young", "grey", "gray", "black", "wright",
}


# ------------------------------------------------------------------------------------------------ renamed task sets

def renamed_taskset(ts: TaskSet, rn: Renamer) -> TaskSet:
    qs = {}
    for qid, q in ts.questions.items():
        qs[qid] = Question(id=q.id, title=rn.apply(q.title), rfp_text=rn.apply(q.rfp_text), positive_desc=rn.apply(q.positive_desc),
                           negative_desc=rn.apply(q.negative_desc), literal=rn.apply(q.literal), structured=q.structured, subparts=q.subparts,
                           breadth=q.breadth, richness=q.richness, pair=q.pair)
    return TaskSet(name=ts.name + "__renamed", context=rn.apply(ts.context), questions=qs, positive_label=ts.positive_label,
                   negative_label=ts.negative_label, gate_question=rn.apply(ts.gate_question), source=ts.source)


ENRON_NAMED_NOTE = (" The Company is Enron Corp.; the e-mails are from the Enron corpus (the complaint refers to the Company by the "
                    "pseudonym \"Volteron\").")
ENRON_RENAMED_NOTE = " The Company is Volteron Corp."


def arm_tasksets(arm: str, rn: Renamer | None) -> dict[str, TaskSet]:
    """Condition → TaskSet. For the Enron arms the named condition states that the Company is Enron; the renamed condition
    uses the pseudonym. For Veridian the renamed condition is the context passed through the renamer. For Mallinckrodt the
    two conditions are without / with the case brief."""
    ts = TaskSet.load(ROOT / ARMS[arm]["task"])
    if arm in ("enron_j", "enron_k"):
        named = TaskSet(name=ts.name, context=ts.context + ENRON_NAMED_NOTE, questions=ts.questions, positive_label=ts.positive_label,
                        negative_label=ts.negative_label, gate_question=ts.gate_question, source=ts.source)
        ren = TaskSet(name=ts.name + "__renamed", context=ts.context + ENRON_RENAMED_NOTE, questions=ts.questions, positive_label=ts.positive_label,
                      negative_label=ts.negative_label, gate_question=ts.gate_question, source=ts.source)
        return {"named": named, "renamed": ren}
    if arm == "veridian":
        return {"named": ts, "renamed": renamed_taskset(ts, rn)}
    brief = (DATA / "mnk_brief.md").read_text() if (DATA / "mnk_brief.md").exists() else MNK_BRIEF
    with_brief = TaskSet(name=ts.name + "__brief", context=ts.context + "\n\n" + brief.strip(), questions=ts.questions,
                         positive_label=ts.positive_label, negative_label=ts.negative_label, gate_question=ts.gate_question, source=ts.source)
    return {"named": ts, "renamed": with_brief}  # 'renamed' slot = the treated condition, here 'with brief'


# ------------------------------------------------------------------------------------------------ build

def build(log=print) -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    samples = {arm: sample_arm(arm, rng) for arm in ARMS}
    for arm, rows in samples.items():
        c = Counter((r["meta"].get("topic_key", "all"), lab) for r in rows for lab in (list(r["labels"].values())[:1] or ["-"]))
        log(f"{arm}: {len(rows)} docs; " + ", ".join(f"{k[0]}={v}{'+' if k[1]=='responsive' else '-'}" for k, v in sorted(c.items())))
    enron_texts = [r["text"] for r in samples["enron_j"] + samples["enron_k"]]
    rn_e, info_e = build_enron_renamer(enron_texts, log)
    rn_v, info_v = build_veridian_renamer([r["text"] for r in samples["veridian"]], log)
    dose_rn = Renamer(KNOWLEDGE_PHRASES, {k.rstrip(","): v for k, v in ENRON_PEOPLE.items()}, COMMON_WORD_SURNAMES)

    stats = {}
    for arm, rows in samples.items():
        (DATA / f"{arm}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        rn = rn_e if arm.startswith("enron") else rn_v if arm == "veridian" else None
        if rn is None:
            continue
        out, residual, n_sub, doses = [], 0, 0, []
        for r in rows:
            new = rn.apply(r["text"])
            dose = dose_rn.count_hits(r["text"]) if arm.startswith("enron") else rn.count_hits(r["text"])
            doses.append(dose)
            n_sub += sum(1 for a, b in zip(r["text"].split(), new.split()) if a != b)
            if arm.startswith("enron") and re.search(r"enron", new, re.I):
                residual += 1
            out.append({**r, "text": new, "meta": {**r["meta"], "dose": dose}})
        (DATA / f"{arm}__renamed.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
        stats[arm] = {"docs": len(rows), "changed_tokens": n_sub, "residual_enron_mentions": residual,
                      "dose_hist": dict(Counter("0" if d == 0 else "1-2" if d <= 2 else "3+" for d in doses))}
        log(f"{arm}: renamed; {n_sub} tokens changed; residual 'enron' in {residual} docs; dose {stats[arm]['dose_hist']}")
    # dose for named rows too (same doc) — written into the named file's meta for convenience
    for arm in ("enron_j", "enron_k"):
        rows = samples[arm]
        for r in rows:
            r["meta"]["dose"] = dose_rn.count_hits(r["text"])
        (DATA / f"{arm}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (DATA / "mnk_brief.md").write_text(MNK_BRIEF)
    # renamed request text / context, for the record
    ctx = {arm: {c: {"context": t.context, "requests": {q: t.questions[q].rfp_text for q in t.qids}} for c, t in arm_tasksets(arm, rn_e if arm.startswith("enron") else rn_v if arm == "veridian" else None).items()}
           for arm in ARMS}
    mapping = {"seed": SEED, "enron": info_e, "veridian": info_v, "knowledge_phrases_for_dose": sorted(KNOWLEDGE_PHRASES), "stats": stats, "contexts": ctx}
    (DATA / "mapping.json").write_text(json.dumps(mapping, indent=1, ensure_ascii=False))
    log(f"wrote {DATA}")
    return mapping


def rebuild_veridian_renamed(log=print) -> dict:
    """Regenerate only data/ablation/veridian__renamed.jsonl (and the veridian / stats / contexts entries of mapping.json) from the
    existing veridian.jsonl sample, after a renamer fix. The previous renamed file is kept as veridian__renamed.leaky_v1.jsonl;
    the Enron files and mapping are not touched (not re-run, see results/ablation/renamer_audit.md)."""
    rows = [json.loads(l) for l in (DATA / "veridian.jsonl").read_text().splitlines() if l.strip()]
    rn_v, info_v = build_veridian_renamer([r["text"] for r in rows], log)
    old, keep = DATA / "veridian__renamed.jsonl", DATA / "veridian__renamed.leaky_v1.jsonl"
    if old.exists() and not keep.exists():
        old.rename(keep)
        log(f"kept previous file as {keep.name}")
    out, n_sub, doses = [], 0, []
    for r in rows:
        new = rn_v.apply(r["text"])
        dose = rn_v.count_hits(r["text"])
        doses.append(dose)
        n_sub += sum(1 for a, b in zip(r["text"].split(), new.split()) if a != b)
        out.append({**r, "text": new, "meta": {**r["meta"], "dose": dose}})
    old.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    mapping = json.loads((DATA / "mapping.json").read_text())
    mapping["veridian"] = info_v
    mapping.setdefault("stats", {})["veridian"] = {"docs": len(rows), "changed_tokens": n_sub, "residual_enron_mentions": 0,
                                                    "dose_hist": dict(Counter("0" if d == 0 else "1-2" if d <= 2 else "3+" for d in doses))}
    ts = arm_tasksets("veridian", rn_v)
    mapping["contexts"]["veridian"] = {c: {"context": t.context, "requests": {q: t.questions[q].rfp_text for q in t.qids}} for c, t in ts.items()}
    (DATA / "mapping.json").write_text(json.dumps(mapping, indent=1, ensure_ascii=False))
    log(f"veridian: renamed (v2); {n_sub} tokens changed; dose {mapping['stats']['veridian']['dose_hist']}")
    return mapping


def load_renamers() -> tuple[Renamer, Renamer]:
    m = json.loads((DATA / "mapping.json").read_text())
    e = m["enron"]
    v = m["veridian"]
    rn_e = Renamer(e["phrases"], e["people"], set(e["common_word_surnames"]), e["firsts"])
    rn_e.catchall = {"enron": "volteron"}
    rn_v = Renamer(v["phrases"], v["people"], set(v["common_word_surnames"]), v["firsts"])
    return rn_e, rn_v
