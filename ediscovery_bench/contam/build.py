"""
Build the contamination-probe items: data/contam/probes.jsonl.

Five probes (design/06_contamination_probe.md):
  verbatim        document prefix -> next ~60 words        (memorisation of the documents)
  entity_recall   "who is {name}?"                         (knowledge of the people in the matter)
  entity_recog    "was {name} affiliated with {org}?" x 4  (same, as a yes/no recognition matrix)
  bench_knowledge "list the topics of TREC ..."            (knowledge of the benchmark itself)
  label_recall    "was document {id} judged relevant?"     (memorisation of published relevance judgments)

Every item: {"item_id", "probe", "corpus", "system", "user", "gold": {...}, "meta": {...}}.
Veridian (synthetic, written 2026-09) is the negative control in every probe. Seeds are fixed.
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "contam"

# ------------------------------------------------------------------------------------------------ corpora

CORPORA: dict[str, dict] = {
    "enron": dict(
        file="data/legal10/legal10.jsonl",
        label="Enron (EDRM v2 / TREC Legal 2010)",
        era="1999-2002",
        org_short="Enron",
        org_desc="Enron Corporation, the Houston-based energy company",
        org_keywords=["enron"],
        kind="email",
    ),
    "jebbush": dict(
        file="data/trec/local_subset.jsonl",
        label="Jeb Bush e-mails (TREC 2016 Total Recall)",
        era="1999-2007",
        org_short="Florida Governor Jeb Bush's administration",
        org_desc=(
            "the administration of Florida Governor Jeb Bush (1999-2007), as a staff member, state official, "
            "legislator, lobbyist or regular correspondent of the Governor's office"
        ),
        org_keywords=["jeb bush", "governor bush", "florida", "tallahassee"],
        kind="email",
    ),
    "mnk": dict(
        file="data/mallinckrodt/mnk.jsonl",
        label="Mallinckrodt opioid e-mails (OIDA)",
        era="2008-2017",
        org_short="Mallinckrodt / Covidien",
        org_desc="Mallinckrodt Pharmaceuticals or its former parent Covidien",
        org_keywords=[
            "mallinckrodt", "covidien", "cadence pharma", "ofirmev", "exalgo", "specgx", "tyco healthcare",
            "questcor", "acthar", "opioid", "hydrocodone", "oxycodone", "methadone",
        ],
        kind="email",
    ),
    "endo": dict(
        file="data/endo/endo.jsonl",
        label="Endo opioid e-mails (OIDA, held-out 2024-26 production)",
        era="2006-2017",
        org_short="Endo Pharmaceuticals",
        org_desc="Endo Pharmaceuticals / Endo International (maker of Opana ER) or its subsidiaries Par Pharmaceutical and Qualitest",
        org_keywords=[
            "endo pharma", "endo health", "endo international", "endo inc", "endo,", "endo.", "endo ", "opana",
            "par pharmaceutical", "qualitest", "lidoderm", "voltaren gel", "oxymorphone", "opioid", "hydrocodone",
            "oxycodone", "chadds ford", "malvern",
        ],
        kind="email",
        heldout=True,
    ),
    "veridian": dict(
        file="data/veridian/veridian.jsonl",
        label="Veridian (synthetic, 2026)",
        era="2017-2024",
        org_short="Veridian Orthopedics",
        org_desc="Veridian Orthopedics, an orthopaedic implant manufacturer",
        org_keywords=["veridian", "apexhip"],
        kind="email",
        control=True,
    ),
    "cuad": dict(
        file="data/cuad/cuad.jsonl",
        label="CUAD contracts",
        era=None,
        kind="contract",
    ),
    # ---- positive controls: material every model has certainly seen many times -------------------------------
    "canon": dict(
        loader="canon",
        label="Positive control: US founding documents (Federalist Papers, Constitution, Declaration)",
        era="1770s-1790s",
        org_short="the framing of the US Constitution",
        org_desc=(
            "the framing and ratification of the United States Constitution, as a delegate to the 1787 Philadelphia "
            "Convention, a signer of the Constitution, or an author of The Federalist"
        ),
        org_keywords=["constitution", "continental congress", "founding father", "federalist", "philadelphia convention",
                      "declaration of independence", "framer"],
        kind="canon",
        anchor=True,
        # The cast is fixed, tiered by fame rather than by header frequency (there are no headers).
        names=[
            ("George Washington", "top"), ("Benjamin Franklin", "top"), ("Alexander Hamilton", "top"), ("James Madison", "top"),
            ("John Jay", "top"), ("Gouverneur Morris", "top"), ("Roger Sherman", "top"), ("James Wilson", "top"),
            ("John Dickinson", "top"), ("Rufus King", "top"),
            ("Charles Cotesworth Pinckney", "mid"), ("Robert Morris", "mid"), ("Elbridge Gerry", "mid"), ("George Mason", "mid"),
            ("Edmund Randolph", "mid"), ("John Rutledge", "mid"), ("William Paterson", "mid"), ("Pierce Butler", "mid"),
            ("Nathaniel Gorham", "mid"), ("Jonathan Dayton", "mid"),
            ("Jacob Broom", "tail"), ("Richard Bassett", "tail"), ("Jared Ingersoll", "tail"), ("Nicholas Gilman", "tail"),
            ("William Few", "tail"), ("Abraham Baldwin", "tail"), ("Daniel Carroll", "tail"), ("John Blair", "tail"),
            ("Hugh Williamson", "tail"), ("Richard Dobbs Spaight", "tail"),
        ],
    ),
    "titanic": dict(
        loader="titanic",
        label="Positive control: Kaggle Titanic train.csv (verbatim rows; passenger -> Survived)",
        era=None,
        kind="csv",
        anchor=True,
    ),
}

ENTITY_CORPORA = ["enron", "jebbush", "mnk", "endo", "veridian", "canon"]  # CUAD / Titanic have no cast of people to ask about
# NB: adding Endo also adds one new recognition distractor ("affiliated with Endo?") for every existing name; those are new
# item ids, so existing results are untouched and only the new items run.

RAW_DIR = OUT_DIR / "raw"
RAW_SOURCES = {
    "federalist.txt": "https://www.gutenberg.org/cache/epub/1404/pg1404.txt",
    "constitution.txt": "https://www.gutenberg.org/cache/epub/5/pg5.txt",
    "declaration.txt": "https://www.gutenberg.org/cache/epub/1/pg1.txt",
    "titanic.csv": "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv",
}


def _raw(name: str) -> Path:
    p = RAW_DIR / name
    if not p.exists():
        import urllib.request  # noqa: PLC0415

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(RAW_SOURCES[name], p)
    return p


def _unwrap(text: str) -> str:
    """Join Gutenberg's hard-wrapped lines inside paragraphs; keep paragraph breaks."""
    text = text.replace("\r\n", "\n")
    return re.sub(r"(?<!\n)\n(?!\n)", " ", text)


def _gutenberg_body(text: str) -> str:
    m = re.search(r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.S)
    n = re.search(r"\*\*\* END OF THE PROJECT GUTENBERG EBOOK", text)
    return text[(m.end() if m else 0):(n.start() if n else len(text))]


def load_canon() -> list[dict]:
    docs = []
    fed = _gutenberg_body(_raw("federalist.txt").read_text(encoding="utf-8", errors="replace")).replace("\r\n", "\n")
    parts = re.split(r"^FEDERALIST\.? No\. (\d+)\s*$", fed, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        num, body = parts[i], parts[i + 1]
        docs.append({"id": f"FED-{int(num):02d}", "text": _unwrap(f"FEDERALIST No. {num}\n\n{body.strip()}"), "labels": {}, "gray": [], "meta": {"source": "federalist"}})
    con = _gutenberg_body(_raw("constitution.txt").read_text(encoding="utf-8", errors="replace")).replace("\r\n", "\n")
    chunks = re.split(r"^(Article \d+|Amendment [IVXL]+)\s*$", con, flags=re.M)
    docs.append({"id": "CONST-preamble", "text": _unwrap(chunks[0].strip()), "labels": {}, "gray": [], "meta": {"source": "constitution"}})
    for i in range(1, len(chunks) - 1, 2):
        docs.append({"id": f"CONST-{chunks[i].replace(' ', '-')}", "text": _unwrap(f"{chunks[i]}\n\n{chunks[i + 1].strip()}"), "labels": {}, "gray": [], "meta": {"source": "constitution"}})
    dec = _gutenberg_body(_raw("declaration.txt").read_text(encoding="utf-8", errors="replace")).replace("\r\n", "\n")
    m = re.search(r"IN CONGRESS, July 4, 1776", dec)
    docs.append({"id": "DECL-1776", "text": _unwrap(dec[m.start():].strip() if m else dec.strip()), "labels": {}, "gray": [], "meta": {"source": "declaration"}})
    return [d for d in docs if len(d["text"]) >= 700]


def load_titanic_rows() -> tuple[str, list[str]]:
    lines = _raw("titanic.csv").read_text(encoding="utf-8").replace("\r\n", "\n").strip().split("\n")
    return lines[0], lines[1:]


def load_titanic(rows_per_doc: int = 14, n_docs: int = 20, seed: int = 7) -> list[dict]:
    """Chunks of consecutive CSV rows as 'documents' (header + rows): the row-completion test of Bordt et al. 2024."""
    header, rows = load_titanic_rows()
    rng = random.Random(seed)
    starts = sorted(rng.sample(range(0, len(rows) - rows_per_doc), n_docs))
    return [{"id": f"TITANIC-rows-{s + 1}-{s + rows_per_doc}", "text": header + "\n" + "\n".join(rows[s:s + rows_per_doc]), "labels": {}, "gray": [], "meta": {"source": "titanic_csv", "first_row": s + 1}} for s in starts]


def load_docs(corpus: str) -> list[dict]:
    c = CORPORA[corpus]
    if c.get("loader") == "canon":
        return load_canon()
    if c.get("loader") == "titanic":
        return load_titanic()
    path = ROOT / c["file"]
    docs = []
    with path.open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("text"):
                r["text"] = r["text"].replace("\r\n", "\n").replace("\r", "\n")
                docs.append(r)
    return docs


# ------------------------------------------------------------------------------------------------ names

HEADER_KEY_RE = re.compile(
    r"^(From|To|Cc|CC|Bcc|BCC|Sent|Date|Subject|Importance|Attachments?|X-[A-Za-z-]+|Message|Priority|Reply-To)\s*:",
    re.M,
)
CHAT_LINE_RE = re.compile(r"^\[[^\]]+\]\s+([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,2}):", re.M)
HONORIFICS = {"dr", "dr.", "mr", "mr.", "ms", "ms.", "mrs", "mrs.", "prof", "prof.", "hon", "hon.", "rep", "rep.", "sen", "sen."}
SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "esq", "esq.", "phd", "ph.d.", "md", "m.d.", "cpa"}
NAME_STOP = {
    "office", "group", "team", "enron", "mail", "list", "admin", "support", "sales", "marketing", "legal", "dept",
    "department", "gov", "governor", "chairman", "press", "info", "everyone", "all", "staff", "undisclosed",
    "recipients", "committee", "board", "council", "news", "daily", "corp", "inc", "llc", "company", "state",
    "florida", "county", "city", "the", "of", "and", "for", "houston", "america", "north", "global", "capital",
    "energy", "services", "research", "center", "centre", "school", "university", "association", "foundation",
    "clips", "digest", "alert", "update", "report", "bulletin", "online", "system", "systems", "mailbox",
    "distribution", "notice", "notification", "unknown", "noreply", "no-reply", "webmaster", "request",
    "mgmt", "management", "agency", "relations", "senator", "representative", "secretary", "director", "president",
    "communications", "operations", "facilities", "finance", "accounting", "compliance", "quality", "regulatory",
    "human", "resources", "payroll", "security", "helpdesk", "desk", "partners", "associates", "consulting",
}
TOKEN_RE = re.compile(r"^[A-Z][a-zA-Z'\-]+$")


def _header_block(text: str) -> str:
    return text.split("\n\n", 1)[0]


def header_fields(text: str) -> dict[str, str]:
    """Field -> value for the From/To/Cc lines of the header block; tolerant of wrapped lines."""
    block = _header_block(text)
    out: dict[str, str] = {}
    matches = list(HEADER_KEY_RE.finditer(block))
    for i, m in enumerate(matches):
        key = m.group(1).lower()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(block)
        val = block[m.end():end].replace("\n", " ").strip()
        if key in ("from", "to", "cc", "bcc"):
            out[key] = (out.get(key, "") + "; " + val).strip("; ")
    return out


def _split_addresses(val: str) -> list[str]:
    parts, buf, depth, quoted = [], [], 0, False
    for ch in val:
        if ch == '"':
            quoted = not quoted
        elif ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        if ch in ",;" and not quoted and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def normalize_name(display: str) -> str | None:
    """'Shankman  Jeffrey A.' / 'Tyler, Amber' / 'Dr. Leon Adeyemi' / 'Ken Lay - Office of the Chairman' -> 'First Last'."""
    s = display.strip().strip('"').strip("'").strip()
    if "<" in s:
        s = s.split("<", 1)[0].strip().strip('"').strip()
    if not s or "@" in s:
        return None
    s = s.split(" - ", 1)[0].strip()
    s = re.sub(r"\s*\((?:State|E-mail|EOG|GOV|Gov|[A-Z]{2,})\)\s*$", "", s)  # 'Susan Albershardt (State)'
    s = re.sub(r"\s*\[.*?\]\s*", " ", s).strip()
    if "," in s:
        last, first = s.split(",", 1)
        s = f"{first.strip()} {last.strip()}"
    elif "  " in s:  # Enron 'Last  First M.'
        last, first = s.split("  ", 1)
        s = f"{first.strip()} {last.strip()}"
    toks = [t for t in s.split() if t.lower() not in HONORIFICS and t.lower() not in SUFFIXES]
    toks = [t for t in toks if not (len(t.rstrip(".")) <= 1) and not (len(t) == 2 and t.endswith("."))]
    if len(toks) < 2 or len(toks) > 3:
        return None
    if len(toks) == 3:
        toks = [toks[0], toks[2]]  # drop middle name
    if any(t.lower().strip(".") in NAME_STOP for t in toks):
        return None
    if not all(TOKEN_RE.match(t) and len(t) >= 2 for t in toks):
        return None
    if toks[0].isupper() or toks[1].isupper():  # ALL CAPS fragments ('FW', 'RE', org acronyms)
        return None
    return f"{toks[0]} {toks[1]}"


def names_in_doc(text: str) -> set[str]:
    out: set[str] = set()
    for val in header_fields(text).values():
        for a in _split_addresses(val):
            n = normalize_name(a)
            if n:
                out.add(n)
    for m in CHAT_LINE_RE.finditer(text):
        n = normalize_name(m.group(1))
        if n:
            out.add(n)
    return out


def name_tiers(docs: list[dict], rng: random.Random, per_tier: int = 10) -> list[tuple[str, str, int]]:
    """(name, tier, doc_frequency); tiers: top (ranks 1-10), mid (11-40), tail (frequency <= 2)."""
    freq: Counter = Counter()
    for d in docs:
        for n in names_in_doc(d["text"]):
            freq[n] += 1
    ranked = sorted(freq, key=lambda n: (-freq[n], n))  # deterministic across processes (set order is not)
    top = ranked[:per_tier]
    mid_pool = ranked[per_tier:per_tier + 30]
    mid = rng.sample(mid_pool, min(per_tier, len(mid_pool)))
    tail_pool = [n for n, c in freq.items() if c <= 2 and n not in top and n not in mid]
    tail = rng.sample(sorted(tail_pool), min(per_tier, len(tail_pool)))
    return [(n, "top", freq[n]) for n in top] + [(n, "mid", freq[n]) for n in mid] + [(n, "tail", freq[n]) for n in tail]


# ------------------------------------------------------------------------------------------------ verbatim

QUOTE_RE = re.compile(
    r"^(?:\s*-{3,}\s*(?:Original Message|Forwarded|Original Appointment)|\s*From:\s|\s*Sent:\s|\s*To:\s|\s*Subject:\s"
    r"|_{5,}|>|On .{5,120} wrote:|\s*-{5,}\s*$|\s*\*{5,})",
    re.M,
)
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-\.]*")


def split_doc(text: str) -> tuple[str, str]:
    """(header, body). Emails: header block up to first blank line. Chat logs / bare text: no header."""
    if "\n\n" in text:
        head, body = text.split("\n\n", 1)
        if HEADER_KEY_RE.search(head) or head.startswith("Contract:") or head.startswith("["):
            return head.strip(), body.strip()
    return "", text.strip()


def body_region(body: str) -> str:
    """Body up to the first quoted-reply / forwarded-header marker."""
    m = QUOTE_RE.search(body)
    return body[: m.start()].rstrip() if m else body


VERBATIM_CUT = 0.45                                # default hand-off point: fraction of the body region used as prefix
VERBATIM_ALT_CUTS = (0.60, 0.30, 0.75)             # fall-back windows tried (in order) when the default window is boilerplate


def make_verbatim_item(doc: dict, corpus: str, min_chars: int = 700, target_words: int = 60, cut_frac: float = VERBATIM_CUT) -> dict | None:
    head, body = split_doc(doc["text"])
    region = body_region(body)
    if len(region) < min_chars:
        return None
    words = list(WORD_RE.finditer(region))
    if len(words) < 160:
        return None
    # prefix: ~45% of the region (or an alternative hand-off point), clamped to [250, 1200] chars, cut at a word boundary
    cut = int(len(region) * cut_frac)
    cut = max(250, min(cut, 1200))
    cut = region.rfind(" ", 0, cut)
    if cut < 200:
        return None
    prefix_body = region[:cut].rstrip()
    rest = region[cut:].lstrip()
    rest_words = list(WORD_RE.finditer(rest))
    if len(rest_words) < target_words:
        return None
    target = rest[: rest_words[target_words - 1].end()]
    prefix = (head + "\n\n" + prefix_body) if head else prefix_body
    # a non-default window gets its own id, so the resumable run step treats it as a new item rather than reusing the old response
    suffix = "" if cut_frac == VERBATIM_CUT else f"#w{int(round(cut_frac * 100))}"
    return {
        "item_id": f"verbatim:{corpus}:{doc['id']}{suffix}",
        "probe": "verbatim",
        "corpus": corpus,
        "system": (
            "You are assisting with a text-completion memorisation audit. Follow the instructions exactly and "
            "output only the requested text."
        ),
        "user": (
            "Below is the beginning of a document from a public document collection. Write the text that "
            f"immediately follows it, about {target_words} words. If you recognise the document, reproduce the "
            "original continuation exactly as written. Otherwise write your best guess of how it continues. "
            "Output only the continuation: no preamble, quotation marks, or commentary.\n\n"
            f"<document_start>\n{prefix}\n</document_start>"
        ),
        "gold": {"target": target, "prefix": prefix},
        "meta": {"doc_id": doc["id"], "prefix_chars": len(prefix), "region_chars": len(region), "cut_frac": cut_frac},
    }


def _is_email_like(doc: dict, corpus: str) -> bool:
    if CORPORA[corpus]["kind"] != "email":
        return True
    if corpus == "enron" and doc.get("meta", {}).get("is_attachment"):
        return False
    head, _ = split_doc(doc["text"])
    return bool(HEADER_KEY_RE.search(head)) or head.startswith("[")


def _window_ok(w: dict, kind: str, df, screen_rows: dict[str, dict]) -> tuple[bool, str | None]:
    """Both pool filters on one window: the boilerplate rules, then the LLM screen (screen_rows: item_id -> screen row)."""
    from .boilerplate import boilerplate_reasons  # noqa: PLC0415
    from .screen import effective_class  # noqa: PLC0415

    rs = boilerplate_reasons(w["gold"]["prefix"], w["gold"]["target"], kind, df)
    if rs:
        return False, f"boilerplate:{rs[0]}"
    cls = effective_class(screen_rows.get(w["item_id"]), w["corpus"])
    if cls is None:
        return False, "unscreened"
    return cls == "original_internal", (None if cls == "original_internal" else cls)


def verbatim_items(corpus: str, docs: list[dict], rng: random.Random, n: int = 60, log=print, stats: dict | None = None,
                   existing: list[dict] | None = None, screen: bool = True) -> list[dict]:
    """The verbatim pool for one corpus: n windows that pass BOTH quality filters — the boilerplate rules (boilerplate.py) and the
    LLM screen (screen.py; only `original_internal` windows are kept) — drawn in a deterministic shuffle of the e-mail-like documents.

    `existing` are the corpus's windows from the current probe file. They are kept in the output unchanged, whether or not they pass
    (an excluded window keeps its id so the scorer and the review page can show it as excluded, with its responses), and only the
    shortfall is drawn as replacements: documents not already used, in shuffle order, in batches several times the shortfall; a
    document whose default window (45 % hand-off) fails is retried at the alternative hand-off points in VERBATIM_ALT_CUTS, and a
    non-default window gets a distinct id. Replacements carry meta.replacement = True. Rule look-ups and screen calls are batched;
    the screen is cached (results/contam/v_screen.jsonl), so re-building is free once judged."""
    from .boilerplate import CorpusIndex  # noqa: PLC0415
    from .screen import screen as run_screen  # noqa: PLC0415

    kind = CORPORA[corpus]["kind"]
    kinds = {c: CORPORA[c]["kind"] for c in CORPORA}
    index = CorpusIndex(corpus, docs=docs)
    pool = [d for d in docs if _is_email_like(d, corpus)]
    rng.shuffle(pool)
    rejected: Counter = Counter()

    def judge(windows: list[dict]) -> dict[str, tuple[bool, str | None]]:
        if not windows:
            return {}
        df = index.lookup([w["gold"]["target"] for w in windows] + [w["gold"]["prefix"][-400:] for w in windows], log=log)
        from .boilerplate import boilerplate_reasons  # noqa: PLC0415
        passed_rules = [w for w in windows if not boilerplate_reasons(w["gold"]["prefix"], w["gold"]["target"], kind, df)]
        rows = run_screen(passed_rules, kinds, log=log) if (screen and passed_rules) else {}
        return {w["item_id"]: _window_ok(w, kind, df, rows) for w in windows}

    # 1. the existing windows: kept in the file; count how many are in the pool
    existing = list(existing or [])
    verdict = judge(existing)
    kept_existing = [w for w in existing if verdict[w["item_id"]][0]]
    for w in existing:
        if not verdict[w["item_id"]][0]:
            rejected[verdict[w["item_id"]][1]] += 1
    used_docs = {w["meta"]["doc_id"] for w in existing}

    # 2. replacements for the shortfall
    out: list[dict] = list(existing)
    need = n - len(kept_existing)
    n_alt, pos, tried = 0, 0, 0
    new_kept: list[dict] = []
    while need > 0 and pos < len(pool):
        batch_docs = []
        for d in pool[pos: pos + max(30, 3 * need)]:
            if d["id"] not in used_docs:  # also de-duplicates a document that appears twice in the corpus file
                used_docs.add(d["id"])
                batch_docs.append(d)
        pos += max(30, 3 * need)
        cands = [[w for w in (make_verbatim_item(d, corpus, cut_frac=f) for f in (VERBATIM_CUT, *VERBATIM_ALT_CUTS)) if w] for d in batch_docs]
        cands = [ws for ws in cands if ws]
        tried += len(cands)
        v = judge([w for ws in cands for w in ws])
        for ws in cands:
            chosen = None
            for w in ws:
                ok, why = v[w["item_id"]]
                if ok:
                    chosen = w
                    break
                rejected[why] += 1
            if chosen is not None:
                chosen["meta"]["replacement"] = True
                new_kept.append(chosen)
                n_alt += chosen["meta"]["cut_frac"] != VERBATIM_CUT
                need -= 1
                if need <= 0:
                    break
    out += new_kept
    log(f"[verbatim] {corpus}: pool {len(kept_existing) + len(new_kept)}/{n} — {len(kept_existing)} of {len(existing)} existing windows kept, "
        f"{len(new_kept)} replacements from {tried} new documents ({n_alt} at an alternative hand-off point); rejected: {dict(rejected.most_common()) or 'none'}")
    if stats is not None:
        stats[corpus] = {"n_pool": len(kept_existing) + len(new_kept), "n_existing": len(existing), "n_existing_kept": len(kept_existing),
                         "n_replacements": len(new_kept), "docs_tried": tried, "alt_windows": n_alt, "rejected": dict(rejected.most_common())}
    return out


# ------------------------------------------------------------------------------------------------ entities

RECALL_SYSTEM = (
    "You answer factual questions about real people concisely. Do not guess: if you do not know the specific "
    "person asked about, answer exactly UNKNOWN."
)
RECOG_SYSTEM = "You answer factual yes/no questions about real people. Reply with exactly one word."


def entity_items(corpus: str, docs: list[dict], rng: random.Random) -> list[dict]:
    c = CORPORA[corpus]
    out = []
    tiers = [(n, t, None) for n, t in c["names"]] if c.get("names") else name_tiers(docs, rng)
    for name, tier, freq in tiers:
        base_meta = {"name": name, "tier": tier, "doc_freq": freq}
        out.append({
            "item_id": f"entity_recall:{corpus}:{name}",
            "probe": "entity_recall",
            "corpus": corpus,
            "system": RECALL_SYSTEM,
            "user": (
                f"Who is {name}, a person active around {c['era']}? Answer in one or two sentences naming the "
                "organisation(s) they were affiliated with and their role. If you do not know who this specific "
                "person is, answer exactly: UNKNOWN."
            ),
            "gold": {"org_keywords": c["org_keywords"], "true_corpus": corpus},
            "meta": base_meta,
        })
        for org in ENTITY_CORPORA:
            o = CORPORA[org]
            out.append({
                "item_id": f"entity_recog:{corpus}:{name}:{org}",
                "probe": "entity_recog",
                "corpus": corpus,
                "system": RECOG_SYSTEM,
                "user": (
                    f"Was {name}, a person active around {c['era']}, affiliated with {o['org_desc']}? "
                    "Answer with exactly one word: yes, no, or unknown."
                ),
                "gold": {"asked_org": org, "is_true_org": org == corpus},
                "meta": {**base_meta, "asked_org": org},
            })
    return out


# ------------------------------------------------------------------------------------------------ benchmark knowledge

TREC2016_TOPIC_KEYS: list[tuple[str, list[str]]] = [
    ("401 Summer Olympics", ["olympic"]), ("402 Space", ["space"]), ("403 Bottled Water", ["bottled water", "bottling"]),
    ("404 Eminent Domain", ["eminent domain"]), ("405 Newt Gingrich", ["gingrich"]), ("406 Felon Disenfranchisement", ["felon"]),
    ("407 Faith-Based Initiatives", ["faith-based", "faith based"]), ("408 Invasive Species", ["invasive species"]),
    ("409 Climate Change", ["climate change", "global warming"]), ("410 Condominiums", ["condominium", "condo"]),
    ("411 Stand Your Ground", ["stand your ground"]), ("412 2000 Recount", ["recount"]), ("413 James V. Crosby", ["crosby"]),
    ("414 Medicaid Reform", ["medicaid"]), ("415 George W. Bush", ["george w"]), ("416 Marketing", ["marketing", "advertis"]),
    ("417 Movie Gallery", ["movie gallery"]), ("418 War Preparations", ["iraq", "war preparation"]),
    ("419 Rilya Wilson", ["rilya", "foster child"]), ("420 Billboards", ["billboard"]), ("421 Traffic Cameras", ["traffic camera", "red-light camera", "red light camera"]),
    ("422 Non-Resident Aliens", ["non-resident alien", "nonresident alien", "non resident alien"]),
    ("423 National Rifle Association", ["national rifle", "nra"]), ("424 Gulf Drilling", ["offshore drilling", "off-shore drilling", "gulf drilling"]),
    ("425 Civil Rights Act of 2003", ["civil rights act"]), ("426 Jeffrey Goldhagen", ["goldhagen"]), ("427 Slot Machines", ["slot machine"]),
    ("428 New Stadiums and Arenas", ["stadium", "arena"]), ("429 Elian Gonzales", ["elian"]),
    ("430 Restraints and Helmets", ["helmet", "seat belt", "seatbelt"]), ("431 Agency Credit Ratings", ["credit rating"]),
    ("432 Gay Adoption", ["gay adoption"]), ("433 Abstinence", ["abstinence"]), ("434 Bacardi Trademark", ["bacardi"]),
]
LEGAL10_TOPIC_KEYS = [("301 Oil and gas drilling", ["drilling"]), ("302 Spill and blowout response", ["spill", "blowout"]),
                      ("303 Lobbying", ["lobby"]), ("304 Privilege", ["privilege"])]
LEGAL09_TOPIC_KEYS = [("201 Prepay transactions", ["prepay"]), ("202 FAS 140", ["fas 140", "fas140", "fas 125"]),
                      ("203 Financial forecasts", ["forecast", "projection"]), ("204 Document retention/destruction", ["retention", "destruction", "shredd"]),
                      ("205 Energy schedules and bids", ["schedul", "bids", "bidding"]), ("206 Financial analysts", ["analyst"]),
                      ("207 Fantasy football", ["fantasy football"])]
CUAD_CATEGORIES = [
    ("Document Name", ["document name"]), ("Parties", ["parties"]), ("Agreement Date", ["agreement date"]), ("Effective Date", ["effective date"]),
    ("Expiration Date", ["expiration date"]), ("Renewal Term", ["renewal term"]), ("Notice Period to Terminate Renewal", ["notice period"]),
    ("Governing Law", ["governing law"]), ("Most Favored Nation", ["most favored nation", "most favoured nation", "mfn"]), ("Non-Compete", ["non-compete", "noncompete", "non compete"]),
    ("Exclusivity", ["exclusivity"]), ("No-Solicit of Customers", ["solicit of customers", "solicitation of customers", "no-solicit"]), ("Competitive Restriction Exception", ["competitive restriction"]),
    ("No-Solicit of Employees", ["solicit of employees", "solicitation of employees"]), ("Non-Disparagement", ["disparagement"]), ("Termination for Convenience", ["termination for convenience"]),
    ("ROFR/ROFO/ROFN", ["rofr", "right of first refusal", "rofo", "rofn"]), ("Change of Control", ["change of control"]), ("Anti-Assignment", ["anti-assignment", "assignment"]),
    ("Revenue/Profit Sharing", ["revenue/profit sharing", "profit sharing", "revenue sharing"]), ("Price Restrictions", ["price restriction"]), ("Minimum Commitment", ["minimum commitment"]),
    ("Volume Restriction", ["volume restriction"]), ("IP Ownership Assignment", ["ip ownership"]), ("Joint IP Ownership", ["joint ip"]), ("License Grant", ["license grant"]),
    ("Non-Transferable License", ["non-transferable license", "non-transferable"]), ("Affiliate License-Licensor", ["affiliate license"]), ("Affiliate License-Licensee", ["licensee"]),
    ("Unlimited/All-You-Can-Eat License", ["unlimited", "all-you-can-eat", "all you can eat"]), ("Irrevocable or Perpetual License", ["irrevocable", "perpetual"]),
    ("Source Code Escrow", ["source code escrow"]), ("Post-Termination Services", ["post-termination"]), ("Audit Rights", ["audit rights", "audit"]), ("Uncapped Liability", ["uncapped liability"]),
    ("Cap on Liability", ["cap on liability", "liability cap"]), ("Liquidated Damages", ["liquidated damages"]), ("Warranty Duration", ["warranty duration", "warranty"]),
    ("Insurance", ["insurance"]), ("Covenant Not to Sue", ["covenant not to sue"]), ("Third Party Beneficiary", ["third party beneficiary", "third-party beneficiary"]),
]
NEWSGROUPS_20 = [
    ("alt.atheism", ["atheism"]), ("comp.graphics", ["comp.graphics", "graphics"]), ("comp.os.ms-windows.misc", ["ms-windows", "ms_windows"]),
    ("comp.sys.ibm.pc.hardware", ["ibm.pc", "ibm pc"]), ("comp.sys.mac.hardware", ["mac.hardware", "mac hardware"]), ("comp.windows.x", ["windows.x"]),
    ("misc.forsale", ["forsale"]), ("rec.autos", ["autos"]), ("rec.motorcycles", ["motorcycles"]), ("rec.sport.baseball", ["baseball"]),
    ("rec.sport.hockey", ["hockey"]), ("sci.crypt", ["crypt"]), ("sci.electronics", ["electronics"]), ("sci.med", ["sci.med"]),
    ("sci.space", ["sci.space"]), ("soc.religion.christian", ["christian"]), ("talk.politics.guns", ["guns"]),
    ("talk.politics.mideast", ["mideast"]), ("talk.politics.misc", ["politics.misc"]), ("talk.religion.misc", ["religion.misc"]),
]
UNKNOWN_MARKERS = [
    "unknown", "i don't know", "i do not know", "not aware", "no information", "not familiar", "cannot identify",
    "unable to identify", "no record", "fictional", "hypothetical", "does not appear to", "doesn't appear to",
    "i'm not able to find", "i am not able to find", "cannot find", "can't find", "not a real", "no public record",
    "i don't have", "i do not have", "not something i", "no knowledge", "isn't a real", "is not a real", "made up",
    "no such", "not exist", "no verifiable", "cannot verify", "can't verify", "unable to verify",
]

BENCH_SYSTEM = "You answer questions about research datasets and benchmarks from memory, as specifically as you can. If you do not know, say so plainly."


def bench_knowledge_items() -> list[dict]:
    qs = [
        ("trec2016", "jebbush",
         "The TREC 2016 Total Recall track used a test collection called 'athome4', built from the e-mails of Florida Governor Jeb Bush. "
         "List as many of its topics as you can recall (topic numbers and titles).",
         {"keys": TREC2016_TOPIC_KEYS}),
        ("legal10", "enron",
         "The TREC 2010 Legal Track Interactive task had topics 301 to 304, framed as requests for production against the Enron collection. "
         "Describe each topic (number and subject).",
         {"keys": LEGAL10_TOPIC_KEYS}),
        ("legal09", "enron",
         "The TREC 2009 Legal Track Interactive task had topics 201 to 207, framed as requests for production against the Enron collection. "
         "Describe each topic (number and subject).",
         {"keys": LEGAL09_TOPIC_KEYS}),
        ("cuad", "cuad",
         "List the clause categories (label types) annotated in the Contract Understanding Atticus Dataset (CUAD).",
         {"keys": CUAD_CATEGORIES}),
        ("oida_mnk", "mnk",
         "What is the Mallinckrodt document collection in the Opioid Industry Documents Archive? Say who hosts the archive, "
         "where the documents came from, and roughly when they were made public.",
         {"keys": [("UCSF", ["ucsf", "university of california"]), ("Johns Hopkins", ["johns hopkins"]),
                   ("opioid litigation", ["litigation", "settlement", "mdl", "bankruptcy", "lawsuit"]),
                   ("industry documents library", ["industry documents"])]}),
        ("veridian", "veridian",
         "What is the Veridian Orthopedics ApexHip matter? Describe the company, the product, and the litigation or regulatory action it is known for.",
         {"keys": [], "control": True}),
        ("newsgroups20", "canon",
         "List the 20 categories (newsgroup names) of the 20 Newsgroups text-classification dataset.",
         {"keys": NEWSGROUPS_20}),
        ("oida_endo", "endo",
         "What is the Endo document collection in the Opioid Industry Documents Archive? Say who hosts the archive, "
         "where the documents came from, and roughly when they were made public.",
         {"keys": [("UCSF", ["ucsf", "university of california"]), ("Johns Hopkins", ["johns hopkins"]),
                   ("Endo bankruptcy / settlement", ["bankruptcy", "chapter 11", "settlement", "litigation", "mdl", "lawsuit"]),
                   ("industry documents library", ["industry documents"])]}),
    ]
    return [{
        "item_id": f"bench_knowledge:{corpus}:{qid}",
        "probe": "bench_knowledge",
        "corpus": corpus,
        "system": BENCH_SYSTEM,
        "user": text,
        "gold": gold,
        "meta": {"question": qid},
    } for qid, corpus, text, gold in qs]


# ------------------------------------------------------------------------------------------------ label recall

TREC_KEY_TO_TOPIC = {
    "gw_bush": ("415", "George W. Bush"), "movie_gallery": ("417", "Movie Gallery"), "faith_based": ("407", "Faith-Based Initiatives"),
    "marketing": ("416", "Marketing"), "condominiums": ("410", "Condominiums"), "medicaid_reform": ("414", "Medicaid Reform"),
    "recount_2000": ("412", "2000 Recount"), "rilya_wilson": ("419", "Lost Foster Child Rilya Wilson"), "bottled_water": ("403", "Bottled Water"),
    "eminent_domain": ("404", "Eminent Domain"), "nra_rifle": ("423", "National Rifle Association (NRA)"), "nra_aliens": ("422", "Non-Resident Aliens (NRA)"),
}
LABEL_SYSTEM = "You recall facts about published research datasets. Reply with exactly one word."


def _label_prompt(collection_sentence: str, doc_phrase: str, topic_phrase: str) -> str:
    return (
        f"{collection_sentence} According to those published judgments, was {doc_phrase} judged relevant to "
        f"{topic_phrase}? You must answer with exactly one word, relevant or not_relevant; if unsure, give your best guess."
    )


def _balanced_pairs(pos: list[tuple], neg: list[tuple], rng: random.Random, n: int) -> list[tuple]:
    """n pairs, balanced 50/50 *within every topic* (element [1] of each tuple), so that the topic named in the
    prompt carries no label information: a model answering from topic prevalence alone scores exactly 50%."""
    by_pos: dict = defaultdict(list)
    by_neg: dict = defaultdict(list)
    for p in pos:
        by_pos[p[1]].append(p)
    for q in neg:
        by_neg[q[1]].append(q)
    topics = sorted(t for t in by_pos if t in by_neg)
    out: list[tuple] = []
    # round-robin one positive + one negative per topic until n is reached
    pools = {t: (rng.sample(by_pos[t], len(by_pos[t])), rng.sample(by_neg[t], len(by_neg[t]))) for t in topics}
    while len(out) < n and topics:
        for t in list(topics):
            ps, ns = pools[t]
            if not ps or not ns:
                topics.remove(t)
                continue
            out.append(ps.pop())
            out.append(ns.pop())
            if len(out) >= n:
                break
    return out[:n]


def label_items(rng: random.Random, n_per_corpus: int = 100) -> list[dict]:
    out: list[dict] = []

    # Jeb Bush / TREC 2016: eval_ids manifest (labels only, no text needed)
    pos, neg = [], []
    rows = [json.loads(l) for l in (ROOT / "data/trec/eval_ids.jsonl").open()]
    keys = list(TREC_KEY_TO_TOPIC)
    for r in rows:
        docno = r["meta"]["docno"]
        for k in keys:
            if k in r["labels"]:
                pos.append((docno, k))
            elif r["meta"].get("stratum") in ("random", "hard_neg") and not r["labels"]:
                neg.append((docno, k))
    for docno, k in _balanced_pairs(pos, neg, rng, n_per_corpus):
        num, title = TREC_KEY_TO_TOPIC[k]
        gold = "relevant" if (docno, k) in set(pos) else "not_relevant"
        out.append({
            "item_id": f"label_recall:jebbush:{docno}:{k}", "probe": "label_recall", "corpus": "jebbush", "system": LABEL_SYSTEM,
            "user": _label_prompt(
                "The TREC 2016 Total Recall track (test collection athome4, the Jeb Bush e-mail collection) published relevance judgments (qrels).",
                f"document number {docno}", f"topic {num}, \"{title}\""),
            "gold": {"answer": gold}, "meta": {"docno": docno, "topic": num},
        })

    # Enron / TREC Legal 2010: legal10.jsonl labels
    l10_topics = json.load((ROOT / "data/legal10/topics.json").open())["topics"]
    pos, neg = [], []
    with (ROOT / "data/legal10/legal10.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            if r["gray"]:
                continue
            t = r["meta"]["topic"]
            key = l10_topics[t]["key"]
            lab = r["labels"].get(key)
            (pos if lab == "responsive" else neg).append((r["meta"]["docid"], t))
    pos_set = set(pos)
    for docid, t in _balanced_pairs(pos, neg, rng, n_per_corpus):
        out.append({
            "item_id": f"label_recall:enron:{docid}:{t}", "probe": "label_recall", "corpus": "enron", "system": LABEL_SYSTEM,
            "user": _label_prompt(
                "The TREC 2010 Legal Track Interactive task (EDRM Enron v2 collection) published relevance assessments (qrels).",
                f"document {docid}", f"topic {t}, \"{l10_topics[t]['title']}\""),
            "gold": {"answer": "relevant" if (docid, t) in pos_set else "not_relevant"}, "meta": {"docid": docid, "topic": t},
        })

    # Mallinckrodt: our panel labels were never published -> must be chance (control)
    import yaml  # noqa: PLC0415
    mnk_task = yaml.safe_load((ROOT / "tasks/mallinckrodt.yaml").open())["questions"]
    pos, neg = [], []
    with (ROOT / "data/mallinckrodt/mnk.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            for q in mnk_task:
                if q in r["gray"]:
                    continue
                (pos if r["labels"].get(q) == "responsive" else neg).append((r["id"], q, r["meta"].get("bates", "")))
    pos_set = {(a, b) for a, b, _ in pos}
    for did, q, bates in _balanced_pairs(pos, neg, rng, n_per_corpus):
        out.append({
            "item_id": f"label_recall:mnk:{did}:{q}", "probe": "label_recall", "corpus": "mnk", "system": LABEL_SYSTEM,
            "user": _label_prompt(
                "The Mallinckrodt collection of the Opioid Industry Documents Archive has been used as a document-review benchmark with published responsiveness labels.",
                f"document {did} (Bates {bates})", f"the issue \"{mnk_task[q]['title']}\""),
            "gold": {"answer": "relevant" if (did, q) in pos_set else "not_relevant"}, "meta": {"doc_id": did, "question": q},
        })

    # Veridian: synthetic -> chance (control)
    ver_task = yaml.safe_load((ROOT / "tasks/veridian.yaml").open())["questions"]
    pos, neg = [], []
    with (ROOT / "data/veridian/veridian.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            for q in ver_task:
                if q in r["gray"]:
                    continue
                (pos if r["labels"].get(q) == "responsive" else neg).append((r["id"], q))
    pos_set = set(pos)
    for did, q in _balanced_pairs(pos, neg, rng, n_per_corpus):
        out.append({
            "item_id": f"label_recall:veridian:{did}:{q}", "probe": "label_recall", "corpus": "veridian", "system": LABEL_SYSTEM,
            "user": _label_prompt(
                "The Veridian Orthopedics ApexHip eDiscovery benchmark published responsiveness labels for its documents.",
                f"document {did}", f"request \"{ver_task[q]['title']}\""),
            "gold": {"answer": "relevant" if (did, q) in pos_set else "not_relevant"}, "meta": {"doc_id": did, "question": q},
        })

    # Titanic (positive control): PassengerId + name -> Survived. Balanced within the name's title (Mr / Mrs / Miss /
    # Master / other) so that the sex and age the title reveals carry no label information; the only route to > 50%
    # is having memorised the rows of train.csv.
    import csv  # noqa: PLC0415
    _, rows = load_titanic_rows()
    pos, neg = [], []
    for r in csv.reader(rows):
        pid, survived, name = r[0], r[1], r[3]
        tm = re.search(r",\s*([A-Za-z]+)\.", name)
        title = tm.group(1) if tm and tm.group(1) in ("Mr", "Mrs", "Miss", "Master") else "other"
        (pos if survived == "1" else neg).append((pid, title, name))
    pos_set = {p[0] for p in pos}
    for pid, title, name in _balanced_pairs(pos, neg, rng, n_per_corpus):
        out.append({
            "item_id": f"label_recall:titanic:{pid}", "probe": "label_recall", "corpus": "titanic", "system": LABEL_SYSTEM,
            "user": (
                "The Kaggle competition 'Titanic: Machine Learning from Disaster' distributes a public training file "
                "(train.csv, 891 passengers) whose Survived column is 1 or 0. In that file, what is the Survived value for "
                f"PassengerId {pid}, \"{name}\"? You must answer with exactly one word, survived or died; if unsure, give your best guess."
            ),
            "gold": {"answer": "relevant" if pid in pos_set else "not_relevant", "vocab": {"relevant": "survived", "not_relevant": "died"}},
            "meta": {"passenger_id": pid, "topic": title, "name": name},
        })

    # Endo (held-out, labelled 2026-10): labels never published -> must be chance, like Mallinckrodt and Veridian. Appended
    # after Titanic so the earlier corpora's draws from `rng` are unchanged and existing item ids stay stable.
    endo_path = ROOT / "data/endo/endo.jsonl"
    if endo_path.exists():
        endo_task = yaml.safe_load((ROOT / "tasks/endo.yaml").open())["questions"]
        pos, neg = [], []
        with endo_path.open() as f:
            for line in f:
                r = json.loads(line)
                for q in endo_task:
                    if q in r["gray"]:
                        continue
                    (pos if r["labels"].get(q) == "responsive" else neg).append((r["id"], q, r["meta"].get("bates", "")))
        pos_set = {(a, b) for a, b, _ in pos}
        for did, q, bates in _balanced_pairs(pos, neg, rng, n_per_corpus):
            out.append({
                "item_id": f"label_recall:endo:{did}:{q}", "probe": "label_recall", "corpus": "endo", "system": LABEL_SYSTEM,
                "user": _label_prompt(
                    "The Endo collection of the Opioid Industry Documents Archive has been used as a document-review benchmark with published responsiveness labels.",
                    f"document {did} (Bates {bates})", f"the issue \"{endo_task[q]['title']}\""),
                "gold": {"answer": "relevant" if (did, q) in pos_set else "not_relevant"}, "meta": {"doc_id": did, "question": q},
            })
    return out


# ------------------------------------------------------------------------------------------------ main

def build(out_path: Path = OUT_DIR / "probes.jsonl", n_verbatim: int = 60, seed: int = 7, log=print,
          existing_path: Path | None = OUT_DIR / "probes.jsonl", screen: bool = True) -> Path:
    """Build the probe file. Verbatim windows already in `existing_path` are kept (excluded ones included, so their responses stay
    visible as excluded) and only the shortfall of the quality-filtered pool is drawn afresh; see verbatim_items."""
    rng = random.Random(seed)
    items: list[dict] = []
    existing_v: dict[str, list[dict]] = defaultdict(list)
    if existing_path and existing_path.exists():
        for line in existing_path.open():
            it = json.loads(line)
            if it["probe"] == "verbatim":
                existing_v[it["corpus"]].append(it)
    docs_by_corpus: dict[str, list[dict]] = {}
    for corpus in CORPORA:
        if "file" in CORPORA[corpus] and not (ROOT / CORPORA[corpus]["file"]).exists():
            log(f"{corpus}: {CORPORA[corpus]['file']} not built yet; skipped")
            continue
        docs_by_corpus[corpus] = load_docs(corpus)
        log(f"{corpus}: {len(docs_by_corpus[corpus]):,} documents with text")
    v_stats: dict = {}
    for corpus in docs_by_corpus:
        v = verbatim_items(corpus, docs_by_corpus[corpus], random.Random(seed + 1), n_verbatim, log=log, stats=v_stats,
                           existing=existing_v.get(corpus), screen=screen)
        log(f"  verbatim {corpus}: {len(v)} items in file, {v_stats[corpus]['n_pool']} in pool")
        items += v
    for corpus in ENTITY_CORPORA:
        if corpus not in docs_by_corpus:
            continue
        e = entity_items(corpus, docs_by_corpus[corpus], random.Random(seed + 2))
        names = sorted({(i["meta"]["name"], i["meta"]["tier"], i["meta"]["doc_freq"] or 0) for i in e if i["probe"] == "entity_recall"}, key=lambda x: -x[2])
        log(f"  entities {corpus}: {len(names)} names -> {len(e)} items")
        for n, t, f in names:
            log(f"      {t:4s} {f:6d}  {n}")
        items += e
    items += bench_knowledge_items()
    lab = label_items(random.Random(seed + 3))
    log(f"  label_recall: {len(lab)} items ({Counter(i['corpus'] for i in lab)})")
    items += lab
    from .matter import matter_items  # noqa: PLC0415
    items += matter_items(random.Random(seed + 4), log=log)
    from .ladder import LADDER, footprint, ladder_items  # noqa: PLC0415
    items += ladder_items()
    log(f"  ladder: {len(LADDER)} real matters at graded exposure (M0 + M1 each)")
    footprint(log=log)  # Wikipedia exposure proxy; cached in data/contam/raw/wiki_footprint.json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    by = Counter((i["probe"], i["corpus"]) for i in items)
    log(f"wrote {out_path} ({len(items)} items)")
    for (p, c), n in sorted(by.items()):
        log(f"  {p:16s} {c:10s} {n}")
    return out_path
