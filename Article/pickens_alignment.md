# Does the TREC 2016 benchmark do what Jeremy Pickens asks for?

Prepared 2026-09-25. Sources: three past chat transcripts (cited by title and id below), the podcast transcript attached to the first of them, and the repository as of commit `1c737e3`. Nothing in the repo other than this file was changed.

Two things to hold in mind throughout. First, Pickens's remarks were made about **validating one production review** (a Relativity aiR matter, then the Redgrave study), where the strata are the *machine's* predicted-positive and predicted-negative piles and the human labels come from a sample. Our TREC benchmark is a different object: a **comparison of thirteen models against complete, pre-existing NIST labels**, where the strata are defined by the *gold*, not by any model. Several of his points therefore translate only by analogy, and the table below says so where that is the case. Second, Pickens's position moved across the three months of the exchange (two separate samples in May; post-stratifying a single simple random sample in June; "sampling done right" on the podcast), and Ben's own September paraphrase of it is closest to the May version. The quotes are dated so the reader can see which Pickens is being compared to.

---

## 1. What Pickens asks for

All quotes are Pickens's own words unless marked otherwise. Emails are from the thread forwarded into [GenAI review accuracy commentary](2c73d133-6d8c-4fde-b583-fe496785a273) on Aug 26, 2026 (two Gmail threads: "Ben, a question", May 11–13, 2026, and "Confidence Intervals for Recall", May 29–June 11, 2026). The podcast quotes are from the transcript file attached to that same chat on Aug 25, 2026 (Robert Keeling, Jeremy Pickens, Maura Grossman on the Redgrave GenAI accuracy study).

**P1. TAR 1 / GenAI needs two samples, one of the predicted positives and one of the predicted negatives, and recall must come from both.**
> "when one is doing TAR 1, there is neither a full human review of the predicted positives nor of the predicted negative docs (elusion). So you need to do two samples (positives and negatives) in order to get a proper recall estimate." — email, May 13, 2026

> "You essentially have two strata for recall.. the Machine-R (predicted positive) stratum and the Machine-NR (predicted negative) stratum." — email, May 12, 2026

**P2. Sample counts must be normalized to the true stratum sizes; you cannot read recall off the raw confusion matrix.**
> "So this is our question: Which method is correct? Can you calculate the point estimate from the matrix directly? Or should you project the sample estimates onto the actual strata in order to properly normalize the counts. Again, I favor the latter." — email, June 10, 2026

> "But the question is: Do you use the raw sample count, or do you normalize by the size of the stratum." — email, June 11, 2026

> "I don't know the exact size of your Machine-R and Machine-NR strata, for example. And that matters. A lot. You can't validate on the sample only." — email, May 12, 2026

**P3. He is *not* asking for a stratified draw; he is asking for post-stratification of a simple random sample.** (This is the point Ben's later paraphrase blurs.)
> "I'm not arguing for selecting strata first, and then sampling from within each stratum. So, same Ben approach, but being smarter about the numbers that come out of that approach." — email, June 11, 2026

> "What Ben and I are discussing is literally using the exact same simple random sample, taken without a priori knowledge of what the strata were, and then once a posteriori seeing where that simple random sample 'falls' within your strata, calculating your stats based on where it falls." — email, June 11, 2026

**P4. Confidence intervals should be computed per stratum and then combined, and he believes the only honest combination is best/worst case for each.**
> "So with two confidence intervals, one for each stratum, in the best case we could have 27,838 docs in the Machine-R stratum and 14 docs in the Machine-NR stratum. For a recall of: 27,838 / (27,838 + 14) = 99.9% But in the worst case, we cannot (95% confidence) rule out the possibility that there are 22,572 documents in the Machine-R stratum and 8,211 docs in the Machine-NR stratum. This gives us a recall of: 22,572 / (22,572 + 8,211) = 73.3% ... you're getting a very different MoE around the point estimate. I'm not completely convinced that you are validating in the proper way." — email, May 12, 2026

> "when the goal is to prove recall ... there IS no great way (to my and to many other people's knowledge) to combine those two intervals it mathematically OTHER than to assume the worst/best for each." — email, May 13, 2026

(The assistant in that chat showed by simulation that the corner combination is roughly a 99.9% bound, that his elusion MoE used the p = 0.5 worst-case formula rather than a data-driven interval, and that a delta-method or bootstrap propagation gives an interval as tight as or tighter than the direct Wilson interval. That is our analysis, not his; he has not conceded it.)

**P5. Compare methods per instance (per topic), not by averaging each method separately.**
> "In IR, what we do is report not just the mean performance of approach X or approach Y on a set of topics (queries), but we break down the difference between approaches X and Y, on a per topic basis. And we plot histograms of every single difference, by instance." — email, June 11, 2026

**P6. The human judgment of the sample must be independent of the machine's output.**
> "When you are reviewing the sample, are you using the GenAI predictions and explanations to aide that review? Or is the human judge making the decision independently?" — email, May 13, 2026

**P7. "Sampling done right" is a blind sample of everything, and industry-standard shortcuts can manufacture almost any number.**
> "If you sample and you sample properly, you can see what you got and see what you missed ... you could sample what the set was and what they found and what they left behind." — podcast, ~9:00

> "sampling will get you there. See what you've gotten, but only if it's sampling done right. I see in the GenAI world, I still see sampling done wrong. ... the way what Robert has done in his study is sampling done right, but it's not the norm for the industry. ... if doing it wrong, I can take the RAL result ... and get you to 79% recall, 100% precision without changing a single call by just sampling it the way the industry currently does things." — podcast, ~48:33–49:23

Note: the sharper statement of what "wrong" means on that podcast is **Maura Grossman's**, not Pickens's: "We have to stop using elusion to calculate recall ... they're two completely different samples taken under very different circumstances and when you combine them you don't get an honest measure of recall. ... you got to sample from all the different sort of buckets at the same time under the same circumstances with the same subject matter expert." (~50:09–51:06). Grossman opened that remark with "I would agree with Jeremy 100%", so the two are aligned, but the explicit elusion/control-set critique should be attributed to her, not to him.

**P8. Open, checkable data.**
> "thank you Robert and Redgrave profusely for making this data set open because this is exactly the kind of thing that the community needs to have these discussions ... in a neutral way, in a checkable way, in a holistic way." — podcast, ~10:13

**P9. Ben's own description of the ask, and what was answered.** In [UI Work](7792ba26-d6c4-4e4e-874b-8618fda143a2), Sep 21, 2026, Ben wrote: "Whenever we're calculating recall. And precision, I think we need to. Do so in a way that Complies with what, say, Jeremy Pickens suggests, which we have discussed before, I think, but more or less where you're sampling from the positives and negatives, and then winding them together into a, a confidence interval, rather than a simple random sample." Earlier in the same chat (the TREC sampling plan) the assistant had written: "Because the judgments are complete, every sampled email is labeled on all 10 topics ... and recall per topic is unbiased. Precision is reported both raw and reweighted to true prevalence (I'll add that column; it's a one-line weighting since we know the sampling rates)." In the Sep 21 reply it said instead: "every document in each test set is gold-labeled, so recall/precision are exact for the set and the Wilson intervals express how far they'd generalize; there is no review-sample step. If you want the numbers a practitioner would see when validating one of these models the way a TAR project is validated, I can simulate a stratified sample from the flagged and unflagged sets and produce that interval alongside." The reweighted precision column promised in the plan was not built; the simulated validation was offered and not taken up.

**Related sizing note.** [QA about Typesafe Eval Project](d4cab950-361e-496e-b397-04b3d94efccf) gives the Wilson 95% half-width on recall by positives per topic: 25 → ±12–15 pts; 50 → ±8.5–11; 75 → ±7–9; 100 → ±6–8; 150 → ±5–6.5 (at recall 0.90 / 0.80). This is why the design targeted 100 positives per topic.

---

## 2. What we did (verified in the repo)

Checked against `ediscovery_bench/trec/build.py`, `ediscovery_bench/export.py`, `ediscovery_bench/metrics.py`, `ediscovery_bench/scope.py`, `ediscovery_bench/tasks.py`, `tasks/trec.yaml`, `data/trec/eval.jsonl`, `data/trec/dev.jsonl`, `site/src/components/Method.tsx`, `site/src/components/Disclaimer.tsx`, `Article/draft_v2.md` and `Article/precision_projection.md`.

| Claim to check | Verdict | What the repo shows |
|---|---|---|
| Evaluation set is 3,016 emails | **Confirmed** | `eval.jsonl` has 3,116 rows; `scope.py` drops the 100-email `pos:eminent_domain` stratum at scoring time (topic 404 dropped 2026-09-23 for unreliable gold), leaving 3,016. |
| 100 NIST-relevant positives per topic | **Confirmed** | `build_eval(n_pos=100, seed=22)`: relevant docnos per topic shuffled, first 100 that pass the exclusions added with `meta.stratum = "pos:<topic>"`. Eleven `pos:` strata of 100 in scope. |
| 18 for Non-resident aliens | **Corrected** | The `pos:nra_aliens` stratum is **16** emails (topic has 31 qrels-relevant, 18 in the 286k in-scope collection; only 16 survived the exclusions). The sample holds **18** gold positives for the topic because 2 more arrived through the `pos:nra_rifle` stratum. |
| One shared 1,000 "hard negatives" | **Confirmed** | `hard = union(judged non-relevant) − union(relevant on any 2016 topic)`, shuffled, first 1,000; `meta.stratum = "hard_neg"`. Zero of them are gold-positive on the 11 scored topics. |
| One shared 1,000 uniform random draw | **Confirmed, with a nuance** | `all_docnos()` shuffled, first 1,000 not already chosen and not excluded; `meta.stratum = "random"`. Because docs already placed in the positive/hard-negative strata are skipped, it is a uniform draw of the collection *minus* those ~2,100 emails (≤1% under-representation of relevant email). 79 of the 1,000 are gold-positive on at least one scored topic (7.9% vs. 9.19% in the collection). |
| Excludes a 668-email calibration set | **Confirmed, incomplete** | `dev.jsonl` is 668 rows and has zero overlap with eval. The exclusion set also contains `seen_ids.txt` (696 emails read during exploration, per `Method.tsx`) and every email over 12,000 characters (`MAX_CHARS`). |
| Gold = NIST rel 1/2; unjudged = not relevant | **Confirmed** | `trec.yaml` header; `eval.jsonl` labels carry only `responsive`; `Document.gold()` returns the negative label for any absent key. |
| Recall = TP/(TP+FN) on the positive stratum, Wilson 95% | **Partially corrected** | `_prf` computes recall as TP/(TP+FN) over **all gold positives in the sample**, not the `pos:` stratum alone. Per-topic denominators are 101–176 (e.g. George W. Bush: 100 own-stratum + 35 random + 41 from other topics' strata), and doc-level recall is over 1,095 positives (1,016 stratum + 79 random). Interval is `metrics.wilson(k, n, z=1.96)`, no continuity correction, no finite-population factor. |
| Precision = TP/(TP+FP) on the enriched sample, Wilson, not reweighted in the headline | **Confirmed** | `_ci(tp, tp+fp)` over the model's flagged set in the 3,016. No weighting by stratum or prevalence anywhere in `export.py`. `Method.tsx` states: "95% Wilson score. Recall over the gold-positive set, precision over the flagged set; every document carries a gold label." |
| Document-level headline pools 11 topics | **Confirmed** | `_score` builds one (pred-any, gold-any) pair per document; a document is responsive if positive on any of the 11 topics. Decision-level and per-issue metrics are exported alongside. |
| No bootstrap in the headline | **Confirmed** | Bootstraps in `export.py` are for the latency median (1,000 draws) only; the stability metric uses a bootstrap over decisions. Recall/precision intervals are analytic Wilson. |
| An `elusion` field exists | **Confirmed, unused** | `_prf` exports `elusion = FN/(FN+TN)` with a Wilson interval, but on the enriched sample it is not a collection elusion rate, and the site does not display it. |
| The site/article say the sample is enriched | **Confirmed** | `Method.tsx` "Sampling" row describes the three strata; `draft_v2.md` P31–P32 state the sample is enriched ("about a third ... responsive ... versus well under a tenth in the raw collection"). `Disclaimer.tsx` does not mention enrichment or that precision does not transfer. |
| Separate projection reweights with a 2,000-resample bootstrap | **Confirmed** | `precision_projection.md`: recall from all sample positives, FPR from the random stratum only, per-topic collection prevalence from `full.jsonl`; 2,000 percentile-bootstrap resamples (seed 20260925). Analysis only; not in `export.py` or on the site. |
| Matches Jev's real full-collection run within ~1 point | **Confirmed (1–1.5 pts)** | Jev Noul actual 286,326-email run: precision 51.4%, recall 83.0%, 42,532 flagged. Doc-level projection: 50.7% / 81.7% / 42,403. Pooled-per-topic projection: 49.9%. Laya zero-shot and the keyword baseline also match at doc level (10.0 vs 9.8; 11.1 vs 10.9). |

Two further facts worth having on the table: stratum sizes are **known exactly** (per-topic relevant counts from the qrels, 286,326 in-scope emails), which is the quantity Pickens says "matters. A lot"; and the gold labels were made by NIST assessors in 2016, with no knowledge of any of the models tested.

---

## 3. Alignment table

| # | Pickens point | Alignment | Why |
|---|---|---|---|
| P1 | Sample both the positive and the negative side; recall needs both | **Aligned (by analogy)** | We sample known positives (recall side) and both a hard-negative and a uniform random stratum (false-positive side); recall is not an elusion-only or control-set-only figure. Our strata are gold-defined rather than machine-defined, so this is the benchmark analogue, not the literal design. |
| P2 | Normalize sample counts to true stratum sizes | **Not aligned in the headline; aligned in the projection** | Headline precision (e.g. Jev 79.6%) is the raw enriched-sample ratio, exactly the "read it off the matrix" figure he objects to, and it overstates collection precision by 25–40 points for every model. `precision_projection.md` does the normalization he asks for and is validated against the real full-collection run, but it is not published. Recall is unaffected, as he himself notes ("Precision is the same"), except that pooled recall is weighted by sample composition, not by prevalence. |
| P3 | Post-stratify a simple random sample; do not stratify first | **Not aligned (by design)** | We stratified first, deliberately, because an SRS of 3,000 would hold ~4 positives for the rarest topic. This is the one point where his June position and ours are genuinely opposite; it is also the position his own May and podcast remarks cut against, and where the stratum sizes are known (as here) the two converge on the same estimator once reweighted. |
| P4 | Per-stratum intervals, combined | **Partially** | Headline: a single Wilson interval per quantity, no combination, and the precision interval is on the wrong population. Projection: recall and FPR are estimated per stratum and combined by bootstrap, which is a proper propagation rather than his best/worst corner. Neither reports the corner bound he uses. |
| P5 | Per-topic paired differences, not separate means | **Partially** | Every model is scored on the identical 3,016 documents, so comparisons are paired, and the site exposes per-issue recall/precision. But intervals are per-model marginal Wilson intervals; no paired-difference interval or per-topic difference histogram is reported. |
| P6 | Human judgment independent of the machine | **Aligned** | Gold predates the models by a decade; no model output touched a label. Criteria were refined once on a disjoint 668-email set. |
| P7 | Blind sampling of everything, not industry shortcuts | **Aligned on the blind part; diverges on "everything"** | No elusion-only, no control-set richness, no combining samples judged under different conditions. But precision as published is a number of the enriched sample, and a Pickens-style reader would treat "79.6% precision" without a stated richness as the kind of figure his 79%/100% remark warns about. |
| P8 | Open, checkable data | **Aligned** | Public collection and qrels; `findings.json` is regenerated from saved predictions; the projection script reproduces every published confusion matrix exactly (53 of 53 rows). Sampling seeds are in `build.py`. |
| P9 | Ben's paraphrase: sample positives and negatives, wind into one CI | **Partially** | Sampling matches. The "winding together" (prevalence-weighted precision with a propagated interval) exists only in the analysis file, and the reweighted precision column the plan promised was never built. |

One item Pickens would raise that is not on his list because he never saw our design: the **"unjudged = not relevant" convention**. Roughly nine in ten of the random-stratum false positives are emails NIST never judged for that topic. That makes recall exact against NIST but leaves collection precision (both the published lower bound and the projection) possibly pessimistic. He would call this "you can't validate on the sample only" in a different guise.

---

## 4. Gaps and what would close them

| Gap | What closes it | Effort |
|---|---|---|
| Headline precision is an enriched-sample ratio with no richness stated | Relabel it "precision on the evaluation sample (36% responsive)" everywhere; add a "precision at collection richness (9%)" toggle/column driven by random-stratum FPR × per-topic prevalence, bootstrap interval; F1 follows the toggle. The math and validation exist in `/tmp/prec_proj/project.py`; port into `export.py` as a `precision_at_richness` block and add the site control. | ~1 day |
| Pooled recall is sample-weighted, not prevalence-weighted | Same export block: report prevalence-weighted recall alongside (George W. Bush is 43% of relevant email; it moves zero-shot recall by ±4 points, fine-tuned Laya by −13). | included above |
| No elusion reported | Elusion is directly estimable on the random stratum (a uniform draw): misses among random emails the model did not flag ÷ random unflagged, Wilson interval, per topic and any-topic. For Jev, Laya and keyword the exact full-collection elusion is one line from `results/trec_full`. Display next to recall. | ~half day |
| No control-set-style richness cross-check | The random stratum *is* a 1,000-email control set: 79 positives → 7.9% [6.4–9.7] any-topic richness vs. 9.19% true (the small shortfall is the ≤1% exclusion of already-placed emails). Report it as a sanity check on the random stratum. | ~2 hours |
| Intervals are marginal, not paired | Bootstrap over documents (2,000 draws) for recall and precision *differences* between any two selected models; show the difference interval in the compare view and per-topic difference dots. | ~1 day |
| Prevalence sensitivity is in a file, not in front of the reader | Expose the 1/5/10/20% richness strip (or slider) from `precision_projection.md` §C on the TREC panel. | ~half day, after the export block |
| "Unjudged = not relevant" may be pessimistic | Have a reviewer read the unjudged random-stratum emails that Jev (~70) and one LLM (Luna ~200) flag; report how many are genuine NIST misses and bound the correction. | a few hours of review + ~2 hours to report |
| Disclaimer does not mention enrichment | One sentence in `Disclaimer.tsx` (Set-up section): the TREC sample is enriched; recall transfers to the collection, precision does not unless a richness is stated. | ~15 minutes |
| Nra_aliens stratum described as 18 | Where the article or site says 18 positives for Non-resident aliens, say 18 gold positives in the sample (16 drawn for the topic, 2 through the NRA stratum) and 18 relevant in the in-scope collection. | ~15 minutes |

Nothing above requires new model runs. Everything is computable from `results/trec/multi/*.jsonl`, `eval.jsonl`, `full.jsonl` and the qrels.

---

## 5. Suggested statement for the article's methods paragraph

> From the 286,326-email collection we drew a stratified evaluation sample of 3,016 whose labels were fixed by NIST assessors in 2016, independent of every model tested: 100 assessor-relevant emails per topic, 1,000 emails assessors had judged not relevant, and 1,000 drawn uniformly at random, so that recall is estimated on a known-relevant sample and false-positive behaviour on a sample that mirrors the collection. Recall and its 95% Wilson interval transfer directly to the collection; the precision we report first is precision on this enriched sample (36% responsive) and, because precision depends on richness, we also report precision at the collection's 9% richness, obtained by weighting each topic's recall and its false-positive rate on the random stratum by that topic's true prevalence with a bootstrap interval, and checked against a full-collection run of Jev that landed within 1.5 points.

Until the second half of that sentence is true on the site (the reweighted column and its interval), the honest version is the shorter one: *"the precision figures below are precision on the enriched evaluation sample and overstate what a reviewer would see on the collection; see the projection for the collection-richness figure."*
