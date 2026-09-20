# Cost and scope model

Status: DRAFT for discussion (2026-09-19). Prices are standard-tier list
prices from `ediscovery_bench/config.py`. All numbers are estimates.

## Decisions so far

- Synthetic matter: Veridian ApexHip MDL. 10 RFPs, ~100 true positives each.
- Gray docs: gold label + `gray` flag; report with and without.
- Privilege: not a task; only a distractor.
- Jev: run Noul and Choice both.
- LLM protocol: both a single-question arm (one call per doc × RFP) and an
  all-questions arm (all 10 RFPs in one prompt per doc), compared.
- LLM effort: start at each vendor's floor; pilot vs. default and adopt default
  only if significantly better.
- Mallinckrodt: ~2,000 emails, 12 custodians, 2008–2016, ≤3k tokens, headers
  shown; 6 issues × (broad, narrow); gold = LLM panel (Jev excluded).

## The 10 RFPs (from design/01)

| # | Title | Breadth | Richness |
| --- | --- | --- | --- |
| 1 | Recall of cup lots V-2200..V-2299 | narrow | thin |
| 2 | ApexHip design history (inputs, FMEA, reviews, V&V, changes) | broad | rich |
| 3 | Complaints, adverse events, MDRs, trending | medium | medium |
| 4 | Communications with FDA about ApexHip | medium | medium |
| 6 | Marketing / promotional claims and claim review | broad | rich |
| 7 | Payments and things of value to surgeons (Feld, Rao) | medium | medium |
| 8 | Sales training/scripts on revision-rate & metal-ion questions | narrow | thin |
| 9 | Decision to continue selling after 2021 registry signal | medium | medium |
| 13 | Financials: forecasts, reserves, insurance, revenue impact | medium | rich |
| 17 | Personnel files, reviews, comp for ApexHip / QA / RA leadership | broad | rich |

Dropped: 5, 10, 11, 12, 14, 15, 16, 18, 19, 20 (mostly duplicative coverage
or peripheral). Their themes can still appear as distractors.

## Corpus size

100 positives × 10 RFPs, ~30% of positives responsive to 2+ RFPs
→ ~770 positive docs + ~300 hard-negative/gray + ~600 pure noise ≈ **1,700 docs**.

## Token assumptions

| | Synthetic | Mallinckrodt |
| --- | --- | --- |
| Avg document | 500 tok | 800 tok |
| System + matter context + one RFP | 450 tok | 450 tok |
| All-questions prompt (10 or 12 RFPs) | ~4,200 tok incl. doc | ~4,600 tok incl. doc |
| Output, single | 60 tok (+150 thinking on Gemini floor) | same |
| Output, all-questions | 450 tok (+300 Gemini) | 540 tok (+300) |

## Estimates, standard pricing, floor effort

Synthetic, 1,700 docs × 10 RFPs (17,000 single calls or 1,700 batched calls per model):

| Model | Single arm | All-questions arm |
| --- | --- | --- |
| claude-haiku-4.5 | $21 | $11 |
| claude-opus-5 | $106 | $55 |
| gpt-5.6-luna | $5 | $2 |
| gpt-5.6-sol | $85 | $44 |
| gemini-3.8-flash | $26 | $10 |
| gemini-3.1-pro | $75 | $30 |
| **6 LLMs** | **$318** | **$152** |
| jev (Noul + Choice) | $1.40 | $0.60 |

Mallinckrodt, 2,000 emails × 12 questions (24,000 single / 2,000 batched):

| Model | Single arm | All-questions arm |
| --- | --- | --- |
| claude-haiku-4.5 | $37 | $15 |
| claude-opus-5 | $186 | $73 |
| gpt-5.6-luna | $8 | $3 |
| gpt-5.6-sol | $149 | $58 |
| gemini-3.8-flash | $41 | $13 |
| gemini-3.1-pro | $120 | $39 |
| **6 LLMs** | **$541** | **$201** |
| jev | $2.00 | $0.80 |

Other:
- Effort pilot (300 docs × 4 RFPs, 6 models at vendor default): ~$60.
- Synthetic authoring (1,700 docs, ~1,500 in / ~800 out each, split across
  Claude / GPT-5.6 / Gemini large models): ~$35.

**Total, everything, no discounts: ≈ $1,300.** Opus 5 + Sol ≈ 55% of it.

## Levers

| # | Lever | Effect | Cost |
| --- | --- | --- | --- |
| 1 | Vendor batch APIs (Anthropic Message Batches, OpenAI Batch, Gemini Batch) | −50% on all LLM spend | No live latency on batched runs; measure latency on a ~200-doc live subset |
| 2 | Prompt caching of the shared RFP block on the all-questions arm | −60–70% on that arm | None; need to confirm stacking with batch on OpenAI/Gemini |
| 3a | Drop Opus 5 and Sol; Gemini 3.1 Pro is the only large | −45% | Lose two large reference points |
| 3b | One small per vendor + one large | −50% | Same |
| 3c | Large models on all-questions arm only | −30% | Large models not in the single-arm comparison |
| 4 | Single-question arm on a 500-doc subset only | −35% synthetic leg | Batching penalty measured on subset; headline from batched arm |
| 5 | Floor effort only (skip pilot) or pilot on large models × 200 docs × 2 RFPs | −$35 to −$60 | Less certainty that floor effort is "fair" to LLMs |
| 6 | Mallinckrodt: 1,000 emails; single arm only | −$400+ | Smaller panel-gold set |

Levers 1+2 → ≈ $450–550 at full scope. Add 4 → ≈ $350. Add 3a → ≈ $200.

## Not costed here

Human time (none planned), Cursor usage for bible/manifest authoring, storage.
