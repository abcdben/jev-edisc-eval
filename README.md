# eDiscovery classification bench: Jev vs frontier LLMs

Harness for comparing TypeSafe AI's Jev (System One model) against generative
LLMs on eDiscovery classification tasks, on quality (precision / recall / F1 /
elusion / calibration), speed, and cost.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env   # fill in keys
.venv/bin/bench models  # roster, pricing, which keys are set
.venv/bin/bench doctor  # one tiny call per provider to prove auth works
```

## Layout

- `tasks/*.yaml` — a task: label set, criteria, matter context, the question.
  The identical text is sent to every model.
- `data/**/*.jsonl` — documents: `{"id", "text", "labels": {"<task>": "<gold>"}}`.
- `ediscovery_bench/providers/` — one adapter per vendor. Every adapter returns
  a label, a probability per label, latency, tokens, and cost.
  - Jev: `Noul` (yes/no probability) or `Choice` per task setting.
  - LLMs: structured output constrained to `{label, probabilities}`, the same
    shape TypeSafe's own "System One LLM wrapper" uses in their benchmarks.
- `ediscovery_bench/metrics.py` — P/R/F1, elusion, κ, ROC/PR AUC, Brier, ECE,
  log loss, recall-target thresholds (review fraction), latency p50/p95, cost.

## Run

```bash
bench run -t tasks/<task>.yaml -d data/<corpus>.jsonl              # full roster
bench run -t tasks/<task>.yaml -d data/<corpus>.jsonl -m jev -m gpt-5.6-luna
bench run ... -m mock -y                                             # offline test
bench report -t tasks/<task>.yaml                                    # from saved predictions
```

Runs are resumable: predictions land in `results/<task>/<model>.jsonl` and
re-running skips completed documents.

## Reproducing the study

Everything below was run between **2026-09-19 and 2026-09-25**. Each row of the per-decision
results carries `model_resolved`, the exact API snapshot or checkpoint that answered (for
example `claude-haiku-4-5-20251001`); re-running against current endpoints will not reproduce
the numbers exactly, and API models at default temperature are not deterministic even against
the same snapshot (that is what the determinism study measures).

### Environment

- Python **>= 3.11** (`pyproject.toml`); the results were produced on **3.14.5**. Exact package
  versions are pinned in `requirements.lock` (`pip freeze` of that environment):

  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.lock && .venv/bin/pip install -e .
  ```

- Node **26** (npm 11) for the site; `site/package-lock.json` pins the JS dependencies.
- Environment variables (`.env`, loaded by `bench`; `scripts/det_run.sh` sources it directly):

  | Variable | Used by |
  |---|---|
  | `TYPESAFE_API_KEY` | Jev (`ediscovery_bench/providers/typesafe.py`) |
  | `ANTHROPIC_API_KEY` | Claude models |
  | `OPENAI_API_KEY` | GPT models |
  | `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | Gemini models; also the Veridian generator |
  | `LAYA_MAX_BATCH` | Laya batch size (default 64 on CUDA, 16 otherwise) |
  | `OLLAMA_HOST` | Ollama endpoint for Gemma (default `http://127.0.0.1:11434`) |

  `scripts/gpu_box.sh` additionally reads `OUT`, `POOL`, `SKIP_OLLAMA` and the usual
  `TOKENIZERS_PARALLELISM` / `OMP_NUM_THREADS` knobs; see its header.

### Data

Licensing and attribution per corpus are in `data/LICENSE-DATA.md`.

- **TREC 2016 Total Recall (Jeb Bush e-mails)**: the document collection is *not* in the repo.
  Obtain it from NIST under the Total Recall usage agreement, place it at
  `TREC/Jeb Bush TXT/<docno>.txt`, and run `bench trec-build` (`--full` for the full-collection
  tier). The draws are seeded, so the regenerated `data/trec/{dev,eval}.jsonl` contain exactly
  the ids in the tracked manifests `data/trec/{dev,eval,lat200}_ids.jsonl`. Details:
  `data/trec/README.md`.
- **Mallinckrodt** (`data/mallinckrodt/`): included, with text, as sampled from the public
  Opioid Industry Documents Archive. To rebuild from scratch:
  `python -m ediscovery_bench.mnk.sample` (Solr + S3 fetch → `mnk_unlabeled.jsonl`), then
  `bench goldify` with the three-model panel (→ `mnk.jsonl`; costs money and is not
  deterministic), then `bench sample` / `bench laya-ft` for the splits and `bench det-sample`
  for `det300.jsonl`.
- **CUAD** (`data/cuad/`): derived paragraph corpora are included; the upstream files are not
  tracked. `bench cuad-build` downloads CUAD v1 from the Atticus Project and rebuilds them.
- **Veridian** (`data/veridian/`, `veridian/`): included. The corpus was written by Gemini from
  `veridian/manifest*.jsonl` (`ediscovery_bench/synth/plan.py` seed 7, `synth/write.py` seed 11);
  generation is **not reproducible**, so the shipped files are the corpus of record.

### Pipeline

In order, from the repo root with `.venv/bin` on `PATH`:

```bash
bench run -t tasks/<task>.yaml -d data/<corpus>/<file>.jsonl --corpus <corpus> [-m <model> ...] [-a multi|single] [-q <questions>] [--tag <tag>] [--temperature 0] -y
bench report -t tasks/<task>.yaml --corpus <corpus>        # results/<corpus>/summary*.json, REPORT.md
bench tar ...                                              # classical TAR baselines → results/<corpus>/multi/tar__*.tar.json
scripts/det_run.sh <api_multi|api_single|t0_multi|t0_single|laya|gemma>   # repeat runs on det300 → results/mnk_det/
bench determinism                                          # results/determinism.json
bench export-findings                                      # results/findings.json (aggregates + bootstrap CIs)
bench export-examples                                      # results/examples.json
python site/tools/build_cutoffs.py                         # site/public/cutoffs.json
cd site && npm ci && npm run build                         # static bundle in site/dist
```

Runs are resumable and land in `results/<corpus>/<arm>/<model>[__<tag>].jsonl`. Laya and
Gemma runs were executed on a GPU box via `scripts/gpu_box.sh`. Other useful commands:
`bench models`, `bench doctor`, `bench writeup`, `bench jev-recipe`, `bench audit_merge`;
`bench --help` lists them all.

### Results in the repo vs. the Release

`site/src/data.ts` and `site/src/examples.ts` import `results/findings.json` and
`results/examples.json`, so both are **tracked** (together with `results/determinism.json`,
every `results/*/summary*.json` and `REPORT.md`, and `results/trec_lat/sample_ids.json`) and a
fresh clone builds the site without re-running anything.

The per-decision records (`results/**/*.jsonl`, about 11 GB uncompressed) are **not** in git.
They are attached, one `.tar.zst` per corpus, to the GitHub Release
[`v1.0-results`](https://github.com/abcdben/jev-edisc-eval/releases/tag/v1.0-results);
`results/README.md` lists the archives with SHA-256 sums and how to extract them back into
`results/`, after which `bench report`, `bench determinism` and `bench export-findings` can be
re-derived from them.

### Licence and citation

Code: MIT (`LICENSE`). Author-created data and results: CC BY 4.0; third-party corpora per
`data/LICENSE-DATA.md`. Cite via `CITATION.cff`. Live results site: <https://decider.tarcalc.com>.
