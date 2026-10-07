"""Per-contract renaming for the CUAD arm (round 2). No LLM in the loop.

Each contract gets its own deterministic mapping (seeded from its index) covering the things that make a public EDGAR
exhibit *retrievable* without touching the legal content the twelve clause categories depend on:

  organisations   every "Proper Name <corporate suffix>" (Inc., Corp., LLC, Ltd., GmbH, plc, …) found anywhere in the
                  contract, plus the party short names derived from them ("Harpoon Therapeutics, Inc." → "Harpoon") when the
                  short name is not an ordinary English word, plus the EDGAR company token in the excerpt header
  people          names in signature / notice blocks ("By: /s/ Jane Doe", "Name:", "Attention:") → surnames via names.fake_surname
  products        tokens marked ® / ™ and quoted defined terms whose first word is not an English word (brand-like)
  jurisdictions   U.S. state names → a different state, one mapping per contract (abbreviations and cities are left alone)
  dates           every full date and standalone year shifted by a whole number of years (−3…+3, never 0) so durations and
                  ordering inside the contract are unchanged
  dollar amounts  numeric amounts ($, US$, USD) rescaled by a per-contract factor and re-rounded to the original roundness,
                  except where the amount is also spelled out in words ("One Million Dollars ($1,000,000)"), which are left
                  alone so the words and the figure stay consistent

Role aliases ("Licensor", "Buyer", "the Company", "Effective Date") are legal content and are never renamed. Replacement
preserves case shape (LOHA → VELTRA, Loha → Veltra). The mapping is saved to data/ablation/cuad_mapping.json.
"""
from __future__ import annotations

import hashlib
import random
import re
from collections import Counter

from .names import Renamer, _shape, fake_surname

SUFFIX = (r"(?:Inc\.?|Incorporated|Corp\.?|Corporation|LLC|L\.L\.C\.|Ltd\.?|Limited|L\.P\.|LP|LLP|plc|PLC|Co\.|Company|GmbH|S\.A\.|N\.V\.|B\.V\.|AG"
          r"|S\.p\.A\.|Pty\.? Ltd\.?|S\.A\.S\.|SARL|S\.r\.l\.|K\.K\.|Co\., Ltd\.?|CO\., LTD\.?|N\.A\.)")
ORG_RE = re.compile(rf"\b((?:[A-Z][A-Za-z0-9&'\-\.]*,?\s+){{1,6}}){SUFFIX}(?![A-Za-z])")
ORG_CAPS_RE = re.compile(rf"\b((?:[A-Z][A-Z0-9&'\-\.]+,?\s+){{1,6}}){SUFFIX}(?![A-Za-z])")
SUFFIX_WORDS = {"inc", "incorporated", "corp", "corporation", "llc", "ltd", "limited", "lp", "llp", "plc", "co", "company", "gmbh", "sa", "nv", "bv", "ag",
                "spa", "pty", "sas", "sarl", "srl", "kk", "na"}
GENERIC_LEAD = {"general", "american", "national", "international", "united", "first", "new", "global", "north", "south", "east", "west", "central",
                "pacific", "atlantic", "western", "eastern", "northern", "southern", "royal", "standard", "universal", "advanced", "applied", "world"}
SIG_RE = re.compile(r"(?:By|Name|Attn|Attention|Title of Signatory|Signed)\s*:\s*(?:/s/\s*)?([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?))")
TM_RE = re.compile(r"\b([A-Z][A-Za-z0-9\-]{2,})\s?[®™]")
DEFINED_RE = re.compile(r"[\"“]([A-Z][A-Za-z0-9\-]+(?:\s+[A-Z][A-Za-z0-9\-]+){0,2})[\"”]")
HEADER_RE = re.compile(r"^(Contract: .*?)\(([^()]+?)(?:,\s*((?:19|20)\d{2}))?\)\s*$", re.M)
SOURCE_RE = re.compile(r"^Source: (.+?),\s*([A-Z0-9/\-]+),\s*(\d{1,2}/\d{1,2}/\d{4})\s*$", re.M)

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_LONG_RE = re.compile(rf"\b({MONTHS})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+((?:19|20)\d{{2}})\b")
DATE_DMY_RE = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:day of\s+)?({MONTHS}),?\s+((?:19|20)\d{{2}})\b")
DATE_MY_RE = re.compile(rf"\b({MONTHS}),?\s+((?:19|20)\d{{2}})\b")
DATE_NUM_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/((?:19|20)\d{2}|\d{2})\b")
DATE_ISO_RE = re.compile(r"\b((?:19|20)\d{2})-(\d{2})-(\d{2})\b")
YEAR_RE = re.compile(r"(?<![\d/\-])((?:19[5-9]|20[0-3])\d)(?![\d/\-])")
MONEY_RE = re.compile(r"(?:US\$|U\.S\.\$|\$|USD\s?|US\s?\$)\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?")
WORDS_NUM = re.compile(r"\b(million|thousand|hundred|billion|dollars?)\b", re.I)

US_STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii",
             "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
             "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
             "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
             "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]
STATE_RE = re.compile(r"\b(" + "|".join(sorted(US_STATES, key=len, reverse=True)) + r")\b")

# defined terms that are legal roles / generic nouns, never renamed even when capitalised
ROLE_TERMS = {"agreement", "effective", "company", "term", "party", "parties", "licensor", "licensee", "buyer", "seller", "purchaser", "supplier",
              "distributor", "customer", "franchisor", "franchisee", "agent", "principal", "recipient", "sponsor", "member", "board", "territory",
              "products", "product", "services", "software", "system", "shares", "common", "code", "sec", "commission", "royalty", "addendum",
              "trademarks", "marks", "confidential", "information", "business", "closing", "exhibit", "schedule", "section", "article", "annex",
              "contractor", "consultant", "manufacturer", "vendor", "client", "provider", "reseller", "developer", "owner", "operator", "lender",
              "borrower", "guarantor", "indemnifying", "indemnified", "disclosing", "receiving", "breaching", "beneficiary", "trustee", "issuer",
              "holder", "investor", "underwriter", "bank", "association", "insurance", "payment", "users", "reports", "data", "network", "content",
              "field", "specifications", "deliverables", "work", "invention", "inventions", "know-how", "patents", "patent", "improvements", "the",
              "nda", "prc", "gaap", "fda", "irs", "epa", "usa", "u.s.", "united", "states", "america", "europe", "asia", "china", "japan", "canada",
              "exclusive", "nonexclusive", "non-exclusive", "initial", "renewal", "extended", "franchised", "franchise", "promissory", "note",
              "registration", "statement", "purchase", "order", "orders", "quarter", "year", "month", "week", "day", "days", "date", "dates",
              "net", "gross", "sales", "revenue", "cost", "costs", "fee", "fees", "price", "prices", "minimum", "maximum", "annual", "monthly",
              "launch", "approval", "milestone", "milestones", "development", "research", "program", "plan", "budget", "study", "studies", "trial",
              "trials", "phase", "regulatory", "commercialization", "commercialisation", "manufacturing", "supply", "distribution", "marketing",
              "license", "licensed", "licence", "compound", "compounds", "candidate", "candidates", "generic", "biosimilar", "third", "first", "second",
              "joint", "steering", "committee", "escrow", "security", "interest", "collateral", "default", "event", "events", "change", "control",
              "force", "majeure", "governing", "law", "jurisdiction", "arbitration", "notice", "notices", "assignment", "survival", "severability",
              "entire", "amendment", "waiver", "counterparts", "headings", "definitions", "interpretation", "background", "recitals", "whereas",
              "now", "therefore", "witnesseth", "in", "witness", "whereof", "general", "miscellaneous", "term", "termination", "expiration",
              "renewal", "cause", "convenience", "insolvency", "bankruptcy", "liability", "limitation", "damages", "indemnification", "indemnity",
              "warranty", "warranties", "representations", "covenants", "compliance", "audit", "records", "books", "inspection", "taxes", "tax"}

_PRE = ["Veltra", "Norwick", "Calder", "Ashmere", "Brennan", "Lindqvist", "Tarrow", "Oakhurst", "Quillon", "Marrowby", "Fenwick", "Halvane",
        "Corvane", "Stratton", "Zelmor", "Ravelin", "Orbyn", "Kestrel", "Dunmore", "Peltier", "Wexley", "Thornby", "Garrow", "Ellsworth", "Brixton",
        "Caldera", "Mireval", "Solvane", "Tremont", "Ardenne", "Keswick", "Lorimar", "Navarre", "Ostrava", "Pellbrook", "Rathmore", "Selwyn",
        "Tanager", "Umbria", "Vantor", "Wyvern", "Yarrow", "Aldric", "Belmar", "Crestway", "Dorrance", "Everly", "Falkner", "Greyson", "Holbrook"]
_MID = ["", " Holdings", " Technologies", " Systems", " Partners", " Industries", " Labs", " Sciences", " Group", " Networks", " Therapeutics",
        " Media", " Energy", " Capital", " Ventures", " Logistics", " Biosciences", " Devices", " Global", " International"]
_PROD = ["Zenvar", "Orbiq", "Lumetra", "Vastrel", "Kinova", "Tessaro", "Pyrall", "Nexilon", "Quorva", "Brivant", "Caldex", "Soltair", "Verdane",
         "Mirabel", "Axtra", "Helion", "Rivanna", "Corvex", "Daltrex", "Fenova", "Galvex", "Istral", "Jovane", "Keltrix", "Lorvane", "Novexa",
         "Opaline", "Pravex", "Quintar", "Ravenna", "Sylvex", "Tarvix", "Ultrix", "Vexaro", "Wrenly", "Xandor", "Ystara", "Zorvex"]


def _system_words() -> set[str]:
    from pathlib import Path
    p = Path("/usr/share/dict/words")
    if not p.exists():
        return set()
    return {w.strip().lower() for w in p.read_text(errors="ignore").split("\n") if w and len(w) >= 3}


ENGLISH = _system_words()


def _h(s: str) -> int:
    return int(hashlib.md5(s.lower().encode()).hexdigest(), 16)


def _is_english(tok: str) -> bool:
    """English word in any common inflection (Commercializing, Losses, Divested, Indemnitees) or a legal role term."""
    t = tok.lower().strip(".,'’-")
    if t in ENGLISH or t in ROLE_TERMS:
        return True
    for suf, rep in (("ies", "y"), ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("es", ""), ("s", ""), ("d", ""), ("ees", "ee"), ("ly", "")):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            stem = t[: -len(suf)]
            if (stem + rep) in ENGLISH:
                return True
            if len(stem) >= 4 and stem[-1] == stem[-2] and stem[:-1] in ENGLISH:  # controlled -> control, shipping -> ship
                return True
    return False


def _is_acronym(tok: str) -> bool:
    return tok.isupper() and len(tok) <= 5 and tok.isalpha()


def _fake_org(base: str, taken: set[str], rng: random.Random) -> str:
    """A fake company base name, deterministic in the real base name; different real bases get different fakes."""
    h = _h(base)
    for k in range(300):
        cand = _PRE[(h + 13 * k) % len(_PRE)] + (_MID[(h // 7 + 3 * k) % len(_MID)] if len(base.split()) > 1 else "")
        if cand.lower() not in taken and cand.lower() != base.lower():
            taken.add(cand.lower())
            return cand
    return f"Company{h % 1000}"


def _fake_product(name: str, taken: set[str]) -> str:
    h = _h(name)
    for k in range(200):
        cand = _PROD[(h + 11 * k) % len(_PROD)]
        if cand.lower() not in taken and cand.lower() != name.lower():
            taken.add(cand.lower())
            return cand
    return f"Product{h % 1000}"


LEAD_STOP = {"the", "this", "a", "an", "any", "such", "each", "either", "between", "among", "and", "by", "of", "to", "with", "from", "whereas",
             "agreement", "contract", "licensor", "licensee", "buyer", "seller", "supplier", "distributor", "company", "customer", "client",
             "vendor", "franchisor", "franchisee", "sponsor", "party", "parties", "or", "for", "as", "at", "in", "on", "that", "if", "section",
             "article", "exhibit", "schedule", "date", "name", "address", "attention", "attn", "re", "cc", "subject", "source", "notwithstanding"}
MID_CUT = {"the", "this", "a", "an", "and", "between", "among", "by", "whereas", "with", "from", "to", "or", "as", "at", "in", "on", "that", "if",
           "any", "such", "each", "either", "notwithstanding", "company", "licensor", "licensee", "buyer", "seller", "agreement", "contract"}
SIG_STOP = {"fax", "phone", "email", "e-mail", "tel", "telephone", "address", "number", "title", "date", "signature", "counsel", "esq"}


def _base_of(org: str) -> str:
    """'WHEREAS Shenzhen LOHAS Supply Chain Management Co., Ltd.' -> 'Shenzhen LOHAS Supply Chain Management' (suffix and leading
    stop / role words removed)."""
    b = re.sub(rf"\s*{SUFFIX}\s*$", "", org.strip().rstrip(","))
    b = re.sub(rf",?\s*{SUFFIX}\s*$", "", b)  # 'Co., Ltd.' leaves 'Co.,'
    toks = b.strip(" ,.").split()
    norm = lambda t: re.sub(r"['’]s$", "", t.lower().strip(".,:;"))  # noqa: E731
    # a connective inside the run marks where the name starts ("CEO The National Football League Alumni", "AFFIRMATION AND EXECUTION Novo …")
    for i in range(len(toks) - 1, -1, -1):
        if norm(toks[i]) in MID_CUT:
            toks = toks[i + 1:]
            break
    while toks and norm(toks[0]) in LEAD_STOP:
        toks.pop(0)
    return " ".join(toks).strip(" ,.")


def _short_names(base: str, full: str) -> list[str]:
    """Candidate short names of a party: the leading distinctive token(s) of its base name. An English first word ("Harpoon",
    "Phoenix") still counts when the contract uses it standalone as a name at least three times."""
    toks = base.replace(",", "").split()
    out = []
    if not toks:
        return out
    first = toks[0].strip(".")
    if len(first) >= 3 and first.lower() not in ROLE_TERMS and first.lower() not in GENERIC_LEAD and not _is_acronym(first):
        if not _is_english(first):
            out.append(first)
        elif len(re.findall(rf"\b{re.escape(first)}\b(?!\s+{re.escape(toks[1]) if len(toks) > 1 else 'XXXX'})", full)) >= 3:
            out.append(first)
    if len(toks) >= 2 and not all(_is_english(t) for t in toks[:2]) and toks[1].lower() not in SUFFIX_WORDS:
        out.append(" ".join(toks[:2]))
    return out


def _valid_base(base: str, count: int = 1) -> bool:
    toks = base.replace(",", " ").split()
    if not toks or len(toks) > 6:
        return False
    if re.sub(r"['’]s$", "", toks[0].lower()) in ROLE_TERMS:
        return False  # "Company's Products"
    if any(t.lower().strip(".") in SUFFIX_WORDS for t in toks):
        return False  # "AG, Syngenta", "Limited Liability"
    if any(t.endswith(".") and len(t) > 3 for t in toks[:-1]):
        return False  # a run that crossed a sentence boundary ("Products. SECTION THIRTEEN. INDEMNITY")
    if any(re.fullmatch(r"[A-Z]\.|[IVX]+\.|\d+\.", t) for t in toks):
        return False  # "E. Affiliated", "FOURTEEN. SPECIAL"
    if all(_is_english(t) for t in toks) and len(toks) <= 2 and count < 2:
        return False  # "Information Technology", "Corporation Service" (mentioned once); "Harpoon Therapeutics" recurs and is kept
    if all(_is_acronym(t) or _is_english(t) for t in toks) and len(toks) == 1:
        return False
    return True


class ContractRenamer:
    """One contract's mapping: phrases (orgs, short names, products, states, header token), people, date shift, money factor."""

    def __init__(self, contract_idx: int, texts: list[str]):
        self.idx = contract_idx
        self.rng = random.Random(1000 + contract_idx)
        full = "\n".join(texts)
        taken: set[str] = set()
        phrases: dict[str, str] = {}
        orgs: Counter = Counter()
        canon: dict[str, str] = {}  # lower-case base -> first spelling seen
        for rx in (ORG_RE, ORG_CAPS_RE):
            for m in rx.finditer(full):
                org = m.group(0).strip().rstrip(",")
                base = _base_of(org)
                if base:
                    canon.setdefault(base.lower(), base)
                    orgs[base.lower()] += 1
        bases = sorted((b for b in orgs if _valid_base(canon[b], orgs[b])), key=lambda b: (-len(b), b))
        fakes: dict[str, str] = {}
        for bl in bases:
            base = canon[bl]
            # a base that extends an already-mapped base ("Harpoon Therapeutics" vs "Harpoon") shares its fake prefix
            fake = None
            for b2, f2 in fakes.items():
                if bl.startswith(b2.lower() + " "):
                    fake = f2 + base[len(b2):]
                    break
            if fake is None:
                fake = _fake_org(base, taken, self.rng)
            fakes[base] = fake
            phrases[base] = fake
            for s in _short_names(base, full):
                if s.lower() not in {k.lower() for k in phrases} and s.lower() != bl:
                    sf = fake.split()[0] if len(s.split()) == 1 else " ".join(fake.split()[: len(s.split())]) or fake.split()[0]
                    phrases[s] = sf
                    taken.add(sf.lower())
        # header company token: "Contract: Supply Agreement (LohaCompanyltd, 2019)"
        self.header_fake: dict[str, str] = {}
        for m in HEADER_RE.finditer(full):
            co = m.group(2).strip()
            if co and co not in self.header_fake:
                self.header_fake[co] = (_fake_org(co, taken, self.rng)).replace(" ", "")
        # products: ®/™ and brand-like quoted defined terms
        prods: Counter = Counter()
        for m in TM_RE.finditer(full):
            prods[m.group(1)] += 1
        for m in DEFINED_RE.finditer(full):
            term = m.group(1)
            first = term.split()[0]
            # brand-like: one word, not English in any inflection, not a bare acronym (CEO, CT), not already a party name
            if len(term.split()) == 1 and len(first) >= 4 and not _is_english(first) and not _is_acronym(first) \
                    and first.lower() not in {p.lower() for p in phrases}:
                prods[term] += 1
        for p in prods:
            if p.lower() in {k.lower() for k in phrases}:
                continue
            phrases[p] = _fake_product(p, taken)
        # states: one permutation per contract
        states_here = sorted(set(STATE_RE.findall(full)))
        if states_here:
            pool = [s for s in US_STATES if s not in states_here]
            self.rng.shuffle(pool)
            for s, t in zip(states_here, pool):
                phrases[s] = t
        # people in signature blocks
        people: dict[str, str] = {}
        ptaken: set[str] = set()
        for m in SIG_RE.finditer(full):
            sur = m.group(2)
            if len(sur) >= 3 and sur not in people and not _is_english(sur) and sur.lower() not in SIG_STOP and sur.lower() not in {k.lower() for k in phrases}:
                people[sur] = fake_surname(sur, ptaken)
        self.phrases = phrases
        self.people = people
        self.rn = Renamer(phrases, people, set(), []) if (phrases or people) else None
        # dates and money
        self.year_shift = self.rng.choice([-3, -2, -1, 1, 2, 3])
        self.money_factor = self.rng.choice([0.6, 0.75, 0.85, 1.15, 1.3, 1.5])
        self.n_sub = 0

    # ---- passes
    def _shift_year(self, y: str) -> str:
        yi = int(y) if len(y) == 4 else (2000 + int(y) if int(y) < 50 else 1900 + int(y))
        return str(yi + self.year_shift) if len(y) == 4 else f"{(yi + self.year_shift) % 100:02d}"

    def _dates(self, text: str) -> str:
        """Shift every date's year once. Rewritten dates are parked behind sentinels so the standalone-year pass cannot shift them again."""
        parked: list[str] = []

        def park(s: str) -> str:
            parked.append(s)
            self.n_sub += 1
            return f"\x00{len(parked) - 1}\x00"

        text = DATE_LONG_RE.sub(lambda m: park(f"{m.group(1)} {m.group(2)}, {self._shift_year(m.group(3))}"), text)
        text = DATE_DMY_RE.sub(lambda m: park(m.group(0)[: m.start(3) - m.start()] + self._shift_year(m.group(3))), text)
        text = DATE_MY_RE.sub(lambda m: park(f"{m.group(1)} {self._shift_year(m.group(2))}"), text)
        text = DATE_NUM_RE.sub(lambda m: park(f"{m.group(1)}/{m.group(2)}/{self._shift_year(m.group(3))}"), text)
        text = DATE_ISO_RE.sub(lambda m: park(f"{self._shift_year(m.group(1))}-{m.group(2)}-{m.group(3)}"), text)
        text = YEAR_RE.sub(lambda m: park(self._shift_year(m.group(1))), text)  # standalone years (fiscal 2019, the 2019 budget)
        return re.sub(r"\x00(\d+)\x00", lambda m: parked[int(m.group(1))], text)

    def _money(self, text: str) -> str:
        def rep(m):
            start = max(0, m.start() - 70)
            if WORDS_NUM.search(text[start:m.start()]) or WORDS_NUM.search(text[m.end():m.end() + 40]):
                return m.group(0)  # spelled out nearby: leave figure and words consistent
            raw = m.group(1).replace(",", "")
            try:
                v = int(raw)
            except ValueError:
                return m.group(0)
            if v < 10:
                return m.group(0)
            # roundness: number of trailing zeros in the original
            tz = len(raw) - len(raw.rstrip("0")) if raw.strip("0") else 0
            unit = 10 ** max(0, min(tz, len(raw) - 1))
            nv = max(unit, int(round(v * self.money_factor / unit)) * unit)
            s = f"{nv:,}" if "," in m.group(1) or nv >= 10000 else str(nv)
            self.n_sub += 1
            return m.group(0)[: m.start(1) - m.start()] + s + (m.group(2) or "")
        return MONEY_RE.sub(rep, text)

    def _header(self, text: str) -> str:
        """'Contract: Supply Agreement (LohaCompanyltd, 2019)': the company token is replaced here; the year is shifted by _dates
        with every other year. ('Source: LOHA CO. LTD., F-1, 12/9/2019' lines go through the phrase map and the date pass.)"""
        def rep(m):
            co = m.group(2).strip()
            fake = self.header_fake.get(co, co)
            yr = f", {m.group(3)}" if m.group(3) else ""
            self.n_sub += 1
            return f"{m.group(1)}({fake}{yr})"
        return HEADER_RE.sub(rep, text)

    def apply(self, text: str) -> str:
        self.n_sub = 0
        text = self._header(text)
        if self.rn is not None:
            before = text
            text = self.rn.apply(text)
            self.n_sub += sum(1 for a, b in zip(before.split(), text.split()) if a != b)
        text = self._dates(text)
        text = self._money(text)
        return text

    def info(self) -> dict:
        return {"phrases": self.phrases, "people": self.people, "header": self.header_fake, "year_shift": self.year_shift,
                "money_factor": self.money_factor}
