# GitHub publication audit — `typesafe-ai`

Prepared 2026-09-27 against the working tree at commit `e769dfd` (branch `master`, 244 commits, no remote). Read-only audit; nothing was committed, pushed, or modified. Tools: `git` (log/grep/rev-list), `gitleaks 8.30.1` (installed via Homebrew for this audit; run over the full history and over the working-tree publication candidates), `rg`, `du`, `unzip -l` for the `.docx` internals, and two web look-ups of the TREC and UCSF data terms.

## 0. Summary of what matters

1. **No API key or credential was ever committed.** The only live secrets are the four keys in `.env` (TypeSafe, Anthropic, OpenAI, Gemini); `.env` is git-ignored and `git log --all --diff-filter=A` confirms it was never added. gitleaks over the whole history returns 7 findings, all false positives (localStorage key names and `"claude-…"` model-key strings).
2. **The repository history contains data that the TREC Total Recall usage agreement forbids redistributing.** `data/trec/local_subset.jsonl` (600 full Jeb Bush emails, with constituents' names and addresses) has been tracked since commit `8d68bd3` (2026-09-20). Publishing this repo "as is, history included" republishes the collection. Either rewrite history (`git filter-repo`) or start a fresh repo.
3. **Full Mallinckrodt email text is tracked** (`data/mallinckrodt/mnk.jsonl`, `mnk_unlabeled.jsonl`, `ft_*.jsonl`, `local_subset.jsonl`; ~29 MB, 1,840 labelled + ~1,600 unlabelled emails, since commits `a2aae3c`/`8ca8207`). The source archive (UCSF/JHU Opioid Industry Documents Archive) is public but its terms say material may not be "substantially reproduced" without the rights holder's permission; fair use for non-commercial research is invoked. The repo already has a by-id fetcher (`ediscovery_bench/mnk/fetch.py`), so "ids + labels + fetch script" is a low-cost alternative. Author decision.
4. **A `git add -A` today would add 612 MB**, most of it `data/trec/full.jsonl` (585 MB, 286,326 full emails: over GitHub's 100 MB hard limit and non-redistributable) plus 290,100 files under `TREC/Jeb Bush TXT/` (1.3 GB). Both need `.gitignore` entries before anything is staged.
5. **`results/` is 11 GB on disk (693 files, five files over 100 MB, three of 1.4 GB) but compresses about 50×** (measured 41–91× on samples), so the entire per-decision record set is roughly 200–300 MB as `.tar.zst`/`.jsonl.gz`: a GitHub Release asset (2 GB per file limit) or Zenodo deposit, not Git LFS (free quota 1 GB storage/month) and not the repo itself.
6. **`Article/` should not be published as-is.** Four `.docx` drafts (8 MB total) each embed TypeSafe's 1 MB "typesafe-race" GIF, carry `INCLUDEPICTURE "/Users/bensexton/Library/Group…"` field codes and `dc:creator` "Ben Sexton", and the review notes name Jeremy Pickens (18 mentions), quote private Gmail threads, and cite private chat transcripts.
7. **The site cannot be built from a clean clone today**: `site/src/data.ts:1` and `site/src/examples.ts:1` import `../../results/findings.json` and `../../results/examples.json`, which are git-ignored (`results/` in `.gitignore`, only `results/.gitkeep` is tracked).
8. **No `LICENSE`, no lockfile, no tests, no CI, no data-acquisition instructions** in `README.md`.

---

## 1. Secrets

### 1.1 Live secrets on disk (not in git)

| File:line | What | In git? | Action |
|---|---|---|---|
| `.env:4` | `TYPESAFE_API_KEY=apikey_2…` (gitleaks `generic-api-key`) | No. Ignored by `.gitignore:5`; never added in any commit | Keep ignored. Rotating before publication is optional hygiene, not required by anything found here. |
| `.env:7` | `ANTHROPIC_API_KEY=sk-ant-a…` (gitleaks `anthropic-api-key`) | No | same |
| `.env:10` | `OPENAI_API_KEY=sk-proj-…` (gitleaks `openai-api-key`) | No | same |
| `.env:13` | `GEMINI_API_KEY=AQ.Ab8RN…` (gitleaks `generic-api-key`) | No | same |

`.env.example` (tracked) has the same four variable names with empty values and links to each console. Clean.

### 1.2 gitleaks over the full git history (`gitleaks git .`, 244 commits, 157 s)

7 findings, **all false positives**:

| Rule | File:line | Commits | Actual content |
|---|---|---|---|
| generic-api-key | `site/src/components/Disclaimer.tsx:13` | `3324db8f`, `50b75d45`, `7d1ca952`, `1d0fdba5` | `const ACK_KEY = "disclaimer_ack_v3";` (localStorage key) |
| generic-api-key | `site/src/data.ts:71`, `:53` | `7c9f297a`, `35cbd253` | `key: "claude-haiku-4.5"` (model roster key) |
| generic-api-key | `ediscovery_bench/config.py:60` | `262cb72d` | `key="claude-haiku-4.5"` |

### 1.3 gitleaks over the working tree (publication candidates: `Article design data site/src site/tools scripts ediscovery_bench tasks veridian .env .env.example README.md pyproject.toml results/*.json results/*/REPORT.md`)

Beyond `.env` (above), 16 findings, all false positives: `data/trec/full.jsonl:11109, 215292, 226786` (`X-MSExch-Correlation-Key:` mail headers inside email bodies), `ediscovery_bench/config.py:126`, `site/src/data.ts:100`, `site/src/components/Disclaimer.tsx:13`, and ten `model_key":"claude-…` hits on the single line of `results/findings.json`.

### 1.4 Regex sweep for key shapes (`sk-`, `sk-ant-`, `sk-proj-`, `AKIA`, `apikey_`, `jv_live_`, `hf_`, `AIza`, `AQ.`, `ghp_`, `github_pat_`, `xox[bp]-`)

- Tracked files (excluding corpus JSONL): **no hits**.
- Tracked corpus files: one hit in `site/public/cutoffs.json`, a base64 `u16` probability array that happens to match `AKIA…`; not a key.
- Git history (`git log -p --all`): **no key-shaped strings** added or removed in any commit.
- `.env` never appears as a path in any commit.

### 1.5 Personal identifiers, paths, e-mail addresses

**Tracked (would ship with the repo):**

| File:line | Content | Assessment |
|---|---|---|
| `site/src/components/Disclaimer.tsx:10` | `const CONTACT_HREF = "mailto:abcdben@gmail.com";` | Author's contact, already public on decider.tarcalc.com. Keep or swap for a GitHub-issues link. |
| `scripts/deploy_site.sh:13-14` | commit identity `deploy@tarcalc.com`; `git push -q -f https://github.com/abcdben/tarcalc.git main` | No token embedded (relies on local credential helper). Reveals the deploy target and the author's GitHub account; fine if the account is meant to be public. |
| `scripts/gpu_box.sh:150-151` | `sudo systemctl stop ollama` etc. | Fine; no host names, IPs or keys anywhere in the script. |
| `design/04_mallinckrodt_recon.md:34, 105, 107, 108` | `christopher.defusco@mallinckrodt.com`, `stacy.chick@mallinckrodt.com`, `elaine.haynes@mallinckrodt.com` (sample records from the public archive) | Third-party personal data (business e-mails of named employees). Low risk since the source is a public archive, but see §3.2. |
| `veridian/bible.md:127` | `eruiz@whitfieldbarr.com` | Fictional (file header says so). Fine. |
| every commit | author `Ben Sexton <abcdben@gmail.com>` (241 commits) and `Ben Sexton <ben@local>` (3 commits) | Published with the history. The `ben@local` identity is harmless but will not link to a GitHub profile. |
| `/Users/bensexton` | **no occurrences in any tracked file or in any historical diff** | — |

**Untracked (would ship with `git add -A`):**

| File:line | Content |
|---|---|
| `Article/precision_projection.md:174` | `cd /Users/bensexton/Projects/typesafe-ai && .venv/bin/python /tmp/prec_proj/…` |
| `Article/Jev Article For Review.docx`, `… - edited.docx`, `… - callouts addressed.docx`, `Jev Article v2.docx` → `word/document.xml` | 7 × `INCLUDEPICTURE "/Users/bensexton/Library/Group…"` field codes each; `docProps/core.xml` `dc:creator`/`cp:lastModifiedBy` = "Ben Sexton" |
| `Article/pickens_alignment.md:11, 53, 55` | Names Jeremy Pickens; quotes "two Gmail threads"; links three private Cursor chat transcripts by UUID |
| `Article/review.md`, `answers.txt`, `changes*.md`, `callouts_addressed*.md`, `draft_*.md`, `original_callouts_extracted.md`, `review_v2wip.md` | Unpublished drafts and reviewer Q&A; "Pickens" appears 18 times across `Article/*.md` |
| `data/trec/*.jsonl`, `TREC/Jeb Bush TXT/*.txt` | Tens of thousands of constituents' e-mail addresses (`@aol.com`, `@myflorida.com`, `@jeb.org`, …), names, phone numbers (see §3.1) |

### 1.6 Content in history that would need a rewrite to remove

| Path | First commit | Status now | Why it matters |
|---|---|---|---|
| `data/trec/local_subset.jsonl` (1.5 MB, 600 emails, full text) | `8d68bd3` 2026-09-20 | tracked | TREC agreement forbids redistribution (§3.1) |
| `data/mallinckrodt/mnk.jsonl`, `mnk_unlabeled.jsonl`, `ft_train.jsonl`, `ft_test.jsonl`, `local_subset.jsonl`, `ft_split.json` | `a2aae3c`, `8ca8207` 2026-09-19/20 | tracked | Full text from a public archive; redistribution is a judgement call (§3.2) |
| `data/cuad/raw/CUADv1.json` (38.3 MiB), `data/cuad/raw/test.json` (7 MiB) | `72cdd68` 2026-09-20 | tracked | Not a licensing problem (CC BY 4.0) but 45 MB of upstream data that `bench cuad-build` re-downloads anyway |
| `site/src/logos/claude.svg`, `gemini.svg`, `gemma.svg`, `laya.png` | deleted later | history only | Vendor marks as files; now inlined as SVG paths in `site/src/logos.tsx` |
| `data/sample/harbor_point.jsonl`, `tasks/privilege.yaml`, `tasks/responsiveness.yaml` | `262cb72` | deleted | Scaffold-era files; harmless |

Everything else in history is code, YAML, design notes, and the Veridian synthetic corpus.

---

## 2. Inventory and size

### 2.1 Git object store

```
git count-objects -vH:  count 845 (6.77 MiB loose), in-pack 1238, size-pack 22.86 MiB, 2 packs
tracked files: 138        commits: 244        branches: master only        remote: none
```

Tracked working-tree bytes ≈ 123 MB, of which `data/**` + `veridian/*.jsonl` + `site/public/cutoffs.json` ≈ 123 MB and code ≈ 1 MB. Largest tracked blobs: `data/cuad/raw/CUADv1.json` 38.3 MiB, `data/mallinckrodt/mnk.jsonl` 8.8 MiB, `mnk_unlabeled.jsonl` 7.5 MiB, `data/cuad/raw/test.json` 7.0 MiB, `data/veridian/veridian.jsonl` 6.7 MiB. Nothing tracked exceeds GitHub's 50 MB warning or 100 MB hard limit.

### 2.2 Per top-level directory

| Directory | On disk | Tracked files | Untracked, not ignored | Ignored | Notes |
|---|---|---|---|---|---|
| `TREC/` | 1.3 GB | 0 | **290,100** `.txt` in `Jeb Bush TXT/` (1.3 GB) + 13 docno lists in `Responsive Docs/` (928 KB) | `.DS_Store`, `desktop.ini` | Not in `.gitignore`. `git add -A` would stage all 290k files. Directory's link count (65535) already shows filesystem strain. |
| `results/` | **11 GB** | 1 (`.gitkeep`) | 0 | 693 files (`results/` ignored) | `findings.json` 1.0 MB, `examples.json` 0.8 MB, `determinism.json` 85 KB, per-corpus `summary*.json`/`REPORT.md`, and per-decision `.jsonl`: `trec_full/` 4.9 GB (3 × 1.4 GB), `cuad/` 2.8 GB, `trec/` 1.5 GB, `veridian/` 626 MB, `mnk/` 554 MB, `mnk_det/` 105 MB, rest < 25 MB each |
| `data/` | 713 MB | 26 | 21 in `data/trec/` (612 MB: `full.jsonl` 585 MB, `eval.jsonl` 7.4 MB, `dev.jsonl` 1.8 MB, `lat200.jsonl` 0.5 MB, `raw/` 2.3 MB NIST files) + `data/mallinckrodt/det300.jsonl` 1.5 MB | — | Tracked: `cuad/` 59 MB, `mallinckrodt/` 29 MB (minus det300), `veridian/` 27 MB, `trec/{local_subset.jsonl,dev_ids.txt,seen_ids.txt}` |
| `.venv/` | 1.2 GB | 0 | 0 | 45,144 files | ignored |
| `site/` | 80 MB | 51 | 0 | `node_modules/` 74 MB, `dist/` 3.8 MB, `.DS_Store` | `src/` 736 KB, `public/cutoffs.json` 1.5 MB, `package-lock.json` present |
| `Article/` | 48 MB | 0 | 44 (4 `.docx` = 8.3 MB; 16 `.md`/`.txt`; `charts/` 24 PNG = 3.9 MB) | `.docx-venv/` (1,307 files, ~36 MB), `.DS_Store` | `.docx-venv` is ignored only by the `Article/.docx-venv/.gitignore` (`*`) that `python -m venv` wrote inside it, not by the repo's `.gitignore`. Add an explicit rule so the protection does not depend on that file. |
| `veridian/` | 6.8 MB | 5 | 0 | — | `bible.md` + 4 manifests (synthetic matter) |
| `design/` | 376 KB | 8 | 3 (`04_run_plan.md`, `04_run_plan.pdf` 220 KB, `05_jev_recipe.md`) | `.DS_Store` | |
| `ediscovery_bench/` | 1.0 MB | 37 | 0 | `__pycache__` | |
| `tasks/` | 108 KB | 4 | 0 | | |
| `scripts/` | 20 KB | 3 | 0 | | |
| root | | `README.md`, `pyproject.toml`, `.gitignore`, `.env.example` | | `.env`, `.DS_Store`, `Screenshot 2026-09-19 at 2.40.58 PM.png` (1.2 MB), `ediscovery_bench.egg-info/` | |

### 2.3 Against GitHub limits

- **Over the 100 MB per-file hard limit** (push rejected): `data/trec/full.jsonl` 585 MB (untracked, would be staged by `git add -A`); `results/trec_full/multi/jev__base.jsonl`, `laya__recipe.jsonl`, `lexical.jsonl` 1.4 GB each; `results/trec_full/multi/tar__t1_5000_noisy.jsonl` 207 MB; `tar__t1_1000_noisy.jsonl` 107 MB (all ignored today).
- **Over the 50 MB warning:** `results/trec_full/multi/tar__t1_100_div.jsonl` 93 MB, `tar__t1_1000_div.jsonl` 64 MB, `tar__t1_100_noisy.jsonl` 60 MB; nothing tracked.
- **Repository comfort (~1 GB):** the current tracked set (23 MiB packed) is fine. Adding `results/**/*.jsonl` uncompressed (11 GB) or `TREC/` (1.3 GB, 290k files) is not.
- **Compressibility measured** (gzip -6 on the first 50 MB of each): results JSONL 41–91× (`results/trec/multi/claude-haiku-4.5.jsonl` 17.7 MB → 325 KB; `trec_full/multi/jev__base.jsonl` 50×; `tar__t1_5000_noisy.jsonl` 91×). **The whole `results/` tree should pack to roughly 200–300 MB.** Corpus text compresses only 3–4× (`data/trec/full.jsonl` 3.1× → ~190 MB; `mnk.jsonl` 4.2×).
- **Where things belong:**
  - Repo: code, tasks, design, `results/findings.json`, `examples.json`, `determinism.json`, `summary*.json`, `REPORT.md`, `site/public/cutoffs.json`, Veridian and CUAD corpora (small, redistributable), id/label manifests.
  - Release asset or Zenodo (DOI, 50 GB/deposit): one `.tar.zst` per corpus of per-decision `results/**/*.jsonl` (≈ 200–300 MB total); optionally `trec_full/` as its own asset (≈ 100 MB compressed).
  - Git LFS: not recommended. Free tier is 1 GB storage + 1 GB bandwidth per month; every clone with `git lfs pull` burns bandwidth, and the files are not versioned artefacts in any useful sense.
  - Separate download / not published: `TREC/Jeb Bush TXT/`, `data/trec/*.jsonl` (see §3.1); `data/cuad/raw/` (upstream zip, re-downloaded by `bench cuad-build`); `.venv`, `node_modules`, `Article/.docx-venv`.

---

## 3. Data licensing and redistribution

### 3.1 TREC 2016 Total Recall (athome4) — Jeb Bush e-mails and NIST qrels

**What is in the repo**

| Path | Content | Tracked |
|---|---|---|
| `TREC/Jeb Bush TXT/<docno>.txt` | 290,100 full e-mails, "user-supplied copy of the collection" (`ediscovery_bench/trec/build.py:9`) | No (not ignored either) |
| `TREC/Responsive Docs/Responsive/*.txt` | docno lists per topic (ids only; a reformatting of the qrels) | No |
| `data/trec/raw/README.html`, `athome4.facetsandqrels`, `prels.tr2016.alt{1,2,3}`, `tr2016-ext-topics.txt`, `athome1/judgments_athome1{00..09}`, `athome1/topics` | NIST topics and relevance judgments, 2.3 MB | No |
| `data/trec/full.jsonl` (286,326 rows), `eval.jsonl` (3,116), `dev.jsonl` (668), `lat200.jsonl` (200) | **full e-mail text** + labels + meta | No |
| `data/trec/local_subset.jsonl` (600 rows) | **full e-mail text** | **Yes, since `8d68bd3`** |
| `data/trec/dev_ids.txt`, `seen_ids.txt` | ids only | Yes |
| `results/examples.json` → `corpora.trec.documents` | 2 full e-mails (`JB-195816`, …; ≈ 5.2k chars) | No (ignored), but imported by the site |
| `results/trec*/…jsonl`, `site/public/cutoffs.json` | `doc_id` + label/probability only, no text | — |
| `tasks/trec.yaml`, `design/trec/criteria_v0.yaml`, `criteria_v1.yaml`, `dropped_eminent_domain.yaml`, `calibration.md` | the study's own criteria text; quotes topic titles/descriptions | Yes / partly |

**Terms found** (no license file in the repo; `data/trec/raw/README.html` is NIST's one-paragraph index). The NIST "TREC Total Recall Organizational/Individual Usage Agreement" (`https://trec.nist.gov/data/total-recall/tr-ind.pdf`) that gates the athome collections says: use only for research on NLP/IR/document-understanding systems; "summaries, analyses and interpretations … may be derived and published, provided it is not possible to reconstruct the information from these summaries"; "small excerpts … may be displayed to others or published in a scientific or technical" context; otherwise "the display, reproduction, transmission, distribution or publication of the information is prohibited"; access is by signed agreement sent to `tr-request@nist.gov`. The topics and qrels are downloadable from NIST without an agreement (`https://trec.nist.gov/data/total-recall/`).

**Assessment**

- Redistributing e-mail text (`TREC/Jeb Bush TXT/`, `data/trec/*.jsonl` including the tracked `local_subset.jsonl`) is **not permitted** under that agreement. The collection was originally released under Florida's public-records law and Jeb Bush published the e-mails himself in 2015, but the TREC copy is the "(redacted)" NIST-distributed version (Overview paper §2), and the terms attach to the copy the author holds. How the author's copy was obtained (TREC agreement, a colleague, the 2015 public release) is **unknown from the repo** and changes the answer; only the author knows.
- The qrels/topics under `data/trec/raw/` are US-government-distributed research data with no stated license; they are freely downloadable and routinely mirrored. Including them with attribution and the NIST URL is low risk; a `bench trec-build --fetch-qrels` step that downloads them would be cleaner.
- Ids + gold labels + strata (`dev_ids.txt`, `seen_ids.txt`, a new `eval_ids.jsonl` with `{id, labels, meta}` and no `text`) are a "summary" from which the text cannot be reconstructed and are fine to publish; `ediscovery_bench/trec/build.py` already documents the seeded, deterministic draw, so anyone holding the collection can regenerate `dev/eval/full.jsonl` exactly.
- `results/examples.json` currently embeds two full TREC e-mails and two Mallinckrodt e-mails (`corpora.trec.documents`, `corpora.mnk.documents`). Two e-mails is arguably a "small excerpt" in a scientific write-up, but the site republishes them verbatim to the public. Regenerate examples with the TREC texts truncated or replaced by ids before tracking the file.
- **Personal data:** the e-mails contain constituents' full names, personal e-mail addresses (`@aol.com`, `@yahoo.com`, `@juno.com` …), sometimes phone numbers and home towns, plus state employees' addresses. `data/trec/full.jsonl` alone tripped gitleaks on mail headers three times. Any published copy is a personal-data release, independent of the TREC terms.

### 3.2 Mallinckrodt opioid-litigation e-mails (`data/mallinckrodt/`, `results/mnk*`)

**What is in the repo**

| Path | Content | Tracked |
|---|---|---|
| `data/mallinckrodt/mnk.jsonl` (1,840 rows, 9.2 MB) | **full OCR e-mail text**; `labels` from a 3-LLM panel; `meta` = `{stratum, title, author, date, pages, custodian, drug, bates, url, panel{…}}` | Yes (`8ca8207`) |
| `mnk_unlabeled.jsonl` (7.8 MB), `ft_train.jsonl`, `ft_test.jsonl`, `local_subset.jsonl`, `ft_split.json` | full text / derived splits | Yes |
| `det300.jsonl` | 300-doc determinism sample, full text | No |
| `design/02_mallinckrodt_plan.md`, `04_mallinckrodt_recon.md` | plan + sample records with employee names/e-mails | Yes |
| `ediscovery_bench/mnk/fetch.py`, `sample.py` | fetcher (Solr `metadata.idl.ucsf.edu` + S3 `opioid-industry-documents-archive-dataset-bucket`) and stratified sampler; `KEY_CUSTODIANS` lists 23 named employees | Yes |
| `results/mnk/**`, `results/mnk_det/**` | ids + labels/probabilities, no text | ignored |

**Terms found.** Nothing in the repo. The UCSF Industry Documents Library's Copyright & Fair Use page: the archive is public and "makes its collections available under court-approved agreements with the rights holders or legal precedent", but "companies or individuals who created the information may still hold the rights, meaning material cannot be 'substantially' reproduced in books or other media without the copyright holder's permission"; use "for a non-commercial project if it falls under 'Fair Use'"; users hold UC harmless. The FAQ says bulk downloads via the Solr API and the OCR "data set" are offered, which is exactly what `fetch.py` uses.

**Assessment**

- These are produced discovery documents from *In re National Prescription Opiate Litigation* (MDL 2804) and state cases, made public through settlement/court order. Republishing ~3,400 of them (≈ 17 MB of text) in a GitHub repo is "substantial reproduction" by volume even if each is a business e-mail; whether it is fair use for a non-commercial benchmark is a legal judgement, not something the repo settles. **Unknown:** whether the author has any additional permission from UCSF/JHU.
- **Personal data:** business e-mails of named Covidien/Mallinckrodt employees (`eileen.spaulding@covidien.com`, `Karen.Harper@Covidien.com`, …), custodian names, and whatever third parties (pharmacies, DEA staff, physicians) appear in the bodies.
- **Cheap alternative that keeps the study reproducible:** publish `data/mallinckrodt/*.ids.jsonl` = `{id, labels, gray, meta}` without `text` (meta already carries the archive `url` and Bates number), and a `bench mnk-fetch` wrapper around `fetch.email_record`/`fetch_text` that rebuilds `mnk.jsonl` from the public S3 bucket. This requires a history rewrite because the text has been tracked since 2026-09-19/20.
- The gold labels are LLM-panel outputs (`meta.panel` holds Claude Sonnet 5 / GPT-5.6 Terra / Gemini 3.8 Flash probabilities). See §4.1.

### 3.3 CUAD (`data/cuad/`)

- Source: Atticus Project, `https://github.com/TheAtticusProject/cuad/raw/main/data.zip` (`ediscovery_bench/cuad/build.py:31`). The builder's docstring states **CC BY 4.0** (correct for CUAD v1). Redistribution with attribution is permitted.
- `data/cuad/raw/CUADv1.json` (40 MB) and `raw/test.json` (7 MB) are verbatim upstream files and the builder re-downloads them when missing (`build.py:40-44`); they are redundant in the repo and are the two largest tracked blobs. `cuad.jsonl`, `ft_*.jsonl`, `ft_split.json`, `local_subset.jsonl` (≈ 14 MB) are derived paragraph corpora and fine to keep.
- Missing: an attribution line (Hendrycks et al. 2021, CC BY 4.0) in `README.md` or a `data/cuad/ATTRIBUTION.md`. No personal data concern (public EDGAR contracts).

### 3.4 Veridian (`data/veridian/`, `veridian/`, `tasks/veridian.yaml`)

- Fully synthetic. `veridian/bible.md` opens "Fictional. Any resemblance to real companies, products, or people is coincidental." The documents were written by Gemini via `ediscovery_bench/synth/write.py` (reads `GEMINI_API_KEY`) from `veridian/manifest*.jsonl`; `design/01_synthetic_matter.md` describes the design.
- Redistribution: the author owns the generated corpus. Under Google's Gemini API terms the user owns output; a provenance line ("generated with Gemini <model> on 2026-09-19 from `veridian/manifest.jsonl`; seeds 7/11 in `synth/plan.py`, `synth/write.py`") is appropriate. Publish under CC BY 4.0.
- No personal data (fictional names). Note the regeneration is **not reproducible** (LLM sampling), so the corpus itself must be published for anyone to reproduce the Veridian numbers.

### 3.5 Derived and site data

- `site/public/cutoffs.json` (1.5 MB, tracked): per-decision probabilities as quantised base64 arrays keyed by doc id; no text. Fine.
- `results/findings.json`, `determinism.json`: aggregates only; no text, no paths (checked). Fine.
- `results/examples.json`: contains full document text for two examples per corpus (`veridian`, `mnk`, `cuad`, `trec`), ≈ 5.2k chars each. See §3.1/3.2.
- `results/*/summary*.json`, `REPORT.md`: aggregates.

---

## 4. Results and third-party content

### 4.1 Model outputs in `results/`

- Row schema (all per-decision `.jsonl`): `doc_id, question, model_key, model_resolved, arm, label, p_positive, confidence, latency_ms, input_tokens, output_tokens, cached_tokens, cost_usd, list_cost_usd, pricing_mode, gold, gray, error, raw`. **`raw` is `{}` in every row sampled** (0 non-empty in 66,832 rows across `results/mnk/multi/jev__base.jsonl`, `claude-sonnet-5.jsonl`, `results/trec/multi/gpt-5.6-luna.jsonl`). No prompts, no completions, no document text. These are benchmark measurements, not provider content.
- Anthropic, OpenAI and Google terms permit publishing evaluations of their models; the restrictions in their usage policies are on using outputs to train competing models, which republishing labels/probabilities does not do. The Mallinckrodt **gold labels are themselves LLM outputs** (`meta.panel`), so the published dataset is partly derived from Claude/GPT/Gemini output; disclose it (the site's Disclaimer already says "gold labels from a three-model panel").
- `model_resolved` pins the API snapshot (e.g. `claude-haiku-4-5-20251001`), which is what makes the results citable. Keep it.
- **TypeSafe / Jev is "early access"** (`.env.example:3`). Early-access and beta programmes commonly carry confidentiality or "no public benchmarks without consent" clauses. Nothing in the repo records TypeSafe's terms, and the site is already live at decider.tarcalc.com, so this may already be settled; the author should confirm before publishing per-decision Jev outputs and the `jev@*` variant recipes (`ediscovery_bench/providers/typesafe.py`, `design/05_jev_recipe.md`, `bench jev-recipe`).
- Laya (ConvAI, HF `convaiinnovations/laya`, `laya_ft.py:192`): weights are downloaded at run time and `models/` is ignored; no checkpoints are in the repo. Fine-tuned `laya-ft-*` checkpoints are not present. Publishing them would require checking the Laya model licence.

### 4.2 Vendor marks and TypeSafe assets

- `site/src/logos.tsx:4-7`: inline SVG path data for the Anthropic, Google Gemini, Google Gemma and OpenAI marks (shape matches the simple-icons set, which is CC0, but the marks are trademarks). Used nominatively in a comparison chart, which is normal practice; add a "logos are trademarks of their owners" line to the site footer/`README`. `site/src/logos/claude.svg`, `gemini.svg`, `gemma.svg`, `laya.png` survive in history only.
- `site/src/logos/typesafe.png` (2.9 KB alpha mask of TypeSafe's mark) and `laya-mask.png` (ConvAI): same treatment; TypeSafe's consent is implied if they reviewed the site, otherwise ask.
- **The TypeSafe GIF is not a loose file.** It is `word/media/image1.gif` (1,028,829 bytes) inside each of the four `Article/*.docx` (`Article/review_v2wip.md` identifies it as the "typesafe-race" demo). Excluding the `.docx` files removes it. Fonts: the site loads Inter from `fonts.googleapis.com` (`site/index.html:8-11`), OFL, fine.

### 4.3 `Article/` (all untracked)

| File(s) | Why exclude |
|---|---|
| `Jev Article For Review.docx`, `… - edited.docx`, `… - callouts addressed.docx`, `Jev Article v2.docx` (2.0–2.1 MB each) | Unpublished drafts; embed TypeSafe GIF + 6 PNGs; `/Users/bensexton/Library/…` field codes; author metadata |
| `review.md` (49 KB), `review_v2wip.md`, `changes.md`, `changes_v2.md`, `callouts_addressed*.md`, `original_callouts_extracted.md`, `draft_extracted.md`, `draft_v2.md`, `answers.txt` | Reviewer/editor working notes and the author's answers; reference reviewer callouts by name |
| `pickens_alignment.md` | Names Jeremy Pickens throughout; quotes Gmail threads and a podcast transcript; links private chat transcripts by UUID |
| `background_notes.md` | Notes on TypeSafe's public docs; harmless but internal |
| `precision_projection.md` | Contains `/Users/bensexton/…` (line 174); otherwise a useful methods note. Could be cleaned and moved to `design/` |
| `charts/*.png`, `charts/stability/*.png` + `README.md` (3.9 MB) | Figures rendered from results; publishable **if** the final article is published; the nine `01a…01i` variants are design iterations |
| `.docx-venv/` (1,307 files) | A Python venv; must be ignored explicitly |
| `github_publication_audit.md` (this file) | Internal |

Recommendation: keep `Article/` out of the public repo entirely (`.gitignore: Article/`), and when the article is out, add a `paper/` or `docs/` folder with the final text, the final figures and the citation.

### 4.4 Other loose files

- `Screenshot 2026-09-19 at 2.40.58 PM.png` (1.2 MB, root): ignored by `Screenshot*.png`; the non-breaking space in the name is a portability nuisance anyway.
- `design/04_run_plan.pdf` (220 KB, untracked): a rendered copy of `04_run_plan.md`; optional.
- `.DS_Store` in root, `TREC/`, `TREC/Responsive Docs/`, `Article/`, `Article/charts/`, `design/`, `ediscovery_bench/`, `site/`: all ignored.

---

## 5. Reproducibility (gaps only; nothing fixed)

What `README.md` does cover: `python3 -m venv .venv && pip install -e .`, `cp .env.example .env`, `bench models`, `bench doctor`, the `tasks/`–`data/`–`providers/` layout, `bench run`/`bench report`, and that runs are resumable into `results/<task>/<model>.jsonl`. `site/README.md` covers `bench export-findings` → `npm install` → `npm run dev/build`, the determinism flow, and the deploy script.

Missing or wrong:

1. **License and citation.** No `LICENSE`, `CITATION.cff`, or attribution for CUAD/TREC/UCSF.
2. **Python version and lockfile.** `pyproject.toml` says `>=3.11`; the local `.venv` is Python 3.14.5; `scripts/gpu_box.sh:14-22` builds with 3.11/3.12 (or `uv`-fetched 3.12). No `requirements.txt`, `requirements.lock`, `uv.lock` or `pip freeze`. Installed versions that produced the results: `typesafe-sdk 0.7.0`, `anthropic 1.7.0`, `openai 3.16.2`, `google-genai 2.24.0`, `laya 0.3.4`, `torch 2.14.0`, `scikit-learn 1.9.1`, `numpy 2.5.3`, `pydantic 2.13.5`, `typer 0.27.2`. Node `v26.0.0` / npm `11.12.1` (site has `package-lock.json`, good).
3. **Environment variables are not listed in the README.** They are: `TYPESAFE_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`, `providers/gemini.py:18`), plus `LAYA_MAX_BATCH` (`providers/laya_.py:96`), `OLLAMA_HOST` (`providers/ollama_.py:23`), `USE_TF`, `TOKENIZERS_PARALLELISM`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OUT`, `POOL`, `SKIP_OLLAMA` (`scripts/gpu_box.sh`). `scripts/det_run.sh:6` sources `.env` directly.
4. **`README.md` layout section is stale.** It says `data/**/*.jsonl` documents and `tasks/*.yaml`, but omits `design/`, `veridian/`, `scripts/`, `site/`, and the corpus builders; the `Run` examples reference `data/<corpus>.jsonl` while actual files live in `data/<corpus>/<file>.jsonl`.
5. **Data acquisition is undocumented.**
   - TREC: needs the NIST agreement, the collection placed at `TREC/Jeb Bush TXT/<docno>.txt`, the qrels in `data/trec/raw/`, then `bench trec-build` (which also needs `data/trec/seen_ids.txt`). `build.py`'s docstring is the only documentation.
   - Mallinckrodt: `ediscovery_bench/mnk/sample.py` (`python -m …`, not a `bench` command) → `mnk_unlabeled.jsonl`, then `bench goldify` with the 3-model panel (costs money, non-deterministic) → `mnk.jsonl`, then `bench sample`/`laya-ft` splits and `bench det-sample` → `det300.jsonl`. None of this is in the README.
   - CUAD: `bench cuad-build` (documented in the module only).
   - Veridian: `synth/plan.py` → `synth/write.py` (Gemini, non-reproducible) → `bench goldify`/`audit_merge`; must ship the corpus.
6. **The end-to-end pipeline to `results/findings.json` and the site is scattered.** Order, reconstructed from `cli.py`, `scripts/` and `site/`: `bench run` (per task × corpus × model × arm; `--tag`, `-q`, `--temperature`, `--corpus`) → `bench report` → `bench tar` (classical TAR baselines) → `scripts/det_run.sh <arm>` and `scripts/gpu_box.sh det` → `bench determinism` → `bench export-findings` → `bench export-examples` → `python site/tools/build_cutoffs.py` → `cd site && npm run build` → `scripts/deploy_site.sh`. Not written down anywhere in one place; `bench writeup`, `audit_merge`, `jev-recipe`, `det-sample` are undocumented.
7. **Site build depends on ignored files.** `site/src/data.ts:1` and `site/src/examples.ts:1` import `../../results/findings.json` / `examples.json`; a fresh clone fails `npm run build` until those exist. Either track those two files (un-ignore) or document `bench export-findings && bench export-examples` as a prerequisite and commit a snapshot.
8. **Seeds** exist but only in code: `bench sample --seed 3` (`cli.py:145`), `bench laya-ft --seed 11` (`cli.py:178`), synth `seed=7` (`plan.py:209`) and `seed=11` (`write.py:108`), `bench tar --seeds 5` (`cli.py:574`), TREC "seeded draws" (`trec/build.py`), bootstrap CIs (`export.py:248`). No README mention; no note that API-model outputs at default temperature are not reproducible (which the determinism study measures).
9. **Compute and cost expectations** (A100 hours for Laya/Gemma, API spend per corpus, the 8-GPU `octo` layout) live in `design/03_cost_and_scope.md` and `scripts/gpu_box.sh` comments, not the README.
10. **No tests, no CI, no `bench doctor -m mock` smoke test in the README beyond `-m mock -y`.** `ediscovery_bench/providers/mock.py` exists, so an offline CI job is cheap.
11. **Roster drift.** Model keys (`claude-haiku-4.5`, `gpt-5.6-luna`, `gemini-3.8-flash`, …) and prices are in `ediscovery_bench/config.py`; `model_resolved` in results records the snapshot. README should state the run dates (2026-09-19 → 09-25) and that re-running against current endpoints will not reproduce the numbers exactly.
12. **`results/.gitkeep` + `results/` ignored** means the published repo has no results unless the JSON summaries are explicitly un-ignored (`!results/*.json`, `!results/*/summary*.json`, `!results/*/REPORT.md`).

---

## 6. Recommendation

### 6.1 Proposed layout

**Include as-is (tracked today, no issue):**
`README.md` (rewritten), `pyproject.toml`, `.env.example`, `.gitignore` (extended), `ediscovery_bench/**`, `tasks/*.yaml`, `scripts/*.sh`, `design/*.md`, `design/trec/*`, `veridian/bible.md`, `veridian/manifest*.jsonl`, `data/veridian/*`, `data/cuad/{cuad.jsonl,ft_train.jsonl,ft_test.jsonl,ft_split.json,local_subset.jsonl}`, `data/trec/{dev_ids.txt,seen_ids.txt}`, `site/**` except `node_modules/`, `dist/`.

**Add (new, small):**
`LICENSE` (code), `data/LICENSE-DATA.md` or per-corpus `README.md` with terms/attribution, `CITATION.cff`, `requirements.lock` (or `uv.lock`), `data/trec/raw/**` (NIST qrels+topics, 2.3 MB) **or** a fetch step, `data/trec/{dev,eval,lat200}_ids.jsonl` (ids+labels+meta, no text), `data/mallinckrodt/*_ids.jsonl` (if text is withheld) + a `bench mnk-fetch` command, `results/findings.json`, `results/examples.json` (regenerated without TREC/Mallinckrodt full text), `results/determinism.json`, `results/*/summary*.json`, `results/*/REPORT.md`, `results/trec_lat/sample_ids.json`, `design/04_run_plan.md`, `design/05_jev_recipe.md`, a `.github/workflows/ci.yml` running `bench doctor -m mock` and `npm run build`.

**Exclude via `.gitignore` (additions to the current file):**
```
TREC/
data/trec/*.jsonl
data/trec/full_*.jsonl
data/mallinckrodt/det300.jsonl        # and *.jsonl if ids-only is chosen
data/cuad/raw/
Article/
*.docx
*-venv/                               # catches Article/.docx-venv
results/**/*.jsonl
!results/*.json
!results/*/summary*.json
!results/*/REPORT.md
results_gpu*/
*.log
Screenshot*.png                       # already present
```
(`.venv/`, `.env`, `site/node_modules/`, `site/dist/`, `models/`, `__pycache__/`, `*.egg-info/`, `.DS_Store` are already there.)

**Move out of git:**
- `results/**/*.jsonl` (11 GB → ≈ 200–300 MB compressed) → GitHub Release `v1.0-results` with one archive per corpus (`results-trec.tar.zst`, `results-trec_full.tar.zst`, `results-cuad.tar.zst`, `results-mnk.tar.zst`, `results-veridian.tar.zst`, `results-mnk_det.tar.zst`) **and/or** a Zenodo deposit for a DOI. Document `bench report`/`export-findings` re-derivation from the extracted archives.
- `data/cuad/raw/*` → dropped; `bench cuad-build` downloads it.
- `TREC/Jeb Bush TXT/`, `data/trec/*.jsonl` → never published; README points to the NIST agreement and `bench trec-build`.
- `data/mallinckrodt/*.jsonl` → author's call (§6.3); if withheld, ids + `bench mnk-fetch`.

### 6.2 This repo with history, or a fresh repo?

**Publishing `master` as-is is not advisable**: `data/trec/local_subset.jsonl` (TREC text) and the Mallinckrodt full text are in every commit since 2026-09-20, `data/cuad/raw/` adds 45 MB of dead weight, and three commits carry the `ben@local` identity.

Two workable options:

- **A. Rewrite with `git filter-repo`** (keeps the 244-commit narrative, which is genuinely useful for readers who want to see how criteria and rosters evolved):
  `git filter-repo --invert-paths --path data/trec/local_subset.jsonl --path data/cuad/raw --path-glob 'data/mallinckrodt/*.jsonl' --path site/src/logos/claude.svg --path site/src/logos/gemini.svg --path site/src/logos/gemma.svg --path site/src/logos/laya.png` plus `--mailmap` to fold `ben@local` into `abcdben@gmail.com`. Then add the id manifests in a new commit. Verify with `git rev-list --objects --all | git cat-file --batch-check` and a second gitleaks run. Do this on a **clone**, not the working repo.
- **B. Fresh repo, single "initial public release" commit** from a curated export of the working tree. Simplest and safest; loses the history (the commit messages could be pasted into `CHANGELOG.md`).

If the Mallinckrodt text is kept (author decides it is fair use), option A only needs to drop `data/trec/local_subset.jsonl` and `data/cuad/raw/`, which is a five-minute rewrite; A is then the better choice.

### 6.3 License split (suggestion)

- **Code** (`ediscovery_bench/`, `site/`, `scripts/`, `tasks/*.yaml`, `design/`): **Apache-2.0** (patent grant, explicit trademark clause, which matters given the vendor marks) or MIT if brevity is preferred.
- **Author-created data and results** (`data/veridian/*`, `veridian/*`, `tasks/*.yaml` criteria text, `results/*`, id/label manifests, `site/public/cutoffs.json`): **CC BY 4.0**.
- **CUAD-derived files** (`data/cuad/*.jsonl`): CC BY 4.0 with attribution to Hendrycks et al. / The Atticus Project (same licence as upstream).
- **TREC**: not redistributed; `data/trec/raw/` (if included) marked "NIST TREC data, redistributed as-is from trec.nist.gov; the document collection is available from NIST under the Total Recall usage agreement".
- **Mallinckrodt**: if text is included, mark "source: UCSF/JHU Opioid Industry Documents Archive, reproduced for non-commercial research under fair use; rights remain with the original creators; see IDL take-down policy" — a licence cannot be granted by the author. If ids only: CC BY 4.0 on the manifests.
- Add a `NOTICE`/README line that Anthropic, OpenAI, Google, TypeSafe and ConvAI names and marks are trademarks of their owners and are used for identification only.

### 6.4 Publication checklist

1. Author decisions in §6.5 taken.
2. Extend `.gitignore` as in §6.1 **before** any `git add`; run `git status --short | wc -l` and confirm `TREC/` and `data/trec/*.jsonl` no longer appear.
3. Generate id-only manifests: `data/trec/{dev,eval,lat200}_ids.jsonl`, and (if chosen) `data/mallinckrodt/*_ids.jsonl`; add `bench mnk-fetch` (thin wrapper over `mnk/fetch.py`) and a `bench trec-build --check` that validates a user-supplied collection against `seen_ids`/`dev_ids`.
4. Regenerate `results/examples.json` with TREC (and, if withheld, Mallinckrodt) texts replaced by ids/short excerpts; rebuild `site/public/cutoffs.json`; un-ignore `results/findings.json`, `examples.json`, `determinism.json`, `*/summary*.json`, `*/REPORT.md`.
5. Remove `/Users/bensexton` from anything that will ship (currently only `Article/precision_projection.md:174`, which is excluded anyway; re-grep after step 3).
6. Write `LICENSE`, `data/README.md` (per-corpus source, terms, how to rebuild), `CITATION.cff`, and rewrite `README.md` with: Python/Node versions, lockfile, all env vars, data acquisition per corpus, the full pipeline in order (§5 item 6), run dates and model snapshots, cost/GPU expectations, seeds.
7. `pip freeze > requirements.lock` from the `.venv` that produced the results (or adopt `uv` and commit `uv.lock`); confirm `pip install -e .` on Python 3.11 still resolves.
8. Add a mock-provider smoke test and a GitHub Actions workflow (`bench doctor -m mock`, `bench run -m mock -y` on `data/veridian/local_subset.jsonl`, `npm ci && npm run build`).
9. Choose option A or B (§6.2); on a **clone**, run `git filter-repo` (A) or export the tree (B). Fold `ben@local` into the main identity.
10. Re-run `gitleaks git .` and `git rev-list --objects --all | git cat-file --batch-check | sort -k3 -n | tail` on the result; confirm no blob > 50 MB and no `data/trec/local_subset.jsonl` / `mnk.jsonl` objects remain.
11. Pack results: `tar --zstd -cf results-<corpus>.tar.zst results/<corpus>/` per corpus; record sha256s in `results/README.md`.
12. Create the GitHub repo (private first), push, create the release with the archives (and/or Zenodo deposit; record the DOI in `CITATION.cff` and `README.md`).
13. Update `site/src/components/Disclaimer.tsx` / footer with repo link, data-terms note and trademark line; redeploy via `scripts/deploy_site.sh`.
14. Flip to public. Enable "secret scanning" and "push protection" in repo settings.

### 6.5 Decisions only the author can make

1. **Public or private** repo (and whether to publish now or after the article).
2. **Mallinckrodt**: full text (as today, relying on fair use of a public archive) or ids + labels + fetch script. If full text: whether to ask UCSF/JHU (`industrydocuments@ucsf.edu`) first.
3. **TREC**: confirm how the `TREC/Jeb Bush TXT/` copy was obtained and therefore which terms bind it; whether to include `data/trec/raw/` (NIST qrels) directly or fetch; whether the two verbatim TREC examples in `results/examples.json`/the live site count as "small excerpts" or should be replaced.
4. **TypeSafe early-access terms**: confirm there is no confidentiality/benchmark-publication clause covering Jev outputs, the `jev@*` recipes, latency and pricing figures; confirm use of the TypeSafe mark (`site/src/logos/typesafe.png`).
5. **`Article/`**: exclude entirely (recommended), or publish only `charts/` and a final article text once released; whether Jeremy Pickens' name may appear in any published note (`pickens_alignment.md`) — he has not consented to publication of review remarks.
6. **License choice**: Apache-2.0 vs MIT for code; CC BY 4.0 (vs CC0 or CC BY-NC) for author-created data and results.
7. **History**: filter-repo (keep 244 commits) vs fresh single commit; whether the `ben@local` commits should be re-authored.
8. **Repo name and account**: under `abcdben` (already hosts `tarcalc`, the deployed site) or an organisation; suggested names: `ediscovery-bench`, `jev-vs-llms`, `decider-bench`. Whether `scripts/deploy_site.sh` should stay pointed at `abcdben/tarcalc` or the site should move to the new repo's Pages.
9. **Results distribution**: GitHub Release assets only, Zenodo DOI, or both; whether to publish `results/trec_full/` (4.9 GB raw, the full-collection Laya/Jev/lexical pass) at all.
10. **Contact address** in `Disclaimer.tsx` (`abcdben@gmail.com`) and git author e-mail: keep, or switch to a GitHub no-reply address before the history is published.
11. **Key rotation**: rotate the four keys in `.env` before publication as a precaution (not required by any finding here).
