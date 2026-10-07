"""Knowledge-bearing names and the renaming engine (no LLM in the loop).

Three layers, applied in order so that longer matches win:
  1. phrases    — organisations, special-purpose entities, code names, products, domains (case-insensitive, longest first)
  2. full names — "First Last", "Last, First" for every mapped person
  3. surnames   — a capitalised surname anywhere; a lower-case surname only inside e-mail-like tokens (first.last@…, domains);
                  surnames that are also ordinary English words are only replaced next to a first name or on header lines

Replacement preserves case shape (Fastow→Hallam, FASTOW→HALLAM, fastow→hallam). Mapping is deterministic (seeded) and
saved to data/ablation/mapping.json so every arm and the request text use the same substitutions.
"""
from __future__ import annotations

import hashlib
import re

# ------------------------------------------------------------------------------------------------ Enron: curated

# organisation / entity phrases: real → fake. Order does not matter; longest match is applied first.
ENRON_PHRASES: dict[str, str] = {
    "ENE": "VTN", "ENE.N": "VTN.N", "EnronOnline": "VolteronOnline", "ENRONONLINE": "VOLTERONONLINE", "eHRonline": "eHRonline",
    "Enron Corporation": "Volteron Corporation", "Enron Corp.": "Volteron Corp.", "Enron Corp": "Volteron Corp",
    "Enron North America Corp.": "Volteron North America Corp.", "Enron North America": "Volteron North America",
    "Enron Energy Services": "Volteron Energy Services", "Enron Wholesale Services": "Volteron Wholesale Services",
    "Enron Broadband Services": "Volteron Broadband Services", "Enron Global Markets": "Volteron Global Markets",
    "Enron Global Finance": "Volteron Global Finance", "Enron Capital & Trade": "Volteron Capital & Trade",
    "Enron Capital and Trade": "Volteron Capital and Trade", "Enron Credit": "Volteron Credit", "Enron Online": "Volteron Online",
    "EnronOnline": "VolteronOnline", "Enron Industrial Markets": "Volteron Industrial Markets", "Enron Americas": "Volteron Americas",
    "Enron Europe": "Volteron Europe", "Enron Metals": "Volteron Metals", "Enron Net Works": "Volteron Net Works",
    "Enron Transportation Services": "Volteron Transportation Services", "Enron Power Marketing": "Volteron Power Marketing",
    "Enron Oil & Gas": "Volteron Oil & Gas", "Enron Oil and Gas": "Volteron Oil and Gas", "Enron Field": "Volteron Field",
    "Enron": "Volteron", "enron.com": "volteron.com", "enron.net": "volteron.net", "ENRON": "VOLTERON",
    "Portland General Electric": "Cascade General Electric", "Portland General": "Cascade General", "PGE": "CGE",
    "Northern Natural Gas": "Prairie Natural Gas", "Transwestern Pipeline": "Transplateau Pipeline", "Transwestern": "Transplateau",
    "Florida Gas Transmission": "Gulf Coast Gas Transmission", "Azurix": "Aquarel", "Dabhol": "Ratnagar", "Wessex Water": "Severn Water",
    "Arthur Andersen LLP": "Albert Harwood LLP", "Arthur Andersen": "Albert Harwood", "Andersen Consulting": "Harwood Consulting",
    "Vinson & Elkins": "Vance & Ellory", "Vinson and Elkins": "Vance and Ellory", "V&E": "V&L",
    "Dynegy": "Dynatrix", "Mahonia": "Marrowby", "Delta Energy Corporation": "Gamma Energy Corporation", "Delta Energy": "Gamma Energy",
    "Yosemite Securities": "Shenandoah Securities", "Yosemite": "Shenandoah", "Chewco Investments": "Brixco Investments", "Chewco": "Brixco",
    "LJM Cayman": "HLM Cayman", "LJM2": "HLM2", "LJM 2": "HLM 2", "LJM": "HLM", "Raptor": "Tercel", "Raptors": "Tercels", "Talon": "Spur",
    "Whitewing": "Greyfeather", "Osprey Trust": "Kittiwake Trust", "Osprey": "Kittiwake", "Marlin Water": "Sailfin Water", "Marlin": "Sailfin",
    "Condor": "Harrier", "JEDI": "VEDA", "Jedi": "Veda", "Braveheart": "Stoutheart", "Rhythms NetConnections": "Cadence NetConnections",
    "Rhythms": "Cadence", "Swap Sub": "Swap Vehicle", "Southampton Place": "Northbridge Place", "Southampton": "Northbridge",
    "Death Star": "Dark Moon", "Fat Boy": "Big Lad", "Get Shorty": "Go Short", "Ricochet": "Rebound", "Project Summer": "Project Autumn",
    "Project Nahanni": "Project Tundra", "Nahanni": "Tundra", "Cuiaba": "Marapo", "Cuiabá": "Marapo", "Teesside": "Humberside",
    "Houston Natural Gas": "Gulf Natural Gas", "InterNorth": "MidPlains", "Enron Prize": "Volteron Prize",
    # abbreviations used in Lotus Notes addresses and prose
    "ECT": "VCT", "EES": "VES", "ENA": "VNA", "EBS": "VBS", "EGM": "VGM", "EWS": "VWS", "EOTT": "VOTT", "EGF": "VGF",
}

# people: real surname → fake surname. First names are kept (a first name alone carries little case knowledge).
ENRON_PEOPLE: dict[str, str] = {
    "Lay": "Sorrell", "Skilling": "Hallam", "Fastow": "Marchetti", "Causey": "Pembrook", "Glisan": "Thornley", "Kopper": "Vanterpool",
    "Watkins": "Ashcombe", "McMahon": "Redfern", "Whalley": "Grafton", "Delainey": "Oakeshott", "Belden": "Stroud", "Forney": "Larkin",
    "Pai": "Varga", "Baxter": "Lindqvist", "Rice": "Calloway", "Hannon": "Brennan", "Derrick": "Mortlake", "Buy": "Everly",
    "Frevert": "Hollis", "Horton": "Wexford", "Kean": "Ashby", "Lavorato": "Castellan", "Kitchen": "Harwell", "Dasovich": "Petrakis",
    "Shapiro": "Lindgren", "Steffes": "Rutherford", "Mordaunt": "Fairweather", "Olson": "Nystrom", "Mintz": "Feldman",
    "Duncan": "Pruitt", "Temple": "Whitlock", "Odom": "Haskell", "Bass": "Treadwell", "Bauer": "Keller", "Berardino": "Castiglione",
    "Ebbers": "Ebbers",  # not Enron; listed so the engine does not touch it
    "Winokur": "Lindauer", "Jaedicke": "Pemberton", "Gramm": "Holloway", "Mendelsohn": "Arnstein", "Wakeham": "Ashworth", "Belfer": "Stern",
    "Blake": "Carver", "Chan": "Leung", "Duncan,": "Pruitt,", "Mark": "Travers", "Hirko": "Ransome", "Koenig": "Baumann", "Sutton": "Ferris",
    "Bowen": "Garrity", "Boyle": "Harrigan", "Howard": "Pettigrew", "Yeager": "Stenson", "Shelby": "Maddox", "Hughes": "Latimer",
    "Mintz,": "Feldman,", "Cooper": "Blanchard", "Hermann": "Albrecht", "Rogers": "Dunmore", "Sherrick": "Tolliver", "Despain": "Leclair",
    "Lynn": "Marlow", "Kinder": "Rosen", "Sunde": "Hagen", "Haedicke": "Weldon", "Kaminski": "Novak", "Dietrich": "Falk",
}

# first names that identify the famous executives when paired with the surname; kept, but listed so the full-name layer sees them
ENRON_FIRST = ["Ken", "Kenneth", "Jeff", "Jeffrey", "Andy", "Andrew", "Rick", "Richard", "Ben", "Michael", "Sherron", "Greg", "David",
               "Dave", "Tim", "Lou", "Cliff", "Clifford", "Rebecca", "Mark", "Stan", "Stanley", "Steve", "Steven", "John", "Louise", "Nancy"]

# surnames that are also ordinary words: replaced only next to a first name or on header lines
COMMON_WORD_SURNAMES = {"Lay", "Rice", "Buy", "Kitchen", "Mark", "Temple", "Bass", "Cooper", "Howard", "Baxter", "Blake", "Chan",
                        "Lynn", "Kinder", "Horton", "Hughes", "Rogers", "Bowen", "Boyle", "Sutton", "Shelby", "Kean", "Hannon", "Derrick",
                        "Duncan", "Baker", "Taylor", "Jones", "Cox", "Gould", "Beck", "Brown", "White", "Green", "Hall", "Young", "King",
                        "Hill", "Wood", "Stone", "Long", "Short", "Price", "Day", "May", "Bell", "Love", "Grant", "Ward", "Fox", "Wolf",
                        "Bush", "Fields", "Banks", "Lane", "Park", "Berry", "Fish", "Bird", "Rose", "Reed", "Snow", "Frost", "Marsh",
                        "Dean", "Sage", "Church", "Moody", "Savage", "Little", "Best", "Good", "Wise", "Strong", "Power", "Chase", "Case",
                        "Call", "Carter", "Miller", "Smith", "Turner", "Mason", "Walker", "Hunter", "Fisher", "Cook", "Hunt", "Bolt", "Fast",
                        "Sweet", "Sharp", "Swift", "Gay", "Golden", "Silver", "Diamond", "Pearl", "Star", "Sun", "Moon", "Storm", "Rain",
                        "Summer", "Winter", "Spring", "Fall", "North", "South", "East", "West", "Mann", "Street", "Bridge", "Castle", "Tower"}

# ------------------------------------------------------------------------------------------------ Veridian: fictional → different fictional

VERIDIAN_PHRASES: dict[str, str] = {
    "Veridian Orthopedics, Inc.": "Corvane Orthopedics, Inc.", "Veridian Orthopedics": "Corvane Orthopedics", "VERIDIAN ORTHOPEDICS": "CORVANE ORTHOPEDICS",
    "Veridian": "Corvane", "VERIDIAN": "CORVANE", "veridianortho.com": "corvaneortho.com", "veridian.com": "corvane.com",
    "veridianortho": "corvaneortho",  # URL stems other than .com (veridianortho.service-desk)
    "ApexHip": "SummitHip", "APEXHIP": "SUMMITHIP", "Apex Registry": "Summit Registry", "KneeFlex": "FlexKnee", "ClassicHip": "HeritageHip",
    # v2 (2026-10-06 renamer audit): the bare short forms were missing, so renamed documents still said "Apex reserve", "Apex
    # booth", "Northgate", "Aegis" beside "SummitHip" / "Westgate Health" / "Argus Specialty". Longest match wins, so ApexHip and
    # Apex Registry are still handled by their own entries.
    "Apex": "Summit", "APEX": "SUMMIT", "Northgate": "Westgate", "Meridian": "Zenith", "Aegis": "Argus",
    "ShoulderPro": "ShoulderMax", "KinetiCoat": "MotiCoat", "TrackWise": "TraceLine",
    "Northgate Health System": "Westgate Health System", "Northgate Health": "Westgate Health", "northgatehealth.org": "westgatehealth.org",
    "Meridian Testing Labs": "Zenith Testing Labs", "Meridian Testing": "Zenith Testing", "meridiantestinglabs.com": "zenithtestinglabs.com",
    "Kessler Reid": "Kaufer Reade", "kesslerreid.com": "kauferreade.com", "Aegis Specialty Insurance": "Argus Specialty Insurance",
    "Aegis Specialty": "Argus Specialty", "aegisspecialty.com": "argusspecialty.com", "Ibarra Surgical": "Isandro Surgical", "ibarrasurgical.com": "isandrosurgical.com",
    "Atlanta Joint Institute": "Savannah Joint Institute", "atlantajointinstitute.com": "savannahjointinstitute.com", "atlantajoint.com": "savannahjoint.com",
    "Whitfield Barr": "Wakeford Bellamy", "whitfieldbarr.com": "wakefordbellamy.com", "Nashville Hip & Knee": "Memphis Hip & Knee", "Nashville Hip and Knee": "Memphis Hip and Knee",
    "nashvillehipknee.com": "memphishipknee.com", "nashvillehipandknee.com": "memphishipandknee.com", "Denver Ortho": "Boulder Ortho", "denverortho.com": "boulderortho.com",
    "Orthopedic Device News Weekly": "Orthopedic Device Monitor", "orthodevicenews.com": "orthodevicemonitor.com", "Rocky Mountain Orthopedics": "High Plains Orthopedics",
    "Denver Presbyterian Hospital": "Boulder Presbyterian Hospital", "Denver Regional Medical": "Boulder Regional Medical", "Stratton Medical": "Stanwick Medical",
    "Coastal Health": "Harbor Health", "NorthBridge Medical": "EastBridge Medical", "MDL No. 3102": "MDL No. 3185", "MDL 3102": "MDL 3185",
    "V-2200": "C-4100", "V-2299": "C-4199", "V-22": "C-41",
}

VERIDIAN_PEOPLE: dict[str, str] = {
    "Mendes": "Ferreira", "Okonkwo": "Adebayo", "Raman": "Iyer", "Lee": "Han", "Whitfield": "Wakeford", "Tran": "Pham", "Mitchell": "Harlan",
    "Park": "Cho", "Shah": "Mehta", "Halvorsen": "Lindqvist", "Kim": "Yoon", "Berg": "Dahl", "Ruiz": "Ortega", "Steinberg": "Rosenthal",
    "Novak": "Horvath", "Nguyen": "Duong", "Castellano": "Moretti", "Kowalski": "Zielinski", "Ibarra": "Isandro", "Kessler": "Kaufer",
    "Reid": "Reade", "Adeyemi": "Olawale", "Whitaker": "Winslow", "Vance": "Garrow", "Feld": "Brandt", "Rao": "Menon", "Martin": "Marchand",
    "Grant": "Granger", "Doyle": "Devlin", "Anand": "Arora", "Barr": "Bellamy",
}
# v2 (2026-10-06): Nguyen→Duong (was Pham-Le, sharing a token with Tran→Pham); Barr→Bellamy (was a no-op).
VERIDIAN_COMMON = {"Lee", "Park", "Kim", "Grant", "Martin", "Berg", "Reid", "Shah", "Tran", "Vance"}
# v2: surnames that must be replaced wherever they appear even though a word list may class them as ordinary words. Feld and Rao
# (the consulting surgeons named in the requests) were in the common-word class, so "Dr. Feld", "Feld's" and bare "Rao" survived in
# 109 renamed documents while the renamed requests said Brandt and Menon. Mitchell ("D. Mitchell", named in a request) likewise.
VERIDIAN_FORCE_RARE = {"Feld", "Rao", "Mitchell", "Barr", "Castellano", "Tran", "Vance", "Shah", "Berg", "Reid"}
# v2: role words that header parsing mistook for names ("General Counsel", "Quality Manager" in From: lines), which produced
# "General Wexham" and "Quality Harhurst". Never surnames, never first names.
ROLE_WORDS = {"Counsel", "Manager", "Director", "Officer", "President", "Engineer", "General", "Quality", "Marketing", "Client",
              "Regulatory", "Legal", "Affairs", "Compliance", "Finance", "Sales", "Clinical", "Operations", "Support", "Admin",
              "Administrator", "Assistant", "Associate", "Partner", "Chief", "Vice", "Senior", "Team", "Group", "Desk", "Help"}

# ------------------------------------------------------------------------------------------------ fake surname generator

_PRE = ["Har", "Lind", "Mor", "Bren", "Cal", "Thorn", "Ash", "Red", "Graf", "Oak", "Strou", "Lar", "Var", "Pem", "Wex", "Cas", "Pet", "Ruth",
        "Fair", "Nys", "Feld", "Whit", "Has", "Tread", "Kel", "Cast", "Stan", "Hol", "Mar", "Bal", "Dun", "Gar", "Lat", "Mad", "Sten", "Tol",
        "Lec", "Ros", "Hag", "Wel", "Nov", "Fal", "Ken", "Tor", "Vel", "Bar", "Cor", "Del", "Fen", "Gal", "Hen", "Jor", "Kir", "Lan", "Mel",
        "Nor", "Orm", "Per", "Quin", "Ran", "Sal", "Tar", "Ulr", "Ver", "Win", "Yar", "Zel", "Ald", "Bris", "Crom", "Dray", "Els", "Fors", "Gris"]
_SUF = ["low", "berg", "ley", "ton", "nan", "well", "by", "ford", "wick", "mont", "ridge", "sen", "man", "ham", "ard", "stone", "dale", "worth",
        "field", "croft", "more", "bury", "wood", "land", "ster", "ing", "ner", "vale", "holm", "gate", "shaw", "cott", "hurst", "mere", "burn"]


def fake_surname(real: str, taken: set[str]) -> str:
    h = int(hashlib.md5(real.lower().encode()).hexdigest(), 16)
    for k in range(200):
        cand = _PRE[(h + k * 7) % len(_PRE)] + _SUF[(h // 97 + k * 3) % len(_SUF)]
        if cand not in taken and cand.lower() != real.lower():
            taken.add(cand)
            return cand
    return f"{real[0]}{h % 10000:04d}"


# ------------------------------------------------------------------------------------------------ the engine

HEADER_LINE_RE = re.compile(r"^\s*>?\s*(From|To|Cc|CC|cc|Bcc|BCC|bcc|X-From|X-To|X-cc|X-bcc|X-Folder|X-Origin|X-FileName|Sent by|Sent)\s*:", re.M)
FIRST_NAME_RE = r"[A-Z][a-z]+\.?(?:\s+[A-Z]\.?)?"  # First or First M.


def _shape(src: str, repl: str) -> str:
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src.islower():
        return repl.lower()
    return repl


class Renamer:
    def __init__(self, phrases: dict[str, str], people: dict[str, str], common: set[str], firsts: list[str] | None = None):
        self.phrases = dict(phrases)
        self.people = {k.rstrip(","): v.rstrip(",") for k, v in people.items() if k.rstrip(",")}
        self.common = {c for c in common}
        self.firsts = set(firsts or [])
        self._compile()

    def _compile(self):
        keys = sorted(self.phrases, key=len, reverse=True)
        self.phrase_re = re.compile("|".join(rf"(?<![A-Za-z0-9]){re.escape(k)}(?![A-Za-z0-9])" for k in keys), re.I) if keys else None
        # when a phrase is curated in several cases ("Enron"/"ENRON") keep the mixed-case replacement; _shape handles case
        self.phrase_lut = {}
        for k, v in sorted(self.phrases.items(), key=lambda kv: kv[0].isupper()):
            self.phrase_lut.setdefault(k.lower(), v)
        # three classes of surname: rare (replace wherever capitalised); common English words (header lines or full-name
        # position); first-name-like (Bruce, James, Martin: full-name position only, so first names are never touched)
        firstlike = {s for s in self.people if s in self.firsts}
        rare = [s for s in self.people if s not in self.common and s not in firstlike]
        comm = [s for s in self.people if s in self.common and s not in firstlike]
        # v2 (2026-10-06): alphanumeric look-arounds instead of \b so that an underscore counts as a boundary
        # (attachment names such as Feld_Consulting_Agreement.docx were being skipped)
        self.rare_re = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(s) for s in sorted(rare, key=len, reverse=True)) + r")(?![A-Za-z0-9])", re.I) if rare else None
        self.comm_re = re.compile(r"\b(" + "|".join(re.escape(s) for s in sorted(comm, key=len, reverse=True)) + r")\b") if comm else None
        self.email_re = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+|\b[a-z0-9]+(?:\.[a-z0-9]+)+\b")
        self.people_lut = {k.lower(): v for k, v in self.people.items()}
        allp = "|".join(re.escape(s) for s in sorted(self.people, key=len, reverse=True))
        # "First Last", "First M. Last", "Last, First". For common-word surnames the first name must be a known first name
        # (so "Floating Price" or "Total Cash" are left alone); otherwise any capitalised token will do.
        if self.firsts:
            fr = "(?:" + "|".join(re.escape(f) for f in sorted(self.firsts, key=len, reverse=True)) + r")\.?(?:\s+[A-Z]\.?)?"
        else:
            fr = FIRST_NAME_RE
        self.full_re = re.compile(rf"\b({fr})\s+({allp})\b") if allp else None
        self.rev_re = re.compile(rf"\b({allp}),\s+({fr})") if allp else None
        # v2 (2026-10-06): a title or a bare initial before a common-word surname is also a name position ("Dr. Feld", "Mr. Park",
        # "D. Mitchell", "M. Lee"); previously only full names and header lines were, so these survived in body text.
        commp = "|".join(re.escape(s) for s in sorted(comm, key=len, reverse=True))
        self.title_re = re.compile(rf"\b((?:Drs|Dr|Mr|Ms|Mrs|Prof|Gov|Sen|Rep|Hon)\.?\s+|[A-Z]\.\s+)({commp})\b") if commp else None
        self.zlid_re = re.compile(r"(zl-edrm-[a-z]+-v2-)([a-z]+)(-[a-z]-)")

    def add_people(self, mapping: dict[str, str]):
        self.people.update(mapping)
        self._compile()

    # --- passes
    def _phr(self, m):
        return _shape(m.group(0), self.phrase_lut[m.group(0).lower()])

    def _sur(self, m):
        return _shape(m.group(1), self.people_lut[m.group(1).lower()])

    def apply(self, text: str) -> str:
        if self.phrase_re:
            text = self.phrase_re.sub(self._phr, text)
        if self.full_re:
            text = self.full_re.sub(lambda m: f"{m.group(1)} {_shape(m.group(2), self.people_lut[m.group(2).lower()])}", text)
            text = self.rev_re.sub(lambda m: f"{_shape(m.group(1), self.people_lut[m.group(1).lower()])}, {m.group(2)}", text)
        if self.title_re:
            text = self.title_re.sub(lambda m: f"{m.group(1)}{_shape(m.group(2), self.people_lut[m.group(2).lower()])}", text)
        if self.rare_re:
            # capitalised anywhere; lower-case only inside e-mail-like tokens (handled below) — so here require a capital
            text = self.rare_re.sub(lambda m: self._sur(m) if m.group(1)[0].isupper() else m.group(0), text)
        # lower-case surnames inside e-mail addresses / dotted tokens (first.last@…, lastf@…, domains)
        def fix_email(m):
            tok = m.group(0)
            low = tok.lower()
            for s in sorted(self.people, key=len, reverse=True):
                sl = s.lower()
                if s in self.firsts:
                    continue  # mark.koenig@: 'mark' is a first name here
                if len(sl) >= 4 and sl in low:
                    # surname at the end of a token, preceded by at most one letter (jmills@, bruce.mills@) — not inside "franklin"
                    low = re.sub(rf"(?<![a-z][a-z]){re.escape(sl)}(?![a-z])", self.people_lut[sl].lower(), low)
                elif len(sl) == 3 and sl in low:
                    # v2 (2026-10-06): three-letter surnames (Lee, Kim, Rao) only when they end the local part (mlee@, skim@, arao@);
                    # before this the display name was renamed and the address beside it was not
                    low = re.sub(rf"(?<![a-z][a-z]){re.escape(sl)}(?=[@.]|\d|$)", self.people_lut[sl].lower(), low)
            return low if low != tok.lower() else tok
        text = self.email_re.sub(fix_email, text)
        if self.comm_re:
            # common-word surnames: header lines only (full-name forms were handled above)
            out = []
            for line in text.split("\n"):
                if HEADER_LINE_RE.match(line) or "/HOU/" in line or "/Corp/" in line or "/NA/" in line or "/ENRON@" in line.upper():
                    line = self.comm_re.sub(self._sur, line)
                out.append(line)
            text = "\n".join(out)
        # Exchange aliases: CN=PLOVE, CN=Jgosset, CN=Mgarcia6 (initial + surname [+ digits])
        def fix_cn(m):
            init, sur, num = m.group(1), m.group(2), m.group(3)
            fake = self.people_lut.get(sur.lower())
            if fake is None and len(sur) > 4:
                fake = self.people_lut.get(sur[1:].lower())  # two-letter initials: CN=JMLOVE
                if fake is not None:
                    init, sur = init + sur[0], sur[1:]
            if fake is None:
                return m.group(0)
            return f"CN={init}{_shape(sur, fake)}{num}"
        text = re.sub(r"CN=([A-Za-z])([A-Za-z]{3,})(\d*)(?=[>/\s,;)]|$)", fix_cn, text)
        # custodian mailbox id in the EDRM X-ZLID header (zl-edrm-enron-v2-kean-s-1234.eml)
        text = self.zlid_re.sub(lambda m: m.group(1) + self.people_lut.get(m.group(2), m.group(2)).lower() + m.group(3), text)
        # catch-all: the company name embedded inside routing tokens (+40ENRON@, @EnronXGate, EnronCredit.com, enron2000)
        for k, v in self.catchall.items():
            text = re.sub(re.escape(k), lambda m: _shape(m.group(0), v), text, flags=re.I)
        return text

    catchall: dict[str, str] = {}

    def count_hits(self, text: str) -> int:
        """How many knowledge-bearing substitutions the text would receive (dose for the dose–response analysis)."""
        n = 0
        if self.phrase_re:
            n += len(self.phrase_re.findall(text))
        if self.rare_re:
            n += sum(1 for m in self.rare_re.finditer(text) if m.group(1)[0].isupper())
        return n


# ------------------------------------------------------------------------------------------------ header-name extraction

NAME_PATTERNS = [
    re.compile(r"\b([A-Z][a-z]+)\s+(?:[A-Z]\.?\s+)?([A-Z][a-z]+(?:-[A-Z][a-z]+)?)/(?:HOU|NA|Corp|ET|LON|EU|ENRON)", ),  # Lotus: First Last/HOU/ECT
    re.compile(r"^(?:From|To|Cc|X-From|X-To|X-cc|X-bcc):\s*(.+)$", re.M),
    re.compile(r"-----\s*Forwarded by ([A-Z][a-z]+ (?:[A-Z]\.? )?[A-Z][a-z]+)"),
]
PERSON_TOKEN = re.compile(r"^([A-Z][a-z]+)\s+(?:[A-Z]\.?\s+)?([A-Z][a-z]+(?:-[A-Z][a-z]+)?)$")
PERSON_REV = re.compile(r"^([A-Z][a-z]+(?:-[A-Z][a-z]+)?),\s+([A-Z][a-z]+)")
EMAIL_LOCAL = re.compile(r"\b([a-z]+)\.([a-z]{3,})@")


def header_surnames(texts: list[str], min_count: int = 1) -> dict[str, int]:
    """Surnames of people appearing in header fields / Lotus Notes addresses / forwarding lines across the texts."""
    from collections import Counter

    c: Counter = Counter()
    for t in texts:
        for m in NAME_PATTERNS[0].finditer(t):
            c[m.group(2)] += 1
        for m in NAME_PATTERNS[2].finditer(t):
            c[m.group(1).split()[-1]] += 1
        for m in NAME_PATTERNS[1].finditer(t):
            field = re.sub(r"<[^>]*>|\([^)]*\)|\"|'", " ", m.group(1))
            for part in re.split(r"[;,]\s*(?=[A-Z])|,\s+(?=[A-Z][a-z]+\s+[A-Z])|\s{2,}", field):
                part = part.strip(" ,;")
                pm = PERSON_TOKEN.match(part)
                if pm:
                    c[pm.group(2)] += 1
                    continue
                rm = PERSON_REV.match(part)
                if rm:
                    c[rm.group(1)] += 1
        for m in EMAIL_LOCAL.finditer(t.lower()):
            c[m.group(2).capitalize()] += 1
    return {k: v for k, v in c.items() if v >= min_count and len(k) >= 3}


def header_firstnames(texts: list[str], min_count: int = 2) -> dict[str, int]:
    """First names seen in the same header positions (used to anchor replacement of common-word surnames)."""
    from collections import Counter

    c: Counter = Counter()
    for t in texts:
        for m in NAME_PATTERNS[0].finditer(t):
            c[m.group(1)] += 1
        for m in NAME_PATTERNS[2].finditer(t):
            c[m.group(1).split()[0]] += 1
        for m in NAME_PATTERNS[1].finditer(t):
            field = re.sub(r"<[^>]*>|\([^)]*\)|\"|'", " ", m.group(1))
            for part in re.split(r"[;,]\s*(?=[A-Z])|,\s+(?=[A-Z][a-z]+\s+[A-Z])|\s{2,}", field):
                pm = PERSON_TOKEN.match(part.strip(" ,;"))
                if pm:
                    c[pm.group(1)] += 1
                rm = PERSON_REV.match(part.strip(" ,;"))
                if rm:
                    c[rm.group(2)] += 1
        for m in EMAIL_LOCAL.finditer(t.lower()):
            c[m.group(1).capitalize()] += 1
    bad = {"Date", "Subject", "Sent", "From", "The", "Re", "Fw", "Fwd", "Original", "Message", "All", "For", "Dear", "Hi", "Hello", "Thanks", "Please"}
    return {k: v for k, v in c.items() if v >= min_count and len(k) >= 2 and k not in bad}
