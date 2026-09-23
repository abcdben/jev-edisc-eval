# TREC 2016 Total Recall (Jeb Bush email): criteria calibration log

## Why a calibration round

TREC issued each topic as a single sentence. Review teams do not work from a sentence: they draft a protocol,
run it against a sample, read the disagreements, and revise. We replicate that, with one rule that keeps the
evaluation honest: **every document read by a person or scored by a model during calibration is excluded from
the evaluation sample.**

- `data/trec/dev.jsonl`: 668 emails. Per topic, up to 30 gold positives spread round-robin over NIST's
  subtopic facets, and 30 judged-non-relevant emails picked one per TF-IDF k-means cluster (diverse hard
  negatives). Documents the analyst had already opened while exploring the collection were placed in dev first.
- `data/trec/seen_ids.txt`: 696 ids = dev ∪ every document opened during exploration. Excluded from eval and full.
- `data/trec/eval.jsonl`: 3,116 emails, disjoint from the above: 100 gold positives per topic (all 16 remaining
  for non-resident aliens), 1,000 judged-non-relevant "hard" negatives, 1,000 uniformly random emails.
  Positives per question after cross-labeling: 101–182 (nra_aliens 18). (Since 2026-09-23 the 100 emails
  of the `pos:eminent_domain` stratum are excluded at scoring time, so 3,016 emails are scored; see
  "Dropped topic" below. The file itself is unchanged.)
- Emails over 12,000 characters (~3k tokens) are excluded throughout, as for Mallinckrodt.

Gold is NIST's primary-assessor judgment (rel 1 or 2 → responsive; judged-non-relevant and unjudged →
not responsive, the TREC convention). `important` (rel 2) and facet codes are kept in `meta`.

## Protocol

1. **v0** (`criteria_v0.yaml`): positive/negative descriptions, structured criteria, sub-questions and a
   `literal` phrasing written from the official sentence alone, before any document was read for this purpose.
2. Run two cheap models on dev with v0: Jev (base, both arms) and Gemini 3.5 Flash-Lite (multi). ~$1.80.
3. Read the misses and false alarms that *both* models share, per topic.
4. **v1** (`criteria_v1.yaml`): revise. The official `rfp_text` is never changed.
5. Re-run the same models on dev with v1; compare on the 668 common documents.
6. Read v1's shared false alarms. Decide whether a v2 is warranted (it was not; see below). Freeze.

Criteria are identical for every model in the comparison, so calibration does not favour any contestant.
It does raise absolute scores relative to running the bare sentence; v0 numbers are kept for that reason.

## What the calibration round found

**The assessors judged at the level of the underlying issue, not the sentence.** This is the dominant
finding and drives nearly every v1 change:

| topic | official sentence says | gold also includes (from dev) |
|---|---|---|
| Recount 2000 | contested result of the 2000 election | 2003 removal of Broward's supervisor of elections, Katherine Harris's resignation, 2004 absentee-ballot talking points, felon rights restoration, election-ethics fights |
| Eminent domain | legality/morality of expropriating land for commercial development | CARL and Everglades state land acquisition, billboard-removal compensation veto |
| Bottled water | extraction of water for bottling | "Protect Florida's Springs" form letters on minimum flows and consumptive-use permits that never mention bottling; "please sign HB 1911" with no body |
| Rilya Wilson | her disappearance and its aftermath | adoption subsidies, DCF privatization, missing-children legislation, constituents' complaints about DCF handling of their grandchildren |
| Marketing | advertising/marketing by state institutions | Visit Florida, Team Florida economic-development mailings, energy-conference participation, meetings with Mexico's consul, the Governor's webcasts |
| Medicaid reform | efforts to reform Medicaid | NGA dual-eligible letters, Medicaid director hiring, nursing-home and pharmacy program changes, cuts |
| NRA (rifle) | the National Rifle Association | concealed-weapons and gun-show bills, a firearms manufacturer, gun-rights constituents with no NRA mention |
| Condominiums | condominium associations and the ombudsman | homeowners' associations, Cyber Citizens for Justice dispatches, bare "sign SB 1184" / "veto HB 391" notes |

v1 therefore (a) states the issue-level reading once in the shared `context` block and (b) describes each
topic's evident scope in its criteria. Movie Gallery was left alone (F1 ≈ 89 at v0).

**A gold conflict.** 34 of the NRA topic's 286 positives (facet 154, most graded "important") are Florida
bankers' letters about the IRS rule on reporting interest paid to non-resident aliens — the exact subject the
topic text declares "not relevant". The build flags these gray for `nra_rifle` (`GOLD_CONFLICT` in
`ediscovery_bench/trec/build.py`); NIST's label stands, and metrics are reported with and without them. The
criteria keep the official exclusion.

**Unrecoverable positives.** Some gold positives contain no usable text: "Governor Bush, Please sign HB1911",
"VETO HB 391", a CPA's letter about HB 391 (an accounting-deadline bill) judged relevant to condominiums. No
text-only classifier can find these; they cap achievable recall.

**Unjudged positives among the negatives.** Several v1 shared "false alarms" plainly meet the assessors' own
standard but were never judged for that topic (they were judged for a different topic and drawn as hard
negatives): DCF complaint letters and the SB 2046 foster-care bill for Rilya Wilson; Silver Springs and
Kirby Mine land purchases and a "regulatory taking without compensation" letter for eminent domain. Under
the TREC convention these count against precision.

## Dev results, v0 → v1 (668 common documents, threshold 0.5)

Pooled over 12 topics:

| model | arm | v0 P / R / F1 | v1 P / R / F1 |
|---|---|---|---|
| Jev (base) | multi | 68.1 / 58.6 / 63.0 | 67.9 / **74.8** / **71.2** |
| Jev (base) | single | 67.0 / 58.1 / 62.2 | 68.0 / **75.4** / **71.5** |
| Gemini 3.5 Flash-Lite | multi | 69.0 / 67.4 / 68.2 | 56.9 / **87.5** / 69.0 |

Per topic, F1 change v0→v1 (Jev multi / Jev single / Flash-Lite):

| topic | Jev multi | Jev single | Flash-Lite |
|---|---|---|---|
| gw_bush | +2 | +6 | −6 |
| movie_gallery | 0 | 0 | 0 |
| rilya_wilson | +13 | +18 | −1 (recall 50→93, precision 83→46) |
| faith_based | +1 | +4 | −3 |
| marketing | +1 | +2 | −4 |
| recount_2000 | +16 | +12 | −1 (recall 63→93) |
| condominiums | +2 | +1 | +3 |
| bottled_water | +39 | +39 | +30 |
| medicaid_reform | +1 | +2 | 0 |
| eminent_domain | +16 | +17 | −4 (recall 53→77) |
| nra_rifle | +18 | +19 | +16 |
| nra_aliens | +30 | +23 | +15 |

Dev negatives are all hard negatives (judged non-relevant to some topic), so dev precision understates
eval precision, where a third of the sample is uniformly random email. Recall is the signal here: the
issue-level criteria lifted both models' recall by 16–20 points; Flash-Lite converted the broader wording
into many more positives at 0.5, which the threshold sweep on eval will show is a calibration matter.

## Human ceiling

NIST had three alternate assessors re-judge a 150-document weighted sample per topic. Unweighted agreement
with the primary assessor, mean over the three alternates:

| topic | agree % | alt recall of primary positives | alt precision vs primary |
|---|---|---|---|
| gw_bush | 71 | 58 | 75 |
| movie_gallery | 99 | 100 | 96 |
| rilya_wilson | 85 | 58 | 88 |
| faith_based | 83 | 65 | 84 |
| marketing | 81 | 84 | 80 |
| recount_2000 | 87 | 61 | 100 |
| condominiums | 87 | 81 | 93 |
| bottled_water | 83 | 67 | 64 |
| medicaid_reform | 82 | 93 | 70 |
| eminent_domain | 46 | 44 | 5 |
| nra_rifle | 79 | 49 | 93 |
| nra_aliens | 85 | 57 | 49 |

A second human, given the same sentence, recovers roughly half to two-thirds of the primary assessor's
positives on most of these topics, and essentially disagrees with the primary on eminent domain. Model
recall against this gold should be read with that ceiling in mind; the model-vs-model comparison is
unaffected because every model faces the same gold.

With eminent domain dropped (below), the ceiling reads differently: on the eleven scored topics a second
assessor agrees with the primary on 71–99% of documents (mean 84%), recovers 49–100% of the primary's
positives (mean 70%), and is 49–100% precise against them (mean 81%). The one topic where the gold was
essentially a single assessor's idiosyncratic reading is gone; what remains is ordinary inter-assessor
disagreement, concentrated in recall (gw_bush 58%, nra_rifle 49%, rilya_wilson 58%, nra_aliens 57%).

## Dropped topic: 404 Eminent domain (2026-09-23)

Topic 404 (`eminent_domain`) was sampled, calibrated and run as the twelfth topic, and is dropped from
the study at scoring time. The reason is the row above: on the 29 documents of NIST's alternate-assessor
sample for 404 that the primary assessor had judged, the three alternates agreed with the primary on
27.6% / 10.3% / 6.9% of documents, and their precision against the primary's positives was
9.1% / 4.0% / 3.8% (the primary judged 3 of the 29 relevant; the alternates judged 22–26 relevant;
`prels.tr2016.alt{1,2,3}` vs `athome4.facetsandqrels`). The next-worst topic agrees at 71%. A label that
a second human reproduces this poorly measures the assessor, not the model, and the dev round already
showed the gold reaching far beyond the sentence (CARL and Everglades land buying, billboard compensation).

What changed, and what did not:

- `tasks/trec.yaml` has eleven questions. The v1 `eminent_domain` block is kept verbatim in
  `dropped_eminent_domain.yaml` (v0 in `criteria_v0.yaml`); `criteria_v1.yaml` is the historical v1 file.
- Nothing was re-run and nothing was deleted: `data/trec/{dev,eval,full}.jsonl` keep the 404 labels and
  eval's `pos:eminent_domain` stratum, and every prediction file keeps its `eminent_domain` rows.
  `ediscovery_bench/trec/build.py` still lists 404 in `TOPICS_2016` so the sampler reproduces the files.
- Scoring (`ediscovery_bench/scope.py`, used by `export.py`, `examples.py`, `writeup.py`, `cli.py`,
  `site/tools/build_cutoffs.py`): predictions for `eminent_domain` are ignored at decision, per-issue and
  any-issue document level; the 100 eval emails with `meta.stratum == "pos:eminent_domain"` are excluded
  (they entered the sample only as 404 positives and would otherwise be unintended extra hard negatives),
  so 3,016 of 3,116 emails are scored. Documents in the `hard_neg` and `random` strata that also carried a
  404 label lose that label (one such email). Dev and the full collection have no strata; there the 404
  question is simply not scored.
- Cost and latency per document are as measured. In the multi arm one call covered all 12 questions and
  the call happened; its cost is not scaled by 11/12. `n_decisions` counts the 11 scored questions. In the
  single arm each question was its own call, so the 404 calls are not charged either.
- `laya-ft-trec` was fine-tuned on `dev.jsonl` with the 404 labels present (one of twelve label columns);
  it is not retrained, it is just no longer scored on 404.
- The tables above are history and still say 12 topics.

## Decision

Frozen at v1. A v2 was considered after reading v1's shared false alarms; they were dominated by unjudged
likely-positives and "Bush"-name over-triggering that the text already addresses, so further edits would be
fitting to assessor noise rather than to the request. Evaluation runs use `tasks/trec.yaml` (= v1) on
`data/trec/eval.jsonl`; the full-collection System-1 run uses `data/trec/full.jsonl` with the same exclusions.
v0 is also run on eval for the System-1 models so the "bare sentence" number is available.
