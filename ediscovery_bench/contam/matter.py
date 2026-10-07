"""Matter-knowledge probes (the legal frame).

A relevance review is defined by a *matter*: a complaint, its allegations, the people and organisations involved,
the factual record and the outcome. The first battery (verbatim / entities / benchmark / labels) asks whether the
*documents* are inside the model. This module asks whether the *case* is, and whether that knowledge is actionable:

    M0  matter identification   does a de-identified sketch of the matter (or the TREC pseudonymised complaint)
                                get mapped to the real company and case?
    M1  matter recall           how much of the factual record (parties, allegations, people, events, outcome) can
                                the model recite from the matter's name alone, and how much of that is *beyond*
                                what the study's task context already tells every model?
    M2  evidence prior          before seeing any document, what people / organisations / code names / products /
                                terms does the model expect in documents responsive to each request?  Scored against
                                the labelled corpus: are the volunteered terms real (grounded) and do they
                                discriminate responsive from non-responsive documents (lift)?
    M3  metadata-only relevance given only an e-mail's header metadata, how accurately does the model call
                                responsiveness, and how much of that accuracy comes from seeing *who* sent and
                                received it (headers vs subject-only condition)?  A small effect test.

Floor: Veridian (fictional matter; any 'fact' is a confabulation).  Ceiling (M0/M1 only): United States v. Microsoft,
a famous case built on e-mail evidence.  Within-Enron contrast: topics 201-207 are the real scandal (Complaint J);
301-303 (Complaint K, an oil-spill action) are not Enron's story.
"""
from __future__ import annotations

import html as H
import json
import random
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

MATTER_ORDER = ["veridian", "jebbush", "enron", "mnk", "endo", "microsoft"]
MATTER_LABEL = {
    "veridian": "Veridian ApexHip MDL (synthetic)",
    "jebbush": "Jeb Bush governorship",
    "enron": "Enron",
    "mnk": "Mallinckrodt opioid litigation",
    "endo": "Endo opioid litigation (held-out corpus)",
    "microsoft": "U.S. v. Microsoft",
}
MATTER_ROLE = {"veridian": "floor", "microsoft": "ceiling"}

# ------------------------------------------------------------------------------------------------ contexts

def _task_context(name: str) -> tuple[str, dict]:
    raw = yaml.safe_load((ROOT / "tasks" / f"{name}.yaml").open())
    return raw["context"].strip(), raw["questions"]


ENRON_J_CONTEXT = (
    "Matter: Grumby v. Volteron Corp., a securities-fraud class action (TREC 2009 Legal Track, Complaint J) on behalf of "
    "purchasers of Volteron common stock between June 1, 1999 and December 2, 2001. Volteron produces electric energy and "
    "natural gas. The complaint alleges that the Company concealed billions of dollars of debt through structured commodity "
    "transactions known as \"prepay transactions\" and through transactions it characterised as compliant with FAS 140; that "
    "it misrepresented whether it would meet its financial forecasts; that, as its true financial condition came to light, "
    "executives shredded documents and deleted electronic data; that it filed energy schedules and bids misrepresenting the "
    "amount and location of load in order to earn congestion payments; and that it managed its contacts with securities "
    "analysts. The documents are the Company's e-mails and attachments, reproduced with their headers."
)
ENRON_J_NAMED_CONTEXT = ENRON_J_CONTEXT.replace("Grumby v. Volteron Corp.", "Grumby v. Enron Corp.").replace(
    "Volteron common stock", "Enron common stock").replace("Volteron produces", "Enron produces") + (
    " (The complaint is the TREC Legal Track's Complaint J, in which Enron appears under the pseudonym \"Volteron\"; it is modelled "
    "on the Enron collapse of 2001.)"
)
ENRON_IS_ENRON = " The Company's e-mail collection is the Enron corpus; \"Volteron\" is the complaint's pseudonym for Enron."
ENRON_K_CONTEXT = (
    "Matter: New Searchland Resort & Spa v. Volteron Corp. et al., a class action (TREC 2010 Legal Track, Complaint K) for "
    "damages from the oil spill that followed the explosion, fire and sinking of the mobile offshore drilling unit Bleak "
    "Horizon on May 7, 2008 on the outer continental shelf, brought against the well's operator Volteron Corp., the rig owner, "
    "the blowout-preventer manufacturer and the cementing contractor. The documents are the Company's e-mails and attachments, "
    "reproduced with their headers."
)

# ------------------------------------------------------------------------------------------------ M0 sketches

SKETCHES = {
    "enron": {
        "kind": "pseudonymised complaint (TREC Legal 2009, Complaint J)",
        "source": "complaint_j",
        "answer_keys": ["enron"],
    },
    "enron_k": {
        "kind": "pseudonymised complaint (TREC Legal 2010, Complaint K)",
        "source": "complaint_k",
        "answer_keys": ["deepwater horizon", "bp", "british petroleum", "macondo", "transocean"],
    },
    "mnk": {
        "kind": "de-identified sketch",
        "text": (
            "A pharmaceutical manufacturer headquartered near St. Louis, Missouri, and later domiciled in Ireland, was among the "
            "largest U.S. producers of generic opioid tablets (oxycodone, hydrocodone, methadone) and also sold a branded "
            "extended-release hydromorphone product. It was sued in the federal opioid multidistrict litigation and by state "
            "attorneys general over its suspicious-order-monitoring programme, its use of chargeback data showing downstream "
            "shipments to pharmacies, its promotion of opioids and its requests for ever-larger DEA production quota. It paid a "
            "DEA/DOJ settlement in 2017 over suspicious-order reporting and later filed for Chapter 11 to resolve the opioid claims."
        ),
        "answer_keys": ["mallinckrodt"],
    },
    "endo": {
        "kind": "de-identified sketch",
        "text": (
            "A specialty pharmaceutical company headquartered in suburban Philadelphia, later redomiciled to Ireland through an "
            "acquisition, sold a branded extended-release oxymorphone tablet that it reformulated in 2012 with a design it promoted as "
            "crush-resistant; a state attorney general later found the claim unsupported and the FDA asked for the product to be "
            "withdrawn in 2017 after injection abuse was linked to outbreaks of HIV and a blood-clotting disorder. Through two "
            "generic subsidiaries it was also a large maker of generic opioids. It was sued in the federal opioid multidistrict "
            "litigation and by states over its marketing, its funding of a pain-advocacy foundation and its failure to report "
            "suspicious prescribing. It filed for Chapter 11 in 2022 and settled the opioid claims through the bankruptcy; a "
            "subsidiary pleaded guilty to misbranding the reformulated product in 2024."
        ),
        "answer_keys": ["endo"],
    },
    "jebbush": {
        "kind": "de-identified sketch",
        "text": (
            "A two-term governor of a large south-eastern U.S. state (in office 1999-2007) whose brother served as President "
            "during his tenure. His administration's e-mail was later made public and used as a research collection. "
            "Controversies during his terms included a contested presidential recount in the state, an end-of-life dispute over a "
            "brain-damaged woman in which the legislature passed a special law, a missing foster child, an executive order ending "
            "racial preferences in university admissions and contracting, and a school-voucher programme struck down by the state "
            "supreme court."
        ),
        "answer_keys": ["jeb bush"],
    },
    "veridian": {
        "kind": "de-identified sketch (fictional matter)",
        "text": (
            "An orthopaedic device company based in Warsaw, Indiana, manufactured a metal-on-metal total hip system cleared by FDA "
            "in March 2017 and withdrawn from the market in February 2024. A federal multidistrict litigation in the Northern District "
            "of Indiana alleges that the implant shed cobalt and chromium wear debris causing tissue damage and early revision "
            "surgery, that the company failed to warn, promoted the device to younger and more active patients, and paid consulting "
            "surgeons to promote it. A separate June 2022 recall concerned the coating adhesion of a range of acetabular cup lots."
        ),
        "answer_keys": [],
        "control": True,
        "template_keys": [("DePuy ASR / J&J", ["depuy", "johnson & johnson", "johnson and johnson", "asr"]),
                          ("Zimmer Biomet", ["zimmer", "biomet"]), ("Stryker", ["stryker", "rejuvenate"]),
                          ("Smith & Nephew", ["smith & nephew", "smith and nephew", "birmingham hip"]),
                          ("Wright / Exactech / other", ["wright medical", "exactech", "conserve"])],
    },
    "microsoft": {
        "kind": "de-identified sketch",
        "text": (
            "In the late 1990s the U.S. federal government and twenty states brought a civil antitrust action against the dominant "
            "vendor of personal-computer operating systems, alleging that it illegally maintained its monopoly by bundling its web "
            "browser with the operating system, restricting what PC makers could install, and pressuring other software companies. "
            "The trial judge found the company had violated the Sherman Act and ordered it split into two companies; the court of "
            "appeals upheld the liability finding but reversed the break-up in 2001, and the case settled later that year."
        ),
        "answer_keys": ["microsoft"],
    },
}


def _complaint_excerpt(path: Path, strip_re: str, anchors: list[tuple[str, int]], before: int = 0) -> str:
    t = path.read_text(errors="replace").replace("\xa0", " ")
    t = re.sub(strip_re, "", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    parts = []
    for a, aft in anchors:
        i = t.find(a)
        if i >= 0:
            parts.append(t[max(0, i - before): i + aft].strip())
    if not parts:
        raise RuntimeError(f"no anchors found in {path}")
    return "\n[...]\n".join(parts)


def sketch_text(key: str) -> str:
    s = SKETCHES[key]
    if s.get("source") == "complaint_j":
        return _complaint_excerpt(ROOT / "data/legal09/raw/LT09_Complaint_J_final.txt",
                                  r"TREC 2009 Legal Track – Complaint J\s*\n(\s*\d+\s*\n)?",
                                  [("NATURE OF THE ACTION", 900), ("c. The accounting techniques improperly used", 1900)], 0)
    if s.get("source") == "complaint_k":
        return _complaint_excerpt(ROOT / "data/legal10/raw/LT10_Complaint_K_final-corrected.txt",
                                  r"TREC 2010 Legal Track – Complaint K\s*\n(-\d+-\s*\n)?",
                                  [("NEW SEARCHLAND RESORT & SPA, individually and on", 2600)], 0)
    return s["text"]


MATTER_ID_SYSTEM = (
    "You are a litigation analyst. You will be shown a description of a legal matter in which the names have been changed or "
    "removed. Say which real-world company, person or case it is modelled on, and why. If you believe it does not correspond "
    "to any real matter, say so."
)


def matter_id_items() -> list[dict]:
    out = []
    for key, s in SKETCHES.items():
        corpus = "enron" if key.startswith("enron") else key
        out.append({
            "item_id": f"matter_id:{key}",
            "probe": "matter_id",
            "corpus": corpus,
            "system": MATTER_ID_SYSTEM,
            "user": f"{sketch_text(key)}\n\nWhich real company, person or case is this modelled on? Name it first, then give your reasons in a few sentences.",
            "gold": {"answer_keys": s["answer_keys"], "control": s.get("control", False), "template_keys": s.get("template_keys", [])},
            "meta": {"sketch": key, "kind": s["kind"]},
        })
    return out


# ------------------------------------------------------------------------------------------------ M1 rubrics

# (label, keywords (lower-case substrings; any hit counts), category, in_context)
# in_context = the study's task context (tasks/*.yaml, or the Complaint-J context above for Enron) already states it.
RUBRICS: dict[str, dict] = {
    "enron": {
        "name": "the Enron scandal and the resulting investigations, litigation and prosecutions (2001-2006)",
        "items": [
            ("bankruptcy filed December 2001", ["december 2001", "dec. 2001", "dec 2001", "december 2, 2001"], "events", False),
            ("SEC investigation", ["sec", "securities and exchange"], "parties", True),
            ("Arthur Andersen (auditor)", ["andersen"], "parties", False),
            ("document shredding", ["shred"], "allegations", True),
            ("special-purpose entities LJM / Chewco / Raptor", ["ljm", "chewco", "raptor", "special purpose", "special-purpose"], "allegations", False),
            ("mark-to-market accounting", ["mark-to-market", "mark to market"], "allegations", False),
            ("prepay transactions with banks (Mahonia / JPMorgan / Citigroup)", ["prepay", "mahonia", "jpmorgan", "jp morgan", "citigroup", "citibank"], "allegations", True),
            ("California energy-crisis trading schemes", ["california", "death star", "fat boy", "get shorty", "ricochet", "western energy"], "allegations", True),
            ("Andrew Fastow (CFO)", ["fastow"], "people", False),
            ("Jeffrey Skilling (CEO)", ["skilling"], "people", False),
            ("Kenneth Lay (chairman)", ["ken lay", "kenneth lay", "kenneth l. lay", "lay and skilling", "skilling and lay", "chairman lay", "mr. lay"], "people", False),
            ("Sherron Watkins (whistle-blower)", ["watkins", "whistleblower", "whistle-blower"], "people", False),
            ("Ben Glisan / Michael Kopper pleas", ["glisan", "kopper"], "people", False),
            ("Richard Causey (chief accounting officer)", ["causey"], "people", False),
            ("Dynegy merger collapse (Nov 2001)", ["dynegy"], "events", False),
            ("Lay / Skilling convicted May 2006", ["2006", "convicted", "conviction"], "outcome", False),
            ("Andersen convicted of obstruction (2002), later reversed", ["obstruction", "reversed", "supreme court"], "outcome", False),
            ("Newby securities class action, ~$7.2bn settlements", ["class action", "newby", "7.2", "7.3", "billion"], "outcome", True),
            ("Sarbanes-Oxley Act (2002)", ["sarbanes"], "outcome", False),
            ("Merrill Lynch Nigerian barge deal", ["barge", "nigeria", "merrill"], "allegations", False),
        ],
    },
    "mnk": {
        "name": "the opioid litigation against Mallinckrodt (MDL 2804 and related state actions, 2017-2023)",
        "items": [
            ("MDL 2804, In re National Prescription Opiate Litigation", ["2804", "national prescription opiate", "multidistrict", "mdl"], "parties", True),
            ("Judge Dan Polster, N.D. Ohio", ["polster", "northern district of ohio", "cleveland"], "parties", False),
            ("generic oxycodone / hydrocodone manufacturer", ["oxycodone", "hydrocodone"], "allegations", True),
            ("Exalgo (hydromorphone ER)", ["exalgo"], "allegations", True),
            ("suspicious order monitoring", ["suspicious order"], "allegations", True),
            ("chargeback data / downstream visibility", ["chargeback"], "allegations", True),
            ("Florida pill mills", ["pill mill", "florida"], "allegations", True),
            ("DEA production quota", ["quota"], "allegations", True),
            ("2017 DEA/DOJ settlement, $35 million", ["35 million", "$35", "2017"], "outcome", False),
            ("Chapter 11 filing, October 2020", ["chapter 11", "bankruptcy", "2020"], "outcome", False),
            ("~$1.6-1.7bn opioid settlement / trust", ["1.6 billion", "1.7 billion", "1.725", "trust"], "outcome", False),
            ("second bankruptcy, 2023", ["2023", "second bankruptcy", "again filed"], "outcome", False),
            ("SpecGx subsidiary", ["specgx"], "parties", False),
            ("Covidien spin-off (2013)", ["covidien"], "parties", False),
            ("Washington Post ARCOS data: ~28% of pills", ["arcos", "28%", "28 percent", "washington post", "billion pills", "billion opioid"], "events", False),
            ("Acthar Gel Medicaid-rebate matter (separate)", ["acthar"], "events", True),
            ("Opioid Industry Documents Archive (UCSF / Johns Hopkins)", ["industry documents", "ucsf", "johns hopkins"], "outcome", False),
            ("Irish domicile (Dublin / Staines)", ["ireland", "irish", "dublin", "staines"], "parties", False),
            # people: public record only (press coverage of the MDL 2804 record and the company's own filings); none is named in the task context
            ("Mark Trudeau (president & CEO 2013-22, through the 2020 Chapter 11)", ["trudeau"], "people", False),
            ("Victor Borelli, national account manager: the 2008 'people are addicted to these things' e-mail to KeySource (Washington Post, 2019)",
             ["borelli", "addicted to these things", "keysource", "key source"], "people", False),
            ("Karen Harper, controlled-substance compliance / suspicious-order monitoring lead, deposed in MDL 2804", ["karen harper", "ms. harper"], "people", False),
        ],
    },
    "endo": {
        "name": "the opioid litigation against Endo International / Endo Pharmaceuticals (MDL 2804, state attorney-general actions, the 2022 bankruptcy and the 2024 plea)",
        "items": [
            ("MDL 2804, In re National Prescription Opiate Litigation", ["2804", "national prescription opiate", "multidistrict", "mdl"], "parties", True),
            ("Opana ER (oxymorphone ER)", ["opana", "oxymorphone"], "allegations", True),
            ("2012 crush-resistant reformulation (INTAC / Grünenthal)", ["crush", "reformulated", "reformulation", "intac", "grunenthal", "grünenthal", "tamper"], "allegations", True),
            ("FDA requested withdrawal, June 2017; removed July 2017", ["2017", "withdrawn", "withdrawal", "withdraw", "removed", "removal"], "events", False),
            ("Scott County, Indiana HIV outbreak / TTP from injected Opana ER", ["hiv", "indiana", "scott county", "ttp", "thrombotic", "blood-clotting", "blood clotting"], "events", False),
            ("New York AG Assurance of Discontinuance, March 2016", ["assurance of discontinuance", "2016", "new york attorney general", "schneiderman"], "outcome", False),
            ("'pseudoaddiction' and 'usually do not become addicted' in training / marketing", ["pseudoaddiction", "pseudo-addiction", "usually do not become addicted", "not common"], "allegations", False),
            ("American Pain Foundation / NIPC / painknowledge.com", ["american pain foundation", "apf", "national initiative on pain control", "nipc", "painknowledge"], "allegations", True),
            ("Par Pharmaceutical (2015) and Qualitest (2010) generic subsidiaries", ["par pharmaceutical", "par sterile", "qualitest"], "parties", True),
            ("Chapter 11, August 2022, S.D.N.Y. (Judge Garrity)", ["chapter 11", "bankruptcy", "bankrupt", "2022", "garrity", "southern district of new york"], "outcome", True),
            ("~$450-465 million opioid settlement / opioid trusts in the bankruptcy", ["450 million", "465 million", "$450", "$465", "opioid trust", "trust"], "outcome", False),
            ("Endo Health Solutions guilty plea, misbranding Opana ER (2024; W.D. Va.; ~$1.086bn fine, largely uncollectable)", ["plea", "pleaded", "guilty", "misbranding", "misbranded", "1.086", "1,086", "western district of virginia", "abingdon"], "outcome", False),
            ("Malvern / Chadds Ford, Pennsylvania; Dublin domicile via Paladin Labs (2014)", ["malvern", "chadds ford", "pennsylvania", "paladin", "dublin", "ireland", "irish"], "parties", False),
            ("Opana ER launched 2006 (with Penwest)", ["2006", "penwest", "launched", "launch"], "events", False),
            ("generic Opana ER / Impax & Actavis; FTC pay-for-delay case (2016-17)", ["impax", "actavis", "pay-for-delay", "pay for delay", "reverse payment", "ftc", "federal trade commission"], "events", False),
            ("Opioid Industry Documents Archive (UCSF / Johns Hopkins) document release", ["industry documents", "ucsf", "johns hopkins", "document archive", "public repository"], "outcome", False),
            ("reps paid bonuses for detailing prescribers later arrested (NY findings)", ["bonus", "arrested", "convicted", "suspicious prescribing", "suspicious prescribers", "diversion"], "allegations", True),
            ("CEOs Rajiv De Silva (2013-16), Paul Campanelli (2016-20), Blaise Coleman (2020-)", ["de silva", "desilva", "campanelli", "coleman"], "people", False),
            ("emerged from bankruptcy as Endo, Inc. (April 2024)", ["endo, inc", "endo inc", "emerged", "april 2024", "2024"], "outcome", False),
            ("Percocet (branded oxycodone / acetaminophen)", ["percocet"], "allegations", False),
        ],
    },
    "jebbush": {
        "name": "Jeb Bush's two terms as Governor of Florida (1999-2007): the major controversies, policy fights and events",
        "items": [
            ("Terri Schiavo / Terri's Law (2003)", ["schiavo"], "events", False),
            ("2000 presidential recount; Katherine Harris", ["recount", "katherine harris"], "events", True),
            ("One Florida (ending racial preferences)", ["one florida", "affirmative action"], "allegations", False),
            ("A+ Plan / vouchers; Bush v. Holmes (2006)", ["voucher", "a+ plan", "a-plus", "holmes", "opportunity scholarship"], "allegations", False),
            ("Rilya Wilson / DCF", ["rilya", "dcf", "children and families"], "events", True),
            ("2004 hurricanes (Charley, Frances, Ivan, Jeanne)", ["hurricane", "charley", "frances", "ivan", "jeanne"], "events", False),
            ("Everglades restoration (CERP)", ["everglades"], "allegations", False),
            ("felon voter purge / disenfranchisement", ["felon", "purge", "disenfranchise"], "allegations", False),
            ("James Crosby (corrections secretary) corruption", ["crosby"], "people", False),
            ("Elián González (2000)", ["elian", "elián", "gonzalez", "gonzález"], "events", False),
            ("Lt. Governors Frank Brogan / Toni Jennings", ["brogan", "jennings"], "people", False),
            ("Medicaid reform pilot (2005)", ["medicaid"], "allegations", True),
            ("class-size amendment (2002)", ["class size", "class-size"], "events", False),
            ("Scripps Florida biotech deal", ["scripps"], "events", False),
            ("Stand Your Ground (2005)", ["stand your ground"], "events", False),
            ("medical-malpractice / tort reform (2003)", ["malpractice", "tort"], "allegations", False),
            ("FCAT testing / school grades", ["fcat", "school grades"], "allegations", False),
            ("public release of jeb@jeb.org e-mails", ["jeb@jeb.org", "released his e", "e-mails public", "emails public", "email release"], "outcome", True),
        ],
    },
    "veridian": {
        "name": "In re Veridian Orthopedics ApexHip Products Liability Litigation, MDL No. 3102 (N.D. Ind.)",
        "items": [],  # fictional: every stated fact is a confabulation
        "control": True,
    },
    "microsoft": {
        "name": "United States v. Microsoft Corp., the antitrust case (1998-2002)",
        "items": [
            ("Judge Thomas Penfield Jackson", ["jackson"], "parties", False),
            ("DOJ (Joel Klein) and 20 states", ["department of justice", "doj", "joel klein", "attorneys general", "states"], "parties", False),
            ("David Boies (government trial counsel)", ["boies"], "people", False),
            ("Bill Gates videotaped deposition", ["gates"], "people", False),
            ("Netscape Navigator", ["netscape"], "allegations", False),
            ("Internet Explorer bundled with Windows", ["internet explorer", "browser"], "allegations", False),
            ("Sherman Act section 2 monopolisation", ["sherman", "section 2", "monopol"], "allegations", False),
            ("OEM licensing restrictions (Compaq etc.)", ["oem", "compaq", "pc makers", "manufacturers"], "allegations", False),
            ("Java / Sun Microsystems", ["java", "sun microsystems"], "allegations", False),
            ("'cut off Netscape's air supply' e-mails", ["air supply"], "events", False),
            ("Findings of Fact, November 1999", ["findings of fact", "november 1999"], "events", False),
            ("break-up order, June 2000", ["break-up", "breakup", "break up", "two companies", "split"], "outcome", False),
            ("D.C. Circuit reversal of the break-up, June 2001", ["d.c. circuit", "court of appeals", "2001"], "outcome", False),
            ("settlement / consent decree, Judge Kollar-Kotelly (2001-02)", ["kollar", "settlement", "consent decree"], "outcome", False),
            ("middleware threat theory", ["middleware"], "allegations", False),
            ("1994-95 consent decree / Judge Sporkin", ["1995", "1994", "sporkin"], "events", False),
        ],
    },
}

MATTER_RECALL_SYSTEM = (
    "You answer from memory about real legal matters. Be specific: name the parties, the key allegations or issues, the key "
    "people and their roles, the main events with dates, and how the matter ended. If you do not know a matter, say so plainly "
    "rather than guessing."
)


def matter_recall_items() -> list[dict]:
    out = []
    for key, r in RUBRICS.items():
        out.append({
            "item_id": f"matter_recall:{key}",
            "probe": "matter_recall",
            "corpus": key,
            "system": MATTER_RECALL_SYSTEM,
            "user": f"Describe {r['name']}: the parties, the key allegations or issues, the key people, the main events with dates, and the outcome.",
            "gold": {"rubric": [{"label": a, "keys": b, "cat": c, "in_context": d} for a, b, c, d in r["items"]], "control": r.get("control", False),
                     "template_keys": SKETCHES["veridian"]["template_keys"] if key == "veridian" else []},
            "meta": {"matter": key},
        })
    return out


# ------------------------------------------------------------------------------------------------ topic sets

def _norm_text(t: str) -> str:
    return t.replace("\r\n", "\n").replace("\r", "\n")


def topic_sets() -> list[dict]:
    """One entry per (corpus, request): context, request text, and the judged documents with their gold for that request.
    docs: list of (id, text, is_responsive)."""
    sets: list[dict] = []

    # Enron: learning topics 201-207 (Complaint J; the real scandal) on learn.jsonl, interactive 301-303 (Complaint K) on legal10.jsonl
    l09 = json.load((ROOT / "data/legal09/topics.json").open())["topics"]
    l10 = json.load((ROOT / "data/legal10/topics.json").open())["topics"]
    by_topic: dict[str, list] = defaultdict(list)
    for line in (ROOT / "data/legal10/learn.jsonl").open():
        r = json.loads(line)
        if r["gray"] or not r.get("text"):
            continue
        t = r["meta"]["topic"]
        if t == "200":
            continue
        key = l09[t]["key"]
        by_topic[t].append((r["id"], _norm_text(r["text"]), r["labels"].get(key) == "responsive"))
    for t in sorted(by_topic):
        base = {"corpus": "enron", "topic": t, "key": l09[t]["key"], "title": l09[t]["title"], "rfp": l09[t]["rfp_text"], "scandal": t != "207", "docs": by_topic[t]}
        # as TREC framed it (pseudonym), for the evidence prior and the metadata probe ...
        sets.append({**base, "set": "enron_j", "context": ENRON_J_CONTEXT, "meta_context": ENRON_J_CONTEXT + ENRON_IS_ENRON})
        # ... and with the company named, for the evidence prior only: does naming it unlock the case knowledge?
        sets.append({**base, "set": "enron_j_named", "context": ENRON_J_NAMED_CONTEXT, "metadata": False})
    by_topic = defaultdict(list)
    for line in (ROOT / "data/legal10/legal10.jsonl").open():
        r = json.loads(line)
        if r["gray"] or not r.get("text"):
            continue
        t = r["meta"]["topic"]
        if t not in ("301", "302", "303"):
            continue
        key = l10[t]["key"]
        by_topic[t].append((r["id"], _norm_text(r["text"]), r["labels"].get(key) == "responsive"))
    for t in sorted(by_topic):
        sets.append({"corpus": "enron", "set": "enron_k", "topic": t, "key": l10[t]["key"], "title": l10[t]["title"], "rfp": l10[t]["rfp_text"],
                     "context": ENRON_K_CONTEXT, "meta_context": ENRON_K_CONTEXT + ENRON_IS_ENRON, "scandal": False, "docs": by_topic[t]})

    # Mallinckrodt, Veridian, Jeb Bush (and Endo, appended last so earlier rng draws are unchanged): every document is judged for every request
    for corpus, task, path in (("mnk", "mallinckrodt", "data/mallinckrodt/mnk.jsonl"),
                               ("veridian", "veridian", "data/veridian/veridian.jsonl"),
                               ("jebbush", "trec", "data/trec/local_subset.jsonl"),
                               ("endo", "endo", "data/endo/endo.jsonl")):
        if not (ROOT / path).exists():
            continue
        ctx, qs = _task_context(task)
        rows = [json.loads(l) for l in (ROOT / path).open()]
        rows = [r for r in rows if r.get("text")]
        for qid, q in qs.items():
            docs = [(r["id"], _norm_text(r["text"]), r["labels"].get(qid) == "responsive") for r in rows if qid not in r.get("gray", [])]
            sets.append({"corpus": corpus, "set": corpus, "topic": qid, "key": qid, "title": q["title"], "rfp": q["rfp_text"].strip(),
                         "context": ctx, "scandal": None, "docs": docs})
    return sets


# ------------------------------------------------------------------------------------------------ M2 evidence prior

EVIDENCE_SYSTEM = (
    "You are the review lead preparing a document review for the matter described. No documents have been seen yet. "
    "Using everything you know about this matter, the organisation and the people involved, list the specific things you "
    "expect to see in documents responsive to the request: named people, organisations, deal / project / code names, "
    "products, places, time periods and distinctive terms. Prefer specific proper nouns over generic words. "
    "Return strict JSON only: {\"note\": \"<one sentence on how much you actually know about this matter>\", "
    "\"items\": [{\"term\": \"...\", \"type\": \"person|organisation|codename|product|place|period|keyword\"}, ...]} with exactly 25 items."
)


def evidence_prior_items(sets: list[dict]) -> list[dict]:
    out = []
    for s in sets:
        out.append({
            "item_id": f"evidence_prior:{s['set']}:{s['key']}",
            "probe": "evidence_prior",
            "corpus": s["corpus"],
            "system": EVIDENCE_SYSTEM,
            "user": f"{s['context']}\n\nRequest — {s['title']}: {s['rfp']}\n\nList the 25 most specific things you expect to see in responsive documents. JSON only.",
            "gold": {"set": s["set"], "topic": s["topic"], "key": s["key"]},
            "meta": {"set": s["set"], "topic": s["topic"], "key": s["key"], "title": s["title"], "scandal": s["scandal"], "n_docs": len(s["docs"]),
                     "n_pos": sum(1 for d in s["docs"] if d[2])},
        })
    return out


# ------------------------------------------------------------------------------------------------ M3 metadata-only

META_KEY_RE = re.compile(r"^(From|Sent|Date|To|Cc|CC|Bcc|BCC|Subject|Attach(?:ments?)?|Importance)\s*:\s*(.*)$")
ANY_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,24}\s*:")  # any other header key (X-SDOC:, Message-ID:, ...) ends a value
SUBJECT_PREFIX_RE = re.compile(r"^\s*((re|fw|fwd|aw|tr)\s*:\s*)+", re.I)


def parse_meta(text: str) -> dict | None:
    """Date / From / To / Cc / Subject from the header block. Handles the OCR layout where the keys appear on their own
    lines and the values follow in order (Mallinckrodt). Returns None unless From and Subject are both present."""
    text = _norm_text(text)
    block, _, rest = text.partition("\n\n")
    lines = block.split("\n")
    fields: dict[str, str] = {}
    order: list[str] = []
    cur = None
    for ln in lines:
        m = META_KEY_RE.match(ln.strip())
        if m:
            cur = m.group(1).lower()
            cur = {"sent": "date", "cc": "cc", "bcc": "bcc"}.get(cur, cur)
            if cur not in fields:
                order.append(cur)
                fields[cur] = m.group(2).strip()
            else:
                fields[cur] = (fields[cur] + " " + m.group(2).strip()).strip()
        elif ANY_KEY_RE.match(ln) and not ln.startswith((" ", "\t")):
            cur = None  # some other header field; stop appending to the previous value
        elif cur and (ln.startswith((" ", "\t")) or ln.strip()):
            fields[cur] = (fields[cur] + " " + ln.strip()).strip()
    if fields and all(not v for v in fields.values()):
        vals = [l.strip() for l in rest.split("\n\n", 1)[0].split("\n") if l.strip()]
        for k, v in zip(order, vals):
            fields[k] = v
    out = {k: re.sub(r"\s+", " ", H.unescape(v)).strip() for k, v in fields.items() if k in ("date", "from", "to", "cc", "subject")}
    if not out.get("from") or len(SUBJECT_PREFIX_RE.sub("", out.get("subject", "")).strip()) < 3:
        return None
    return out


def _trim_addresses(val: str, n: int = 6) -> str:
    sep = ";" if ";" in val else ","
    parts = [p.strip() for p in val.split(sep) if p.strip()]
    if len(parts) > n:
        return "; ".join(parts[:n]) + f" (+{len(parts) - n} more)"
    return "; ".join(parts)


def meta_block(meta: dict, condition: str) -> str:
    lines = []
    if meta.get("date"):
        lines.append(f"Date: {meta['date']}")
    if condition == "headers":
        lines.append(f"From: {meta['from']}")
        if meta.get("to"):
            lines.append(f"To: {_trim_addresses(meta['to'])}")
        if meta.get("cc"):
            lines.append(f"Cc: {_trim_addresses(meta['cc'])}")
    lines.append(f"Subject: {meta['subject']}")
    return "\n".join(lines)


METADATA_SYSTEM = (
    "You are reviewing e-mails for responsiveness in a legal matter. You will see only an e-mail's header metadata, not its "
    "body. Decide whether the e-mail is more likely than not responsive to the request. Reply with exactly one word: "
    "responsive or not_responsive."
)

STOP = {"the", "and", "with", "from", "that", "this", "for", "all", "any", "documents", "concerning", "relating", "related",
        "broad", "narrow", "contacts", "meeting", "efforts", "reform", "rules", "state", "florida", "governor", "office"}


def _title_terms(title: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-']{3,}", title) if w.lower() not in STOP]


def metadata_items(sets: list[dict], rng: random.Random, per_class: dict[str, int] | None = None) -> list[dict]:
    per_class = per_class or {"enron": 20, "mnk": 20, "endo": 20, "veridian": 20, "jebbush": 15}
    out = []
    for s in sets:
        if s.get("metadata") is False:
            continue
        ctx = s.get("meta_context", s["context"])
        n = per_class.get(s["corpus"], 20)
        pos, neg = [], []
        for did, text, resp in s["docs"]:
            m = parse_meta(text)
            if not m:
                continue
            (pos if resp else neg).append((did, m))
        k = min(n, len(pos), len(neg))
        if k < 5:
            continue
        chosen = [(d, m, "responsive") for d, m in rng.sample(pos, k)] + [(d, m, "not_responsive") for d, m in rng.sample(neg, k)]
        tt = _title_terms(s["title"])
        for did, m, gold in chosen:
            lex = "responsive" if any(t[:5] in m["subject"].lower() for t in tt) else "not_responsive"
            for cond in ("headers", "subject"):
                out.append({
                    "item_id": f"metadata_relevance:{s['set']}:{s['key']}:{did}:{cond}",
                    "probe": "metadata_relevance",
                    "corpus": s["corpus"],
                    "system": METADATA_SYSTEM,
                    "user": f"{ctx}\n\nRequest — {s['title']}: {s['rfp']}\n\nE-mail metadata:\n{meta_block(m, cond)}\n\nOne word: responsive or not_responsive.",
                    "gold": {"answer": gold, "lexical": lex},
                    "meta": {"set": s["set"], "topic": s["topic"], "key": s["key"], "doc_id": did, "condition": cond, "scandal": s["scandal"]},
                })
    return out


# ------------------------------------------------------------------------------------------------ build entry

def matter_items(rng: random.Random, log=print) -> list[dict]:
    sets = topic_sets()
    log(f"  matter: {len(sets)} request sets " + ", ".join(f"{s['set']}:{s['key']}({sum(d[2] for d in s['docs'])}/{len(s['docs'])})" for s in sets))
    items = matter_id_items() + matter_recall_items() + evidence_prior_items(sets)
    md = metadata_items(sets, rng)
    log(f"  matter_id {len(SKETCHES)}, matter_recall {len(RUBRICS)}, evidence_prior {len(sets)}, metadata_relevance {len(md)}")
    return items + md


# ------------------------------------------------------------------------------------------------ scoring

def _lower(s: str) -> str:
    return (s or "").lower()


def _kw_hit(text_lower: str, keys: list[str]) -> bool:
    """Any key present as a whole word/phrase (so 'delay' does not hit 'lay')."""
    for k in keys:
        k = k.lower().strip()
        if not k:
            continue
        pat = (r"(?<![a-z0-9])" if k[0].isalnum() else "") + re.escape(k) + (r"(?![a-z0-9])" if k[-1].isalnum() else "")
        if re.search(pat, text_lower):
            return True
    return False


DECLINE_RE = re.compile(
    r"can.?t reliably describe|cannot reliably describe|not aware of any|i.?m not aware|don.?t know of a|do not know of a|"
    r"no (?:reliable|verified|verifiable) information|in the future relative|knowledge cutoff|not familiar with|"
    r"unable to (?:find|identify|describe)|i don.?t know this|i do not know this|not a matter i|no such (?:case|matter)|cannot (?:identify|describe) (?:this|that)",
    re.I)


def declines(resp: str, head: int = 400) -> bool:
    """Did the answer *open* by saying it does not know the matter? (Judged on the opening so that a hedge buried in a long,
    knowledgeable answer — 'no public record of X's exact title' — does not count as not knowing.)"""
    from .score import is_unknown  # noqa: PLC0415
    h = resp.strip()[:head]
    return is_unknown(h) or bool(DECLINE_RE.search(h))


def score_matter_id(item: dict, resp: str) -> dict:
    r = _lower(resp)
    g = item["gold"]
    hit = _kw_hit(r, g["answer_keys"])
    templates = [lab for lab, keys in g.get("template_keys", []) if _kw_hit(r, keys)]
    return {"hit": bool(hit), "control": g["control"], "unknown": declines(resp), "templates": templates,
            "first_line": resp.strip().split("\n", 1)[0][:160]}


def score_matter_recall(item: dict, resp: str) -> dict:
    r = _lower(resp)
    g = item["gold"]
    q = _lower(item.get("user", ""))
    hits = []
    for it in g["rubric"]:
        # in_prompt: the question itself states this fact (e.g. the names in 'Describe the SEC's case against X and Y'), so an
        # answer that merely echoes the question gets no credit for it
        hits.append({"label": it["label"], "cat": it["cat"], "in_context": it["in_context"], "in_prompt": _kw_hit(q, it["keys"]),
                     "hit": _kw_hit(r, it["keys"])})
    n = len(hits)
    n_hit = sum(h["hit"] for h in hits)
    beyond = [h for h in hits if not h["in_context"]]
    beyond_prompt = [h for h in hits if not h["in_prompt"]]
    cats = defaultdict(list)
    for h in hits:
        cats[h["cat"]].append(h["hit"])
    templates = [lab for lab, keys in g.get("template_keys", []) if _kw_hit(r, keys)]
    return {
        "n": n, "n_hit": n_hit, "share": round(n_hit / n, 3) if n else None,
        "n_beyond": len(beyond), "n_hit_beyond": sum(h["hit"] for h in beyond),
        "share_beyond": round(sum(h["hit"] for h in beyond) / len(beyond), 3) if beyond else None,
        "n_beyond_prompt": len(beyond_prompt), "n_hit_beyond_prompt": sum(h["hit"] for h in beyond_prompt),
        "share_beyond_prompt": round(sum(h["hit"] for h in beyond_prompt) / len(beyond_prompt), 3) if beyond_prompt else None,
        "by_cat": {c: round(sum(v) / len(v), 3) for c, v in cats.items()},
        "missed": [h["label"] for h in hits if not h["hit"]],
        "control": g["control"], "unknown": declines(resp), "templates": templates, "n_words": len(resp.split()),
    }


NAMED_TYPES = {"person", "organisation", "organization", "codename", "product", "place"}
TERM_CLEAN_RE = re.compile(r"[^a-z0-9&'\-\. ]+")


def parse_evidence(resp: str) -> tuple[list[dict], str]:
    """Pull the JSON items list out of the response; tolerant of code fences and leading prose."""
    s = resp.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.S)
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j < 0:
        return [], ""
    try:
        obj = json.loads(s[i:j + 1])
    except json.JSONDecodeError:
        # salvage: individual {"term": ..., "type": ...} objects
        items = [{"term": m.group(1), "type": m.group(2)} for m in re.finditer(r'\{\s*"term"\s*:\s*"([^"]+)"\s*,\s*"type"\s*:\s*"([^"]+)"', s)]
        return items, ""
    items = obj.get("items", []) if isinstance(obj, dict) else []
    out = []
    for it in items:
        if isinstance(it, dict) and it.get("term"):
            out.append({"term": str(it["term"]).strip(), "type": str(it.get("type", "keyword")).strip().lower()})
        elif isinstance(it, str):
            out.append({"term": it.strip(), "type": "keyword"})
    return out, str(obj.get("note", "")) if isinstance(obj, dict) else ""


def _term_key(term: str) -> str:
    t = TERM_CLEAN_RE.sub(" ", term.lower()).strip(" .")
    return re.sub(r"\s+", " ", t)


def _term_re(key: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])")


def score_evidence_prior(item: dict, resp: str, s: dict, docs_lower: list[tuple[str, bool]]) -> dict:
    """docs_lower: [(text_lower, is_responsive)] for the request's judged documents."""
    items, note = parse_evidence(resp)
    given = _term_key(s["context"] + " " + s["title"] + " " + s["rfp"])
    n_docs = len(docs_lower)
    n_pos = sum(1 for _, r in docs_lower if r)
    terms = []
    seen = set()
    for it in items:
        key = _term_key(it["term"])
        if len(key) < 3 or key in seen:
            continue
        seen.add(key)
        typ = it["type"] if it["type"] in NAMED_TYPES | {"period", "keyword"} else "keyword"
        # 'named' = typed as an entity *and* written as a proper noun ('Mahonia Limited', 'DCF'), so that a model that labels
        # 'backup tapes' a product does not get credit for case knowledge
        proper = bool(re.search(r"(?:^|[\s\-/(])[A-Z]", it["term"].strip())) and not it["term"].strip().islower()
        named = typ in NAMED_TYPES and proper
        # 'given' if the term (or the term without a trailing parenthetical / corporate suffix) is already in the prompt
        bare = _term_key(re.sub(r"\s*\([^)]*\)\s*$", "", it["term"]))
        bare = re.sub(r"\b(inc|corp|corporation|plc|llc|ltd|co)\b\.?$", "", bare).strip()
        novel = key not in given and (not bare or bare not in given)
        rx = _term_re(key)
        df_all = df_pos = 0
        for txt, r in docs_lower:
            if key in txt and rx.search(txt):  # cheap substring prefilter, then the whole-word check
                df_all += 1
                if r:
                    df_pos += 1
        p_pos = df_pos / n_pos if n_pos else 0.0
        p_all = df_all / n_docs if n_docs else 0.0
        lift = (p_pos / p_all) if p_all > 0 else None
        terms.append({"term": it["term"], "type": typ, "named": named, "novel": novel, "df_all": df_all, "df_pos": df_pos,
                      "lift": round(lift, 2) if lift is not None else None,
                      "grounded": df_all >= 2, "discriminative": df_all >= 2 and df_pos >= 2 and lift is not None and lift >= 2.0})
    nov = [t for t in terms if t["novel"]]
    nov_named = [t for t in nov if t["named"]]
    nov_generic = [t for t in nov if not t["named"]]

    def rate(xs, k):
        return round(sum(1 for t in xs if t[k]) / len(xs), 3) if xs else None

    return {
        "n_items": len(items), "n_terms": len(terms), "n_novel": len(nov), "n_novel_named": len(nov_named),
        "novel_rate": round(len(nov) / len(terms), 3) if terms else None,
        "grounded_rate_named": rate(nov_named, "grounded"), "discriminative_rate_named": rate(nov_named, "discriminative"),
        "grounded_rate_generic": rate(nov_generic, "grounded"), "discriminative_rate_generic": rate(nov_generic, "discriminative"),
        "grounded_rate_all": rate(nov, "grounded"), "discriminative_rate_all": rate(nov, "discriminative"),
        "n_discriminative_named": sum(1 for t in nov_named if t["discriminative"]),
        "top_terms": sorted([t for t in nov if t["grounded"]], key=lambda t: -(t["lift"] or 0))[:8],
        "named_terms": [t["term"] for t in nov_named],
        "note": note[:300], "parsed": bool(items),
    }


def parse_responsive(resp: str) -> str:
    r = _lower(resp).strip()
    if "not_responsive" in r or "not responsive" in r or r.startswith("no"):
        return "not_responsive"
    if "responsive" in r or r.startswith("yes"):
        return "responsive"
    return "unknown"
