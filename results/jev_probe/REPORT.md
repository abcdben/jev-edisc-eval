# Classifier-native contamination tests on Jev — results

Jev is a system under test. Its vendor states it is trained on synthetic data; every result below is reported as evidence consistent or inconsistent with that statement, never as proof.

Spend: OpenAI $5.14 (T1+T2 $3.88: predictions $3.76 of which the T1 v1 run $1.07 and the T1 v2 re-run of Mallinckrodt and Endo $0.51 (cap $3.00), edit generation $0.12; T3 paraphrases $0.18; T3/T4 predictions $1.08); Jev $0.152 (own key).

## T1 — Code-name swap, v2 with token-free contexts (case knowledge through the classifier)

Same templated document twice: a real matter token (an Enron financing vehicle, a Florida controversy, an opioid brand or subsidiary) vs a fictional token of the same shape; the request describes the conduct without naming the token. *Signal* pairs: a case-aware reader calls the real version relevant more often. *Decoy* pairs: the real token is a thing a case-aware reader knows is *not* what the request asks for (Azurix, FCAT, Ofirmev, Lidoderm…), so knowledge should lower the call. A system with no case knowledge gives the same call in both versions of either kind. Paired bootstrap CIs over pairs; exact McNemar on discordant pairs; Δp = mean difference in p(responsive).

**Correction (v2).** v2 (token-free contexts, 2026-10-04). v1 used the task-yaml contexts as sent to the study's systems; the Mallinckrodt and Endo contexts named the opioid brands and the non-opioid decoys, so a real token in the document could match the prompt rather than training knowledge. v2 replaces those two contexts with product-nameless versions (check C's) and asserts in code that no T1 token appears in any context or request. Enron and Jeb Bush prompts were already token-free and their v1 predictions are carried over unchanged; Mallinckrodt and Endo were re-run on all four systems. v1 is kept under t1_v1_confounded. The v1 table is kept below for the record.

| matter | model | signal: real | fake | Δ rate [95% CI] | McNemar p | Δp | decoy: real | fake | Δ rate | signal − decoy contrast [CI] |
|---|---|---|---|---|---|---|---|---|---|---|
| enron (n=28+12) | Jev | 57% | 39% | +17.9 pp [+3.6, +32.1] | 0.062 | +0.118 | 8% | 17% | -8.3 pp | +26.2 pp [+7.1, +50.0] |
| enron (n=28+12) | Luna | 96% | 82% | +14.3 pp [+0.0, +28.6] | 0.219 | +0.161 | 0% | 58% | -58.3 pp | +72.6 pp [+39.3, +104.8] |
| enron (n=28+12) | Terra | 89% | 57% | +32.1 pp [+14.3, +53.6] | 0.012 | +0.315 | 0% | 8% | -8.3 pp | +40.5 pp [+17.9, +66.7] |
| enron (n=28+12) | Sol | 100% | 93% | +7.1 pp [+0.0, +17.9] | 0.500 | +0.143 | 8% | 25% | -16.7 pp | +23.8 pp [+3.6, +48.8] |
| jebbush (n=23+8) | Jev | 78% | 43% | +34.8 pp [+13.0, +56.5] | 0.008 | +0.198 | 0% | 12% | -12.5 pp | +47.3 pp [+21.7, +81.0] |
| jebbush (n=23+8) | Luna | 83% | 39% | +43.5 pp [+21.7, +65.2] | 0.002 | +0.456 | 0% | 0% | +0.0 pp | +43.5 pp [+26.1, +65.2] |
| jebbush (n=23+8) | Terra | 91% | 57% | +34.8 pp [+17.4, +56.5] | 0.008 | +0.380 | 0% | 12% | -12.5 pp | +47.3 pp [+21.2, +80.4] |
| jebbush (n=23+8) | Sol | 91% | 70% | +21.7 pp [+4.3, +39.1] | 0.062 | +0.268 | 0% | 12% | -12.5 pp | +34.2 pp [+8.7, +67.9] |
| mnk (n=19+12) | Jev | 79% | 16% | +63.2 pp [+42.1, +84.2] | <0.001 | +0.345 | 33% | 8% | +25.0 pp | +38.2 pp [+5.7, +68.4] |
| mnk (n=19+12) | Luna | 79% | 42% | +36.8 pp [+15.8, +57.9] | 0.016 | +0.367 | 33% | 33% | +0.0 pp | +36.8 pp [-6.1, +78.5] |
| mnk (n=19+12) | Terra | 79% | 11% | +68.4 pp [+47.4, +89.5] | <0.001 | +0.651 | 0% | 0% | +0.0 pp | +68.4 pp [+47.4, +89.5] |
| mnk (n=19+12) | Sol | 84% | 53% | +31.6 pp [+10.5, +52.6] | 0.031 | +0.322 | 0% | 0% | +0.0 pp | +31.6 pp [+10.5, +52.6] |
| endo (n=19+12) | Jev | 89% | 79% | +10.5 pp [+0.0, +26.3] | 0.500 | +0.154 | 0% | 25% | -25.0 pp | +35.5 pp [+10.5, +65.8] |
| endo (n=19+12) | Luna | 100% | 84% | +15.8 pp [+0.0, +31.6] | 0.250 | +0.133 | 17% | 8% | +8.3 pp | +7.5 pp [-14.5, +31.6] |
| endo (n=19+12) | Terra | 89% | 11% | +78.9 pp [+57.9, +94.7] | <0.001 | +0.712 | 8% | 0% | +8.3 pp | +70.6 pp [+43.4, +91.7] |
| endo (n=19+12) | Sol | 95% | 16% | +78.9 pp [+57.9, +94.7] | <0.001 | +0.741 | 0% | 0% | +0.0 pp | +78.9 pp [+57.9, +94.7] |

Per token (rate real / fake; mean p real / fake), Jev:

- **enron**: Azurix 33/67% (p 0.49/0.48, n=3); Chewco 100/50% (p 0.82/0.40, n=4); Dabhol 0/0% (p 0.22/0.21, n=3); EnronOnline 0/0% (p 0.05/0.10, n=3); JEDI 33/33% (p 0.42/0.39, n=3); LJM2 80/40% (p 0.57/0.40, n=5); Marlin 0/0% (p 0.24/0.29, n=1); Osprey 50/50% (p 0.54/0.53, n=2); Portland General 0/0% (p 0.15/0.25, n=3); Raptor 67/50% (p 0.62/0.50, n=6); Talon 25/25% (p 0.38/0.40, n=4); Whitewing 33/33% (p 0.39/0.36, n=3)
- **jebbush**: Crosby 50/17% (p 0.41/0.36, n=6); Elián 100/80% (p 0.92/0.72, n=5); FCAT 0/0% (p 0.02/0.22, n=4); One Florida 67/33% (p 0.56/0.38, n=6); Schiavo 100/50% (p 0.96/0.59, n=6); Scripps 0/25% (p 0.21/0.30, n=4)
- **mnk**: Acthar 25/25% (p 0.19/0.33, n=4); Exalgo 100/0% (p 0.83/0.33, n=5); INOmax 0/0% (p 0.10/0.18, n=3); Methadose 75/0% (p 0.59/0.23, n=4); Ofirmev 60/0% (p 0.55/0.31, n=5); Roxicodone 100/0% (p 0.84/0.21, n=4); SpecGx 50/50% (p 0.48/0.47, n=6)
- **endo**: Aveed 0/33% (p 0.17/0.45, n=3); INTAC 67/67% (p 0.64/0.60, n=3); Lidoderm 0/25% (p 0.29/0.29, n=4); Opana 100/0% (p 0.96/0.32, n=1); Opana ER 100/89% (p 0.91/0.73, n=9); Percocet 100/100% (p 0.84/0.66, n=4); Qualitest 50/50% (p 0.47/0.54, n=2); Supprelin 0/33% (p 0.31/0.42, n=3); Voltaren Gel 0/0% (p 0.07/0.28, n=2)

### T1 v1 → v2: what changed and why

Prompt audit of v1 (every T1 token, real and fictional, searched in the context and all request fields with word boundaries): Enron — none; Jeb Bush — none (the context names Governor Jeb Bush and Florida, i.e. the matter, equally in both arms); Mallinckrodt — Exalgo, Roxicodone, Methadose, Ofirmev, INOmax, Acthar, all in the context; Endo — Opana ER / Opana, Qualitest, Lidoderm, Voltaren Gel, Aveed, Supprelin, all in the context. So on the two opioid matters the v1 context told every system which real tokens were opioids and which were the non-opioid decoys: a real token could match the prompt rather than training knowledge, in both the signal and the decoy direction. v2 contexts name the company and describe the conduct generically; the code now refuses to build a T1 task set containing any token. Enron and Jeb Bush rows are the v1 predictions carried over (identical prompts); Mallinckrodt and Endo were re-run on all four systems.

Signal-pair Δ (real − fictional relevance rate, pp [95% CI]) and Jev's decoy Δ, v1 vs v2:

| matter | version | Jev signal Δ | Luna | Terra | Sol | Jev decoy Δ (real / fake) | Jev signal − decoy [CI] |
|---|---|---|---|---|---|---|---|
| enron | v1 (contexts named products) | +17.9 pp [+3.6, +32.1] | +14.3 pp [+0.0, +28.6] | +32.1 pp [+14.3, +53.6] | +7.1 pp [+0.0, +17.9] | -8.3 pp (8% / 17%) | +26.2 pp [+7.1, +50.0] |
| enron | v2 (token-free) | +17.9 pp [+3.6, +32.1] | +14.3 pp [+0.0, +28.6] | +32.1 pp [+14.3, +53.6] | +7.1 pp [+0.0, +17.9] | -8.3 pp (8% / 17%) | +26.2 pp [+7.1, +50.0] |
| jebbush | v1 (contexts named products) | +34.8 pp [+13.0, +56.5] | +43.5 pp [+21.7, +65.2] | +34.8 pp [+17.4, +56.5] | +21.7 pp [+4.3, +39.1] | -12.5 pp (0% / 12%) | +47.3 pp [+21.7, +81.0] |
| jebbush | v2 (token-free) | +34.8 pp [+13.0, +56.5] | +43.5 pp [+21.7, +65.2] | +34.8 pp [+17.4, +56.5] | +21.7 pp [+4.3, +39.1] | -12.5 pp (0% / 12%) | +47.3 pp [+21.7, +81.0] |
| mnk | v1 (contexts named products) | +68.4 pp [+47.4, +89.5] | +42.1 pp [+21.1, +63.2] | +73.7 pp [+52.6, +89.5] | +52.6 pp [+31.6, +73.7] | -25.0 pp (0% / 25%) | +93.4 pp [+63.2, +125.9] |
| mnk | v2 (token-free) | +63.2 pp [+42.1, +84.2] | +36.8 pp [+15.8, +57.9] | +68.4 pp [+47.4, +89.5] | +31.6 pp [+10.5, +52.6] | +25.0 pp (33% / 8%) | +38.2 pp [+5.7, +68.4] |
| endo | v1 (contexts named products) | +36.8 pp [+15.8, +57.9] | +57.9 pp [+36.8, +78.9] | +73.7 pp [+52.6, +89.5] | +68.4 pp [+47.4, +89.5] | -8.3 pp (0% / 8%) | +45.2 pp [+21.1, +74.6] |
| endo | v2 (token-free) | +10.5 pp [+0.0, +26.3] | +15.8 pp [+0.0, +31.6] | +78.9 pp [+57.9, +94.7] | +78.9 pp [+57.9, +94.7] | -25.0 pp (0% / 25%) | +35.5 pp [+10.5, +65.8] |

**Before / after.** Jev's signal Δ on the re-run matters: mnk +68.4 pp → +63.2 pp [+42.1, +84.2]; endo +36.8 pp → +10.5 pp [+0.0, +26.3]. The LLMs moved too (Luna on Endo +57.9 pp → +15.8 pp; Terra and Sol barely), which is the signature of the confound: part of every system's v1 Endo effect was the prompt naming Opana ER. Jev's signal CI excludes zero on 3 of 4 matters in v2 (enron, jebbush, mnk) against 4 of 4 in v1; the signal − decoy contrast excludes zero on 4 of 4 in both versions. Jev's Δ is within the LLMs' range on 3 of 4 matters in v2 (below it on endo), the same count as v1. One decoy result reversed: on mnk Jev's decoy pairs now move *up* with the real token (33% vs 8%) — in v1 the context had said those products were non-opioids not at issue, so Jev's v1 'knowledge' that Ofirmev / INOmax / Acthar are not opioids was prompt-following; without the prompt it treats a real pharmaceutical brand in a marketing e-mail as more likely to be the opioid asked about than an invented one (Terra and Sol still call every decoy irrelevant; Luna calls a third relevant in both versions). Jev's Mallinckrodt effect is therefore partly 'recognises a real drug brand' rather than 'knows which brands are opioids'; the contrast still excludes zero.

## Bare-token check (FAS 140)

Header plus one sentence containing Raptor / LJM2 / Chewco (real) or Tercel / HLM2 / Brixco (fictional), 20 sentences × 3 tokens × 2 = 120 documents, Jev only. Criteria *as written* in `tasks/enron_j.yaml` (verified: they name FAS 140 / FAS 125 and no vehicle) vs the same criteria with one sentence added naming the vehicles (*named*). Context as written (never names the company) and, as a supplement, with the ablation's "The Company is Enron Corp." sentence (*enronctx*).

| criteria | context | real token: responsive rate | mean p | fictional token: responsive rate | mean p | paired Δ rate [CI] | Δp |
|---|---|---|---|---|---|---|---|
| aswritten | as written | 0% (0/60) [0, 6] | 0.108 | 0% (0/60) [0, 6] | 0.084 | +0.0 pp [+0.0, +0.0] | +0.024 |
| named | as written | 78% (47/60) [66, 87] | 0.567 | 0% (0/60) [0, 6] | 0.125 | +78.3 pp [+68.3, +88.3] | +0.442 |
| aswritten | names Enron | 0% (0/60) [0, 6] | 0.124 | 0% (0/60) [0, 6] | 0.093 | +0.0 pp [+0.0, +0.0] | +0.031 |
| named | names Enron | 83% (50/60) [72, 91] | 0.572 | 0% (0/60) [0, 6] | 0.124 | +83.3 pp [+73.3, +91.7] | +0.448 |

Per token, criteria as written: Raptor real 0% (p 0.08) vs fictional 0% (p 0.09); LJM2 real 0% (p 0.09) vs fictional 0% (p 0.08); Chewco real 0% (p 0.14) vs fictional 0% (p 0.09).

## T2 — Minimal-edit label flip (label / document memorisation)

Documents with published gold labels (Enron: TREC Legal 2010 learning-task qrels; Jeb Bush: TREC 2016 athome4 qrels), half relevant / half not, each given a 1–2 sentence edit by GPT-5.6 Luna that flips the true relevance and leaves everything else identical. Veridian (no public label; our own labels as the 'old' label) calibrates how often a system simply fails to notice the edit. *Label-following rate* = share of calls on the edited document equal to the OLD label; *reads edit* = equal to the NEW label. A memorised label would raise label-following on the public collections above the Veridian rate.

**enron**: 97 edited of 100 (2 infeasible, 1 failed to apply); median edit 324 chars in documents of median 1366 chars; second-model check (Terra reads the edited document): 40% (4/10) [17, 69] agree with the intended new label.

**jebbush**: 90 edited of 100 (1 infeasible, 9 failed to apply); median edit 422.5 chars in documents of median 1609.0 chars; second-model check (Terra reads the edited document): 50% (5/10) [24, 76] agree with the intended new label.

**veridian**: 94 edited of 100 (6 infeasible, 0 failed to apply); median edit 539.5 chars in documents of median 1263.5 chars; second-model check (Terra reads the edited document): 70% (7/10) [40, 89] agree with the intended new label.

| collection | model | acc. on originals | label-following (edited) | …given original call was right | reads edit | by direction: rel→not / not→rel label-following | mean abs Δp |
|---|---|---|---|---|---|---|---|
| enron | Jev | 72% (70/97) [63, 80] | 20% (19/97) [13, 29] | 26% (18/70) [17, 37] | 80% (78/97) [71, 87] | 24% (12/49) [15, 38] / 15% (7/48) [7, 27] | 0.429 |
| enron | Luna | 78% (76/97) [69, 85] | 31% (30/97) [23, 41] | 36% (27/76) [26, 47] | 69% (67/97) [59, 77] | 53% (26/49) [39, 66] / 8% (4/48) [3, 20] | 0.466 |
| enron | Terra | 74% (72/97) [65, 82] | 27% (26/97) [19, 36] | 32% (23/72) [22, 43] | 73% (71/97) [64, 81] | 35% (17/49) [23, 49] / 19% (9/48) [10, 32] | 0.514 |
| enron | Sol | 77% (75/97) [68, 85] | 31% (30/97) [23, 41] | 39% (29/75) [28, 50] | 69% (67/97) [59, 77] | 43% (21/49) [30, 57] / 19% (9/48) [10, 32] | 0.475 |
| jebbush | Jev | 84% (76/90) [76, 91] | 30% (27/90) [22, 40] | 36% (27/76) [26, 47] | 70% (63/90) [60, 78] | 47% (20/43) [33, 61] / 15% (7/47) [7, 28] | 0.425 |
| jebbush | Luna | 76% (68/90) [66, 83] | 32% (29/90) [23, 42] | 40% (27/68) [29, 52] | 68% (61/90) [58, 77] | 58% (25/43) [43, 72] / 9% (4/47) [3, 20] | 0.427 |
| jebbush | Terra | 81% (73/90) [72, 88] | 36% (32/90) [26, 46] | 42% (31/73) [32, 54] | 64% (58/90) [54, 74] | 56% (24/43) [41, 70] / 17% (8/47) [9, 30] | 0.477 |
| jebbush | Sol | 81% (73/90) [72, 88] | 32% (29/90) [23, 42] | 38% (28/73) [28, 50] | 68% (61/90) [58, 77] | 58% (25/43) [43, 72] / 9% (4/47) [3, 20] | 0.501 |
| veridian | Jev | 97% (91/94) [91, 99] | 46% (43/94) [36, 56] | 47% (43/91) [37, 57] | 54% (51/94) [44, 64] | 59% (26/44) [44, 72] / 34% (17/50) [22, 48] | 0.414 |
| veridian | Luna | 100% (94/94) [96, 100] | 41% (39/94) [32, 52] | 41% (39/94) [32, 52] | 59% (55/94) [48, 68] | 80% (35/44) [65, 89] / 8% (4/50) [3, 19] | 0.530 |
| veridian | Terra | 100% (94/94) [96, 100] | 43% (40/94) [33, 53] | 43% (40/94) [33, 53] | 57% (54/94) [47, 67] | 66% (29/44) [51, 78] / 22% (11/50) [13, 35] | 0.537 |
| veridian | Sol | 99% (93/94) [94, 100] | 50% (47/94) [40, 60] | 51% (47/93) [41, 60] | 50% (47/94) [40, 60] | 77% (34/44) [63, 87] / 26% (13/50) [16, 40] | 0.483 |

Label-following rate minus the Veridian rate (independent bootstrap): Jev on enron -26.2 pp [-38.8, -13.4]; Jev on jebbush -15.7 pp [-29.8, -1.6]; Luna on enron -10.6 pp [-24.0, +3.1]; Luna on jebbush -9.3 pp [-23.4, +5.2]; Terra on enron -15.7 pp [-29.3, -2.1]; Terra on jebbush -7.0 pp [-21.2, +7.3]; Sol on enron -19.1 pp [-32.7, -5.4]; Sol on jebbush -17.8 pp [-31.9, -3.6].

## T3 — Paraphrase sensitivity (document memorisation; Jev only, it returns p)

Original vs meaning-preserving Luna paraphrase (headers kept verbatim), ~100 documents per corpus, every request of the corpus's task set. Enron is in The Pile (presence likely), Endo is post-cutoff, Veridian is synthetic. Under 'no document memory' no corpus differs. |Δp| per (document, request); flip = call changes; bootstrap CIs by document; Mann-Whitney on |Δp| vs Veridian. Similarity = difflib ratio of original to paraphrase (lower = heavier paraphrase).

| corpus | docs | decisions | mean abs Δp [CI] | median | p90 | call-flip rate [CI] | docs with ≥1 flip | similarity (mean) | MW p vs Veridian |
|---|---|---|---|---|---|---|---|---|---|
| enron | 96 | 576 | 0.006 [0.004, 0.007] | 0.000 | 0.010 | 0.7% [0.2, 1.4] | 4% (4/96) [2, 10] | 0.72 | 0.746 |
| endo | 99 | 792 | 0.012 [0.010, 0.014] | 0.000 | 0.030 | 0.9% [0.3, 1.5] | 7% (7/99) [3, 14] | 0.67 | <0.001 |
| veridian | 100 | 1000 | 0.006 [0.005, 0.008] | 0.000 | 0.010 | 0.4% [0.1, 0.8] | 4% (4/100) [2, 10] | 0.58 | — |

By paraphrase intensity (similarity band: docs, mean |Δp|, flip rate): **enron** <0.60 26d 0.005/0.0%, 0.60-0.75 23d 0.004/0.7%, >=0.75 47d 0.007/1.1%; **endo** <0.60 34d 0.011/0.4%, 0.60-0.75 39d 0.012/1.6%, >=0.75 26d 0.012/0.5%; **veridian** <0.60 51d 0.008/0.6%, 0.60-0.75 35d 0.005/0.3%, >=0.75 14d 0.003/0.0%.

## T4 — Published vs unpublished labels (label contamination)

**Enron (Complaint J, six substantive requests).** Judged: 144 learning-task documents (balanced per topic × label, qrels gold). Unjudged: 144 EDRM v2 messages in no TREC Legal qrels, one length-matched twin per judged document (half drawn from documents with a lexical cue for the twin's topic, half at random), labelled by a two-model panel (Luna + Terra, unanimous only). Confound stated up front: judged documents were pool-selected by 2010 participants' systems and are not a random sample of the collection; our cue-enriched half imitates that selection and the random half does not.

| side | n | reference | Jev positive rate | reference positive rate | Jev accuracy / agreement | …on reference-positive | …on reference-negative | panel acc. vs qrels |
|---|---|---|---|---|---|---|---|---|
| judged | 144 | qrels | 33% (47/144) [26, 41] | 50% (72/144) [42, 58] | 74% (107/144) [67, 81] | 57% (41/72) [45, 68] | 92% (66/72) [83, 96] | — |
| judged | 138 | panel | 33% (47/144) [26, 41] | 36% (49/138) [28, 44] | 92% (127/138) [86, 95] | 86% (42/49) [73, 93] | 96% (85/89) [89, 98] | 78% (107/138) [70, 84] |
| unjudged | 139 | panel | 5% (7/144) [2, 10] | 6% (8/139) [3, 11] | 98% (136/139) [94, 99] | 62% (5/8) [31, 86] | 100% (131/131) [97, 100] | — |
| unjudged, cue-enriched half | 67 | panel | — | 12% (8/67) [6, 22] | 96% (64/67) [88, 98] | — | — | — |

- Jev accuracy on judged (vs qrels) minus agreement on unjudged (vs panel): -23.5 pp [-31.2, -15.9]
- agreement with the panel on both sides, judged minus unjudged: -5.8 pp [-10.9, -0.8]
- …on panel-responsive documents only: +23.2 pp (n 49 vs 8; 86% (42/49) [73, 93] vs 62% (5/8) [31, 86])
- …on panel-not responsive documents only: -4.5 pp (n 89 vs 131; 96% (85/89) [89, 98] vs 100% (131/131) [97, 100])

**Jeb Bush (TREC 2016, 11 topics; offline from the study's `results/trec` run).** 34,276 (document, topic) pairs on the 3,116-e-mail evaluation sample; 1,639 are in the athome4 qrels and 32,637 are not. Reference for unjudged pairs: 6-LLM panel (gpt-5.6-luna, gpt-5.6-terra, claude-sonnet-5, gemini-3.8-flash, claude-haiku-4.5, gemini-3.5-flash-lite), majority with at most one dissenter among the LLMs that answered; 32,331 pairs qualify. One length-matched unjudged twin per judged pair on the same topic (1,639). The base rates differ sharply (qrels pairs are mostly relevant, unjudged pairs almost all not), so the by-reference-label rows are the ones to read.

| side | n | reference | reference positive rate | Jev accuracy / agreement | …on reference-positive | …on reference-negative | panel acc. vs qrels |
|---|---|---|---|---|---|---|---|
| judged | 1639 | qrels | 70% (1155/1639) [68, 73] | 76% (1251/1639) [74, 78] | 76% (878/1155) [73, 78] | 77% (373/484) [73, 81] | — |
| judged | 1520 | panel | 77% (1174/1520) [75, 79] | 86% (1307/1520) [84, 88] | 82% (963/1174) [80, 84] | 99% (344/346) [98, 100] | 86% (1314/1520) [85, 88] |
| unjudged, matched | 1639 | panel | 1% (14/1639) [1, 1] | 100% (1634/1639) [99, 100] | 71% (10/14) [45, 88] | 100% (1624/1625) [100, 100] | — |

- accuracy on judged (vs qrels) minus agreement on matched unjudged (vs panel): -23.4 pp [-25.5, -21.4]
- agreement with the panel, judged minus unjudged: -13.7 pp [-15.5, -11.9]
- …on panel-positive pairs only: +10.6 pp [-11.2, +33.7] (n 1174 vs 14)
- …on panel-negative pairs only: -0.5 pp [-1.4, +0.1] (n 346 vs 1625)

## Reading

- **T1 (v2, token-free contexts).** Jev's real-vs-fictional difference in relevance rate excludes zero on 3 of 4 matters (enron, jebbush, mnk; endo +10.5 pp [+0.0, +26.3]). Decoy tokens move the other way on enron, jebbush, endo and *with* the real token on mnk; the signal − decoy contrast excludes zero on 4 of 4. This is evidence that the classifier's call depends on recognising real-world tokens — drug brands, Enron's vehicles, Florida controversies — i.e. that it carries matter / world knowledge, though on Mallinckrodt part of it is recognising a real drug brand rather than knowing which brands are opioids. It is **consistent with** either pre-training on public text **or** training on synthetic data generated by a model that has that knowledge; the test cannot separate the two. The GPT-5.6 rows show the same direction on every matter (an LLM is the positive comparison for 'knows the matter'); Jev's Δ is within the LLMs' range on 3 of 4 matters (below it on endo). It is **inconsistent with** a reading of the vendor claim under which the classifier has no real-world knowledge at all. v1 of this test overstated the opioid-matter effects because its contexts named the products (see the v1 → v2 note above).
- **Bare token.** Under the FAS 140 request as written, a header plus one sentence naming Raptor / LJM2 / Chewco is called responsive 0% of the time (fictional 0%; mean p 0.11 vs 0.08); once the criteria name the vehicles the real token is called responsive 78% vs 0%. The token alone does not trigger the as-written request, so the ablation's FAS 140 loss is not a bare-name effect; T1's Enron rows show the knowledge is used when the token sits in substantive context.
- **T2.** Jev's label-following rate on the public collections minus Veridian: enron -26.2 pp [-38.8, -13.4]; jebbush -15.7 pp [-29.8, -1.6]. Neither interval lies above zero: Jev stays with the old published label *less* often on Enron and Jeb Bush than it stays with our own never-published label on Veridian. Within each collection, where every system sees the identical edits, Jev's label-following is at or below the LLMs' (enron Jev 20% vs LLMs 27%–31%; jebbush Jev 30% vs LLMs 32%–36%). Caveat on the instrument: the second-model check confirms the intended flip on only enron 4/10, jebbush 5/10, veridian 7/10 sampled edits, so roughly half of the 'flips' did not fully change the document's true relevance; that dilutes label-following toward the correct old label for *every* system equally, so the within-collection Jev-vs-LLM comparison stands while the Veridian contrast (cleaner synthetic documents, harder to flip) should be read with that in mind. Result: **consistent with** no memorisation of the published judgments; no cell points the other way.
- **T3.** Mean |Δp| and call-flip rate under paraphrase: enron 0.006 / flip 0.7% (MW p 0.746); endo 0.012 / flip 0.9% (MW p <0.001); veridian 0.006 / flip 0.4%. All three are tiny (fewer than 1 call in 100 flips). Enron — the one corpus that is in public pre-training text — is indistinguishable from the synthetic floor (MW p 0.746, and at matched paraphrase intensity the heaviest-paraphrase band is 0.005 vs 0.008); the corpus that differs is Endo, which is post-cutoff and cannot have been memorised, so its larger shift reflects document style (dense pharma-marketing prose where wording carries the call), not memory. **Consistent with** no document memorisation; the one 'significant' difference is in the direction that memorisation cannot produce.
- **T4 Jeb Bush.** Jev's accuracy against the published qrels is 76%, *below* its agreement with the LLM panel on the same documents (86%); the panel itself agrees with the qrels 86%. Judged-minus-unjudged agreement with the panel is +10.6 pp [-11.2, +33.7] on panel-positive pairs (n 1174 vs 14) and -0.5 pp [-1.4, +0.1] on panel-negative pairs. The unjudged side has almost no panel-positives (the pool-selection confound in its purest form: relevant Jeb Bush e-mails were almost all judged), so the positive-side interval is wide and uninformative; the negative side shows no judged-set advantage. A system that had memorised the qrels would agree with the qrels more than with an LLM panel on judged documents; Jev does the reverse. **Consistent with** no label memorisation.
- **T4 Enron.** Same pattern: Jev agrees with the qrels on 74% of judged documents but with the Luna + Terra panel on 92% of them (the panel agrees with the qrels 78%); Jev calls 33% of judged documents responsive where the qrels say 50% — it misses the 2010 assessors' positives at the same places the LLMs do. Agreement with the panel, judged minus unjudged: -5.8 pp [-10.9, -0.8] overall, +23.2 pp on panel-positives (n 49 vs 8) and -4.5 pp on panel-negatives. The judged side is balanced by construction and the unjudged side (even its cue-enriched half) is mostly non-responsive, so the overall difference is a base-rate artefact. The panel-positive cell does lean toward a judged-set advantage, but it rests on 8 unjudged documents (62% (5/8) [31, 86]) and its interval covers the judged rate; the panel-negative cell shows none. Net: **weakly consistent with** no label memorisation — the Jeb Bush run, with 1,174 panel-positive judged pairs, is the better-powered version of the same test and the pool-selection confound is the binding limit on both.
- **Overall.** The classifier-native tests find that Jev *uses* real-world matter knowledge (T1 signal Δ excluding zero on 3 of 4 matters and the signal − decoy contrast on 4 of 4, with token-free prompts; bare token once the request names the vehicles) and find no sign that it *remembers* the benchmark's documents or labels (T2, T3, T4 — every cell at or below the LLM / synthetic comparison, and on judged documents Jev tracks the LLM panel more closely than the human qrels). Both halves are evidence, not proof: T1 is compatible with the vendor's statement if the synthetic training data was generated by a model that knows these matters, and T2–T4 bound memorisation only at these sample sizes and for these collections.
