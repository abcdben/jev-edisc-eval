# TREC 2016 Total Recall (athome4) — Jeb Bush e-mail collection

Source: NIST TREC Total Recall track, <https://trec.nist.gov/data/total-recall/>.

## What is in this directory

| Path | Content | Tracked |
|---|---|---|
| `raw/tr2016-ext-topics.txt` | 2016 topics (title, description) | yes |
| `raw/athome4.facetsandqrels` | 2016 relevance judgments: `topic docno rel subtopic` (rel 0/1/2) | yes |
| `raw/prels.tr2016.alt{1,2,3}` | alternate-assessor samples | yes |
| `raw/athome1/` | 2015 athome1 topics and complete judgments (full-collection tier) | yes |
| `raw/README.html` | NIST's index page for the download | yes |
| `eval_ids.jsonl`, `dev_ids.jsonl`, `lat200_ids.jsonl` | the exact evaluation, development and latency samples used in the study, **without document text**: `id`, `labels`, `gray`, `meta` (docno, stratum, facet, importance) | yes |
| `dev_ids.txt`, `seen_ids.txt` | docnos excluded from `eval`/`full` (dev set; documents the analyst read while exploring) | yes |
| `eval.jsonl`, `dev.jsonl`, `lat200.jsonl`, `full.jsonl` | the same rows **with text** | no (`.gitignore`) |
| `local_subset.jsonl` | 600 e-mails **with text**, an early local-model pilot subset | yes, since 2026-09-20 (legacy; see `Article/github_publication_audit.md` §1.6 — to be removed, with a history rewrite, before any public release) |
| `../../TREC/Jeb Bush TXT/<docno>.txt` | the document collection | no (`.gitignore`) |

The topics and qrels are redistributed as-is from trec.nist.gov (US-government research data, freely downloadable; NIST is the source of record).

## The document collection is not redistributed

The Jeb Bush e-mail collection is distributed by NIST under the **TREC Total Recall Organizational/Individual Usage Agreement** (<https://trec.nist.gov/data/total-recall/>), which restricts use to research and prohibits redistribution of the documents. Apart from the legacy `local_subset.jsonl` noted above and the two worked examples in `results/examples.json`, this repository contains no e-mail text; the id manifests above are the "summaries" the agreement allows, from which the text cannot be reconstructed.

To reproduce the corpus files:

1. Obtain the athome4 collection from NIST under the usage agreement (instructions on the page above; requests go to `tr-request@nist.gov`).
2. Place the plain-text e-mails at `TREC/Jeb Bush TXT/<docno>.txt` in the repository root (one file per document, named by the numeric docno, e.g. `TREC/Jeb Bush TXT/1899.txt`).
3. Keep `data/trec/raw/`, `dev_ids.txt` and `seen_ids.txt` as tracked.
4. Run

   ```bash
   bench trec-build            # writes dev.jsonl, dev_ids.txt, eval.jsonl
   bench trec-build --full     # additionally writes full.jsonl (~290k e-mails, ~600 MB)
   ```

   The sampler (`ediscovery_bench/trec/build.py`) uses fixed seeds and the historical 12-topic definition, so the draws are deterministic: the regenerated `dev.jsonl` / `eval.jsonl` contain exactly the ids in `dev_ids.jsonl` / `eval_ids.jsonl`. Verify with

   ```bash
   diff <(jq -r .id data/trec/eval.jsonl) <(jq -r .id data/trec/eval_ids.jsonl) && echo eval OK
   ```

5. `lat200.jsonl` (the 200-e-mail latency sample) is the subset of `eval.jsonl` whose ids are listed in `lat200_ids.jsonl` (also `results/trec_lat/sample_ids.json`); filter `eval.jsonl` by those ids to rebuild it.

Gold convention (see `ediscovery_bench/trec/build.py`): rel 1 or 2 → `responsive`; judged non-relevant and unjudged → not responsive. Topic 404 (`eminent_domain`) is present in the files but excluded from the study at scoring time (`design/trec/dropped_eminent_domain.yaml`).
