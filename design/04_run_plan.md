# Run plan (the grid)

Updated 2026-09-20 09:30 from the repo state (`results/`, `config.py`, `scripts/gpu_box.sh`).
Supersedes the earlier draft. Status: ✅ complete · ◐ partial · ⏳ queued.

One raw prediction per cell (label, probability per label, latency, tokens, paid and
list cost) saved to `results/<corpus>/<arm>/<model>[__tag].jsonl`. All metrics are
computed afterward from those files.

## Datasets

| Code | Set | Docs | Questions | Gold |
| --- | --- | --- | --- | --- |
| V | Synthetic: Veridian ApexHip MDL | 1,954 | 10 RFPs (binary; gray flag) | Spec labels from the manifest, relabeled at spec level and text-audited by the mid-tier LLMs |
| M | Real: Mallinckrodt opioid emails (OIDA) | 1,840 | 4 issues × (broad, narrow) = 8 | 3-model LLM panel (Sonnet 5, Terra, Gemini 3.8 Flash); Jev and Laya never feed gold |

Subsets: V pilot 120 docs; V literal 600; V/M local 400 each (for slow local models);
V/M fine-tune splits 30% train / 70% test (586/1,368 and 552/1,288).

Arms: **single** = one question per call; **multi** = all questions for a document in one call.

## Models

| Group | Models | Where it runs | Setting |
| --- | --- | --- | --- |
| Jev | jev-1.13.0 (+ jev-preview) | TypeSafe API | 12 ablation variants, see below |
| Cloud small | Claude Haiku 4.5, GPT-5.6 Luna, Gemini 3.5 Flash-Lite | vendor APIs (batch + cache) | floor effort |
| Cloud mid | Claude Sonnet 5, GPT-5.6 Terra, Gemini 3.8 Flash | vendor APIs (batch + cache) | floor effort |
| Laya (System-One competitor) | laya, laya-typed, laya-multilingual | local Mac / rented A100 | 11 zero-shot variants |
| Laya fine-tuned (supervised) | laya-ft-veridian, laya-ft-mnk | A100 | trained on 30% split, scored on 70% |
| Local open LLM | Gemma 3 12B (Ollama) | Mac / A100 | temp 0, no thinking |
| Baseline | lexical (keyword overlap, no model) | local | — |

## Cloud LLM runs

| Run | Set | Models | Arm | Effort | Cells / model | Purpose | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | V | 6 cloud | single | floor | 19,540 | Headline LLM quality | ✅ |
| L2 | V | 6 cloud | multi | floor | 1,954 | Batching effect | ✅ |
| L3 | M | 6 cloud | single | floor | 14,720 | Headline on real data | ✅ |
| L4 | M | 6 cloud | multi | floor | 1,840 | Batching effect, real data | ✅ |
| L5 | V pilot (120) | 6 cloud | single | floor vs vendor default | 1,200 each | Does default effort beat floor? | ✅ |
| L6 | V literal (600) | 3 small | single | floor | 6,000 | Jev's "literal" phrasing applied to LLMs (fairness) | ✅ |
| G1 | V (all) | 3 mid | multi | floor | 1,954 | Gold: spec-level relabel + text audit | ✅ |
| G2 | M (all) | 3 mid | multi | floor | 1,840 | Gold: Mallinckrodt panel | ✅ |

## Jev runs (every variant, both sets, both arms)

Baseline then one lever changed at a time. base / choice / score are on every document;
the other levers ran on subsets first and are being filled in to full coverage.

| Variant | Lever | Setting | V single | V multi | M single | M multi |
| --- | --- | --- | --- | --- | --- | --- |
| jev@base | — | Noul; verbatim RFP; label descriptions as criteria; structured state w/ context; jev-1.13.0 | ✅ | ✅ | ✅ | ✅ |
| jev@choice | form | Choice | ✅ | ✅ | ✅ | ✅ |
| jev@score | form | Score, 5-level rubric | ✅ | ✅ | ✅ | ✅ |
| jev@crit_none | criteria | none | ◐ | ◐ | ◐ | ◐ |
| jev@crit_struct | criteria | structured JSON | ◐ | ◐ | ◐ | ◐ |
| jev@literal | phrasing | literal condition w/ boundary cases | ◐ | ◐ | ◐ | ◐ |
| jev@no_context | state | matter context off | ◐ | ◐ | ◐ | ◐ |
| jev@state_string | state | plain string | ◐ | ◐ | ◐ | ◐ |
| jev@gate | composition | relevance-gate Noul | ◐ | ◐ | ◐ | ◐ |
| jev@ensemble | composition | 3 phrasings averaged | ◐ | ◐ | ◐ | ◐ |
| jev@decompose | composition | subpart Nouls OR'd in code | ◐ | ◐ | ◐ | ◐ |
| jev@preview | version | jev-preview alias | ◐ | ◐ | ◐ | ◐ |
| jev@recipe | combined | best of the above, fixed after reading the V table | ⏳ | ⏳ | ⏳ | ⏳ |

(Headers on/off is not a Jev lever: M email headers are part of the document text for every model.)

## Laya runs (local; $0 API)

15 variants × 2 arms × 2 corpora, all documents. Laya's 512-token window truncates most
instructions and ~half the documents, so two Laya-only levers exist: `compact` (short
instructions/criteria) and `chunk` (sliding window, max-pool).

| Variant | Lever | Status |
| --- | --- | --- |
| laya@base, @choice, @score, @literal, @gate, @ensemble, @decompose | same levers as Jev | ◐ (V single base/compact and V multi base done locally; rest queued on A100) |
| laya@compact, @chunk, @recipe (compact+chunk), @recipe_choice | Laya-only window levers | ◐ |
| laya-typed@base, @recipe | typed-decisions checkpoint | ⏳ |
| laya-multilingual@base, @recipe | multilingual checkpoint (1024 ctx) | ⏳ |
| laya-ft-veridian@compact, @recipe | SUPERVISED fine-tune on V train split, scored on V test split | ⏳ |
| laya-ft-mnk@compact, @recipe | SUPERVISED fine-tune on M train split, scored on M test split | ⏳ |
| latency sample | laya@base, @recipe, laya-typed@base at concurrency 1 on 400-doc subsets | ⏳ |

## Other local runs

| Run | Set | Model | Arm | Status |
| --- | --- | --- | --- | --- |
| O1 | V, M all docs | lexical baseline | single + multi | ✅ |
| O2 | V local (400) | Gemma 3 12B | multi | ✅ |
| O3 | V local (400) | Gemma 3 12B | single | ⏳ A100 |
| O4 | M local (400) | Gemma 3 12B | single + multi | ⏳ A100 |

## Prep jobs (not evaluation runs)

| Job | Model | Status |
| --- | --- | --- |
| Veridian manifest planner | Sonnet 5 | ✅ |
| Veridian document writer, ⅓ each | Sonnet 5 / Terra / Gemini 3.8 Flash (author recorded per doc) | ✅ |
| Mallinckrodt stratified sample via Solr keyword tiers + narrow-issue top-up | none | ✅ |

## Analyses from the saved grid (no API calls)

Per question and pooled: precision, recall, F1, macro-F1, elusion, κ, ROC/PR AUC, Brier,
ECE, best-F1 threshold, review fraction at 90%/95% recall; with vs without gray docs;
panel-unanimous vs majority gold (M); by author family (V); label/probability
inconsistency; inter-model agreement; latency p50/p95 (live samples, not batched rows);
spend ledger, paid vs list price; per-issue cutoff slider tool (later).
