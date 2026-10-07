"""Build the Endo e-mail sample (held-out, post-cutoff corpus).

Mirrors ediscovery_bench/mnk/sample.py. Differences from Mallinckrodt:
- No custodian restriction (the Endo production spans ~280 custodians; the Bates prefix, not the
  custodian, is the useful cut), so strata are body-text queries over the whole email collection.
- Strata follow the four request pairs in tasks/endo.yaml (Opana promotion / abuse-deterrence,
  SOM-DEA / flagged-order decisions, risk messaging / rep reports of diversion, third-party
  advocacy / editorial control) plus an adjacent non-opioid hard-negative stratum and random.
- Each row carries ``meta.case`` = Bates prefix (e.g. ENDO-OPIOID_MDL, STAUBUS_LIT, CHI_LIT) so the
  corpus can be cut by the matter it was produced in, plus filepath / attachment / conversation ids
  so family links can be reconstructed.

Keyword strata are NOT labels: gold comes from the model panel (bench run ... -a multi + goldify).

Output: data/endo/endo_unlabeled.jsonl
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..mnk.fetch import EMAIL_FL, email_record, fetch_text, solr_search

ROOT = Path(__file__).resolve().parents[2]
EMAIL_BASE_Q = '(collection:"Endo Documents" AND type:email)'
DOC_URL = "https://www.industrydocuments.ucsf.edu/opioids/docs/#id="

# stratum -> (Solr body-text query, target n). Targets sum to 1,900.
STRATA: dict[str, tuple[str, int]] = {
    "opana_promo": ('ot:Opana AND ot:(promotion OR promotional OR "sales aid" OR messaging OR detailing OR "call plan" OR launch OR formulary)', 110),
    "opana_crush": ('ot:Opana AND ot:("crush resistant" OR "crush-resistant" OR "abuse deterrent" OR "abuse-deterrent" OR "tamper resistant" OR INTAC OR crush OR crushing OR snort OR snorting OR inject OR injection)', 110),
    "som": ('ot:"suspicious order"', 110),
    "som_release": ('ot:"suspicious order" AND ot:(pended OR released OR release OR "on hold" OR held OR "due diligence" OR "site visit")', 80),
    "dea": ('ot:DEA AND ot:(inspection OR investigation OR registration OR quota OR ARCOS OR audit OR subpoena)', 100),
    "risk_msg": ('ot:(Opana OR opioid OR opioids) AND ot:(addiction OR pseudoaddiction OR abuse OR dependence) AND ot:(training OR speaker OR "sales force" OR "talking points" OR messaging OR "fair balance")', 110),
    "rep_report": ('ot:(diversion OR "pill mill" OR "inappropriate prescribing" OR arrested OR "license suspended") AND ot:(prescriber OR physician OR "Dr.") AND ot:(rep OR representative OR detail OR detailing OR "call plan" OR target)', 100),
    "advocacy": ('ot:("American Pain Foundation" OR APF OR "National Initiative on Pain Control" OR NIPC OR painknowledge OR "American Academy of Pain Medicine" OR AAPM OR "American Pain Society")', 110),
    "kol_cme": ('ot:("key opinion leader" OR KOL OR KOLs OR "advisory board" OR "thought leader" OR CME OR "unrestricted grant" OR "educational grant")', 100),
    "editorial": ('ot:(APF OR "Pain Foundation" OR NIPC OR CME OR "advisory board" OR "patient education") AND ot:(edit OR edits OR edited OR "review and approve" OR approval OR disclosure OR disclose OR acknowledge OR acknowledgment OR unbranded)', 90),
    "adjacent": ('ot:(Lidoderm OR Voltaren OR Aveed OR Fortesta OR Supprelin OR Testim OR Valstar OR Xiaflex OR Frova OR Sanctura)', 170),
    "random": ("*:*", 610),
    # top-up after the first panel pass: som_narrow had 26 positives at 1,800 docs (~15% yield inside the SOM strata), so 200 more
    # suspicious-order e-mails were added to bring the narrowest request nearer the >=60-positive target. Recorded as its own stratum.
    "som_topup": ('ot:"suspicious order"', 200),
}

MIN_CHARS, MAX_CHARS = 300, 12_000
OVERSAMPLE = 3.0
NEWSLETTER_RE = re.compile(r"daily news|news report|news digest|newsletter|press clips|media monitoring|pulse\b|google alert|first word|fiercepharma|^\s*fw:\s*\[", re.I)
BATES_RE = re.compile(r"^([A-Za-z][A-Za-z_\-]*?)[\-_]?\d{5,}")


def bates_case(bates: str | None) -> str | None:
    """Collapse a Bates number to its production prefix (the matter it was produced in)."""
    if not bates:
        return None
    m = BATES_RE.match(bates.strip())
    return (m.group(1) if m else bates.split("-")[0]).rstrip("-_")


def norm_key(title: str | None, text: str) -> str:
    t = re.sub(r"^(re|fw|fwd)\s*:\s*", "", (title or "").lower()).strip()
    t = re.sub(r"\s+", " ", t)
    body = re.sub(r"\s+", " ", text[:600].lower())
    body = re.sub(r"^(subject|from|date|to|cc|sent):.*?(?=\s(subject|from|date|to|cc|sent):|$)", "", body)
    return f"{t}|{body[:300]}"


def build(out: Path, seed: int = 31, log=print) -> None:
    rng = random.Random(seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    have: dict[str, dict] = {}
    if out.exists():
        for l in out.read_text().splitlines():
            if l.strip():
                r = json.loads(l); have[r["id"]] = r
        log(f"resuming with {len(have)} docs")
    seen_keys = {norm_key(r["meta"].get("title"), r["text"]) for r in have.values()}
    per_stratum = Counter(r["meta"]["stratum"] for r in have.values())
    candidates_seen = 0

    with out.open("a") as f, ThreadPoolExecutor(max_workers=8) as pool:
        for stratum, (q, target) in STRATA.items():
            need = target - per_stratum.get(stratum, 0)
            if need <= 0:
                continue
            full_q = f"{EMAIL_BASE_Q} AND pg:[1 TO 6]" + ("" if q == "*:*" else f" AND ({q})")
            want = int(need * OVERSAMPLE)
            log(f"[{stratum}] need {need}; pulling {want} candidates")
            cands = list(solr_search(full_q, EMAIL_FL, want, {"sort": f"random_{seed + len(stratum)} asc"}))
            candidates_seen += len(cands)
            rng.shuffle(cands)
            recs = [email_record(d) for d in cands if d.get("id") not in have]
            got = 0
            for i in range(0, len(recs), 32):
                if got >= need:
                    break
                batch = recs[i : i + 32]
                texts = list(pool.map(lambda r: _safe_text(r["id"]), batch))
                for rec, text in zip(batch, texts):
                    if got >= need:
                        break
                    if not text:
                        continue
                    text = text.strip()
                    if not (MIN_CHARS <= len(text) <= MAX_CHARS):
                        continue
                    if NEWSLETTER_RE.search(rec["title"] or ""):
                        continue
                    k = norm_key(rec["title"], text)
                    if k in seen_keys or rec["id"] in have:
                        continue
                    seen_keys.add(k)
                    row = {
                        "id": rec["id"],
                        "text": text,
                        "labels": {},
                        "gray": [],
                        "meta": {
                            "stratum": stratum, "title": rec["title"], "author": rec["author"], "date": rec["date"],
                            "pages": rec["pages"], "custodian": rec["custodian"], "drug": rec["drug"],
                            "bates": rec["bates"], "case": bates_case(rec["bates"]),
                            "filepath": rec["filepath"], "conversation": rec["conversation"],
                            "attachments": rec["attachments"],
                            "url": f"{DOC_URL}{rec['id']}",
                        },
                    }
                    have[rec["id"]] = row
                    f.write(json.dumps(row) + "\n"); f.flush()
                    got += 1
                time.sleep(0.1)
            log(f"[{stratum}] added {got} (candidates {len(recs)})")
    log(f"total {len(have)} docs; candidates pulled this run {candidates_seen}")
    stats(have, log)


def stats(have: dict[str, dict], log=print) -> None:
    rows = list(have.values())
    log("by stratum: " + ", ".join(f"{k}={v}" for k, v in sorted(Counter(r["meta"]["stratum"] for r in rows).items())))
    log("by case:    " + ", ".join(f"{k}={v}" for k, v in Counter(r["meta"].get("case") for r in rows).most_common(12)))
    years = Counter((r["meta"].get("date") or "")[:4] for r in rows)
    log("by year:    " + ", ".join(f"{k}={v}" for k, v in sorted(years.items()) if k))
    log(f"custodians: {len({c for r in rows for c in r['meta'].get('custodian') or []})}; "
        f"with attachments: {sum(1 for r in rows if r['meta'].get('attachments'))}; "
        f"in a conversation: {sum(1 for r in rows if r['meta'].get('conversation'))}; "
        f"median chars: {sorted(len(r['text']) for r in rows)[len(rows)//2] if rows else 0}")


def _safe_text(doc_id: str) -> str | None:
    try:
        return fetch_text(doc_id)
    except Exception as e:  # noqa: BLE001
        print(f"  text fetch failed {doc_id}: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    build(ROOT / "data" / "endo" / "endo_unlabeled.jsonl")
