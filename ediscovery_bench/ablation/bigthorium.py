"""Big Thorium — a sixth collection for the knowledge ablation: the Relativity aiR for Review demo workspace, distributed by
Relativity to customers and demo users (fictional company BigThorium, fictional City of Atlantis bribery investigation; see
data/bigthorium/raw/SOURCES.md). Public documents, invented case: between Veridian (private, invented) and CUAD (public, no case).

Like Veridian it is a *floor* for case knowledge: the matter is fictional, so no model can hold case knowledge from the news, so renaming should cost nothing beyond the
mechanical disruption of the substitution itself. Unlike Veridian it ships no usable gold (the demo coding has 18 positives in
1,000 documents and the aiR results are not in the archive), so the arm uses the study's panel-gold procedure (as Mallinckrodt
and Endo did): the three OpenAI models' *named* reviews vote, and every system is scored against a gold that excludes its own
votes (leave-one-out for the LLMs; the three-model majority for Jev). Agreement with the 1,000 human demo codes is reported as
a check.

Steps (all resumable, all behind `bench bigthorium-*`):
  sample   — 1,000-document stratified sample of the 2,091 (strata: matter keywords / off-matter control keywords / other)
  rename   — Big-Thorium-specific mapping on the v2 renamer (phrases + header-derived surnames); residual audit must be zero
  run      — named → (goldify) → renamed → brief, through the ordinary runner; spend recorded in data/ablation/round2_spend.json
  score    — P/R/F1 with cluster bootstrap CIs, named vs renamed per system, matter vs control requests, brief effect, figures
"""
from __future__ import annotations

import json
import random
import re
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from ..runner import job_path, load_predictions, run_job
from ..tasks import Document, TaskSet
from .build import DATA, ROOT, _ENGLISH_WORDS, renamed_taskset
from .names import COMMON_WORD_SURNAMES, ROLE_WORDS, Renamer, fake_surname
from .run import ALL_MODELS, JEV, LLM_MODELS, key_available
from .score import _clusters, boot_delta, contrast, flips, mcnemar, prf

ARM = "bigthorium"
BT = ROOT / "data" / "bigthorium"
ALL_DOCS = BT / "bigthorium_all.jsonl"
CRITERIA = BT / "air_criteria.json"
HUMAN = BT / "human_coding.json"
TASK = ROOT / "tasks" / "bigthorium.yaml"
SAMPLE = DATA / "bigthorium.jsonl"
RENAMED = DATA / "bigthorium__renamed.jsonl"
MAPPING = DATA / "bigthorium_mapping.json"
SAMPLING = DATA / "bigthorium_sampling.json"
BRIEF_PATH = DATA / "bigthorium_brief.md"
OUT = ROOT / "results" / "ablation" / ARM
RUNS_CORPUS = "runs"         # run_job writes OUT/runs/multi/<model>__<cond>__all.jsonl (outside the round-1 scorer's */multi glob)
FIG_DIR = ROOT / "results" / "contam" / "article" / "pr_options"
PANEL = list(LLM_MODELS)     # the three OpenAI models vote; Jev is scored against their majority
MATTER_Q = ["rfp01_atlantis_rfp", "rfp02_gifts", "rfp03_officials", "rfp04_contract", "rfp05_third_party", "rfp06_investigation"]
CONTROL_Q = ["rfp07_nuclear_compliance", "rfp08_remote_work"]
SEED = 20261006
N_SAMPLE = 1000
N_BRIEF = 300
RNG = np.random.default_rng(2026)

# ------------------------------------------------------------------------------------------------ sampling

MATTER_RE = re.compile(r"atlantis|eldorado|el dorado|\bRFP\b|\bGNS\b|Law Firm|Maskbook|brib|kickback|\bgift|Rolex|investigat|subpoena|\baudit", re.I)
CONTROL_RE = re.compile(r"nuclear|reactor|\bNRC\b|compliance|remote work|work from home|working from home|hybrid", re.I)


def all_rows() -> list[dict]:
    return [json.loads(l) for l in ALL_DOCS.read_text().split("\n") if l.strip()]


def stratum(row: dict) -> str:
    t = row["text"]
    if MATTER_RE.search(t):
        return "matter"
    if CONTROL_RE.search(t):
        return "control"
    return "other"


def build_sample(n: int = N_SAMPLE, seed: int = SEED, log=print) -> list[dict]:
    """Stratified sample: 65 % from documents that mention the matter's keywords (where the matter requests' positives live),
    15 % from documents that mention only the off-matter control topics, 20 % from the rest; the 18 human-coded positives are
    always included (they are in the matter stratum bar one). Empty documents are excluded. Order is shuffled (seeded)."""
    rows = [r for r in all_rows() if r["text"].strip()]
    rng = random.Random(seed)
    by = defaultdict(list)
    for r in rows:
        by[stratum(r)].append(r)
    quota = {"matter": int(round(n * 0.65)), "control": int(round(n * 0.15))}
    quota["other"] = n - quota["matter"] - quota["control"]
    picked: list[dict] = []
    detail = {}
    for s in ("matter", "control", "other"):
        pool = sorted(by[s], key=lambda r: r["id"])
        must = [r for r in pool if r["meta"].get("human_code") == "Responsive"]
        rest = [r for r in pool if r not in must]
        k = min(quota[s], len(pool))
        take = must + rng.sample(rest, max(0, k - len(must)))
        detail[s] = {"available": len(pool), "sampled": len(take), "human_positive_forced": len(must)}
        for r in take:
            r = dict(r)
            r["labels"] = {}
            r["gray"] = []
            r["meta"] = {**r["meta"], "stratum": s}
            picked.append(r)
    rng.shuffle(picked)
    SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in picked))
    info = {"n": len(picked), "seed": seed, "strata": detail, "matter_re": MATTER_RE.pattern, "control_re": CONTROL_RE.pattern,
            "human_coded_in_sample": sum(1 for r in picked if r["meta"].get("human_code")),
            "mean_chars": round(statistics.mean(len(r["text"]) for r in picked)), "at": time.strftime("%Y-%m-%d %H:%M")}
    SAMPLING.write_text(json.dumps(info, indent=1))
    log(f"sample: {len(picked)} docs  " + "  ".join(f"{s}={d['sampled']}/{d['available']}" for s, d in detail.items()))
    return picked


def sample_rows(path: Path = SAMPLE) -> list[dict]:
    return [json.loads(l) for l in path.read_text().split("\n") if l.strip()]


# ------------------------------------------------------------------------------------------------ renamer

# fictional → different fictional. Longest match wins (the Renamer sorts by length), so the compounds are safe beside the bare forms.
BT_PHRASES: dict[str, str] = {
    "Big Thorium, Inc.": "Vast Radium, Inc.", "BigThorium, Inc.": "VastRadium, Inc.", "Big Thorium": "Vast Radium", "BigThorium": "VastRadium",
    "BIGTHORIUM": "VASTRADIUM", "Thorium": "Radium", "THORIUM": "RADIUM",
    "bigthorium.com": "vastradium.com", "bigthorium.uk": "vastradium.uk", "bigthorium-press.com": "vastradium-press.com",
    "bigthorim.com": "vastradum.com", "bigthorium": "vastradium",
    "City of Atlantis": "City of Thalassa", "New Atlantis": "New Thalassa", "Atlantis Times": "Thalassa Times", "atlantistimes.com": "thalassatimes.com",
    "cityofatlantis.gov": "cityofthalassa.gov", "atlantiss.gov": "thalassaa.gov", "atlantis.gov": "thalassa.gov",
    "Atlantean": "Thalassan", "Atlantis": "Thalassa", "ATLANTIS": "THALASSA",
    "El Dorado": "Zerzura", "Eldorado": "Zerzura", "ELDORADO": "ZERZURA", "eldorado.gov": "zerzura.gov",
    "Law Firm X": "Law Firm K", "Firm X": "Firm K", "lawfirmx.com": "lawfirmk.com", "Law Firm A": "Law Firm M", "lawfirma.com": "lawfirmm.com",
    "GNS Partners": "HRT Partners", "gnspartners.com": "hrtpartners.com", "GNS": "HRT",
    "Little Big Energy": "Small Grand Power", "littlebigenergy.com": "smallgrandpower.com",
    "Maskbook": "Veilbook", "maskbook.com": "veilbook.com",
}
# surnames of the cast that a word list classes as ordinary words but that are, in this collection, almost only names: replaced
# wherever they appear capitalised (the Veridian v2 lesson — Feld, Rao — applied up front)
BT_FORCE_RARE = {"Clark", "Smith", "Baker", "Carter", "Archer", "Reed", "Thompson", "Roberts", "Williams", "Jenkins", "Simmons", "Maxwell",
                 "Mitchell", "Cooper", "Johnson", "Stewart", "Turner", "Coleman", "Adams", "Parker", "Patel", "Babuder", "Diaz", "Mason",
                 "Foster", "Davis", "Moore", "Fisher", "Bailey", "Brooks", "Allen", "Ross", "Nelson", "Russell", "Greene", "Butler", "Snyder",
                 "Watson", "Myers", "Ryan", "Garcia", "Wright", "Sanchez", "Edwards", "Jordan", "Barnes", "Wilson", "Lewis", "Murray",
                 "Ramirez", "Anderson", "Hayes", "Mills", "Collins", "Thomas", "Santos", "Knight", "Rogers", "Scott", "Torres", "Porter",
                 "Perry", "Campbell", "Jackson", "Wallace", "Taylor", "Richardson", "Martinez", "Hernandez", "Harris", "Walker", "Evans",
                 "Phillips", "Morris", "Cook", "Morgan", "Bennett", "Gray", "Hughes", "Kelly", "Howard", "Ward", "Cox", "Peterson",
                 "Robinson", "Gonzalez", "Lopez", "Rodriguez", "Reyes", "Flores", "Rivera", "Gomez", "Price", "Hart", "Ford", "Rice",
                 "Coffee", "Bass", "Fry"}
# display names in the headers that are mailboxes or roles, not people
NOT_PEOPLE = {"Newsletter", "Update", "Tracker", "Program", "Announcements", "Updates", "Alerts", "News", "Promotion", "Deals", "Invitations",
              "Requests", "Invite", "Airlines", "Digest", "Notifications", "Development", "Treasurer", "Representative", "Counsel", "Sales",
              "Specialist", "Operations", "Manager", "Officer", "Partner", "Now", "Times", "Team", "Support", "Office", "Desk",
              "Feedback", "Staff", "Participants", "Customer", "All", "Everyone", "Members", "Committee", "Board", "Group", "Reports", "Report"}
HDR_PAIR_RE = re.compile(r"([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-\.]+){1,3})\s*[\[<]\s*([\w.+'-]+)@([\w.-]+)")


def header_people(rows: list[dict]) -> tuple[Counter, Counter, dict[str, str], dict[str, str], set[str]]:
    """(surname → count, first name → count, e-mail local part → surname) from the From/To/CC header pairs 'First Last [local@domain]'.
    A display name counts as a person only when its surname (lower-cased) appears in the local part, which drops mailboxes
    ('HR Announcements [hr@…]') and catches the typo'd addresses separately (returned in the third element as local → surname)."""
    sur: Counter = Counter()
    first: Counter = Counter()
    odd: dict[str, str] = {}
    locals_: dict[str, str] = {}
    middles: set[str] = set()
    for r in rows:
        for f in ("from", "to", "cc"):
            for m in HDR_PAIR_RE.finditer(r.get("meta", {}).get(f) or ""):
                parts = m.group(1).replace("...", "").split()
                if len(parts) < 2:
                    continue
                s, fn, local = parts[-1].strip("."), parts[0], m.group(2).lower()
                if s in NOT_PEOPLE or s in ROLE_WORDS or fn in ROLE_WORDS or len(s) < 3:
                    continue
                if s.lower() in local:
                    sur[s] += 1
                    first[fn] += 1
                    locals_[local] = s
                    middles.update(parts[1:-1])
                elif re.fullmatch(r"[a-z]\.?[a-z]{4,}", local):
                    odd[local] = s  # mkuman → Kumar, ejacskon → Jackson
    return sur, first, odd, locals_, middles


def build_bt_renamer(rows: list[dict], log=print) -> tuple[Renamer, dict]:
    sur, first, odd, locals_, middles = header_people(rows)
    phrase_words = {w.lower() for k in BT_PHRASES for w in re.split(r"[\s,.]+", k) if w}
    taken = set(sur)  # a fake surname must not be another real person's name in this collection
    people: dict[str, str] = {}
    for s, _ in sorted(sur.items(), key=lambda kv: (-kv[1], kv[0])):
        if s.lower() in phrase_words:
            continue
        people[s] = fake_surname(s, taken)
    # body full names "First Last" whose first name is a known header first name and whose surname is new (signatures of people who
    # never appear in a header), kept when seen at least twice
    firsts = {f for f in first if f not in ROLE_WORDS and f not in NOT_PEOPLE and f.lower() not in phrase_words}
    body_full = re.compile(r"\b(" + "|".join(re.escape(f) for f in sorted(firsts, key=len, reverse=True)) + r")\s+([A-Z][a-z]{2,})\b")
    extra: Counter = Counter()
    for r in rows:
        for _, s in body_full.findall(r["text"]):
            if s not in people and s not in NOT_PEOPLE and s not in ROLE_WORDS and s.lower() not in phrase_words and s not in firsts and s not in middles:
                extra[s] += 1
    for s, n in extra.items():
        if n >= 2 and s.lower() not in _ENGLISH_WORDS:
            people[s] = fake_surname(s, taken)
    common = ({s for s in people if s.lower() in _ENGLISH_WORDS} | (set(people) & COMMON_WORD_SURNAMES)) - BT_FORCE_RARE
    rn = _single_line_full_names(Renamer(BT_PHRASES, people, common, sorted(firsts)))
    # typo'd local parts (mkuman@, ejacskon@) and the few first-initial variants the generic e-mail pass cannot see
    rn.catchall = {loc: loc[0] + people[s].lower() for loc, s in odd.items() if s in people}
    # surnames that are also first names (James, Thomas, Alexander) are replaced in name positions only, and the generic e-mail pass
    # skips them on purpose; their actual local parts (ejames@) are therefore mapped one by one
    for loc, s in locals_.items():
        if s in people and s in firsts:
            rn.catchall[loc] = re.sub(re.escape(s.lower()), people[s].lower(), loc)
    info = {"phrases": BT_PHRASES, "people": people, "common_word_surnames": sorted(common & set(people)), "firsts": sorted(firsts),
            "catchall": rn.catchall, "header_surnames_found": len(sur), "body_surnames_added": sorted(s for s, n in extra.items() if n >= 2 and s.lower() not in _ENGLISH_WORDS),
            "version": 2, "note": "Big Thorium mapping on the v2 renamer (2026-10-06): header 'Name [local@domain]' pairs define the people; "
                                  "the cast's common-word surnames are forced rare; typo'd local parts mapped by catch-all."}
    log(f"bigthorium mapping: {len(BT_PHRASES)} phrases, {len(people)} surnames ({len(common & set(people))} common-word), {len(firsts)} first names")
    return rn, info


def _single_line_full_names(rn: Renamer) -> Renamer:
    """The engine's full-name pattern lets the whitespace between first and last name span a line break, which on this collection
    joins a sign-off first name to the full name on the next line ("James\n\nJames Brown" → "James Forsing Brown" when James is
    also a surname). Here the two parts must sit on one line. (Local to this arm; the other arms' files are frozen as built.)"""
    if rn.full_re is not None:
        rn.full_re = re.compile(rn.full_re.pattern.replace(r")\s+(", r")[ \t]+("))
    return rn


def load_bt_renamer() -> Renamer:
    m = json.loads(MAPPING.read_text())
    rn = _single_line_full_names(Renamer(m["phrases"], m["people"], set(m["common_word_surnames"]), m["firsts"]))
    rn.catchall = m.get("catchall", {})
    return rn


def rename_row(r: dict, rn: Renamer) -> dict:
    out = dict(r)
    out["text"] = rn.apply(r["text"])
    meta = dict(r.get("meta") or {})
    for k in ("from", "to", "cc", "subject"):
        if meta.get(k):
            meta[k] = rn.apply(meta[k])
    meta["dose"] = rn.count_hits(r["text"])
    out["meta"] = meta
    return out


def audit(named: list[dict], renamed: list[dict], info: dict, log=print) -> dict:
    """Residual audit of the renamed texts: original phrases (any case), mapped surnames capitalised anywhere, mapped surnames
    inside e-mail-like tokens, original domains. The common-word surnames are reported separately with contexts (they are
    replaced only in name positions by design), everything else must be zero before the renamed run."""
    phrases = sorted(info["phrases"], key=len, reverse=True)
    phrase_re = re.compile("|".join(rf"(?<![A-Za-z0-9]){re.escape(k)}(?![A-Za-z0-9])" for k in phrases), re.I)
    people = info["people"]
    firsts = set(info["firsts"])
    common = set(info["common_word_surnames"])
    rare = [s for s in people if s not in common and s not in set(info["firsts"])]
    rare_re = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(s) for s in sorted(rare, key=len, reverse=True)) + r")(?![A-Za-z0-9])")
    comm_re = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(s) for s in sorted(common, key=len, reverse=True)) + r")(?![A-Za-z0-9])") if common else None
    email_re = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+")
    hits: dict[str, Counter] = {"phrase": Counter(), "rare_surname": Counter(), "email_local": Counter(), "common_surname": Counter()}
    contexts: dict[str, list[str]] = defaultdict(list)
    docs_hit: Counter = Counter()
    for r0, r1 in zip(named, renamed):
        t = r1["text"] + "\n" + " ".join(str(r1["meta"].get(k) or "") for k in ("from", "to", "cc", "subject"))
        for m in phrase_re.finditer(t):
            hits["phrase"][m.group(0)] += 1
            docs_hit["phrase"] += 1
            if len(contexts["phrase"]) < 40:
                contexts["phrase"].append(t[max(0, m.start() - 60): m.end() + 60].replace("\n", " "))
        for m in rare_re.finditer(t):
            if m.group(1)[0].isupper():
                hits["rare_surname"][m.group(1)] += 1
                if len(contexts["rare_surname"]) < 40:
                    contexts["rare_surname"].append(t[max(0, m.start() - 60): m.end() + 60].replace("\n", " "))
        for m in email_re.finditer(t):
            local = m.group(0).split("@")[0].lower()
            for s in people:
                sl = s.lower()
                if s in firsts:
                    continue  # James, Howard, Thomas: a first name in an address; the real local parts are in the catch-all list
                if len(sl) >= 4 and re.search(rf"(?<![a-z][a-z]){re.escape(sl)}(?![a-z])", local) or (len(sl) == 3 and re.search(rf"(?<![a-z][a-z]){re.escape(sl)}$", local)):
                    hits["email_local"][m.group(0).lower()] += 1
                    if len(contexts["email_local"]) < 40:
                        contexts["email_local"].append(m.group(0))
        for loc in info.get("catchall", {}):
            n_c = len(re.findall(re.escape(loc), t, re.I))
            if n_c:
                hits["email_local"][loc] += n_c
        if comm_re:
            for m in comm_re.finditer(t):
                hits["common_surname"][m.group(1)] += 1
                if len(contexts["common_surname"]) < 80:
                    contexts["common_surname"].append(t[max(0, m.start() - 50): m.end() + 50].replace("\n", " "))
    doses = [r["meta"].get("dose", 0) for r in renamed]
    out = {"n_docs": len(renamed), "residuals": {k: sum(v.values()) for k, v in hits.items()}, "top": {k: v.most_common(25) for k, v in hits.items()},
           "contexts": dict(contexts), "dose_mean": round(statistics.mean(doses), 1) if doses else 0, "dose_zero_docs": sum(1 for d in doses if d == 0),
           "at": time.strftime("%Y-%m-%d %H:%M")}
    log("audit residuals: " + ", ".join(f"{k}={v}" for k, v in out["residuals"].items()) + f"; mean dose {out['dose_mean']}")
    return out


def build_renamed(log=print) -> dict:
    rows = sample_rows()
    rn, info = build_bt_renamer(rows, log=log)
    MAPPING.write_text(json.dumps(info, indent=1, ensure_ascii=False))
    renamed = [rename_row(r, rn) for r in rows]
    RENAMED.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in renamed))
    rep = audit(rows, renamed, info, log=log)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "renamer_audit.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    return rep


# ------------------------------------------------------------------------------------------------ task sets and the brief

def taskset(cond: str) -> TaskSet:
    ts = TaskSet.load(TASK)
    if cond == "named":
        return ts
    if cond == "renamed":
        return renamed_taskset(ts, load_bt_renamer())
    if cond == "brief":
        return TaskSet(name=ts.name + "__brief", context=ts.context + "\n\n" + brief_text().strip(), questions=ts.questions,
                       positive_label=ts.positive_label, negative_label=ts.negative_label, gate_question=ts.gate_question, source=ts.source)
    raise ValueError(cond)


def brief_text() -> str:
    """The brief is Relativity's own aiR for Review case summary for the demo (the latest prompt-criteria version in the archive),
    rendered section by section — i.e. exactly the background a reviewer, or aiR itself, is given for this matter."""
    if BRIEF_PATH.exists():
        return BRIEF_PATH.read_text()
    c = json.loads(CRITERIA.read_text())["latest"]
    cs = c["case_summary"]
    titles = {"matterOverview": "Matter overview", "peopleAndAliases": "People and aliases", "noteworthyTerms": "Noteworthy terms",
              "dateRange": "Relevant period", "privilegeAndWorkProduct": "Privilege and work product"}
    parts = ["Case brief (the review protocol's case summary, as supplied to reviewers):"]
    for k, v in cs.items():
        if isinstance(v, str) and v.strip():
            parts.append(f"{titles.get(k, k)}:\n{v.strip()}")
    parts.append("Relevance criteria:\n" + (c["criteria"] if isinstance(c["criteria"], str) else json.dumps(c["criteria"])))
    text = "\n\n".join(parts) + "\n"
    BRIEF_PATH.write_text(text)
    return text


def _docs(rows: list[dict]) -> list[Document]:
    return [Document(id=r["id"], text=r["text"], labels=r.get("labels") or {}, gray=frozenset(r.get("gray") or []), meta=r.get("meta") or {}) for r in rows]


def cond_rows(cond: str) -> list[dict]:
    rows = sample_rows(RENAMED if cond == "renamed" else SAMPLE)
    if cond == "brief":
        ids = set(json.loads(SAMPLING.read_text()).get("brief_subset", []))
        rows = [r for r in rows if r["id"] in ids]
    return rows


# ------------------------------------------------------------------------------------------------ panel gold

def result_file(model: str, cond: str) -> Path:
    return job_path(OUT, RUNS_CORPUS, "multi", model, f"{cond}__all")


def votes(cond: str = "named") -> dict[tuple[str, str], dict[str, tuple[str, float]]]:
    """(doc, question) → {panel model: (label, p_positive)} from the panel's runs of one condition."""
    out: dict = defaultdict(dict)
    for m in PANEL:
        f = result_file(m, cond)
        if not f.exists():
            continue
        for p in load_predictions(f):
            if not p.error and p.label:
                out[(p.doc_id, p.question)][m] = (p.label, p.p_positive)
    return out


def majority(vs: dict[str, tuple[str, float]], exclude: str | None = None) -> tuple[int | None, bool]:
    """(gold 0/1 or None, gray). Majority of the votes not from `exclude`; gray when they split or the mean p is in [0.35, 0.65]
    (the study's goldify rule). With two voters (leave-one-out) a split is a gray — the pair is not scored for that system."""
    vv = [(lab, p) for m, (lab, p) in vs.items() if m != exclude]
    if not vv:
        return None, True
    yes = sum(1 for lab, _ in vv if lab == "responsive")
    mean_p = sum(p for _, p in vv) / len(vv)
    gold = 1 if yes * 2 > len(vv) else 0 if yes * 2 < len(vv) else None
    gray = gold is None or 0.35 <= mean_p <= 0.65
    return gold, gray


def goldify(log=print) -> dict:
    """Write the three-model majority labels (goldify rule) into the sample and the renamed file, so the later conditions carry a
    gold in their prediction rows (the scorer recomputes leave-one-out gold itself). Also picks the brief subset."""
    vs = votes("named")
    missing = [m for m in PANEL if not result_file(m, "named").exists()]
    if missing:
        raise RuntimeError(f"named runs missing for {missing}")
    labels: dict[str, dict[str, str]] = defaultdict(dict)
    gray: dict[str, set[str]] = defaultdict(set)
    panel: dict[str, dict[str, dict]] = defaultdict(dict)
    for (d, q), v in vs.items():
        g, gr = majority(v)
        if g == 1:
            labels[d][q] = "responsive"
        if gr:
            gray[d].add(q)
        panel[d][q] = {m: round(p, 3) for m, (_, p) in v.items()}
    for path in (SAMPLE, RENAMED):
        if not path.exists():
            continue
        rows = sample_rows(path)
        for r in rows:
            r["labels"] = labels.get(r["id"], {})
            r["gray"] = sorted(gray.get(r["id"], set()))
            r["meta"]["panel"] = panel.get(r["id"], {})
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    rows = sample_rows(SAMPLE)
    n_pos = Counter(q for r in rows for q in r["labels"])
    n_gray = Counter(q for r in rows for q in r["gray"])
    log("panel gold: " + "  ".join(f"{q}: +{n_pos.get(q, 0)}/gray {n_gray.get(q, 0)}" for q in TaskSet.load(TASK).qids))
    # brief subset: every document with a matter-request positive (non-gray) first, then random negatives, to N_BRIEF
    rng = random.Random(SEED + 1)
    pos = sorted(r["id"] for r in rows if any(q in r["labels"] and q not in r["gray"] for q in MATTER_Q))
    neg = sorted(r["id"] for r in rows if r["id"] not in set(pos))
    rng.shuffle(pos)
    rng.shuffle(neg)
    sub = pos[: int(N_BRIEF * 2 / 3)]
    sub += neg[: N_BRIEF - len(sub)]
    info = json.loads(SAMPLING.read_text())
    info["brief_subset"] = sorted(sub)
    info["brief_subset_detail"] = {"n": len(sub), "matter_positive_docs_available": len(pos), "positives_taken": sum(1 for d in sub if d in set(pos)),
                                   "rule": "two thirds documents with a non-gray matter-request positive, one third random others"}
    info["panel"] = {"models": PANEL, "positives": dict(n_pos), "gray": dict(n_gray), "rule": "majority; gray when split or mean p in [0.35, 0.65]"}
    SAMPLING.write_text(json.dumps(info, indent=1))
    log(f"brief subset: {len(sub)} docs ({info['brief_subset_detail']['positives_taken']} with a matter positive)")
    return info


# ------------------------------------------------------------------------------------------------ cost and runs

def estimate(n_docs: int | None = None, log=print) -> dict:
    """Per-condition, per-model paid cost from the realised Veridian per-call token means (round2._veridian_obs), scaled to this
    arm's 8 questions and its mean document length; the ratio realised/estimated on the Veridian v2 renamed re-run is applied."""
    from .round2 import _veridian_obs, call_cost, estimate_runs  # noqa: PLC0415
    o = _veridian_obs()
    ts = TaskSet.load(TASK)
    q = len(ts.qids) / len(TaskSet.load(ROOT / "tasks" / "veridian.yaml").qids)
    rows = sample_rows() if SAMPLE.exists() else all_rows()
    n = n_docs or len(rows)
    d_tok = statistics.mean(len(r["text"]) for r in rows) / 4
    prompt_in, jev_prompt = (o["in"] - o["doc_chars"] / 4) * q, (o["jev_in"] - o["doc_chars"] / 4) * q
    # realised/estimate calibration from the Veridian renamed re-run (the ledger step) against estimate_runs' Veridian figure
    spend = json.loads((DATA / "round2_spend.json").read_text()) if (DATA / "round2_spend.json").exists() else {"steps": []}
    rerun = next((s for s in spend["steps"] if s["step"].startswith("rerun:veridian:renamed")), None)
    est_v = estimate_runs().get("veridian", {}).get("renamed", {})
    calib = 1.0
    if rerun and est_v:
        e = sum(v["paid"] for m, v in est_v.items() if m != JEV)
        calib = rerun["realised_usd"] / e if e else 1.0
    brief_tok = len(brief_text()) / 4
    out = {"n_docs": n, "doc_tokens": round(d_tok), "calibration": round(calib, 3), "conditions": {}}
    for cond, nd in (("named", n), ("renamed", n), ("brief", min(n, N_BRIEF))):
        out["conditions"][cond] = {}
        for m in ALL_MODELS:
            extra = brief_tok if cond == "brief" else 0
            if m == JEV:
                paid, _ = call_cost(m, jev_prompt + d_tok + extra, 0, o["jev_out"] * q)
            else:
                paid, _ = call_cost(m, prompt_in + d_tok + extra, o["cached"] * q + extra, o["out"] * q)  # the brief sits in the cached prefix
            out["conditions"][cond][m] = round(paid * nd * calib, 3)
        out["conditions"][cond]["total"] = round(sum(out["conditions"][cond][m] for m in ALL_MODELS), 2)
    out["total"] = round(sum(c["total"] for c in out["conditions"].values()), 2)
    log(f"estimate ({n} docs, {round(d_tok)} doc tokens, calibration ×{calib:.2f}): " + "; ".join(f"{c} ${v['total']}" for c, v in out["conditions"].items()) + f"; total ${out['total']}")
    return out


async def run(conditions: list[str], models: list[str] | None = None, limit: int | None = None, concurrency: int | None = None, log=print) -> dict:
    from .round2 import dedupe, record_spend  # noqa: PLC0415
    models = models or ALL_MODELS
    live = [m for m in models if key_available(m)]
    for m in models:
        if m not in live:
            log(f"[pending] {m}: key not set — skipped")
    est = estimate(log=lambda *_: None)
    spent: Counter = Counter()
    t0 = time.time()
    for cond in conditions:
        ts = taskset(cond)
        docs = _docs(cond_rows(cond))
        if limit:
            docs = docs[:limit]
        for m in live:
            tag = f"{cond}__all" + (f"__pilot{limit}" if limit else "")
            path = job_path(OUT, RUNS_CORPUS, "multi", m, tag)
            dedupe(path, log=log)
            before = {(p.doc_id, p.question) for p in load_predictions(path) if not p.error} if path.exists() else set()
            preds = await run_job(ts, docs, m, "multi", OUT, RUNS_CORPUS, concurrency=concurrency, tag=tag, log=log)
            ok = [p for p in preds if not p.error]
            new = [p for p in ok if (p.doc_id, p.question) not in before]
            paid_new = sum(p.cost_usd for p in new)
            spent[m] += paid_new
            realised = sum(p.cost_usd for p in ok)
            e = est["conditions"].get(cond, {}).get(m)
            if not limit:
                record_spend(f"bigthorium:run:{cond}:{m}", e, realised, {"rows": len(ok), "docs": len({p.doc_id for p in ok})})
            log(f"  bigthorium/{cond}/{m}: {len(ok)} rows ({len(new)} new), paid ${realised:.3f}" + (f" vs est ${e:.3f} ({realised / e:.0%})" if e else ""))
    log(f"bigthorium run: paid ${sum(spent.values()):.2f} new in {time.time() - t0:.0f}s")
    return {"spent": dict(spent), "total": round(sum(spent.values()), 4)}


# ------------------------------------------------------------------------------------------------ scoring

def _preds(model: str, cond: str) -> dict[tuple[str, str], tuple[int, float, float]]:
    f = result_file(model, cond)
    if not f.exists():
        return {}
    return {(p.doc_id, p.question): (1 if p.label == "responsive" else 0, p.p_positive, p.cost_usd) for p in load_predictions(f) if not p.error and p.label}


def gold_for(model: str, vs) -> dict[tuple[str, str], int]:
    """Leave-one-out gold for a panel member (the other two must agree and not be in the gray band); the full majority for Jev."""
    out = {}
    for k, v in vs.items():
        g, gr = majority(v, exclude=model if model in PANEL else None)
        if g is not None and not gr:
            out[k] = g
    return out


def _stats(gold: np.ndarray, pred: np.ndarray, clusters, nb: int = 1000) -> dict:
    """Point P/R/F1 with cluster-bootstrap percentile CIs (for the precision–recall figure)."""
    base = prf(gold, pred)
    nC = len(clusters)
    s = np.empty((nb, 3))
    for i in range(nb):
        pick = RNG.integers(0, nC, nC)
        idx = np.concatenate([clusters[j] for j in pick])
        r = prf(gold[idx], pred[idx])
        s[i] = (r["precision"], r["recall"], r["f1"])
    ci = {}
    for j, nm in enumerate(("precision", "recall", "f1")):
        col = s[:, j][~np.isnan(s[:, j])]
        ci[nm] = (base[nm], float(np.percentile(col, 2.5)) if len(col) else None, float(np.percentile(col, 97.5)) if len(col) else None)
    return {**base, "ci": ci}


def compare(model: str, a_cond: str, b_cond: str, vs, restrict: set[str] | None = None) -> dict | None:
    A, Bm = _preds(model, a_cond), _preds(model, b_cond)
    gold = gold_for(model, vs)
    keys = sorted(k for k in set(A) & set(Bm) & set(gold) if restrict is None or k[0] in restrict)
    if not keys:
        return None
    g = np.array([gold[k] for k in keys]); a = np.array([A[k][0] for k in keys]); b = np.array([Bm[k][0] for k in keys])
    qs = np.array([k[1] for k in keys])
    res = {"n_pairs": len(keys), "n_docs": len({k[0] for k in keys}), "n_unscored_split": len(set(A) & set(Bm)) - len(set(A) & set(Bm) & set(gold)),
           "cost_usd": {a_cond: round(sum(A[k][2] for k in keys), 4), b_cond: round(sum(Bm[k][2] for k in keys), 4)}, "topics": {}}
    cl = _clusters(keys)
    res[a_cond] = _stats(g, a, cl); res[b_cond] = _stats(g, b, cl)
    res["delta"], samples = boot_delta(g, a, b, cl)
    res["_samples"] = samples
    res["mcnemar"] = mcnemar(a == g, b == g)
    res["flips"] = flips(g, a, b)
    res["label_changed_share"] = float((a != b).mean())
    # how marginal were the documents whose label changed? (a decision model sitting near its threshold moves on surface tokens)
    pa = np.array([A[k][1] for k in keys]); pb = np.array([Bm[k][1] for k in keys])
    ch = np.where(a != b)[0]
    res["changed_pairs"] = {"n": int(len(ch)), "near_threshold_named_p_share": float((np.abs(pa[ch] - 0.5) < 0.1).mean()) if len(ch) else None,
                            "mean_abs_p_shift": float(np.abs(pb[ch] - pa[ch]).mean()) if len(ch) else None,
                            "examples": [{"doc": keys[i][0], "q": keys[i][1], "gold": int(g[i]), "p_named": round(float(pa[i]), 3), "p_" + b_cond: round(float(pb[i]), 3)} for i in ch[:12]]}
    for grp, qset in (("matter", MATTER_Q), ("control", CONTROL_Q)):
        gi = np.where(np.isin(qs, qset))[0]
        if len(gi) < 10:
            continue
        d, s = boot_delta(g[gi], a[gi], b[gi], _clusters([keys[i] for i in gi]))
        res[grp] = {"n_pairs": int(len(gi)), a_cond: prf(g[gi], a[gi]), b_cond: prf(g[gi], b[gi]), "delta": d, "_samples": s, "flips": flips(g[gi], a[gi], b[gi]),
                    "mcnemar": mcnemar(a[gi] == g[gi], b[gi] == g[gi])}
    if "matter" in res and "control" in res:
        res["knowledge_effect"] = contrast(res["matter"]["_samples"], res["control"]["_samples"], res["matter"]["delta"], res["control"]["delta"])
    for q in sorted(set(qs)):
        qi = np.where(qs == q)[0]
        d, _ = boot_delta(g[qi], a[qi], b[qi], _clusters([keys[i] for i in qi]), nb=500)
        res["topics"][q] = {"n": int(len(qi)), a_cond: prf(g[qi], a[qi]), b_cond: prf(g[qi], b[qi]), "delta": d, "flips": flips(g[qi], a[qi], b[qi])}
    return res


def human_check(vs, log=print) -> dict:
    """Document-level agreement of the panel gold and each system's named review with the demo's human coding (Responsive /
    Not Responsive per document): a document is 'responsive' when any matter request is positive."""
    rows = {r["id"]: r for r in sample_rows()}
    coded = {d: r["meta"]["human_code"] for d, r in rows.items() if r["meta"].get("human_code")}
    out = {"n_coded_in_sample": len(coded), "n_human_positive": sum(1 for v in coded.values() if v == "Responsive"), "systems": {}}

    def doc_level(pred_fn) -> dict:
        tp = fp = fn = tn = 0
        for d, code in coded.items():
            pr = pred_fn(d)
            if pr is None:
                continue
            h = code == "Responsive"
            tp += pr and h; fp += pr and not h; fn += (not pr) and h; tn += (not pr) and not h
        P = tp / (tp + fp) if tp + fp else None; R = tp / (tp + fn) if tp + fn else None
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": P, "recall": R, "panel_positive_rate": (tp + fp) / max(1, tp + fp + fn + tn)}

    def panel_pred(d):
        qs = [q for q in MATTER_Q if (d, q) in vs]
        if not qs:
            return None
        return any(majority(vs[(d, q)])[0] == 1 for q in qs)
    out["panel"] = doc_level(panel_pred)
    for m in ALL_MODELS:
        for cond in ("named", "renamed"):
            P = _preds(m, cond)
            if not P:
                continue
            out["systems"][f"{m}:{cond}"] = doc_level(lambda d: any(P.get((d, q), (0,))[0] == 1 for q in MATTER_Q) if any((d, q) in P for q in MATTER_Q) else None)
    log(f"human check: {out['n_coded_in_sample']} coded docs in sample, {out['n_human_positive']} human positives; panel doc-level recall "
        f"{out['panel']['recall']}, precision {out['panel']['precision']}")
    return out


def _strip(d):
    if isinstance(d, dict):
        return {k: _strip(v) for k, v in d.items() if not k.startswith("_")}
    if isinstance(d, list):
        return [_strip(x) for x in d]
    if isinstance(d, float) and np.isnan(d):
        return None
    if isinstance(d, (np.floating, np.integer)):
        return d.item()
    return d


def score(log=print) -> dict:
    vs = votes("named")
    brief_ids = set(json.loads(SAMPLING.read_text()).get("brief_subset", [])) if SAMPLING.exists() else set()
    summary: dict = {"arm": ARM, "n_docs": len({d for d, _ in vs}), "panel": PANEL, "gold_rule": "leave-one-out majority of the other panel members (LLMs); three-model majority (Jev); split or mean p in [0.35, 0.65] unscored",
                     "rename": {}, "brief": {}, "sampling": json.loads(SAMPLING.read_text()) if SAMPLING.exists() else {}}
    for m in ALL_MODELS:
        r = compare(m, "named", "renamed", vs)
        if r:
            summary["rename"][m] = r
            d = r["delta"]["f1"]; ke = r.get("knowledge_effect", {}).get("f1", {})
            log(f"rename {m:14s} n={r['n_pairs']:5d}  F1 {100 * r['named']['f1']:.1f} → {100 * r['renamed']['f1']:.1f}  Δ {100 * d['delta']:+.1f} [{100 * d['lo']:+.1f}, {100 * d['hi']:+.1f}]"
                + (f"  knowledge effect {100 * ke['delta']:+.1f} [{100 * ke['lo']:+.1f}, {100 * ke['hi']:+.1f}]" if ke and ke.get("delta") is not None else ""))
        if brief_ids:
            b = compare(m, "named", "brief", vs, restrict=brief_ids)
            if b:
                summary["brief"][m] = b
                d = b["delta"]["f1"]
                log(f"brief  {m:14s} n={b['n_pairs']:5d}  F1 {100 * b['named']['f1']:.1f} → {100 * b['brief']['f1']:.1f}  Δ {100 * d['delta']:+.1f} [{100 * d['lo']:+.1f}, {100 * d['hi']:+.1f}]")
    summary["human_check"] = human_check(vs, log=log)
    spend = json.loads((DATA / "round2_spend.json").read_text())
    steps = [s for s in spend["steps"] if s["step"].startswith("bigthorium:")]
    summary["spend"] = {"steps": steps, "total_realised_usd": round(sum(s["realised_usd"] for s in steps), 2)}
    # Veridian, for the floor-vs-floor comparison
    s1 = ROOT / "results" / "ablation" / "summary.json"
    if s1.exists():
        v = json.loads(s1.read_text()).get("arms", {}).get("veridian", {}).get("per_model", {})
        summary["veridian_delta_f1"] = {m: (x.get("delta") or {}).get("f1") for m, x in v.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(_strip(summary), indent=1))
    figures(summary, log=log)
    (OUT / "REPORT.md").write_text(report(summary))
    log(f"wrote {OUT / 'summary.json'}, {OUT / 'REPORT.md'}")
    return summary


# ------------------------------------------------------------------------------------------------ figures (same style as pr_options.py)

SYSTEMS = [("gpt-5.6-luna", "GPT-5.6 Luna"), ("gpt-5.6-terra", "GPT-5.6 Terra"), ("gpt-5.6-sol", "GPT-5.6 Sol"), ("jev@base", "Jev (decision model)")]
COLORS = {"gpt-5.6-luna": "#4C78A8", "gpt-5.6-terra": "#F58518", "gpt-5.6-sol": "#54A24B", "jev@base": "#B279A2"}


def _small_multiples(fname: Path, data: dict, title: str, cap: str, cond_names: tuple[str, str], conds: tuple[str, str]):
    import textwrap  # noqa: PLC0415
    import matplotlib  # noqa: PLC0415
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415
    from matplotlib.lines import Line2D  # noqa: PLC0415
    from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: PLC0415

    def ci(d, nm):
        return d[nm]["ci"] if "ci" in d[nm] else None

    xs, ys = [], []
    for key in data:
        for c in conds:
            s = data[key][c]["ci"]
            xs += [s["recall"][1], s["recall"][2]]; ys += [s["precision"][1], s["precision"][2]]
    pad = 0.025
    xlim = (max(0, min(xs) - pad), min(1.0, max(xs) + pad)); ylim = (max(0, min(ys) - pad), min(1.0, max(ys) + pad))
    fig, axes = plt.subplots(2, 2, figsize=(10, 8.6), dpi=160, sharex=True, sharey=True)
    for ax, (key, lab) in zip(axes.flat, SYSTEMS):
        r = np.linspace(0.3, 1.0, 400)
        for f in (70, 75, 80, 85, 90, 95):
            F = f / 100; p = F * r / (2 * r - F); ok = (p > 0) & (p <= 1.05) & (2 * r - F > 0)
            ax.plot(r[ok], p[ok], ls="--", lw=0.7, color="#bbbbbb", zorder=0)
            rr, pp = r[ok], p[ok]; inside = (rr >= xlim[0]) & (rr <= xlim[1]) & (pp >= ylim[0]) & (pp <= ylim[1])
            if inside.any():
                i = np.where(inside)[0][-1]
                ax.annotate(f"F1 {f}", (rr[i], pp[i]), fontsize=8, color="#999999", ha="right", va="bottom", xytext=(-2, 2), textcoords="offset points")
        ax.set_xlim(*xlim); ax.set_ylim(*ylim)
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.grid(True, lw=0.4, color="#eeeeee", zorder=0)
        if key not in data:
            ax.text(0.5, 0.5, "not run", transform=ax.transAxes, ha="center", va="center", fontsize=10, color="#777")
            ax.set_title(lab, fontsize=11, loc="left", fontweight="bold", color="#999")
            continue
        a, b = data[key][conds[0]]["ci"], data[key][conds[1]]["ci"]; c = COLORS[key]
        for d, al in ((a, 0.18), (b, 0.10)):
            ax.add_patch(Rectangle((d["recall"][1], d["precision"][1]), d["recall"][2] - d["recall"][1], d["precision"][2] - d["precision"][1],
                                   facecolor=c, edgecolor=c, alpha=al, lw=0.8, zorder=1))
        ax.add_patch(FancyArrowPatch((a["recall"][0], a["precision"][0]), (b["recall"][0], b["precision"][0]), arrowstyle="-|>", mutation_scale=14,
                                     color=c, lw=1.6, zorder=3, shrinkA=5, shrinkB=5))
        ax.scatter([a["recall"][0]], [a["precision"][0]], s=70, color=c, edgecolor="white", lw=1, zorder=4)
        ax.scatter([b["recall"][0]], [b["precision"][0]], s=70, facecolor="white", edgecolor=c, lw=1.8, zorder=4)
        ax.set_title(lab, fontsize=11, loc="left", fontweight="bold", color=c)
        dF = 100 * (b["f1"][0] - a["f1"][0])
        ax.text(0.98, 0.04, f"F1 {100 * a['f1'][0]:.1f} → {100 * b['f1'][0]:.1f} ({dF:+.1f})", transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color="#444")
    for ax in axes[1]:
        ax.set_xlabel("Recall")
    for ax in axes[:, 0]:
        ax.set_ylabel("Precision")
    h = [Line2D([], [], marker="o", color="#555", ls="", ms=8, label=cond_names[0]),
         Line2D([], [], marker="o", mfc="white", mec="#555", color="#555", ls="", ms=8, mew=1.8, label=cond_names[1]),
         Line2D([], [], color="#555", lw=6, alpha=0.25, label="95% CI")]
    axes[0, 0].legend(handles=h, loc="lower left", frameon=False, fontsize=9)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.005, "\n".join(textwrap.wrap(cap, 150)), fontsize=8.5, color="#666666", ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fname.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fname, facecolor="white"); plt.close(fig)


def figures(summary: dict, log=print):
    rn = summary.get("rename", {})
    if rn:
        any_r = next(iter(rn.values()))
        cap = (f"Big Thorium (the Relativity aiR for Review demo workspace: public documents, invented case), {any_r['n_docs']} e-mails × 8 requests (6 on the matter, 2 off-matter controls) = up to "
               f"{any_r['n_pairs']} scored relevance calls per system per condition, reviewed with the original invented names and then with every company, "
               f"city, firm and person renamed again. Gold: the other panel members' unanimous named votes (leave-one-out; three-model majority for Jev); "
               f"split votes are not scored. Shaded boxes are 95% bootstrap intervals (1,000 resamples over e-mails). Dashed curves: constant F1.")
        _small_multiples(FIG_DIR / "bigthorium_rename.png", rn, "Big Thorium: invented names → renamed again", cap, ("Original names", "Renamed"), ("named", "renamed"))
        log(f"wrote {FIG_DIR / 'bigthorium_rename.png'}")
    br = summary.get("brief", {})
    if br:
        any_b = next(iter(br.values()))
        cap = (f"Big Thorium, {any_b['n_docs']} e-mails (positive-enriched subset) × 8 requests = up to {any_b['n_pairs']} scored relevance calls per system per condition, "
               f"reviewed without and then with Relativity's own aiR case summary for the matter in the prompt (~{len(brief_text().split())} words). On a synthetic set the brief is the only "
               f"possible source of case knowledge. Gold as in the renaming figure (panel votes cast without the brief). Shaded boxes are 95% bootstrap intervals over e-mails.")
        _small_multiples(FIG_DIR / "bigthorium_brief.png", br, "Big Thorium: without case brief → with case brief", cap, ("Without brief", "With brief"), ("named", "brief"))
        log(f"wrote {FIG_DIR / 'bigthorium_brief.png'}")


# ------------------------------------------------------------------------------------------------ report

def _fmt(d: dict | None) -> str:
    if not d or d.get("delta") is None:
        return "—"
    return f"{100 * d['delta']:+.1f} [{100 * d['lo']:+.1f}, {100 * d['hi']:+.1f}]"


def report(s: dict) -> str:
    L = [f"# Big Thorium arm — results\n", "Big Thorium is the Relativity aiR for Review demo workspace, distributed by Relativity to customers and demo users: public documents, invented case "
         "(between Veridian — private, invented — and CUAD — public, no case). The matter is fictional, so there is nothing to know from the news; the e-mails circulate widely among "
         "Relativity users and could have been crawled. The contamination probes (`results/contam/bigthorium_summary.json`) found no recitation (longest shared runs 3–4 words), "
         "recognition or recall of its facts in any model.\n",
         f"Generated {time.strftime('%Y-%m-%d %H:%M')}. {s['n_docs']} documents (stratified sample of 2,091; see `data/ablation/bigthorium_sampling.json`). ",
         f"Gold: {s['gold_rule']}. Spend: ${s['spend']['total_realised_usd']} realised.\n",
         "## Named → renamed (all eight requests)\n", "| System | n pairs | named P / R / F1 | renamed P / R / F1 | ΔF1 [95% CI] | matter ΔF1 | control ΔF1 | knowledge effect | McNemar p | labels changed | Veridian ΔF1 |",
         "|---|---:|---|---|---|---|---|---|---:|---:|---|"]
    for m, lab in SYSTEMS:
        r = s["rename"].get(m)
        if not r:
            continue
        a, b = r["named"], r["renamed"]
        v = (s.get("veridian_delta_f1") or {}).get(m)
        L.append(f"| {lab} | {r['n_pairs']} | {100 * a['precision']:.1f} / {100 * a['recall']:.1f} / {100 * a['f1']:.1f} | {100 * b['precision']:.1f} / {100 * b['recall']:.1f} / {100 * b['f1']:.1f} | "
                 f"{_fmt(r['delta']['f1'])} | {_fmt(r.get('matter', {}).get('delta', {}).get('f1'))} | {_fmt(r.get('control', {}).get('delta', {}).get('f1'))} | "
                 f"{_fmt((r.get('knowledge_effect') or {}).get('f1'))} | {r['mcnemar']['p']:.3f} | {100 * r['label_changed_share']:.1f}% | {_fmt(v)} |")
    L.append("\nΔ = renamed − named in F1 points; knowledge effect = matter-request Δ − control-request Δ (negative would mean the names helped on the matter). "
             "Cluster bootstrap by document, 2,000 resamples. Pairs where the other panel members split are not scored (`n_unscored_split` in summary.json).\n")
    L.append("Label changes under renaming: " + "; ".join(f"{lab}: {r['changed_pairs']['n']} of {r['n_pairs']} pairs, {100 * (r['changed_pairs']['near_threshold_named_p_share'] or 0):.0f}% of them with a named-condition "
                                                          f"p within 0.1 of the 0.5 threshold (mean |Δp| {r['changed_pairs']['mean_abs_p_shift'] or 0:.2f})" for m, lab in SYSTEMS for r in [s["rename"].get(m)] if r) + ".\n")
    if s.get("brief"):
        L += ["## Without brief → with brief (aiR case summary; positive-enriched subset)\n", "| System | n pairs | without P / R / F1 | with P / R / F1 | ΔF1 [95% CI] | matter ΔF1 | control ΔF1 | McNemar p |", "|---|---:|---|---|---|---|---|---:|"]
        for m, lab in SYSTEMS:
            r = s["brief"].get(m)
            if not r:
                continue
            a, b = r["named"], r["brief"]
            L.append(f"| {lab} | {r['n_pairs']} | {100 * a['precision']:.1f} / {100 * a['recall']:.1f} / {100 * a['f1']:.1f} | {100 * b['precision']:.1f} / {100 * b['recall']:.1f} / {100 * b['f1']:.1f} | "
                     f"{_fmt(r['delta']['f1'])} | {_fmt(r.get('matter', {}).get('delta', {}).get('f1'))} | {_fmt(r.get('control', {}).get('delta', {}).get('f1'))} | {r['mcnemar']['p']:.3f} |")
        L.append("\nCaveat: the gold is the panel's *without-brief* majority, so a system that follows the brief away from the panel is scored as wrong; the brief effect here is a lower bound on agreement change, not an accuracy change.\n")
    h = s.get("human_check", {})
    if h:
        L += ["## Check against the demo's human coding (document level, any matter request positive)\n",
              f"{h['n_coded_in_sample']} of the sampled documents carry a human code; {h['n_human_positive']} are coded Responsive. Panel gold: recall {h['panel']['recall']:.2f}, precision {h['panel']['precision']:.3f} "
              f"(the panel marks {100 * h['panel']['panel_positive_rate']:.0f}% of coded documents responsive to at least one matter request — the demo coding is far narrower than the requests). ",
              "Per system (named / renamed) recall of the human positives: " + ", ".join(f"{k} {(v['recall'] or 0):.2f}" for k, v in h["systems"].items()) + ".\n"]
    L += ["## Per-request ΔF1 (named → renamed)\n", "| Request | " + " | ".join(lab for _, lab in SYSTEMS if _ in s["rename"]) + " |", "|---|" + "---|" * len([1 for k, _ in SYSTEMS if k in s["rename"]])]
    qids = sorted({q for r in s["rename"].values() for q in r["topics"]})
    for q in qids:
        L.append(f"| {q} | " + " | ".join(_fmt(s["rename"][m]["topics"].get(q, {}).get("delta", {}).get("f1")) + f" (n={s['rename'][m]['topics'].get(q, {}).get('n', 0)})" for m, _ in SYSTEMS if m in s["rename"]) + " |")
    L.append("\nFigures: `results/contam/article/pr_options/bigthorium_rename.png`" + (", `bigthorium_brief.png`" if s.get("brief") else "") + ". Renamer audit: `renamer_audit.json` (residuals must be zero).")
    return "\n".join(L) + "\n"
