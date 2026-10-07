"""Boilerplate detector for the verbatim (finish-the-document) probe windows.

Shared by the builder (`build.py`: reject a window before it becomes an item) and the scorer (`score.py`: exclude an
already-run item from the V statistics). A window is (prefix shown to the model, true continuation). It is a bad test
of memorisation when the continuation is text any model produces from genre knowledge alone, or when the prefix is
too degraded to anchor a continuation at all:

  disclaimer        confidentiality / privilege / legal-notice language ("intended recipient", "notify the sender" ...)
  signature         signature or footer block (phone / fax / e-mail / URL contact lines, "Sent from my iPhone")
  quoted_header     forwarded / reply header block (-----Original Message-----, From:/Sent:/To:/Subject: lines, "wrote:")
  list_footer       unsubscribe / mailing-list / marketing footer
  auto_message      out-of-office, auto-reply, bounce / delivery-status text, system-generated notices
  scan_notice       virus-scan / mail-gateway notices
  production_stamp  a protective-order legend inside the window (the window straddles a page break of the production)
  repetitive        degenerate repetition, or a continuation that can be copied from the prefix
  key_value_list    structured key: value / attachment / product-code lists
  ocr_garbage       garbled text (vowel-less tokens, or tokens unknown to the lexicon and to the corpus) in the window
  thin_prefix       too little real content before the hand-off (empty header fields, signature, garbage)
  corpus_template   the continuation's 8-grams recur in >= TEMPLATE_MIN_OTHER_DOCS other documents of the same corpus while
                    the text before the hand-off does not: a corpus-specific template (Mallinckrodt's suspicious-order report,
                    form-letter replies, the Endo disclaimer) rather than a document quoted in a reply chain
  duplicate         the whole window recurs in >= DUPLICATE_MIN_OTHER_DOCS other documents: a form-letter campaign, a mass
                    mailing or a long reply chain (over-exposed and over-represented in a sample of "documents")

The e-mail-specific rules (disclaimer, signature, quoted_header, list_footer, auto_message, scan_notice, thin_prefix) run only
for e-mail corpora; the structural and corpus-frequency rules run for every kind. The corpus-frequency rules need document
frequencies from the corpus itself: `CorpusIndex` scans the corpus once for the queried 8-grams / words and caches the counts in
data/contam/raw/boilerplate_df_<corpus>.json; `Lexicon` is the vocabulary (words in >= 3 documents) of every corpus on disk,
built once and cached in data/contam/raw/lexicon.json, so that a drug name or a Veridian product is not "garbage".
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DF_CACHE_DIR = ROOT / "data" / "contam" / "raw"

TOK_RE = re.compile(r"[a-z0-9]+")
NGRAM = 8
TEMPLATE_MIN_OTHER_DOCS = 2      # an 8-gram is "template" if it occurs in at least this many *other* documents
TEMPLATE_COVERAGE = 0.25         # share of the continuation's 8-grams that are template 8-grams
TEMPLATE_RUN = 8                 # or a contiguous stretch of this many template 8-grams (= 15 shared words)
WHOLE_WINDOW = 0.8               # coverage at which the prefix tail / continuation count as recurring wholesale
COPYABLE_RUN = 12                # a continuation stretch of this many words already present verbatim in the prompt is 'repetitive'
DUPLICATE_MIN_OTHER_DOCS = 4     # whole-window recurrence in this many other documents = duplicate (beyond a normal reply chain)
PREFIX_TAIL_CHARS = 300          # the hand-off region of the prefix that the e-mail rules also look at
MIN_CONTENT_WORDS = 40           # real words the prefix body must have before the hand-off
GARBAGE_CONT = 0.20              # share of garbage / unknown tokens in the continuation
GARBAGE_TAIL = 0.30              # ... in the hand-off region of the prefix
LEXICON_MIN_DF = 3               # a word is in the lexicon if it occurs in >= this many documents of any corpus

REASONS = ["disclaimer", "signature", "quoted_header", "list_footer", "auto_message", "scan_notice", "production_stamp",
           "repetitive", "key_value_list", "tabular", "ocr_garbage", "thin_prefix", "corpus_template", "duplicate"]
EMAIL_ONLY = {"disclaimer", "signature", "quoted_header", "list_footer", "auto_message", "scan_notice", "thin_prefix"}

REASON_LABEL = {
    "disclaimer": "confidentiality / privilege disclaimer", "signature": "signature or footer block",
    "quoted_header": "forwarded / reply header block", "list_footer": "unsubscribe / mailing-list footer",
    "auto_message": "auto-reply, out-of-office or bounce", "scan_notice": "virus-scan notice",
    "production_stamp": "protective-order legend in the window", "repetitive": "degenerate repetition (copyable from the prompt)",
    "key_value_list": "key: value / attachment list", "tabular": "table cells or an attendee / name list", "ocr_garbage": "OCR garbage",
    "thin_prefix": "too little real content before the hand-off",
    "corpus_template": "template text recurring across the corpus", "duplicate": "whole window duplicated across the corpus",
}


def _rx(pats: list[str], flags=re.I | re.M) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in pats), flags)


DISCLAIMER_STRONG = _rx([
    r"intended\s+recipient", r"notify\s+the\s+sender", r"delete\s+(?:this|the)\s+(?:e-?mail|message|communication|transmission)",
    r"confidentiality\s+notice", r"e-?mail\s+transmission", r"legally\s+privileged", r"attorney[- ]client\s+(?:privilege|communication)",
    r"if\s+you\s+have\s+received\s+this", r"unauthori[sz]ed\s+(?:review|use|disclosure|dissemination|distribution|copying|forwarding)",
    r"strictly\s+prohibited", r"destroy\s+all\s+copies", r"sole\s+use\s+of\s+the\s+(?:intended|addressee|recipient|individual)",
    r"intended\s+(?:solely|only)\s+for\s+the", r"(?:the\s+)?information\s+(?:contained\s+)?in\s+this\s+(?:e-?mail|message|communication|transmission)",
    r"this\s+(?:e-?mail|email|message|communication)\s*(?:\(including\s+any\s+attachments\)\s*)?(?:,\s*)?(?:including\s+(?:all|any)\s+attachments,?\s+)?"
    r"(?:and\s+any\s+(?:attachments?|files)\s+)?(?:is|are|may\s+be|contains?|may\s+contain)\s+(?:intended|confidential|privileged|proprietary|for\s+the)",
    r"(?:the\s+)?(?:e-?mail|message|communication|transmission)\s+(?:may\s+contain|contains)\s+(?:confidential|privileged|proprietary)",
    r"privileged\s+(?:and|or|,)\s*confidential", r"confidential\s+(?:and|or|,)\s*(?:legally\s+)?privileged", r"may\s+contain\s+confidential",
    r"any\s+(?:views|opinions)\s+(?:expressed|contained)\s+(?:in|herein)", r"does\s+not\s+accept\s+(?:any\s+)?liability",
    r"exempt\s+from\s+disclosure\s+under\s+applicable\s+law", r"please\s+consider\s+the\s+environment",
    r"intended\s+for\s+(?:educational|informational)\s+purposes\s+only", r"for\s+the\s+addressee\s+only",
])
DISCLAIMER_WEAK = [r"\bconfidential", r"\bprivileged", r"\bprohibited", r"\bunauthori[sz]ed", r"\bdisclos", r"\bdissemination",
                   r"\bdistribution\b", r"\bcopying", r"\bthe\s+sender\b", r"\baddressee", r"\bproprietary", r"\bliability", r"\bvirus",
                   r"\battachments?\b", r"\brecipient"]
DISCLAIMER_WEAK_RX = [re.compile(p, re.I) for p in DISCLAIMER_WEAK]

PHONE_RX = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")
CONTACT_LINE_RX = _rx([
    r"^\s*(?:tel|telephone|phone|ph|fax|fx|mobile|mob|cell|cellular|office|direct|main|desk|pager|voice|t|m|f|o|d|c|e|w|p)\s*[:.]\s*\S",
    r"[\w.+-]+@[\w-]+\.[\w.-]+", r"(?:https?://|www\.)\S+", r"^\s*(?:ext|extension|x)\.?\s*\d{3,5}\b",
    r"\b(?:fax|tel|phone|cell|mobile|direct|office|voice|pager)\b",  # short lines only (see _is_contact_line)
], re.I | re.M)
ADDRESS_LINE_RX = _rx([
    r"\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b",
    r"^\s*\d{1,6}\s+[A-Z][\w.]*(?:\s+[\w.]+){0,4}\s+(?:Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Drive|Dr\.?|Road|Rd\.?|Lane|Ln\.?|Suite|Ste\.?|"
    r"Floor|Way|Place|Pl\.?|Court|Ct\.?|Parkway|Pkwy\.?|Plaza|Highway|Hwy\.?|Circle|Center|Centre|Building|Bldg\.?)\b",
    r"^\s*P\.?\s?O\.?\s*Box\b", r"^\s*(?:suite|ste\.?|floor|fl\.?)\s*\d+",
], re.I | re.M)
SIG_PIPE_RX = re.compile(r"^\s*[A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){1,3}\s*[|l]\s+[A-Z]\S")  # "Jen Buist l Sr. Data Analyst" (OCR'd pipe)
CLOSING_RX = re.compile(r"^\s*(?:best\s+regards|kind\s+regards|warm\s+regards|regards|sincerely|thanks|thank\s+you|cheers|best|respectfully|many\s+thanks|thx)[,.!]?\s*$", re.I | re.M)
SENT_FROM_RX = re.compile(r"sent\s+(?:from|via)\s+my\s+(?:iphone|ipad|blackberry|android|mobile|samsung|verizon|windows\s+phone|galaxy|wireless|t-mobile|sprint|at&t)", re.I)
SIG_MAX_WORDS = 10

HEADER_LINE_RX = re.compile(r"^\s*(?:>|&gt;)*\s*(?:[-_*]{2,}\s*)?(?:\*?\*?)(?:From|Sent|To|Cc|CC|Bcc|Subject|Date|Importance|Attachments?|Sent\s+by|Reply-To)\s*\*?\*?\s*:", re.M)
QUOTE_MARK_RX = re.compile(r"^\s*(?:>|&gt;)", re.M)
FORWARD_RX = _rx([r"-{3,}\s*(?:original\s+message|forwarded|original\s+appointment|begin\s+forwarded)", r"begin\s+forwarded\s+message",
                  r"^on\s.{5,160}?\bwrote:\s*$", r"^_{5,}\s*$", r"forwarded\s+by\s+.{3,80}\s+on\s+\d", r"^\s*-+\s*forwarded\s+by"])

LIST_FOOTER_STRONG = _rx([
    r"unsubscribe", r"to\s+be\s+removed\s+from", r"to\s+stop\s+receiving", r"opt[- ]?out", r"you\s+(?:are|were)\s+receiving\s+this",
    r"update\s+your\s+(?:preferences|profile|subscription|e-?mail\s+address)", r"remove\s+(?:yourself|your\s+(?:name|address|e-?mail))",
    r"this\s+(?:e-?mail|email|message|newsletter)\s+(?:was|is)\s+sent\s+(?:to|by|from)", r"no\s+longer\s+wish\s+to\s+receive",
    r"to\s+(?:subscribe|cancel\s+your\s+subscription|change\s+your\s+subscription)", r"mailing\s+list", r"manage\s+your\s+(?:subscriptions?|account)",
    r"reply\s+with\s+(?:\"|')?(?:remove|unsubscribe)", r"forward\s+this\s+(?:e-?mail|newsletter|message)\s+to\s+a\s+friend",
])
LIST_FOOTER_WEAK = [r"all\s+rights\s+reserved", r"copyright\s+(?:©|\(c\)|\d{4})", r"©\s*\d{4}", r"\(c\)\s*\d{4}", r"privacy\s+(?:policy|statement|program)",
                    r"terms\s+(?:of\s+(?:use|service)|and\s+conditions)", r"click\s+here", r"visit\s+our\s+(?:web\s*site|website|site)", r"for\s+more\s+information",
                    r"to\s+learn\s+more", r"\[image\]", r"free\s+shipping", r"special\s+offer", r"limited\s+time", r"shop\s+now"]
LIST_FOOTER_WEAK_RX = [re.compile(p, re.I) for p in LIST_FOOTER_WEAK]

# bounce / system text announces itself anywhere; out-of-office cues count only at the top of the body (a genuine e-mail may
# mention "I will be out of the office" in passing)
BOUNCE_RX = _rx([
    r"auto(?:matic|mated)?[- ]?(?:reply|response|responder|generated|notification)", r"automatically\s+generated",
    r"delivery\s+(?:has\s+)?failed", r"undeliverable", r"delivery\s+(?:status\s+)?notification", r"diagnostic\s+information\s+for\s+administrators",
    r"generating\s+server", r"original\s+message\s+headers", r"^\s*received:\s+from\b", r"mailer-daemon", r"postmaster@", r"do\s+not\s+reply\s+to\s+this",
    r"this\s+is\s+an\s+automated", r"#\s*5\.\d\.\d\b", r"message\s+could\s+not\s+be\s+delivered", r"\bread\s+receipt\b",
    r"your\s+message\s+(?:was|has\s+been)\s+(?:read|deleted|received|recalled)", r"would\s+like\s+to\s+recall\s+the\s+message", r"recall\s+of\s+the\s+message",
    r"this\s+message\s+was\s+created\s+automatically", r"mail\s+delivery\s+(?:subsystem|failure)", r"returned\s+mail",
    r"the\s+following\s+recipient\(s\)\s+could\s+not\s+be\s+reached",
])
OOO_RX = _rx([r"out\s+of\s+(?:the\s+)?office", r"i\s+(?:will|am|'m|'ll)\s+(?:be\s+)?(?:out|away)\s+(?:of|from)\s+the\s+office",
              r"has\s+been\s+(?:accepted|tentatively\s+accepted|declined)\b"])
SCAN_NOTICE_RX = _rx([
    r"scanned\s+(?:for\s+viruses|by|for\s+(?:all\s+)?(?:known\s+)?(?:viruses|malware))", r"virus[- ]?(?:free|scan|check|scanning)", r"anti-?virus",
    r"has\s+been\s+scanned", r"checked\s+by\s+(?:avg|norton|mcafee|symantec|mailscanner|kaspersky|sophos)", r"mailscanner", r"mimecast", r"messagelabs",
    r"proofpoint", r"free\s+from\s+(?:viruses|malware|malicious)", r"believed\s+to\s+be\s+(?:clean|free\s+of)", r"no\s+virus\s+found",
])
PRODUCTION_STAMP_RX = _rx([r"subject\s+to\s+(?:a\s+)?protective\s+order", r"highly\s+confidential", r"confidential\s*[-–—:]\s*(?:produced|subject|pursuant|attorneys)",
                           r"produced\s+(?:pursuant|in\s+response)\s+to", r"\bbates\s+(?:no|number|stamp)"])
KV_LINE_RX = re.compile(r"^\s*[A-Za-z][\w /&().'#*-]{0,40}\s*[:=]\s*\S")
FIRST_TOKEN_RX = re.compile(r"^[A-Za-z][\w.-]*:?$")
FILENAME_RX = re.compile(r"\.(?:pdf|docx?|xlsx?|pptx?|msg|zip|jpe?g|png|gif|txt|csv|rtf|htm|html|wpd|tif|tiff)\b", re.I)
EMPTY_HEADER_RX = re.compile(r"^\s*(?:From|Sent|To|Cc|CC|Bcc|Subject|Date|Importance|Attachments?)\s*:\s*$", re.M)
VOWEL_RX = re.compile(r"[aeiouy]")
CONSONANT_RUN_RX = re.compile(r"[bcdfghjklmnpqrstvwxz]{5,}")
ALPHA_RX = re.compile(r"^[a-z]+$")
KV_MAX_WORDS = 12
LIST_STOP = {"the", "a", "i", "we", "it", "this", "in", "on", "if", "to", "and", "for", "o", "of", "as", "at", "by", "or", "is", "are", "you", "he", "she", "they"}


@dataclass
class DocFreq:
    """Document frequencies for one corpus's windows: 8-gram -> docs containing it, word -> docs containing it, plus the lexicon."""
    ngram_df: dict[tuple[str, ...], int] = field(default_factory=dict)
    word_df: dict[str, int] = field(default_factory=dict)
    lexicon: set[str] | None = None

    def known(self, word: str) -> bool:
        """A word is known if the lexicon has it, or if it recurs in the corpus beyond this document and one other."""
        if self.lexicon is not None and word in self.lexicon:
            return True
        return self.word_df.get(word, 0) > 2


def _tail(prefix: str, chars: int = PREFIX_TAIL_CHARS) -> str:
    return prefix[-chars:]


def _lines(s: str) -> list[str]:
    return [ln for ln in s.split("\n") if ln.strip()]


def _nwords(ln: str) -> int:
    return len(ln.split())


def _count_distinct(rxs: list[re.Pattern], s: str) -> int:
    return sum(1 for rx in rxs if rx.search(s))


def _is_contact_line(ln: str) -> bool:
    if _nwords(ln) > SIG_MAX_WORDS:
        return False
    return bool(PHONE_RX.search(ln) or CONTACT_LINE_RX.search(ln) or SIG_PIPE_RX.search(ln))


def _is_address_line(ln: str) -> bool:
    return _nwords(ln) <= SIG_MAX_WORDS and bool(ADDRESS_LINE_RX.search(ln))


def _is_sig_line(ln: str) -> bool:
    return _is_contact_line(ln) or _is_address_line(ln)


def _garbage_token(t: str) -> bool:
    if len(t) < 3 or not ALPHA_RX.match(t):
        return False
    if not VOWEL_RX.search(t):
        return True
    return len(t) >= 6 and bool(CONSONANT_RUN_RX.search(t))


def _bad_token(t: str, df: DocFreq | None) -> bool:
    if _garbage_token(t):
        return not (df is not None and df.known(t))  # vowel-less acronyms the corpus uses are fine (FYI, DEA, CFR ...)
    return df is not None and df.lexicon is not None and len(t) >= 4 and not df.known(t)


def _garbage_ratio(text: str, df: DocFreq | None) -> float:
    toks = [t for t in TOK_RE.findall(text.lower()) if ALPHA_RX.match(t) and len(t) >= 3]
    if len(toks) < 8:
        return 0.0
    return sum(_bad_token(t, df) for t in toks) / len(toks)


def _reason_disclaimer(prefix: str, cont: str) -> bool:
    tail = _tail(prefix)
    if DISCLAIMER_STRONG.search(cont):
        return True
    if DISCLAIMER_STRONG.search(tail) and _count_distinct(DISCLAIMER_WEAK_RX, cont) >= 1:
        return True  # the disclaimer began just before the hand-off and the continuation is the rest of it
    return _count_distinct(DISCLAIMER_WEAK_RX, cont) >= 4


def _reason_signature(prefix: str, cont: str) -> bool:
    if SENT_FROM_RX.search(cont):
        return True
    cont_lines = _lines(cont)
    pre_lines = _lines(_tail(prefix))[-4:]
    contact_c = [ln for ln in cont_lines if _is_contact_line(ln)]
    addr_c = [ln for ln in cont_lines if _is_address_line(ln) and ln not in contact_c]
    contact_p = [ln for ln in pre_lines if _is_contact_line(ln)]
    if len(contact_c) >= 3:
        return True
    m = CLOSING_RX.search(cont)
    closing_early = bool(m) and m.start() < len(cont) / 2
    if len(contact_c) >= 2 and (closing_early or addr_c or contact_p):
        return True
    if len(contact_c) >= 1 and closing_early and addr_c:
        return True
    # the hand-off is inside a signature block: contact lines just before it, and more signature lines after it
    return len(contact_p) >= 2 and (len(contact_c) + len(addr_c)) >= 1


def _reason_quoted_header(prefix: str, cont: str) -> bool:
    if len(HEADER_LINE_RX.findall(cont)) >= 2 or FORWARD_RX.search(cont):
        return True
    if len(QUOTE_MARK_RX.findall(cont)) >= 3:
        return True
    tail = _tail(prefix)
    return len(HEADER_LINE_RX.findall(tail)) >= 2 or bool(FORWARD_RX.search(tail))


def _reason_list_footer(prefix: str, cont: str) -> bool:
    if LIST_FOOTER_STRONG.search(cont):
        return True
    return _count_distinct(LIST_FOOTER_WEAK_RX, cont) >= 2


def _body(prefix: str) -> str:
    return prefix.split("\n\n", 1)[1] if "\n\n" in prefix else prefix


def _reason_auto_message(prefix: str, cont: str, df: DocFreq | None) -> bool:
    if BOUNCE_RX.search(cont) or BOUNCE_RX.search(prefix):
        return True
    if not (OOO_RX.search(_body(prefix)[:300]) or OOO_RX.search(cont[:150])):
        return False
    return _content_words(prefix, df) < 2 * MIN_CONTENT_WORDS  # a real out-of-office reply is short; a long e-mail may just mention it


def _reason_scan_notice(prefix: str, cont: str) -> bool:
    return bool(SCAN_NOTICE_RX.search(cont)) or bool(SCAN_NOTICE_RX.search(_tail(prefix)))


def _reason_production_stamp(prefix: str, cont: str) -> bool:
    return bool(PRODUCTION_STAMP_RX.search(cont))


def _reason_repetitive(prefix: str, cont: str) -> bool:
    ct = TOK_RE.findall(cont.lower())
    if len(ct) >= 12:
        tri = [tuple(ct[i:i + 3]) for i in range(len(ct) - 2)]
        if len(set(tri)) / len(tri) < 0.5:
            return True
    pt = TOK_RE.findall(prefix.lower())
    if len(ct) >= NGRAM and len(pt) >= NGRAM:
        p8 = {tuple(pt[i:i + NGRAM]) for i in range(len(pt) - NGRAM + 1)}
        c8 = [tuple(ct[i:i + NGRAM]) for i in range(len(ct) - NGRAM + 1)]
        if sum(g in p8 for g in c8) / len(c8) >= 0.6:
            return True
        # a stretch of COPYABLE_RUN+ words that already appears verbatim in the prompt (a repeated bullet in a weekly report, a
        # mirrored clause in a contract): the continuation is partly predictable from the prefix, so it is not a clean test
        best = cur = 0
        for g in c8:
            cur = cur + 1 if g in p8 else 0
            best = max(best, cur)
        if best and best + NGRAM - 1 >= COPYABLE_RUN:
            return True
    return False


def _reason_key_value_list(prefix: str, cont: str) -> bool:
    lines = _lines(cont)
    if len(FILENAME_RX.findall("\n".join(_lines(_tail(prefix))[-4:] + lines))) >= 3:
        return True  # attachment / file list around the hand-off
    if len(lines) < 3:
        return False
    kv = sum(1 for ln in lines if KV_LINE_RX.match(ln) and _nwords(ln) <= KV_MAX_WORDS)
    if kv >= 3 and kv / len(lines) >= 0.6:
        return True
    short = [ln for ln in lines if _nwords(ln) <= KV_MAX_WORDS]
    first = Counter(ln.split()[0].lower() for ln in short if FIRST_TOKEN_RX.match(ln.split()[0]))
    if not first:
        return False
    tok, n = first.most_common(1)[0]
    return n >= 3 and n / len(lines) >= 0.5 and tok.rstrip(":") not in LIST_STOP


NAME_ITEM_RX = re.compile(r"\b[A-Z][a-zA-Z'\-]+,\s?[A-Z][a-zA-Z'\-]+\s*;")   # "Surname, First;" (meeting attendee lists)
NUMBER_CELL_RX = re.compile(r"(?<![\w.\-/])(?:\(\d[\d,]*(?:\.\d+)?\)|\d+(?:\.\d+)?%|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\$\d[\d,]*(?:\.\d+)?|\d+\.\d+)(?![\w/])")  # a table cell: (4,615) · 89% · 1,245 · $12.5 · 7.25 — not a date or a plain count
TABLE_LINE_MAX_WORDS = 4


def _reason_tabular(cont: str) -> bool:
    """Table cells flattened to one short line each (a sales grid: '111%' / 'S10500 - New Jersey'), or a long 'Surname, First;'
    attendee list: the continuation is data layout, predictable in shape and not a test of remembered prose."""
    if len(NAME_ITEM_RX.findall(cont)) >= 6:
        return True
    lines = _lines(cont)
    if len(lines) >= 5:  # rows of a numeric table (a sales grid: label, then three or more figures / percentages per line)
        rows = sum(1 for ln in lines if len(NUMBER_CELL_RX.findall(ln)) >= 3)
        if rows / len(lines) >= 0.4:
            return True
    if len(lines) < 8:
        return False
    short = sum(1 for ln in lines if _nwords(ln) <= TABLE_LINE_MAX_WORDS)
    numeric = sum(1 for ln in lines if re.search(r"\d", ln))
    return short / len(lines) >= 0.6 and numeric / len(lines) >= 0.4


def _reason_ocr_garbage(prefix: str, cont: str, df: DocFreq | None) -> bool:
    return _garbage_ratio(cont, df) >= GARBAGE_CONT or _garbage_ratio(_tail(prefix), df) >= GARBAGE_TAIL


def _content_words(prefix: str, df: DocFreq | None) -> int:
    n = 0
    for ln in _body(prefix).split("\n"):
        if not ln.strip() or HEADER_LINE_RX.match(ln) or _is_sig_line(ln) or (KV_LINE_RX.match(ln) and _nwords(ln) <= 6):
            continue
        n += sum(1 for t in TOK_RE.findall(ln.lower()) if ALPHA_RX.match(t) and not _bad_token(t, df))
    return n


def _reason_thin_prefix(prefix: str, cont: str, df: DocFreq | None) -> bool:
    n = _content_words(prefix, df)
    if n < MIN_CONTENT_WORDS:
        return True
    return len(EMPTY_HEADER_RX.findall(prefix)) >= 3 and n < 1.25 * MIN_CONTENT_WORDS


def ngrams(text: str, n: int = NGRAM) -> list[tuple[str, ...]]:
    t = TOK_RE.findall(text.lower())
    return [tuple(t[i:i + n]) for i in range(len(t) - n + 1)]


def recurrence(text: str, ngram_df: dict[tuple[str, ...], int], min_other: int) -> tuple[float, int]:
    """(share of the text's 8-grams found in >= min_other other documents, longest contiguous stretch of them)."""
    gs = ngrams(text)
    if not gs:
        return 0.0, 0
    flags = [ngram_df.get(g, 1) - 1 >= min_other for g in gs]
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return sum(flags) / len(flags), best


def template_coverage(cont: str, ngram_df: dict[tuple[str, ...], int]) -> tuple[float, int]:
    return recurrence(cont, ngram_df, TEMPLATE_MIN_OTHER_DOCS)


def _recurrence_reasons(prefix: str, cont: str, df: DocFreq | None) -> list[str]:
    if df is None or not df.ngram_df:
        return []
    tail = _tail(prefix, 400)
    cov_c, run_c = recurrence(cont, df.ngram_df, TEMPLATE_MIN_OTHER_DOCS)
    cov_t, _ = recurrence(tail, df.ngram_df, TEMPLATE_MIN_OTHER_DOCS)
    whole = cov_c >= WHOLE_WINDOW and cov_t >= WHOLE_WINDOW
    out = []
    if (cov_c >= TEMPLATE_COVERAGE or run_c >= TEMPLATE_RUN) and not whole:
        out.append("corpus_template")
    dup_c, _ = recurrence(cont, df.ngram_df, DUPLICATE_MIN_OTHER_DOCS)
    dup_t, _ = recurrence(tail, df.ngram_df, DUPLICATE_MIN_OTHER_DOCS)
    if dup_c >= WHOLE_WINDOW and dup_t >= WHOLE_WINDOW:
        out.append("duplicate")
    return out


def boilerplate_reasons(prefix: str, continuation: str, kind: str = "email", df: DocFreq | None = None) -> list[str]:
    """Every rule that fires, in REASONS order. `kind` is the corpus kind from build.CORPORA (email / contract / canon / csv)."""
    out: list[str] = []
    email = kind == "email"
    checks = [
        ("disclaimer", lambda: email and _reason_disclaimer(prefix, continuation)),
        ("signature", lambda: email and _reason_signature(prefix, continuation)),
        ("quoted_header", lambda: email and _reason_quoted_header(prefix, continuation)),
        ("list_footer", lambda: email and _reason_list_footer(prefix, continuation)),
        ("auto_message", lambda: email and _reason_auto_message(prefix, continuation, df)),
        ("scan_notice", lambda: email and _reason_scan_notice(prefix, continuation)),
        ("production_stamp", lambda: kind != "csv" and _reason_production_stamp(prefix, continuation)),
        ("repetitive", lambda: _reason_repetitive(prefix, continuation)),
        ("key_value_list", lambda: kind not in ("csv", "canon") and _reason_key_value_list(prefix, continuation)),
        ("tabular", lambda: kind not in ("csv", "canon") and _reason_tabular(continuation)),
        ("ocr_garbage", lambda: kind != "csv" and _reason_ocr_garbage(prefix, continuation, df)),
        ("thin_prefix", lambda: email and _reason_thin_prefix(prefix, continuation, df)),
    ]
    for name, fn in checks:
        if fn():
            out.append(name)
    if kind != "csv":
        out += _recurrence_reasons(prefix, continuation, df)
    return out


def is_boilerplate_window(prefix: str, continuation: str, kind: str = "email", df: DocFreq | None = None) -> tuple[bool, str | None]:
    """(flag, first reason). `df`: DocFreq from CorpusIndex.lookup (None disables the corpus-frequency and lexicon rules)."""
    rs = boilerplate_reasons(prefix, continuation, kind, df)
    return (bool(rs), rs[0] if rs else None)


# ------------------------------------------------------------------------------------------------ corpus document frequencies

def _doc_key(doc: dict, corpus: str) -> str:
    """Identity for document-frequency counting: a CUAD contract (not its segments); otherwise the body text (exact duplicates
    of the same e-mail in several mailboxes count once)."""
    if corpus == "cuad":
        return str(doc.get("meta", {}).get("contract") or doc["id"])
    text = doc.get("text", "")
    body = text.split("\n\n", 1)[1] if "\n\n" in text else text
    return hashlib.md5(" ".join(TOK_RE.findall(body.lower())).encode()).hexdigest()


class Lexicon:
    """Words occurring in >= LEXICON_MIN_DF documents of any corpus on disk (one full pass per corpus, cached)."""
    path = DF_CACHE_DIR / "lexicon.json"
    _words: set[str] | None = None

    @classmethod
    def get(cls, log=None) -> set[str]:
        if cls._words is not None:
            return cls._words
        from .build import CORPORA, ROOT as BROOT, load_docs  # noqa: PLC0415

        sources = sorted(c for c in CORPORA if "file" in CORPORA[c] and (BROOT / CORPORA[c]["file"]).exists())
        if cls.path.exists():
            raw = json.loads(cls.path.read_text())
            if raw.get("sources") == sources and raw.get("min_df") == LEXICON_MIN_DF:
                cls._words = set(raw["words"])
                return cls._words
        words: set[str] = set()
        for c in sources:
            if log:
                log(f"[boilerplate] lexicon: scanning {c}")
            df: Counter = Counter()
            for d in load_docs(c):
                df.update({t for t in TOK_RE.findall(d.get("text", "").lower()) if ALPHA_RX.match(t) and len(t) >= 3})
            words |= {w for w, n in df.items() if n >= LEXICON_MIN_DF}
        cls.path.parent.mkdir(parents=True, exist_ok=True)
        cls.path.write_text(json.dumps({"sources": sources, "min_df": LEXICON_MIN_DF, "words": sorted(words)}, separators=(",", ":")))
        cls._words = words
        return words


class CorpusIndex:
    """Document frequency of queried 8-grams and words in one corpus, computed by a single pass over the documents and cached."""

    def __init__(self, corpus: str, docs: list[dict] | None = None, cache_dir: Path = DF_CACHE_DIR):
        self.corpus = corpus
        self._docs = docs
        self.path = cache_dir / f"boilerplate_df_{corpus}.json"
        self.ngram_df: dict[tuple[str, ...], int] = {}
        self.word_df: dict[str, int] = {}
        self.n_docs: int | None = None
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            self.n_docs = raw.get("n_docs")
            self.ngram_df = {tuple(k.split(" ")): v for k, v in raw.get("ngram_df", {}).items()}
            self.word_df = dict(raw.get("word_df", {}))

    def docs(self) -> list[dict]:
        if self._docs is None:
            from .build import load_docs  # noqa: PLC0415

            self._docs = load_docs(self.corpus)
        return self._docs

    def lookup(self, texts: list[str], log=None, lexicon: bool = True) -> DocFreq:
        """DocFreq covering every 8-gram and word of `texts`; scans the corpus once for the ones not yet cached."""
        want_g = {g for t in texts for g in ngrams(t)}
        want_w = {w for t in texts for w in TOK_RE.findall(t.lower()) if ALPHA_RX.match(w) and len(w) >= 3}
        miss_g = want_g - self.ngram_df.keys()
        miss_w = want_w - self.word_df.keys()
        if miss_g or miss_w:
            if log:
                log(f"[boilerplate] {self.corpus}: scanning corpus for {len(miss_g):,} 8-grams / {len(miss_w):,} words")
            self._scan(miss_g, miss_w)
            self._save()
        return DocFreq({g: self.ngram_df.get(g, 1) for g in want_g}, {w: self.word_df.get(w, 1) for w in want_w},
                       Lexicon.get(log) if lexicon else None)

    def _scan(self, want_g: set, want_w: set) -> None:
        cg: Counter = Counter()
        cw: Counter = Counter()
        seen: set[str] = set()
        n = NGRAM
        for d in self.docs():
            key = _doc_key(d, self.corpus)
            if key in seen:
                continue
            seen.add(key)
            t = TOK_RE.findall(d.get("text", "").lower())
            if want_w:
                cw.update(want_w.intersection(t))
            if want_g and len(t) >= n:
                cg.update({g for g in (tuple(t[i:i + n]) for i in range(len(t) - n + 1)) if g in want_g})
        self.n_docs = len(seen)
        for g in want_g:
            self.ngram_df[g] = cg.get(g, 0)
        for w in want_w:
            self.word_df[w] = cw.get(w, 0)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"n_docs": self.n_docs, "ngram_df": {" ".join(g): v for g, v in self.ngram_df.items()},
                                         "word_df": self.word_df}, separators=(",", ":")))
