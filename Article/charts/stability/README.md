# Stability chart candidates

Eight candidate visualisations of the run-to-run stability comparison, one PNG each (2400 px wide, white background). All are drawn from the raw per-decision run files, not from `results/determinism.json`.

## Data

- Corpus: Mallinckrodt opioid-litigation emails, the 300-document stratified sample in `data/mallinckrodt/det300.jsonl` (100 gray / 100 clear-positive / 100 clear-negative) × 8 issues = 2,400 decisions per run.
- Runs: rep1 is the benchmark run (`results/mnk/multi/<model>.jsonl`, restricted to the 300 sample documents); rep2–rep5 are `results/mnk_det/multi/<model>__rep{2..5}.jsonl`. Temperature-0 runs are `<model>__t0_rep{1..5}.jsonl`. This mirrors `ediscovery_bench/determinism.py`.
- Metric: pairwise disagreement = for each decision, the probability that two runs drawn without replacement give a different label; averaged over the 2,400 decisions. A "flip" is a decision where not all runs gave the same label.
- Models shown (display name → run key): Jev · Noul → `jev@base`, Jev · Choice → `jev@choice`, Jev · Score → `jev@score`, Gemma 3 12B → `gemma3-12b`, Gemini 3.8 Flash, Claude Sonnet 5, GPT-5.6 Terra, Claude Haiku 4.5, Gemini 3.5 Flash-Lite, GPT-5.6 Luna. Other Jev configurations in the run data (`jev@state_string`), Laya, and the keyword baseline are left out.
- Colours: one hue per family, two lightness levels where a family has two models. Jev blues (Noul darkest), Anthropic orange, OpenAI green, Google purple, Gemma olive.

### Reproduction check

The published pairwise rates reproduce exactly from the raw runs:

| Model | Runs | Reproduced | Published | Flipped decisions |
|---|---|---|---|---|
| Jev · Noul | 5 | 0.27% | 0.27% | 13 |
| Jev · Score | 5 | 0.32% | 0.32% | 15 |
| Jev · Choice | 5 | 0.38% | 0.38% | 18 |
| Gemma 3 12B | **4** | 0.44% | 0.44% | 21 |
| Gemini 3.8 Flash | 5 | 0.88% | 0.88% | 42 |
| Claude Sonnet 5 | 5 | 1.16% | 1.16% | 58 |
| GPT-5.6 Terra | 5 | 1.48% | 1.48% | 73 |
| Claude Haiku 4.5 | 5 | 1.82% | 1.82% | 91 |
| Gemini 3.5 Flash-Lite | 5 | 2.02% | 2.02% | 98 |
| GPT-5.6 Luna | 5 | 2.11% | 2.11% | 103 |

Temperature 0: Haiku 0.40%, Gemini 3.8 Flash 0.68%, GPT-5.6 Terra 0.92%, GPT-5.6 Luna 1.67%, Gemini 3.5 Flash-Lite 2.23% (published 2.22%; the underlying value is 0.02226, so this is rounding at the fourth decimal). Claude Sonnet 5 has no t = 0 cell (the API rejected the parameter); Jev and Gemma have none.

Two things to be aware of when the article says "5 runs":

- **Gemma 3 12B has 4 runs, not 5.** Its benchmark run covered only a 400-document local subset (80 of the 300 sample documents), so `determinism.py` does not count it as rep1, and the published 0.44% is over rep2–rep5. Every chart marks it "(4 runs)".
- Every model's p(responsive) is present for every decision (no missing probabilities).

## Charts

### 01_paired_temperature.png — default sampling vs temperature 0

Paired horizontal bars per model: solid = vendor default sampling, hatched = temperature 0. Single bar where no t = 0 run exists, with the reason printed (Jev: no sampling parameter; Sonnet 5: API rejects temperature; Gemma: no t = 0 run).

Numbers (default → t = 0): Gemini 3.8 Flash 0.88% → 0.68%; GPT-5.6 Terra 1.48% → 0.92%; Claude Haiku 4.5 1.82% → 0.40%; Gemini 3.5 Flash-Lite 2.02% → 2.23%; GPT-5.6 Luna 2.11% → 1.67%. Jev 0.27 / 0.32 / 0.38%, Gemma 0.44%, Sonnet 5 1.16% unchanged (no second bar).

What it adds over the current bar chart: it shows that turning the temperature down does not close the gap for most LLMs (Flash-Lite gets slightly worse, Luna and Terra stay well above Jev) and that Jev's figure is not the product of a sampling setting.

### 02_dotplot_intervals.png — dot plot with 95% bootstrap intervals

Point estimate per model with a 95% interval from resampling the 2,400 decisions (2,000 draws, seed 7).

| Model | Rate | 95% interval |
|---|---|---|
| Jev · Noul | 0.27% | 0.13 – 0.43 |
| Jev · Choice | 0.38% | 0.21 – 0.58 |
| Jev · Score | 0.32% | 0.16 – 0.49 |
| Gemma 3 12B (4 runs) | 0.44% | 0.27 – 0.62 |
| Gemini 3.8 Flash | 0.88% | 0.63 – 1.18 |
| Claude Sonnet 5 | 1.16% | 0.88 – 1.47 |
| GPT-5.6 Terra | 1.48% | 1.14 – 1.84 |
| Claude Haiku 4.5 | 1.82% | 1.44 – 2.22 |
| Gemini 3.5 Flash-Lite | 2.02% | 1.62 – 2.42 |
| GPT-5.6 Luna | 2.11% | 1.72 – 2.53 |

What it adds: the intervals show which differences the sample can actually support — the three Jev forms and Gemma overlap each other, Gemini 3.8 Flash sits apart from both groups, and the four least stable LLMs overlap each other but not Jev.

### 03_flip_counts.png — decisions that changed between runs

Count of decisions (of 2,400) where at least one run gave a different label, with the share and a "1 in N" reading.

Jev · Noul 13 (0.5%, 1 in 185), Jev · Score 15 (0.6%, 1 in 160), Jev · Choice 18 (0.8%, 1 in 133), Gemma 3 12B 21 (0.9%, 1 in 114, 4 runs), Gemini 3.8 Flash 42 (1.8%, 1 in 57), Claude Sonnet 5 58 (2.4%, 1 in 41), GPT-5.6 Terra 73 (3.0%, 1 in 33), Claude Haiku 4.5 91 (3.8%, 1 in 26), Gemini 3.5 Flash-Lite 98 (4.1%, 1 in 24), GPT-5.6 Luna 103 (4.3%, 1 in 23).

What it adds: it restates the rate as a count of concrete review decisions, which is the unit a reviewer would recognise; a pairwise rate of 2% is 103 of 2,400 decisions that came back differently on at least one run.

### 04_agreement_stack.png — how the runs split

Left panel: share of the 2,400 decisions where all runs agree (model colour) vs not. Right panel: the non-unanimous remainder magnified, split into one dissenting run (4 of 5 agree, light grey) and two dissenting runs (3 of 5 agree, dark grey). Gemma has 4 runs, so its categories are 3 of 4 and 2 of 4.

| Model | All agree | One run differs | Two runs differ |
|---|---|---|---|
| Jev · Noul | 2,387 (99.46%) | 6 | 7 |
| Jev · Choice | 2,382 (99.25%) | 8 | 10 |
| Jev · Score | 2,385 (99.38%) | 6 | 9 |
| Gemma 3 12B (4 runs) | 2,379 (99.12%) | 21 | 0 |
| Gemini 3.8 Flash | 2,358 (98.25%) | 20 | 22 |
| Claude Sonnet 5 | 2,342 (97.58%) | 35 | 23 |
| GPT-5.6 Terra | 2,327 (96.96%) | 42 | 31 |
| Claude Haiku 4.5 | 2,309 (96.21%) | 54 | 37 |
| Gemini 3.5 Flash-Lite | 2,302 (95.92%) | 52 | 46 |
| GPT-5.6 Luna | 2,297 (95.71%) | 56 | 47 |

What it adds: it separates a lone outlier run from a genuine near-coin-flip (3 v 2), which the single rate cannot; for the four least stable LLMs, 41–47% of the flipped decisions are 3-2 splits.

### 05_flips_by_pband.png — disagreement by mean p(responsive)

Small multiples, one panel per model. Decisions are binned by the model's own mean p(responsive) across its runs; the bar is the pairwise disagreement within the band, with n (decisions in the band) under each bar.

Pairwise disagreement within band (n in parentheses):

| Model | 0–0.2 | 0.2–0.4 | 0.4–0.6 | 0.6–0.8 | 0.8–1.0 |
|---|---|---|---|---|---|
| Jev · Noul | 0% (1,968) | 0% (142) | 13.5% (49) | 0% (78) | 0% (163) |
| Jev · Choice | 0% (2,025) | 0% (80) | 24.9% (37) | 0% (53) | 0% (205) |
| Jev · Score | 0% (1,969) | 0% (138) | 14.2% (55) | 0% (74) | 0% (164) |
| Gemma 3 12B (4 runs) | 0% (1,815) | 8.4% (89) | 17.9% (14) | 0.4% (139) | 0% (343) |
| Gemini 3.8 Flash | 0% (2,061) | 23.8% (32) | 57.9% (19) | 11.8% (22) | 0% (266) |
| Claude Sonnet 5 | 0% (1,987) | 28.1% (64) | 12.5% (75) | 0.4% (91) | 0% (183) |
| GPT-5.6 Terra | 0.1% (2,027) | 33.5% (43) | 54.8% (23) | 11.8% (51) | 0.2% (256) |
| Claude Haiku 4.5 | 0.1% (2,004) | 47.3% (30) | 57.1% (28) | 8.8% (132) | 0% (206) |
| Gemini 3.5 Flash-Lite | 0.0% (1,972) | 32.3% (47) | 60.0% (37) | 36.6% (29) | 0% (315) |
| GPT-5.6 Luna | 0.2% (1,815) | 16.9% (83) | 27.4% (68) | 28.1% (47) | 0.3% (387) |

What it adds: all of Jev's flips fall in the 0.4–0.6 band (decisions its own probability already marks as borderline), while the LLMs also flip decisions whose mean p is in the 0.2–0.4 and 0.6–0.8 bands, i.e. decisions that look settled on average but are produced by runs jumping between, say, 0.15 and 0.75.

### 06_issue_heatmap.png — disagreement by issue

Models × 8 issues, cell = pairwise disagreement rate (%) over that issue's 300 decisions, plus an "all issues" column. Greyscale so the family colours are not overloaded.

| Model | SOM broad | Flagged orders | Marketing broad | Exalgo risk | Distribution data | Florida pill mills | DEA dealings | DEA quota | All |
|---|---|---|---|---|---|---|---|---|---|
| Jev · Noul | 0.13 | 0.13 | 0.87 | 0.13 | 0 | 0 | 0.73 | 0.20 | 0.27 |
| Jev · Choice | 0.13 | 0.40 | 0.40 | 0.47 | 0.13 | 0.20 | 1.20 | 0.13 | 0.38 |
| Jev · Score | 0.60 | 0.20 | 0.53 | 0.33 | 0 | 0.13 | 0.53 | 0.27 | 0.32 |
| Gemma 3 12B (4 runs) | 0.33 | 0.50 | 0.67 | 0.67 | 0.33 | 0.17 | 0.33 | 0.50 | 0.44 |
| Gemini 3.8 Flash | 0.87 | 0.40 | 2.00 | 0.47 | 0.87 | 0.67 | 1.00 | 0.80 | 0.88 |
| Claude Sonnet 5 | 0.67 | 2.27 | 0.67 | 0.73 | 2.27 | 0.67 | 1.87 | 0.13 | 1.16 |
| GPT-5.6 Terra | 0.67 | 0.80 | 3.33 | 1.00 | 2.13 | 0.40 | 2.60 | 0.87 | 1.48 |
| Claude Haiku 4.5 | 0.80 | 2.73 | 1.80 | 1.13 | 2.20 | 0.60 | 4.60 | 0.73 | 1.82 |
| Gemini 3.5 Flash-Lite | 1.27 | 2.93 | 2.33 | 1.27 | 2.47 | 1.00 | 3.60 | 1.27 | 2.02 |
| GPT-5.6 Luna | 1.33 | 1.40 | 4.80 | 1.80 | 2.53 | 1.20 | 2.73 | 1.07 | 2.11 |

What it adds: the instability is concentrated in the broad issues (marketing broad, DEA dealings broad, distribution data broad) and in the narrow "flagged orders" issue, and the worst single cells (Luna 4.8% on marketing broad, Haiku 4.6% on DEA dealings) are several times the headline rate — the aggregate hides where the problem is.

### 07_beeswarm.png — five p values per model on six decisions

Six decisions (email × issue) picked for LLM disagreement: ranked by how many LLMs flipped, then by total minority votes and total p-spread, with distinct emails and at most two per issue. Each panel plots each model's p(responsive) from each run (jittered), the 0.5 threshold, and "responsive votes / runs" above any model whose runs did not all agree.

| Email · issue | Models whose runs split (responsive votes / runs) |
|---|---|
| fljv0252 · DEA dealings (broad) | Gemma 1/4, Gemini 3.8 Flash 4/5, GPT-5.6 Terra 2/5, Claude Haiku 4.5 2/5, Gemini 3.5 Flash-Lite 1/5 |
| mzyn0244 · DEA dealings (broad) | Claude Sonnet 5 4/5, GPT-5.6 Terra 1/5, Claude Haiku 4.5 3/5, Gemini 3.5 Flash-Lite 2/5, GPT-5.6 Luna 1/5 |
| npnn0235 · DEA quota (narrow) | Gemini 3.8 Flash 1/5, GPT-5.6 Terra 4/5, Claude Haiku 4.5 4/5, GPT-5.6 Luna 3/5 |
| rflc0235 · Exalgo risk (narrow) | Claude Sonnet 5 4/5, Claude Haiku 4.5 3/5, Gemini 3.5 Flash-Lite 1/5, GPT-5.6 Luna 1/5 |
| ltjf0238 · Flagged orders (narrow) | Claude Sonnet 5 3/5, GPT-5.6 Terra 4/5, Claude Haiku 4.5 1/5, GPT-5.6 Luna 4/5 |
| yplv0247 · Flagged orders (narrow) | Claude Sonnet 5 2/5, Claude Haiku 4.5 3/5, GPT-5.6 Luna 3/5 |

On all six, the three Jev forms gave five close probabilities (largest run-to-run spread 0.15, most under 0.08) and the same label on every run. Example, fljv0252 · DEA dealings: Jev · Noul 0.20 / 0.22 / 0.21 / 0.21 / 0.21; Gemini 3.8 Flash 0.85 / 0.85 / 0.85 / 0.15 / 0.80; GPT-5.6 Terra 0.72 / 0.12 / 0.70 / 0.10 / 0.08; Claude Haiku 4.5 0.15 / 0.15 / 0.75 / 0.72 / 0.15. Full per-run values are in the script's `numbers.json`.

What it adds: it shows the shape of an LLM flip — the runs do not drift across 0.5, they jump between two confident answers (≈0.1 and ≈0.8) — where the aggregate rate only says how often it happens. Because the decisions are selected for disagreement, this chart illustrates rather than measures; the caption says so.

### 08_cumulative_flips.png — where the flips accumulate

One line per model: decisions ordered by the model's own mean p(responsive) on x, cumulative count of flipped decisions on y; the 0.3–0.7 band is shaded. End labels give the total.

| Model | Total flips | Flips with mean p < 0.3 | 0.3–0.7 | > 0.7 |
|---|---|---|---|---|
| Jev · Noul | 13 | 0 | 13 | 0 |
| Jev · Choice | 18 | 0 | 18 | 0 |
| Jev · Score | 15 | 0 | 15 | 0 |
| Gemma 3 12B (4 runs) | 21 | 11 | 10 | 0 |
| Gemini 3.8 Flash | 42 | 6 | 35 | 1 |
| Claude Sonnet 5 | 58 | 21 | 37 | 0 |
| GPT-5.6 Terra | 73 | 22 | 43 | 8 |
| Claude Haiku 4.5 | 91 | 21 | 62 | 8 |
| Gemini 3.5 Flash-Lite | 98 | 21 | 68 | 9 |
| GPT-5.6 Luna | 103 | 30 | 52 | 21 |

What it adds: the Jev curves are flat until mean p ≈ 0.45 and flat again after ≈ 0.55, so every Jev flip is a decision the model itself scored as close to the threshold; the LLM curves start rising around p ≈ 0.15–0.2 and Luna's keeps rising past 0.8, meaning flips occur on decisions the model, on average, called confidently.

## Reproducing

Script and data loader live outside the repository at `/tmp/stability_charts/` (`load.py`, `charts.py`; a venv with matplotlib 3.11 / numpy 2.5). `charts.py` writes the PNGs here and `numbers.json` next to itself. Nothing under `results/`, `ediscovery_bench/`, `scripts/`, or `site/` was modified.
