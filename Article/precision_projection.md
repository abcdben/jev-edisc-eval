# TREC 2016: precision at collection richness (analysis only, nothing on the site changed)

Prepared 2026-09-25 from `results/trec/multi/*.jsonl`, `data/trec/eval.jsonl`, `data/trec/full.jsonl`, `data/trec/raw/athome4.facetsandqrels` and `results/findings.json`. Scratch script: `/tmp/prec_proj/project.py` (section G). No file under `results/`, `site/`, `data/` or `ediscovery_bench/` was modified.

## A. Method, in plain language

The published TREC precision figures come from a 3,016-email test sample that was deliberately built to contain far more responsive email than the real collection does: 100 known-responsive emails per topic, 1,000 emails NIST assessors had judged *not* relevant ("hard negatives"), and 1,000 emails drawn at random. In that sample 36 of every 100 emails are responsive to at least one of the 11 topics; in the actual 286,326-email collection it is 9 of every 100 (and under 1 in 100 for nine of the eleven topics). Recall does not depend on how many non-responsive emails are around, so it carries over; precision does, because every non-responsive email is another chance for a false positive. To estimate what a reviewer would actually see, we take each model's recall on the known-responsive emails and its false-positive rate on the 1,000 *random* emails only (the random draw is the one stratum that looks like the collection), and combine them with each topic's true prevalence in the collection: projected precision = (recall × prevalence) ÷ (recall × prevalence + false-positive rate × (1 − prevalence)). Uncertainty is a bootstrap (2,000 resamples of the random emails and of each topic's positives). Where a model was also run over the entire collection (Jev, zero-shot Laya, the keyword baseline in `results/trec_full/`), the projection is checked against the real answer, and it lands within about one point.

**Setup facts confirmed from the data** (they differ slightly from the framing in the request): the hard-negative and random strata are 1,000 emails *in total*, shared across all topics, not 1,000 per topic; the 100-per-topic positives make 1,016 positive-stratum emails (Non-resident aliens has only 16; the 100 Eminent-domain positives are excluded from scoring), for 3,016 in scope. Per-topic richness in the sample is 3.3–5.8% (100–176 positives of 3,016); document-level richness ("responsive to anything") is 36.3%, versus 9.19% in the collection.

## B. Before / after

Published figures are document level (an email counts as responsive if any of the 11 topics is positive), all strata, each model's own label, from `results/findings.json`. Two projections are shown: the per-topic pooled formula requested (ΣTP_t / (ΣTP_t + ΣFP_t) over topics, decision level) and a document-level "any topic" projection that is the like-for-like counterpart of the published number (false-positive rate = share of random emails with no gold label that the model flags on any topic; recall re-weighted to the collection's mix of topics). Both are within one to three points of each other for every roster model. "Projected recall" is the collection-prevalence-weighted recall (George W. Bush, 43% of all relevant email, dominates it), which is what the pooled recall on the real collection would be.

| Model | Published recall | Published precision | Precision, positive + random strata only | Random stratum alone (direct, 1,000 emails) | **Projected collection precision** (pooled per topic) [95% CI] | Projected doc-level precision (any topic) [95% CI] | Projected recall | Projected F1 [95% CI] |
|---|---|---|---|---|---|---|---|---|
| Jev · Noul (`jev@base`) | 78.5% | 79.6% | 92.1% | 48.3% [40–56] | **49.9%** [44.7–55.6] | 50.7% [45.4–56.6] | 80.9% | 61.8% [57.5–66.2] |
| Jev · Choice (`jev@choice`) | 77.3% | 79.6% | 91.8% | 47.2% [39–55] | **49.7%** [45.1–55.8] | 50.3% [45.4–56.2] | 81.2% | 61.7% [57.9–66.2] |
| Jev · Score (`jev@score`) | 83.2% | 78.8% | 92.1% | 46.2% [38–54] | **49.4%** [44.5–55.6] | 49.8% [44.9–56.0] | 82.3% | 61.7% [57.6–66.6] |
| Jev · Facets (`jev@decompose`) | 88.9% | 75.0% | 89.2% | 37.6% [31–45] | **38.6%** [34.8–43.0] | 41.0% [37.0–45.4] | 86.6% | 53.4% [49.6–57.6] |
| Jev · Three-Phrasing Ensemble (`jev@ensemble`) | 80.7% | 79.1% | 92.0% | 47.3% [39–55] | **49.0%** [44.1–54.6] | 49.9% [45.1–55.6] | 81.9% | 61.3% [57.1–65.7] |
| Jev · Relevance Gate (`jev@gate`) | 70.3% | 82.1% | 93.3% | 51.3% [42–60] | **53.4%** [47.2–60.5] | 54.0% [47.8–61.0] | 68.5% | 60.0% [55.6–64.7] |
| Laya, fine-tuned (`laya-ft-trec@recipe`) | 57.3% | 84.5% | 95.0% | 52.9% [41–64] | **53.0%** [45.5–62.0] | 56.7% [49.1–65.8] | 44.5% | 48.4% [44.6–52.4] |
| Claude Haiku 4.5 | 93.9% | 70.4% | 86.4% | 31.4% [26–38] | **32.1%** [29.3–35.3] | 34.8% [31.9–38.1] | 91.0% | 47.5% [44.3–51.0] |
| Claude Sonnet 5 | 89.7% | 77.8% | 91.5% | 44.8% [37–52] | **45.7%** [41.5–50.8] | 47.0% [42.6–52.3] | 86.2% | 59.8% [55.9–64.1] |
| GPT-5.6 Luna | 94.8% | 67.5% | 84.3% | 28.7% [24–34] | **28.9%** [26.4–31.8] | 31.4% [28.9–34.4] | 93.8% | 44.2% [41.2–47.5] |
| GPT-5.6 Terra | 94.9% | 71.2% | 86.9% | 33.3% [28–40] | **34.4%** [31.5–37.9] | 36.0% [33.0–39.6] | 94.1% | 50.4% [47.2–54.1] |
| Gemini 3.5 Flash-Lite | 92.9% | 68.6% | 85.3% | 29.7% [24–36] | **30.5%** [27.8–33.7] | 32.7% [29.9–36.0] | 90.9% | 45.7% [42.5–49.2] |
| Gemini 3.8 Flash | 93.3% | 73.0% | 88.9% | 37.9% [32–45] | **39.1%** [35.5–43.4] | 40.3% [36.5–44.6] | 92.5% | 55.0% [51.3–59.1] |
| Gemma 3 12B (local) * | 83.8% | 71.8% | 83.1% | 18.2% [10–30] | **16.4%** [13.1–21.4] | 21.6% [17.6–27.1] | 69.0% | 26.5% [21.8–32.9] |

\* Gemma ran on a 577-email stratified subsample: 186 random emails, 142 hard negatives, 249 positives. Its random stratum is present, so it is projected, but on 61 false-positive decisions rather than ~100–200; treat its interval as indicative.

**Every model loses 25–40 points of precision.** The ranking is broadly preserved (Jev Noul/Choice/Score, Relevance Gate and fine-tuned Laya at ~50%; Sonnet 5 at ~46%; Gemini 3.8 Flash and Jev Facets at ~39%; Terra, Haiku, Flash-Lite and Luna at 29–34%), but the spread widens: the gap between Jev Noul and Luna is 12 points on the sample and 21 points at collection richness, because the high-recall LLMs pay for their recall with a false-positive rate two to three times Jev's, and at 9% richness that rate is what sets precision. Recall moves too, but only a little for the zero-shot models: pooled recall on the collection is within ±4 points of the published figure (Jev Noul +2.4, Sonnet 5 −3.4, Luna −1.0), because George W. Bush, 43% of all relevant email, is about as easy as the average topic for them. It drops 13 points for fine-tuned Laya (11% recall on George W. Bush, 10% on Marketing) and 15 for Gemma (48% on George W. Bush).

**Validation against real full-collection runs** (`results/trec_full/multi/`, 286,326 emails, same gold convention):

| Model | Actual full-collection recall | Actual precision (lower bound) | Actual emails flagged | Projected (doc level): precision / recall / flagged | Projected (pooled per topic) |
|---|---|---|---|---|---|
| Jev · Noul | 83.0% | 51.4% | 42,532 | 50.7% / 81.7% / 42,403 | 49.9% |
| Laya zero-shot, recipe | 96.2% | 10.0% | 253,684 | 9.8% / 94.6% / 254,405 | 2.3% † |
| Keyword baseline | 95.2% | 11.1% | 226,299 | 10.9% / 96.1% / 231,385 | 2.0% † |

† For models that flag most emails on most topics, the pooled per-topic formula counts one email as up to 11 false positives, so it understates document-level precision; the doc-level projection is the right comparator and matches the actual runs. For the roster models the two agree.

Per-topic collection prevalence (π_t). "Collection" here is the 286,326-email universe the models are run over (`data/trec/full.jsonl`: the 290,099-email Jeb Bush collection minus the 668-email calibration set, 696 emails read during exploration, and emails over 12,000 characters); NIST's raw qrels counts over the 290,099 are shown alongside.

| Topic | Relevant in collection | π_t | NIST qrels relevant (of 290,099) | Emails NIST judged (rel or not) | Random-stratum emails NIST judged | Random-stratum gold positives |
|---|---|---|---|---|---|---|
| George W. Bush (`gw_bush`) | 11,426 | 3.991% | 12,106 (4.17%) | 13,883 | 46 | 35 |
| Movie Gallery (`movie_gallery`) | 5,901 | 2.061% | 5,931 (2.04%) | 6,801 | 26 | 19 |
| Rilya Wilson (`rilya_wilson`) | 1,833 | 0.640% | 1,989 (0.69%) | 2,799 | 1 | 0 |
| Faith-based (`faith_based`) | 1,496 | 0.522% | 1,586 (0.55%) | 2,719 | 7 | 7 |
| Marketing (`marketing`) | 1,399 | 0.489% | 1,446 (0.50%) | 3,047 | 12 | 9 |
| 2000 recount (`recount_2000`) | 1,350 | 0.471% | 1,410 (0.49%) | 1,687 | 1 | 1 |
| Condominiums (`condominiums`) | 1,284 | 0.448% | 1,346 (0.46%) | 2,653 | 11 | 5 |
| Bottled water (`bottled_water`) | 1,059 | 0.370% | 1,090 (0.38%) | 2,254 | 5 | 2 |
| Medicaid reform (`medicaid_reform`) | 786 | 0.275% | 839 (0.29%) | 1,025 | 3 | 3 |
| NRA (`nra_rifle`) | 251 | 0.088% | 286 (0.10%) | 1,399 | 4 | 0 |
| Non-resident aliens (`nra_aliens`) | 18 | 0.006% | 31 (0.01%) | 348 | 1 | 0 |
| Any topic | 26,317 | 9.19% | | | | 71 of 1,000 |

### The three precision numbers, and why they differ

1. **Published sample precision (e.g. Jev 79.6%)**: 1,095 responsive emails against 1,921 non-responsive, of which 1,000 were chosen *because* an assessor had looked at them and said no. Those hard negatives draw one and a half to two times the false-positive rate of random email (Jev: 1.38% vs 0.70% per decision; Sonnet 5: 1.78% vs 0.88%; Luna: 2.99% vs 1.98%). So the sample is simultaneously too rich (36% vs 9%) and too hard (half its negatives are near-misses). The two distortions partly cancel, which is why the published number is not absurd, but they do not cancel evenly across models.
2. **Positive + random strata only (Jev 92.1%)**: dropping the hard negatives removes the "too hard" distortion but leaves the "too rich" one, and makes it worse: 1,095 positives among 2,016 emails is 54% richness. This number needs no prevalence assumption but describes a matter richer than almost any real one. It is reported because it was asked for; it should not be published as a headline.
3. **Projected at collection prevalence (Jev ~50%)**: uses only the random stratum for the negative side and the collection's real topic mix. It removes both distortions, at the cost of an assumption (the 1,000 random emails represent the collection's non-responsive email) and wide per-topic intervals. It is corroborated by the direct estimate on the random stratum alone (Jev 48.3%, 1,000 emails, no modelling) and, for the three models that were run on the whole collection, by the real answer.

## C. Sensitivity: precision on a matter of a given richness

Single-issue reading: a model with this recall and this false-positive rate (decision level, pooled over the 11 topics; recall on all sample positives, false-positive rate on the random stratum), applied to a matter where the stated share of documents is responsive. Brackets are bootstrap 95% intervals.

| Model | Recall (per decision) | FPR, random emails | FPR, hard negatives | Precision at 1% | at 5% | at 10% | at 20% |
|---|---|---|---|---|---|---|---|
| Jev · Noul | 75.9% | 0.70% | 1.38% | 52.4% [47–58] | 85.2% [82–88] | 92.4% [91–94] | 96.5% [96–97] |
| Jev · Choice | 74.5% | 0.71% | 1.34% | 51.6% [47–58] | 84.8% [82–88] | 92.2% [91–94] | 96.4% [96–97] |
| Jev · Score | 80.4% | 0.72% | 1.57% | 52.9% [48–59] | 85.4% [83–88] | 92.5% [91–94] | 96.5% [96–97] |
| Jev · Facets | 85.8% | 1.18% | 1.93% | 42.3% [38–47] | 79.3% [76–82] | 89.0% [87–91] | 94.8% [94–96] |
| Jev · Three-Phrasing Ensemble | 78.0% | 0.73% | 1.48% | 51.8% [47–58] | 84.9% [82–88] | 92.2% [91–94] | 96.4% [96–97] |
| Jev · Relevance Gate | 68.1% | 0.51% | 1.05% | 57.3% [51–64] | 87.5% [84–90] | 93.7% [92–95] | 97.1% [96–98] |
| Laya, fine-tuned | 54.6% | 0.34% | 0.75% | 61.9% [55–70] | 89.4% [86–92] | 94.7% [93–96] | 97.6% [97–98] |
| Claude Haiku 4.5 | 91.7% | 1.65% | 2.62% | 36.0% [33–39] | 74.5% [72–77] | 86.1% [84–88] | 93.3% [92–94] |
| Claude Sonnet 5 | 88.1% | 0.88% | 1.78% | 50.3% [46–56] | 84.1% [82–87] | 91.8% [90–93] | 96.2% [95–97] |
| GPT-5.6 Luna | 92.9% | 1.98% | 2.99% | 32.2% [30–35] | 71.2% [69–74] | 83.9% [82–86] | 92.1% [91–93] |
| GPT-5.6 Terra | 93.7% | 1.54% | 2.55% | 38.1% [35–42] | 76.2% [74–79] | 87.1% [86–89] | 93.8% [93–95] |
| Gemini 3.5 Flash-Lite | 91.5% | 1.78% | 2.81% | 34.2% [31–38] | 73.0% [70–76] | 85.1% [83–87] | 92.8% [92–94] |
| Gemini 3.8 Flash | 92.1% | 1.24% | 2.41% | 42.9% [39–47] | 79.7% [77–82] | 89.2% [88–91] | 94.9% [94–96] |
| Gemma 3 12B (local) * | 78.0% | 3.01% | 3.14% | 20.8% [17–26] | 57.7% [51–65] | 74.2% [69–80] | 86.6% [83–90] |

Reading it: at 5% richness (a typical single-issue matter) Jev Noul and Sonnet 5 sit at about 85%, the high-recall LLMs at 71–80%; at 1% every model except fine-tuned Laya is below 60% and the ranking is set almost entirely by false-positive rate. The 5% column is *higher* than the published sample figure for most models because it uses random-email false-positive rates rather than the sample's hard negatives, and because it is one issue at a time rather than 11 issues compounded on one email. The 9%-richness, 11-issue TREC collection lands where section B says.

## D. Per-topic detail: Jev Noul, Claude Sonnet 5, GPT-5.6 Luna

Columns: gold positives in the sample for the topic; recall on them; random-stratum emails that are gold-negative for the topic; false positives among them, split into NIST-unjudged / NIST-judged-non-relevant; false-positive rate on random and on hard-negative emails; collection prevalence; projected precision with bootstrap interval (for topics with zero false positives the interval collapses to 100%, so the value that would follow from the rule-of-three upper bound on the false-positive rate, 3/n, is given instead); and how many of the random stratum's own gold positives the model caught. The last column of the Jev table also shows the real full-collection precision for the topic (`results/trec_full`).

**Jev · Noul (`jev@base`)**

| Topic | Gold pos | Recall | Random negatives | FP (unjudged / judged non-rel) | FPR random | FPR hard-neg | π_t | Projected precision [95% CI] | Random TP / gold pos | Actual full-collection precision |
|---|---|---|---|---|---|---|---|---|---|---|
| gw_bush | 176 | 84.1% | 965 | 20 (18 / 2) | 2.07% | 4.30% | 3.991% | 62.8% [53–74] | 31 / 35 | 62.2% |
| movie_gallery | 119 | 99.2% | 981 | 0 (0 / 0) | 0.00% | 0.00% | 2.061% | 100% (0 FP seen; ≥ 87.2% if FPR were 3/n) | 19 / 19 | 99.4% |
| rilya_wilson | 102 | 36.3% | 1000 | 8 (8 / 0) | 0.80% | 0.80% | 0.640% | 22.6% [13–45] | 0 / 0 | 36.7% |
| faith_based | 109 | 58.7% | 993 | 3 (3 / 0) | 0.30% | 0.50% | 0.522% | 50.5% [30–100] | 4 / 7 | 38.1% |
| marketing | 109 | 75.2% | 991 | 24 (23 / 1) | 2.42% | 5.60% | 0.489% | 13.2% [10–20] | 6 / 9 | 12.5% |
| recount_2000 | 102 | 43.1% | 999 | 0 (0 / 0) | 0.00% | 0.10% | 0.471% | 100% (0 FP seen; ≥ 40.5% if FPR were 3/n) | 1 / 1 | 75.6% |
| condominiums | 105 | 84.8% | 995 | 4 (2 / 2) | 0.40% | 1.30% | 0.448% | 48.7% [31–80] | 4 / 5 | 62.8% |
| bottled_water | 102 | 96.1% | 998 | 1 (1 / 0) | 0.10% | 0.30% | 0.370% | 78.1% [53–100] | 2 / 2 | 89.7% |
| medicaid_reform | 104 | 93.3% | 997 | 12 (12 / 0) | 1.20% | 1.80% | 0.275% | 17.6% [12–30] | 3 / 3 | 14.3% |
| nra_rifle | 101 | 77.2% | 1000 | 4 (2 / 2) | 0.40% | 0.50% | 0.088% | 14.5% [7–43] | 0 / 0 | 33.3% |
| nra_aliens | 18 | 88.9% | 1000 | 0 (0 / 0) | 0.00% | 0.00% | 0.006% | 100% (0 FP seen; ≥ 1.8% if FPR were 3/n) | 0 / 0 | 22.2% |

The per-topic check makes the small-count caveat concrete: where the random stratum yields 8 or more false positives (George W. Bush, Marketing, Medicaid, Rilya Wilson) the projection is within a few points of the real full-collection figure; where it yields 0–4 it can be off by 15–80 points in either direction, and for Non-resident aliens (18 relevant emails in 286k) a single false positive in 1,000 would move projected precision from 100% to about 5%. The pooled figures are robust because they are dominated by the topics with the most email.

**Claude Sonnet 5 (`claude-sonnet-5`)**

| Topic | Gold pos | Recall | Random negatives | FP (unjudged / judged non-rel) | FPR random | FPR hard-neg | π_t | Projected precision [95% CI] | Random TP / gold pos |
|---|---|---|---|---|---|---|---|---|---|
| gw_bush | 176 | 78.4% | 965 | 16 (12 / 4) | 1.66% | 3.50% | 3.991% | 66.3% [56–78] | 31 / 35 |
| movie_gallery | 119 | 99.2% | 981 | 0 (0 / 0) | 0.00% | 0.10% | 2.061% | 100% (0 FP seen; ≥ 87.2% if FPR were 3/n) | 19 / 19 |
| rilya_wilson | 102 | 93.1% | 1000 | 32 (31 / 1) | 3.20% | 2.70% | 0.640% | 15.8% [12–22] | 0 / 0 |
| faith_based | 109 | 81.7% | 993 | 4 (4 / 0) | 0.40% | 1.20% | 0.522% | 51.6% [34–82] | 6 / 7 |
| marketing | 109 | 82.6% | 991 | 17 (17 / 0) | 1.72% | 5.90% | 0.489% | 19.1% [14–30] | 8 / 9 |
| recount_2000 | 102 | 75.5% | 999 | 3 (3 / 0) | 0.30% | 0.60% | 0.471% | 54.4% [34–100] | 1 / 1 |
| condominiums | 105 | 91.4% | 995 | 3 (2 / 1) | 0.30% | 2.30% | 0.448% | 57.7% [37–100] | 5 / 5 |
| bottled_water | 102 | 96.1% | 998 | 1 (0 / 1) | 0.10% | 0.50% | 0.370% | 78.1% [54–100] | 2 / 2 |
| medicaid_reform | 104 | 97.1% | 997 | 16 (16 / 0) | 1.60% | 1.90% | 0.275% | 14.3% [10–23] | 3 / 3 |
| nra_rifle | 101 | 91.1% | 1000 | 4 (2 / 2) | 0.40% | 0.80% | 0.088% | 16.7% [8–45] | 0 / 0 |
| nra_aliens | 18 | 94.4% | 1000 | 0 (0 / 0) | 0.00% | 0.10% | 0.006% | 100% (0 FP seen; ≥ 1.9% if FPR were 3/n) | 0 / 0 |

**GPT-5.6 Luna (`gpt-5.6-luna`)**

| Topic | Gold pos | Recall | Random negatives | FP (unjudged / judged non-rel) | FPR random | FPR hard-neg | π_t | Projected precision [95% CI] | Random TP / gold pos |
|---|---|---|---|---|---|---|---|---|---|
| gw_bush | 176 | 93.2% | 965 | 35 (32 / 3) | 3.63% | 5.30% | 3.991% | 51.6% [44–61] | 34 / 35 |
| movie_gallery | 119 | 99.2% | 981 | 0 (0 / 0) | 0.00% | 0.00% | 2.061% | 100% (0 FP seen; ≥ 87.2% if FPR were 3/n) | 19 / 19 |
| rilya_wilson | 102 | 90.2% | 1000 | 29 (28 / 1) | 2.90% | 2.70% | 0.640% | 16.7% [13–24] | 0 / 0 |
| faith_based | 109 | 94.5% | 993 | 13 (13 / 0) | 1.31% | 1.50% | 0.522% | 27.5% [19–42] | 7 / 7 |
| marketing | 109 | 93.6% | 991 | 96 (95 / 1) | 9.69% | 15.10% | 0.489% | 4.5% [4–6] | 9 / 9 |
| recount_2000 | 102 | 79.4% | 999 | 4 (4 / 0) | 0.40% | 1.00% | 0.471% | 48.4% [31–80] | 1 / 1 |
| condominiums | 105 | 90.5% | 995 | 5 (3 / 2) | 0.50% | 2.60% | 0.448% | 44.8% [29–80] | 5 / 5 |
| bottled_water | 102 | 96.1% | 998 | 1 (0 / 1) | 0.10% | 0.60% | 0.370% | 78.1% [54–100] | 2 / 2 |
| medicaid_reform | 104 | 98.1% | 997 | 22 (22 / 0) | 2.21% | 2.40% | 0.275% | 10.9% [8–16] | 3 / 3 |
| nra_rifle | 101 | 93.1% | 1000 | 5 (3 / 2) | 0.50% | 1.50% | 0.088% | 14.0% [8–45] | 0 / 0 |
| nra_aliens | 18 | 88.9% | 1000 | 6 (6 / 0) | 0.60% | 0.20% | 0.006% | 0.9% [1–3] | 0 / 0 |

Luna's Marketing row is the single biggest driver of its collection-level result: it flags almost 1 in 10 random emails as Marketing (the topic is about the state's own marketing of Florida, which the model reads broadly), and at 0.49% prevalence that is ~27,000 false positives for ~1,300 true ones.

## E. Caveats

- **Small false-positive counts.** Per topic the random stratum yields 0–35 false positives for most model/topic pairs; the exceptions are Marketing (41–96 for the LLMs and Jev Facets) and Rilya Wilson (24–49 for several LLMs). Per-topic projections are therefore rough (see the Jev validation column above); the pooled figures rest on 56–216 false-positive decisions per model (37 for fine-tuned Laya, 61 for Gemma) and have ±3–7 point intervals. Topics with zero observed false positives (Movie Gallery for everyone; 2000 recount and Non-resident aliens for some) project to 100% only because 0/1,000 was observed; the rule-of-three bound (FPR ≤ 0.3%) leaves them anywhere from 87% (Movie Gallery) down to ~2% (Non-resident aliens).
- **Unjudged emails are counted as false positives.** Of the false positives in the random stratum, roughly nine in ten are emails NIST never judged for that topic (Jev 69 of 76; Sonnet 5 87 of 96; Luna 206 of 216; Facets 119 of 129; fine-tuned Laya 33 of 37), and only about one in ten was affirmatively judged non-relevant. NIST's Total Recall assessment aimed at finding every relevant email, and only 0.1–4.6% of the random stratum was judged at all per topic, so "unjudged = not relevant" is the standard convention and is also what the published recall and the full-collection runs assume. But if some of those flagged emails are genuine NIST misses, the projection is pessimistic; the same is true of the "precision lower bound" already reported for the full-collection runs. A cheap check would be a reviewer reading the ~70 unjudged emails Jev flags in the random stratum (or the ~200 Luna flags).
- **Each model's own label, not a tuned cutoff.** The score uses each model's stated label; for Jev that is exactly p ≥ 0.5 (0 disagreements), the Anthropic models disagree with their own probability on 4–7 of 33,176 decisions, Luna on 550 (1.7%), Gemma on 301 of 6,347. No cutoff was tuned to prevalence: on a 9%-rich collection a model could trade recall for precision by raising its threshold, and the ranking at a fixed recall target (the site's `cutoffs` view) is a fairer comparison of the underlying scores than precision at the default label.
- **The random stratum stands in for the collection's negatives.** It is a uniform draw of the collection minus the ~2,200 emails already placed in the positive and hard-negative strata (a ≤1% under-representation of relevant email, so a very slight optimism in the false-positive rate), with the same length and exclusion rules as the collection file. The Jev, Laya and keyword full-collection runs agreeing with the projection to within ~1 point is the best evidence the assumption holds for this collection; it would not automatically hold for a collection with a different mix (e.g. more near-duplicate threads).
- **Prevalence is the collection's, not a client's.** π_t comes from NIST's qrels; a real matter's richness is unknown in advance and is exactly what section C is for.
- **Recall is re-weighted, not unchanged.** Pooled recall on the collection is dominated by George W. Bush (43% of relevant email); topics with 18–250 relevant emails barely register. The published per-topic recalls are unaffected.
- **Gemma 3 12B** is projected from a 186-email random stratum and 249 positives; the direction is clear but the numbers are soft.

## F. Recommendation for the site and article (not implemented)

1. **Keep the published sample precision, but relabel it.** Call it "precision on the evaluation sample (36% responsive)" wherever it appears, and add one sentence to the TREC method row saying the sample is enriched and that precision, unlike recall, does not transfer to the collection.
2. **Add a secondary figure, "precision at collection richness (9%)", next to the primary one** for the TREC corpus: the doc-level projection in section B with its interval, footnoted as a projection from the random stratum and validated against the full-collection run for Jev. On the Compare page this could be a toggle ("sample" / "at collection richness") rather than a second bar, so the chart does not double in width. F1 should follow the toggle.
3. **Expose the sensitivity table as a prevalence control**, either a small slider (1–20%) on the TREC panel or a fixed 1/5/10/20% strip under the chart, driven by each model's recall and random-stratum false-positive rate (both already derivable from `findings.json` if `per_issue` gains an FPR-on-random field, or from a small extra export). This is the figure a practitioner can actually use: "on my 3%-rich matter, what would I see?"
4. **In the article**, replace the single precision sentence with the three-number framing of section B ("79.6% on the enriched sample; about 50% at the collection's 9% richness; 85% on a 5%-rich single-issue matter") and cite the Jev full-collection run (51.4%) as the anchor. Present recall as the headline that transfers and precision as the one that must be stated with a richness.
5. **Do not publish the positive+random-only figure** (92%); it is the least representative of the three.
6. **Optional follow-up, cheap:** have a reviewer judge the unjudged random-stratum emails Jev and one LLM flag, to bound how pessimistic the "unjudged = non-relevant" convention is.

Implementation, if approved, would be a new field on the TREC records in `ediscovery_bench/export.py` (random-stratum FPR and the projection, computed the same way as here from `meta.stratum`), a `precision_at_richness` block in `findings.json`, and a toggle/slider in `site/src`; none of that has been touched.

## G. Reproduction

Script: `/tmp/prec_proj/project.py`. Run from the repo root with the project venv:

```
cd /Users/bensexton/Projects/typesafe-ai && .venv/bin/python /tmp/prec_proj/project.py
```

It writes `/tmp/prec_proj/out/results.json` (every number above, per model and per topic, including bootstrap intervals and the unjudged/judged split) and `/tmp/prec_proj/out/tables.md` (all tables, plus an appendix row for every other TREC all-issues configuration in `findings.json`: Jev ablations, zero-shot Laya checkpoints, keyword baseline and the TAR rows). Runtime ~11 s. Seed 20260925, 2,000 bootstrap resamples; percentile intervals; resampling is over random-stratum emails (one draw shared across topics, preserving their correlation) and independently over each topic's gold positives.

**Reproduction check (step 2).** Before projecting, the script recomputes the published document-level confusion (tp/fp/fn/tn) for every TREC all-issues row from the raw `results/trec/multi/*.jsonl` and `data/trec/eval.jsonl` with the export's rules (in-scope strata, 11 scored topics, error rows dropped, each model's own label, gold = NIST rel 1/2, unjudged = not responsive). All 53 rows match `results/findings.json` exactly, including Jev Noul (860/221/235/1700 → recall 78.5%, precision 79.6%), Claude Sonnet 5 (982/280/113/1641 → 89.7%, 77.8%) and GPT-5.6 Luna (1038/501/57/1420 → 94.8%, 67.5%).
