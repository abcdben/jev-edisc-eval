# OpenAI Decisions API — adding a second decision model to the bake-off

OpenAI's Decisions API (`POST /v1/decisions`, model `gpt-6-luna`) went to public beta on 2026-10-06. It is the first commercial
analogue of the Jev / Laya "decision model" shape: no generated text, a per-question probability, priced on input tokens only
($0.10 / M, no output tokens). This note records how it was run so its rows on the site are comparable to Jev's, and what the
run itself revealed about the API.

Code: `ediscovery_bench/providers/openai_decisions.py`; model key `openai-decisions` (config.py), which the CLI expands to the two
variants `openai-decisions@predicate` and `openai-decisions@choice`. Results: `results/<corpus>/<arm>/openai-decisions__{predicate,choice}*.jsonl`.

---

## 1. Two question forms, mirroring Jev's two configurations

The API has three question types: `predicate` (yes/no → `probability`), `choice` (options → a probability per option plus a
separate `confidence`) and `score`. Two map onto configurations Jev already has on the site:

| variant | question | Jev analogue | what becomes p(responsive) |
|---|---|---|---|
| `@predicate` | one predicate per issue; `instructions` = the RFP text with `True (responsive): …` / `False (not_responsive): …` appended | Jev · Noul | `answers[i].probability` |
| `@choice` | one choice per issue; `choices` = the two labels, each with the task's positive / negative description | Jev · Choice | the responsive option's entry in `probabilities` |

Input is the same text every other model sees: `MATTER BACKGROUND:\n<context>\n\nDOCUMENT:\n<text>` as a single flat string
(the API accepts `input` as a string or user messages; the string form was used). A refusal or missing answer is recorded as
p = 0.5 with no label (`raw.refused`); none occurred in the main runs.

The multi arm sends all of a corpus's questions in one request; the single arm sends one question per request, exactly as for Jev.

## 2. Protocol — matched to Jev

| | Jev | OpenAI Decisions |
|---|---|---|
| main runs (all four corpora, both arms) | 12 requests in flight | 12 in flight (`-c 12`) |
| TREC all-issues speed | dedicated concurrency-1 sample, 200 e-mails (`--tag latency`) | same 200 e-mails, concurrency 1 |
| stability | det300 (Mallinckrodt, 300 stratified e-mails), 5 repeats, multi + single on the two narrow issues | same |
| retries / timeout | provider default | SDK `max_retries=6`, `timeout=120 s` |

The first TREC multi pass had briefly been started at 32 in flight; it was resumed at 12. Its main-run latencies are therefore mixed,
but TREC multi speed on the site comes from the concurrency-1 sample, so no displayed figure is affected. Every other main run
was at 12 throughout.

Observed limits on the account during the run: 30,000 RPM / 180 M TPM. Nothing throttled.

## 3. Costs

Per-document cost, multi arm (list price): Jev ≈ $0.00011–0.00016; Decisions ≈ $0.00032–0.00045, i.e. 2.5–3× Jev and roughly a third
of GPT-5.6 Luna ($0.0010–0.0012), ~40× under Sonnet 5. The single arm multiplies each by the number of issues (no caching is credited
in the bench's cost model, although `usage.input_tokens_details.cached_tokens` is recorded).

Whole study (four corpora × two arms × two variants, plus Endo, the latency sample and the determinism repeats): 646 k decisions,
381 M input tokens, ≈ $38 at list price.

## 4. What the run showed about the API

Three properties, all visible in the raw result files and none of them true of Jev or the LLMs:

1. **Deterministic.** Five repeats on det300 gave identical probabilities on every decision, both variants, both arms
   (`identical_prob` = 1.00, decision flip 0 %). Jev · Noul: 0.5 % flip, 49 % identical p; GPT-5.6 Luna: 4.3 % flip.
2. **Question-independent.** Multi-arm answers equal single-arm answers exactly — the Mallinckrodt single-arm table reproduces the
   multi-arm table to the decimal. Each question appears to be scored on its own; bundling questions saves money but changes nothing
   else. (Jev's two arms differ slightly.)
3. **Two-decimal probabilities.** Every `probability` is on a 0.01 grid, so threshold sweeps step in 0.01 and ties are common at the
   default 0.5 cut.

## 5. Results at a glance (multi arm, all gold, p ≥ 0.5)

Decision-level precision / recall / F1:

| corpus | Jev · Noul | Decisions · Predicate | Decisions · Choice | GPT-5.6 Luna | Sonnet 5 |
|---|---|---|---|---|---|
| TREC 2016 | 75.2 / 75.9 / **75.6** | 69.1 / 89.2 / **77.8** | 65.3 / 89.1 / 75.4 | 60.6 / 92.8 / 73.3 | 74.3 / 88.1 / 80.7 |
| Mallinckrodt | 85.7 / 82.0 / **83.8** | 75.2 / 86.0 / 80.2 | 70.2 / 87.6 / 77.9 | 63.6 / 96.9 / 76.8 | 73.7 / 90.8 / 81.3 |
| Veridian | 83.8 / 89.6 / **86.6** | 70.0 / 94.7 / 80.5 | 70.3 / 93.5 / 80.3 | 69.9 / 98.6 / 81.8 | 77.3 / 97.0 / 86.0 |
| CUAD | 51.7 / 82.6 / 63.6 | 56.5 / 77.0 / 65.2 | 58.9 / 77.6 / **67.0** | 52.1 / 79.3 / 62.9 | 47.1 / 84.8 / 60.6 |

Pattern: Decisions sits between Jev and the LLMs — much higher recall than Jev, lower precision; it beats Jev on F1 on TREC and CUAD,
loses on Mallinckrodt and Veridian. Speed (TREC, concurrency 1, p50): Jev 157 ms, Decisions 208–230 ms, GPT-5.6 Luna 2.5 s (standard tier),
Sonnet 5 3.7 s.

## 6. Wiring

* `export.py` MODELS (primary roster) + `OPENAI_DECISIONS_LEVERS` in `_variant_models()` (configurations page, group `openai-decisions`);
  `determinism.py` MODELS; `study.py` two measured arms; `explore.py` MEASURED_ARMS; `examples.py` request / response worked examples
  (`openai-decisions` notes key); `writeup.py` via the shared report.
* Site: `data.ts` roster (`--c-oad`, `--c-oad-2` in every theme and Studio preset), `makers.ts` / `logos.tsx` (OpenAI mark), `palettes.ts`,
  `examples.ts` + `Explain.tsx`, `studyData.ts`, copy in `Disclaimer.tsx`, `Method.tsx`, `App.tsx`, `opsRows.ts`.
* Not run: `trec_full` (the 286 k-message Jeb Bush collection; ≈ $130 and several hours at 12 in flight) — the TREC rows use the
  3,116-e-mail evaluation sample like every other model. `endo` multi was run for completeness (no gold).
