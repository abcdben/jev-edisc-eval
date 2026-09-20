"""Build the Mallinckrodt email sample.

Design (see design/02 and 04):
- Emails only, from a set of key custodians, text 300-12,000 chars (long docs excluded per plan).
- Stratified: keyword-doped strata for each issue pair (so narrow issues are not empty) plus an
  adjacent-topic hard-negative stratum plus a random background stratum. Strata are recorded in
  meta so results can be cut by stratum. Keyword strata are *not* labels: gold comes from the panel.
- Dedupe by normalized subject + first 400 chars of body to thin near-duplicate thread copies.

Output: data/mallinckrodt/mnk_unlabeled.jsonl
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .fetch import EMAIL_BASE_Q, EMAIL_FL, email_record, fetch_text, solr_search

ROOT = Path(__file__).resolve().parents[2]

KEY_CUSTODIANS = [
    "Harper, Karen", "Spaulding, Eileen", "Tetzlaff, Gail", "Gillies, John", "Ratliff, Bill",  # compliance / security
    "Wessler, Michael", "Collier, Ginger", "Falcone, Melissa", "Webb, Kevin", "Muhlenkamp, Kate", "Terifay, Terrence",  # marketing
    "Cardetti, Lisa", "Becker, Steven", "New, Bonnie", "Borelli, Victor", "Chick, Stacy", "Williams, Jane", "Wickline, Ronald",  # sales / accounts
    "Kilper, Jeff", "Naten, Derek", "Decker, John", "Morelli, Art", "Neuman, Herb",  # finance / gov affairs / medical
]

# stratum -> (Solr body-text query, target n)
STRATA: dict[str, tuple[str, int]] = {
    "som": ('ot:"suspicious order"', 110),
    "som_release": ('ot:"suspicious order" AND ot:(pended OR released OR release OR "on hold" OR held)', 90),
    "mktg": ('ot:(Exalgo OR Roxicodone OR Methadose OR Xartemis) AND ot:(promotion OR promotional OR "sales aid" OR messaging OR "speaker program" OR "call plan")', 110),
    "mktg_abuse": ('ot:Exalgo AND ot:(abuse OR addiction OR diversion OR dependence OR "fair balance")', 90),
    "data": ('ot:(chargeback OR chargebacks OR "IMS data" OR "867 data" OR Xponent)', 110),
    "data_florida": ('ot:Florida AND ot:(oxycodone OR "pill mill" OR "pain clinic" OR pharmacy)', 90),
    "dea": ('ot:DEA AND ot:(inspection OR investigation OR registration OR subpoena OR audit OR "administrative")', 110),
    "dea_quota": ('ot:quota AND ot:(oxycodone OR hydrocodone OR DEA)', 90),
    "adjacent": ('ot:(Ofirmev OR INOmax OR Acthar OR Optiray OR "contrast")', 100),
    "random": ("*:*", 700),
}

MIN_CHARS, MAX_CHARS = 300, 12_000
OVERSAMPLE = 3.0


def custodian_clause() -> str:
    return "(" + " OR ".join(f'custodian:"{c}"' for c in KEY_CUSTODIANS) + ")"


def norm_key(title: str | None, text: str) -> str:
    t = re.sub(r"^(re|fw|fwd)\s*:\s*", "", (title or "").lower()).strip()
    t = re.sub(r"\s+", " ", t)
    body = re.sub(r"\s+", " ", text[:600].lower())
    body = re.sub(r"^(subject|from|date|to|cc|sent):.*?(?=\s(subject|from|date|to|cc|sent):|$)", "", body)
    return f"{t}|{body[:300]}"


def build(out: Path, seed: int = 21, log=print) -> None:
    rng = random.Random(seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    have: dict[str, dict] = {}
    if out.exists():
        for l in out.read_text().splitlines():
            if l.strip():
                r = json.loads(l); have[r["id"]] = r
        log(f"resuming with {len(have)} docs")
    seen_keys = {norm_key(r["meta"].get("title"), r["text"]) for r in have.values()}
    per_stratum = {s: sum(1 for r in have.values() if r["meta"]["stratum"] == s) for s in STRATA}
    cust = custodian_clause()

    with out.open("a") as f, ThreadPoolExecutor(max_workers=8) as pool:
        for stratum, (q, target) in STRATA.items():
            need = target - per_stratum.get(stratum, 0)
            if need <= 0:
                continue
            full_q = f"{EMAIL_BASE_Q} AND {cust} AND pg:[1 TO 6]" + ("" if q == "*:*" else f" AND ({q})")
            want = int(need * OVERSAMPLE)
            log(f"[{stratum}] need {need}; pulling {want} candidates")
            cands = list(solr_search(full_q, EMAIL_FL, want, {"sort": f"random_{seed + len(stratum)} asc"}))
            rng.shuffle(cands)
            recs = [email_record(d) for d in cands if d.get("id") not in have]
            got = 0
            # fetch text in parallel batches
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
                    if "Daily News Report" in (rec["title"] or "") or "Pulse" in (rec["title"] or "")[:8]:
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
                            "pages": rec["pages"], "custodian": rec["custodian"], "drug": rec["drug"], "bates": rec["bates"],
                            "url": f"https://www.industrydocuments.ucsf.edu/opioids/docs/#id={rec['id']}",
                        },
                    }
                    have[rec["id"]] = row
                    f.write(json.dumps(row) + "\n"); f.flush()
                    got += 1
                time.sleep(0.1)
            log(f"[{stratum}] added {got} (candidates {len(recs)})")
    log(f"total {len(have)} docs")


def _safe_text(doc_id: str) -> str | None:
    try:
        return fetch_text(doc_id)
    except Exception as e:  # noqa: BLE001
        print(f"  text fetch failed {doc_id}: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    build(ROOT / "data" / "mallinckrodt" / "mnk_unlabeled.jsonl")
