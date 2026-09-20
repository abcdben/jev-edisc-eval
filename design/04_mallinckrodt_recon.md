# 04 — Mallinckrodt Litigation Documents: data-access recon

Date: 2026-09-19. Goal: programmatically pull a sample of **emails with full text**
from the UCSF/JHU Opioid Industry Documents Archive (OIDA), collection
"Mallinckrodt Litigation Documents" (`collectioncode:mnk`).

Module: `ediscovery_bench/mnk/fetch.py` (stdlib + `httpx`; falls back to `urllib`).
Smoke test: `.venv/bin/python -m ediscovery_bench.mnk.fetch` (5 emails, metadata + text) — passes.

Collection size (verified via Solr): 1,414,503 docs; `dt_facet`: document 1,015,383 · **email 550,657** ·
spreadsheet 280,158 · presentation 41,333 · image 41,212 · other 21,765 · text 8,156.

---

## 1. Metadata API (Solr)

Use **`https://metadata.idl.ucsf.edu/solr/ltdl3/select`** — not `/query`.

| Handler | Behaviour |
|---|---|
| `/solr/ltdl3/query` | Ignores `rows`, `fl`, `facet.*`; always returns 1000 full docs with *friendly* field names (`author`, `recipient`, `type`, ...). Useless for paging/facets. |
| `/solr/ltdl3/select` | Real Solr `edismax` handler. Honors `rows` (up to 1000 tested), `fl`, `sort`, `cursorMark`, `facet.*`, `json.facet`, `echoParams=all`. Returns **raw** schema field names. |

Handler config (from `echoParams=all`): `defType=edismax`, `q.op=AND`, `mm=0%`, `df=er` ("everywhere"),
`qf=ot^0.01 ti^10.1 md_high_boost^10 md_no_boost md_low_boost^0.05`, `fq=published:true`, `timeAllowed=10000`.

### Field names: aliases vs raw
Friendly names work **only inside `q`** (edismax `f.<alias>.qf` aliases). `fl` and `facet.field` need raw names.

| alias (in `q`) | raw field | notes |
|---|---|---|
| `type` | `dt` (+ `dt_facet`) | `type:email` == `dt:email` |
| `title` | `ti` | |
| `author` | `au` | e.g. `"DeFusco, Chris R" <christopher.defusco@mallinckrodt.com>` |
| `recipient` | `rc` | comma-joined display names+addresses |
| `copied` | `cc` | |
| `documentdate` / `date` | `dd` (+ `dddate`) | string like `2013 October 03` |
| `pages` | `pg` | |
| `drug` | `dg` (+ `dg_facet`) | |
| `bates` | `bn` | e.g. `MNKOI0000257089` |
| `text` | `ot` | **full extracted text** (indexed, not returned) |
| (none) | `custodian` | `text_ngram` — multivalued, returned, **not facetable** |
| (none) | `datesent`, `timesent`, `datereceived`, `conversation`, `filepath`, `attachment`, `originalformat`, `filename`, `case`, `collection`, `collectioncode` | returned as stored |

Facetable fields that exist: `dt_facet`, `dg_facet`, `collection_facet`, `industry_facet`, `availability_facet`,
`availabilitystatus_facet`, `collectioncode`, `id`. **There is no `custodian_facet`**; `facet.field=custodian`
returns `[]` (fc) or n-gram garbage (enum). `au`/`rc` are not facetable either.

### Paging
- `cursorMark=*` + `sort=id asc` works (module default); `nextCursorMark` returned.
- `start` offset paging works only for `start <= 10000`; the proxy returns **HTTP 403** above that.
- `sort=random_<seed> asc` works (Solr RandomSortField) → cheap random sampling (≤ 10k per seed).
- POST bodies (JSON request API), `/terms`, `/admin/luke`, `/schema` → 403.
- Mirror host `https://solr.idl.ucsf.edu/solr/ltdl3/select` behaves identically; it also hosts a
  small `mnkemail` core (546,364 rows; `sender_facet`, `name_facet`, `email_facet`) that backs the
  website's "Mallinckrodt Email Tracker" (counts of emails *by sender*, not by custodian).

### Full-text search
Default field `er` covers text + metadata; `ot:` restricts to body text; `ti:` to subject/title.
Phrases and boolean operators are standard Lucene. Counts restricted to `EMAIL_BASE_Q`:

| query | default `q` (er) | `ot:` (body text) | `ti:` (title) |
|---|---:|---:|---:|
| `"suspicious order"` | 11,126 | 9,014 | 5,025 |
| `chargeback` | 5,831 | 5,807 | 1,204 |
| `Exalgo AND (abuse OR addiction)` | 4,317 | 3,404 | 75 |
| `Florida AND oxycodone` | 6,135 | 5,191 | 74 |
| `"speaker program"` | 8,086 | 8,082 | 2,665 |
| `"pill mill"` | 3,339 | 3,338 | 439 |

(`er` > `ot` because `er` also matches subject/author/filepath metadata; `Florida AND oxycodone` picks up the
`dg` drug tag.)

---

## 2. Full text on S3

Bucket `opioid-industry-documents-archive-dataset-bucket` (us-east-1, public, no auth; HTTPS works, no CLI needed).

Key layout — 4 single-char levels from the id, then an id directory:

```
<c1>/<c2>/<c3>/<c4>/<id>/<id>.ocr        # extracted text  (UTF-8 with BOM)  <-- what we want
<c1>/<c2>/<c3>/<c4>/<id>/<id>.pdf        # rendered PDF (INTELLIGENT_TIERING)
<c1>/<c2>/<c3>/<c4>/<id>/<id>.tif        # page images
<c1>/<c2>/<c3>/<c4>/<id>/<id>_thumb.png  # thumbnail
```

e.g. `hsvn0234` → `h/s/v/n/hsvn0234/hsvn0234.ocr`. Other top-level keys: `README.md`, `OIDA metadata notes.xlsx`,
`metadata/oida-index.parquet` (2.6 GB) and `metadata/oida-index-by-artifact.parquet` (3.0 GB, updated 2026-09-14),
`data-products/`, `samples/`.

Confirmed by downloading `.ocr` for 5 email ids (`nndn0234`, `qndn0234`, `hsvn0234`, `ffbb0235`, `ffbb0238`) and
then 40 random emails — **0 missing** (`fetch_text` returns `None` on 404). Latency ≈ 0.2–0.4 s/object.

---

## 3. Header situation

The `.ocr` text **includes headers** — no reconstruction needed, but two formats occur:

1. **Clean RFC-style header block** (≈ 92% of sample: 37/40) produced by the archive's MSG→text conversion:
   ```
   Subject: Re: CONFIDENTIAL FW: Q4 2013 SICP addendum ...
   From: "DeFusco, Chris R" <christopher.defusco@mallinckrodt.com>
   Date: Thu, 03 Oct 2013 18:24:55 -0400
   To: "Chick, Stacy A" <stacy.chick@mallinckrodt.com>,
       "Haynes, Elaine E" <elaine.haynes@mallinckrodt.com>
   Cc: ...
   <blank lines>
   body ... quoted thread with "From:/Sent:/To:/Subject:" blocks
   ```
   `Date:` absent in ~5/37 (then only in Solr `dd`/`datesent`/`timesent`).
2. **OCR of a page-image rendering** (≈ 8%): a `Message` / `From:` / `Sent:` / `To:` / `Subject:` block, sometimes
   with labels and values on separate lines or OCR noise (e.g. `nnddist.S040O0O3@PWALUNCKRO0`), plus Bates/
   "Confidential — Subject to Agreed Protective Order" footers. Calendar items use `From  :` / `Sent  :` / `Location :`.

Recommendation: keep the text's own header (it's what a reviewer would see) and carry Solr `au`/`rc`/`cc`/`dd`/`ti`
as structured metadata; fall back to Solr for a synthesized header only when `^From:` is missing.
Exchange DN addresses (`/o=mkglobal/ou=exchange administrative group/...`) appear instead of SMTP in some `From:`.

### Text length (40 random emails, `sort=random_11`)
- min 191 · Q1 840 · **median 1,786** · Q3 5,052 · mean 7,354 · max 90,975 chars
- **> 12,000 chars: 4 / 40 (10%)**; > 6,000: 7 (18%); > 30,000: 2 (5%)
- The long tail is newsletters ("Mallinckrodt Daily News Report" 81–91k chars, PhRMA "Pulse" 20k) and long
  quoted threads. `pg` (pages) correlates: 1-page emails ≈ 200–2,700 chars.

---

## 4. Custodians (`type:email`)

No custodian facet exists, so distribution was estimated from an 11,000-email random sample (`random_7`,
`start` ≤ 10,000) and then **exact counts** obtained per name with `custodian:"Last, First"` (sample ratios match
exact counts within ~2%). Caveat: `custodian` is n-gram analysed, so a short name that is a prefix of another
inflates ("Buist, Jen" 9,809 ⊇ "Buist, Jennifer" 9,033). Roles: **KA** = Key Actors page, **Dep** = Depositions page
(both from the collection page's "Where to start" links, CMS `cms.libckm.org/api/graphql`, slugs
`mallinckrodt-litigation-documents--key-actors`, `...--depositions`), **Sig** = mined from email signature blocks.

| # | custodian | emails | role / title | src |
|--:|---|--:|---|---|
| 1 | Wessler, Michael | 37,573 | Product Director, Marketing (Specialty Pharmaceuticals); earlier Marketing Manager | Dep/Sig |
| 2 | Spaulding, Eileen | 33,439 | Controlled Substances Compliance (Compliance Analyst), 1998–2019 | Dep/Sig |
| 3 | Cardetti, Lisa | 31,873 | Director, National Accounts (2006–2017); earlier Product Manager | Dep/Sig |
| 4 | Harper, Karen | 29,281 | Senior Manager, Controlled Substances Compliance (SOM program lead), 1975–2019 | KA |
| 5 | Collier, Ginger | 18,174 | Senior Director of Marketing, Specialty Generics (2009–2015) | KA |
| 6 | Becker, Steven | 17,973 | National Account Manager (2000–2014), wholesaler/chain relationships | KA |
| 7 | Network Share | 15,930 | (shared drive, not a person) | — |
| 8 | Webb, Kevin | 15,440 | Senior Product Manager (2007–09); Director, Advocacy & Stakeholder Engagement (2013–16) | KA |
| 9 | New, Bonnie | 14,937 | National/Regional Account Manager (1989–2018) | KA |
| 10 | Falcone, Melissa | 14,301 | Senior Product Manager, Specialty Pharmaceuticals | Sig |
| 11 | Kisinger, Connie | 13,567 | Western Region Sales Director | Sig |
| 12 | Rehkop, Brenda | 12,259 | Customer Service Representative | Sig |
| 13 | Brendel, Diane | 11,695 | Manager, Communications | Sig |
| 14 | Decker, John | 11,654 | Director, Scientific Communications | Sig |
| 15 | Young, Jim | 11,482 | VP, Program Management & Clinical Operations / VP, R&D Operations | Sig |
| 16 | Kilper, Jeff | 10,522 | Senior Director, Finance, Specialty Generics (2016–) | Dep |
| 17 | Buist, Jennifer (+ "Buist, Jen") | 9,033 (9,809) | unknown | — |
| 18 | Williams, Jane | 9,583 | Vice President, Retail Sales, Specialty Generics (2010–2015) | KA |
| 19 | Abbey, Michael | 8,911 | unknown | — |
| 20 | Rago, Jay | 8,181 | District Sales Manager, Boston | Sig |
| 21 | McGowan, Gavin | 7,659 | Eastern Regional Sales Director | Sig |
| 22 | Becker, Kevin | 7,595 | District Sales Manager | Dep |
| 23 | DuMont, Kirk | 7,515 | Regional Sales Manager (2010–) | Dep |
| 24 | Naten, Derek | 7,376 | Sr. Director, Government Affairs & Advocacy | Sig |
| 25 | Borelli, Victor | 6,885 | National Sales Manager (2006?–2012), wholesaler liaison; emails prominent in press | KA |
| 26 | Steffens, Jane | 6,884 | unknown | — |
| 27 | Phillips, Lynn (Kipler) | 6,461 | Manager, Media Relations | Dep |
| 28 | Meyer, Jay | 6,370 | Regional Sales Director (Central / West) | Sig |
| 29 | Donalty, Brian | 6,294 | District Manager, Virginia | Sig |
| 30 | Tetzlaff, Gail | 5,737 | Compliance (per depositions page, "Compliance?") | Dep |
| 31 | Chick, Stacy (Deanna) | 5,369 | Vice President of Specialty Sales (2013–2015) | KA |
| 32 | Wickline, Ronald | 5,087 | Vice President, Sales (2010–2014) | KA |
| 33 | Terifay, Terrence | 5,058 | VP, General Management/Marketing, brands (2011–2014) | KA |
| 34 | Grelle, Ed | 4,861 | Director, Sales Training | Sig |
| 35 | Rausch, Jim | 4,826 | Customer Service Manager, Finished Goods | Dep |
| 36 | Patterson, Steven | 4,617 | District Sales Manager, New York Metro | Sig |
| 37 | Silver, David | 4,448 | Vice President (function not confirmed) | Sig |
| 38 | Kelly, Shannon | 4,250 | District Manager | Sig |
| 39 | Lum, Alice | 4,183 | Senior District Sales Manager | Sig |
| 40 | Cramer, Shannon | 3,715 | unknown | — |

Next 40 (exact counts): Muhlenkamp (Neely), Kate 3,568 (Product Manager 2007–11, KA) · Stewart, Cathy 3,461 (Manager,
Customer Service, Dep) · Nichols, Bill 3,368 (Regional Sales Director, Southeast, Sig) · Dress, Timothy 3,324 ·
Morelli, Art 3,162 (VP Medical Affairs, Dep) · Neuman, Herb 3,141 (Chief Medical Officer, Sig) · Degen, Karen 3,139
(Sr Hospital District Sales Mgr, Dep) · Gillies, John 2,981 (VP Global Security 2012–19, KA) · Hankins, Shawna 2,906 ·
Long, Erika 2,815 · O'Neill, Hugh 2,799 (EVP, Chief Commercial Officer, KA) · Polesovsky, Daniel 2,749 ·
Papakonstantis, Stephanie 2,747 · Wilmert, Sean 2,667 · Kelly, John 2,560 · Holthaus, Gena 2,455 · Jones, Paul C 2,430 ·
Darrell, Mary 2,104 · McDaniel, Neal 2,022 · Kampfl, Christian 1,940 · Synchrony 1,910 (agency) · Saffold, George 1,788
(Director, Global Customer Service, Dep) · Jackson, Catherine 1,705 (Manager, Medical Advocacy, Dep) · Adams, John 1,476
(VP Sales, MNK Generics 2004–10, Dep) · Rowley-Kilper, Tiffany 1,434 (Trade Relations Mgr, Contracts, Dep) ·
Gallegos, Kimberly 1,378 · Kenyon, Scott 1,298 · Rochester Drug Communications 1,245 · Becerra, Patricia (Celeste) 1,238 ·
Psaros, Harry 1,194 · Seger, Deborah 1,121 · Sandys, Steven 1,067 · Klein, Warren 1,021 · Clark, Christopher 955
(Specialty Sales, Dep) · DePriest, Julie 953 · Druen, Todd 937 · Mills, Janie 926 · Egan, Edward 918 · Ratliff, Bill 895
(Chief Security Officer 2000–12, KA) · Elsbernd, Brian 883 · Kern, Greg 879.

Key actors with few emails as *custodian* (they appear mostly as author/recipient): Harbaugh, Matthew (CEO Specialty
Generics / CFO), Trudeau, Mark (President & CEO 2012–), Vorderstrasse, Kevin (Sr Director, Product Mgmt & Analytics),
Cox, Erin 679 (Sales Specialist), Hichman, Eric 598, Jolliff, Susan 455, Pate, George 375, Dean, Todd 363.

Full raw lists: `/tmp/mnk_custodian_sample.txt`, `/tmp/mnk_custodian_exact.txt` (not committed).

---

## 5. Gotchas

- **Use `/select`, not `/query`.** `/query` silently ignores paging/field/facet params.
- **`fl` must use raw field names** (`ti,au,rc,dd,pg,...`); aliases are silently dropped (you get only `id`).
  `fetch.solr_search` translates common aliases via `FIELD_ALIASES`.
- **`start > 10000` → HTTP 403** from the proxy. Use `cursorMark` (needs `sort` ending in `id asc`).
- **No custodian/author facets.** Estimate via `sort=random_N` sampling (`fetch.sample_field_counts`) then get exact
  counts with `custodian:"Last, First"` queries. N-gram analysis makes short names match longer ones.
- `custodian` contains non-people values: `Network Share`, `Synchrony`, `Rochester Drug Communications`,
  `Central Files-PARC`, `Mallinckrodt Grant Files`, `deposition exhibits`.
- POST / JSON request API / admin endpoints → 403. GET only. No observed per-request rate limiting at ~2–5 req/s
  (~200 Solr + ~150 S3 requests in this session; zero 429/5xx). Module sleeps 0.2 s between pages and retries with
  backoff (`FetchError` after 4 attempts).
- `.ocr` files start with a UTF-8 **BOM** (`fetch_text` decodes with `utf-8-sig`). Line endings `\n`; some OCR files
  have long runs of blank lines (spreadsheet renderings).
- Most Solr fields come back as **single-element lists** (`au`, `rc`, `dd`, `ti`...); `email_record()` unwraps.
- Dates: `dd` is a display string (`2013 October 03`); `dddate` is the ISO/date field; `timesent` is a 12-h string.
- ~10% of emails exceed 12k chars (newsletters, long threads); consider truncating to the first N chars/first
  message for LLM review, or filter `pg:[1 TO 4]`.
- Emails are near-duplicated heavily across custodians (same thread in many mailboxes); `conversation` and
  `title` help dedupe. Attachments are separate docs (ids in `attachment` = Bates numbers, not ids).
- The public website's Solr for the "Email Tracker" (`solr.idl.ucsf.edu/solr/mnkemail`) is a sender-level index
  only; `metadata.idl.ucsf.edu` 403s that core.
