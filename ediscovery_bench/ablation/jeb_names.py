"""Knowledge-bearing names for the Jeb Bush arm (round 2) and the renamer built on names.Renamer.

Minimal mapping that removes *identification* while keeping the topics intact: people are renamed (the Governor and his family,
his staff, the Florida public figures the matter-knowledge probes showed the models know, every correspondent found in a header
field), and so are the Governor's personal domain and e-mail address. The state, its cities, its agencies (DCF, AHCA, SBA, DEP…),
statutes, programmes and the state e-mail domains (myflorida.com, eog.state.fl.us) are kept: renaming Florida would break the
topical relevance of most requests (Everglades, Tallahassee, Florida statutes), and the Enron leak check already showed that a
fact pattern identifies a matter whatever the names say. The leak check (`bench ablation2-leak`) measures what is left.

Dose (meta.dose) = number of mentions of *public figures other than the Governor* (JEB_PUBLIC): the people whose names carry case
knowledge beyond what the request itself states.
"""
from __future__ import annotations

import re

from .names import COMMON_WORD_SURNAMES, Renamer, fake_surname, header_firstnames, header_surnames

# the Governor and his family: first names that identify him are mapped as phrases (first names are otherwise kept)
JEB_PHRASES: dict[str, str] = {
    "Jeb Bush": "Cal Weston", "JEB BUSH": "CAL WESTON", "Jeb": "Cal", "JEB": "CAL", "jeb.org": "calweston.org", "jeb@jeb.org": "cal@calweston.org",
    "Columba": "Marisol", "Noelle": "Nadia", "Dubya": "Dub", "George P.": "George R.", "Jebbie": "Callie", "Rilya": "Kiara", "RILYA": "KIARA",
    "Bush v. Gore": "Weston v. Hartwell", "Bush-Cheney": "Weston-Rourke", "Bush/Cheney": "Weston/Rourke", "Gore-Lieberman": "Hartwell-Feldman",
    "Bush-Brogan": "Weston-Maddox", "Bush/Brogan": "Weston/Maddox",
}

# public figures (surname -> fake): the Bush family, the two tickets of 2000, the Governor's senior staff and cabinet, the people
# named in the request texts (Katherine Harris, Rilya Wilson, Miriam Oliphant) and the Florida figures the M2 probe produced
JEB_PUBLIC: dict[str, str] = {
    "Bush": "Weston", "Gore": "Hartwell", "Cheney": "Rourke", "Lieberman": "Feldman", "Nader": "Varga", "Clinton": "Marlow", "Reno": "Castellan",
    "Harris": "Ashcombe", "Oliphant": "Pembrook", "Wilson": "Thornley", "Schiavo": "Lindqvist", "Schindler": "Hollis",
    "Brogan": "Maddox", "Jennings": "Grafton", "Shanahan": "Redfern", "Stutler": "Oakeshott", "Yablonski": "Stroud", "Oviedo": "Larkin",
    "Bradshaw": "Wexford", "Stipanovich": "Petrakis", "Cardenas": "Lindgren", "Tilley": "Rutherford", "Hadi": "Fairweather", "Regier": "Nystrom",
    "Kearney": "Feldmann", "Levine": "Prentiss", "Arduin": "Whitlock", "Struhs": "Haskell", "Castille": "Treadwell", "Fasano": "Keller",
    "Chiles": "Castiglione", "Horne": "Lindauer", "Feeney": "Pemberton", "Byrd": "Holloway", "Thrasher": "Arnstein", "Bense": "Ashworth",
    "Webster": "Stern", "Pruitt": "Carver", "Rubio": "Leung", "Nelson": "Ransome", "Graham": "Baumann", "McBride": "Ferris", "Crist": "Garrity",
    "Gallagher": "Harrigan", "Butterworth": "Pettigrew", "Hood": "Stenson", "Milligan": "Tolliver", "Thompson": "Leclair", "Hammer": "Hagen",
    "Sasser": "Weldon", "Levesque": "Novak", "Hanley": "Falk", "Gormley": "Dunmore", "Branker": "Blanchard", "Bahrami": "Albrecht",
    "Bergemann": "Latimer", "Bratina": "Stenholm", "Gilley": "Tarrow", "Kaplan": "Orwell", "Piferrer": "Quillon", "Klock": "Mireval",
    "Mencia": "Selwyn", "Lounsberry": "Garrow", "Canady": "Aldric", "Hampton": "Belmar", "Towne": "Crestway", "Kottkamp": "Dorrance",
    "Mack": "Everly", "Foley": "Falkner", "Deutsch": "Greyson", "Wasserman": "Holbrook", "Sembler": "Keswick", "Scripps": "Lorimar",
}
# first names that identify the family / cast when paired with the surname (kept, but the full-name layer sees them)
JEB_FIRST = ["Jeb", "George", "Barbara", "Laura", "Marvin", "Neil", "Dorothy", "Columba", "Noelle", "Al", "Dick", "Joe", "Ralph", "Bill", "Hillary",
             "Janet", "Katherine", "Miriam", "Terri", "Michael", "Frank", "Toni", "Kathleen", "Denver", "Brian", "Nina", "Sally", "Mac",
             "Al", "Cory", "Lucy", "Jerry", "Alan", "Donna", "David", "Charlie", "Tom", "Bob", "Glenda", "Marion", "Charla", "Pam", "Pamella",
             "Raquel", "Bunny", "Dana", "Carol", "Betty", "Jill", "Jim", "Jan", "Mark", "Steve", "Mike", "Alex", "Janice", "Karen", "Fred",
             "Jennifer", "Kim", "Douglas", "Robert", "Patricia", "William", "John", "Tramm"]
# surnames that are also ordinary English words / first names: header lines or full-name position only
JEB_COMMON = {"Hood", "Webster", "Nelson", "Graham", "Hammer", "Mack", "Foley", "Hampton", "Towne", "Wilson", "Harris", "Reno", "Clinton", "Thompson",
              "Pruitt", "Byrd", "Horne", "Crist", "Gore", "Bush"} - {"Bush", "Gore", "Harris", "Wilson", "Clinton"}  # these five are knowledge-bearing wherever capitalised
HEADER_TOKENS = {"Date", "Subject", "Sent", "Re", "Fw", "Fwd", "Original", "Message", "Attachment", "Attachments", "Governor", "Office", "Press",
                 "Secretary", "Mail", "Web", "Large", "Dana", "John", "Paul", "Peggy", "Barry", "Ross", "State", "House", "Senate", "News", "Florida",
                 "Importance", "High", "Low", "Internet", "Info", "Staff", "Team", "Group", "Admin", "Hr", "Tv", "Fax", "Bcc"}


class JebRenamer(Renamer):
    """names.Renamer plus a pass over e-mail local parts of the form surname+initial / initial+surname (oviedon@, kshanahan@)."""

    def apply(self, text: str) -> str:
        text = super().apply(text)

        def fix_local(m):
            local = m.group(1)
            low = local.lower()
            for s in sorted(self.people, key=len, reverse=True):
                sl = s.lower()
                if len(sl) < 4 or s in self.firsts:
                    continue
                if re.fullmatch(rf"[a-z]{{0,2}}[._-]?{re.escape(sl)}[a-z]?\d*|{re.escape(sl)}[._-]?[a-z]{{1,2}}\d*", low):
                    return low.replace(sl, self.people_lut[sl].lower()) + "@"
            return m.group(0)
        text = re.sub(r"\b([A-Za-z][A-Za-z0-9._-]{2,})@", fix_local, text)
        # lower-case "governor bush" / "gov. bush" / "mr bush" / "president bush" (the surname layer only sees capitalised tokens)
        return _LOWER_BUSH_RE.sub(lambda m: m.group(1) + m.group(2) + "weston", text)


_LOWER_BUSH_RE = re.compile(r"\b((?:[Gg]overnor|[Gg]ov\.?|[Mm]rs?\.?|[Pp]resident|[Gg]ov)(\s+))bush\b")


def build_jeb_renamer(texts: list[str], log=print) -> tuple[JebRenamer, dict]:
    hdr = header_surnames(texts)
    people = dict(JEB_PUBLIC)
    taken = set(people.values())
    phrase_words = {w.lower() for k in JEB_PHRASES for w in k.split()}
    skipped = []
    firsts_seen = set(header_firstnames(texts))
    for s, n in sorted(hdr.items(), key=lambda kv: -kv[1]):
        if s in people or s.lower() in phrase_words or s in JEB_FIRST or s in firsts_seen:
            continue
        if s in HEADER_TOKENS or len(s) < 4:
            skipped.append(s)
            continue
        people[s] = fake_surname(s, taken)
    from .build import _ENGLISH_WORDS  # noqa: PLC0415  (the shared dictionary of ordinary words)

    curated = set(JEB_PUBLIC) - JEB_COMMON
    common = (set(COMMON_WORD_SURNAMES) | JEB_COMMON | {s for s in people if s.lower() in _ENGLISH_WORDS}) - curated
    firsts = sorted(set(JEB_FIRST) | firsts_seen)
    rn = JebRenamer(JEB_PHRASES, people, common, firsts)
    info = {"phrases": JEB_PHRASES, "people": people, "common_word_surnames": sorted(common & set(people)), "firsts": firsts,
            "header_surnames_found": len(hdr), "curated_people": len(JEB_PUBLIC), "skipped_tokens": skipped, "public_figures": sorted(JEB_PUBLIC)}
    log(f"jeb mapping: {len(JEB_PHRASES)} phrases, {len(people)} surnames ({len(hdr)} found in headers), {len(common & set(people))} treated as common words")
    return rn, info


def load_jeb_renamer(info: dict) -> JebRenamer:
    return JebRenamer(info["phrases"], info["people"], set(info["common_word_surnames"]), info["firsts"])


def jeb_dose_renamer() -> Renamer:
    """Counts mentions of public figures other than the Governor (knowledge beyond the request text)."""
    pub = {k: v for k, v in JEB_PUBLIC.items() if k not in ("Bush",)}
    return Renamer({}, pub, JEB_COMMON - {"Gore", "Harris", "Wilson", "Clinton"}, [])
