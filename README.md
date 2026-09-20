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
