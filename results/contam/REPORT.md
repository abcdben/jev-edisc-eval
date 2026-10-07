# Training-data contamination probe

Design: `design/06_contamination_probe.md`. Columns run from the real corpora through the two ends of the spectrum: **veridian** (synthetic, written 2026: the model can know nothing) is the negative control in every table, and the positive controls are **canon** (Federalist Papers / Constitution / Declaration; the framers as the cast; 20 Newsgroups as the benchmark) and **titanic** (the Kaggle train.csv: verbatim rows, and passenger -> Survived for label recall). Stars mark one-sided Mann-Whitney vs Veridian (verbatim) or two-sided binomial vs 50% (label recall): * p<0.05, ** p<0.01, *** p<0.001.

Models: `gpt-5.6-luna` (gpt-5.6-luna), `gpt-5.6-sol` (gpt-5.6-sol), `gpt-5.6-terra` (gpt-5.6-terra).  
Cost: gpt-5.6-luna $0.60, gpt-5.6-sol $11.43, gpt-5.6-terra $5.94; total $18.16.

## V. Verbatim memorisation: continue the document

Mean word-level LCS F1 between the model's ~60-word continuation and the true continuation (95% bootstrap CI). Then the share of documents where the continuation reproduces an exact run of ≥ 8 words of the original (`novel`: the run contains at least one 5-gram not present in the prompt, digits masked). Refusal rate in the last column set.

Verbatim pool quality: a window is a fair test of memorisation only if its continuation is text that only someone who had seen this collection could produce. Two filters are applied before any V statistic. (1) Rules (`ediscovery_bench/contam/boilerplate.py`): confidentiality / privilege disclaimers, signature and footer blocks, forwarded-message headers, unsubscribe footers, auto-replies and bounces, scanner notices, protective-order legends, degenerate repetition, key: value lists and tables, OCR garbage, openings with too little real content, and templates or duplicates recurring across the corpus (8-gram document frequency). (2) An LLM screen (`ediscovery_bench/contam/screen.py`, GPT-5.6 Luna, temperature 0) reads prefix + true continuation and assigns one of four classes; only `original_internal` windows are kept. It removes reproductions of public text inside the corpus (Federal Register notices, news and wire stories, newsletters, press releases, product labels, standard clauses) and low-information windows (header-only or garbled openings, continuations predictable from the prefix). The canon and Titanic anchors are public text by design and are exempt from the public-text class only. Of 572 candidate windows, 85 fail the rules and a further 54 fail the screen. Enron: 85 candidates, 60 kept (public text 15, boilerplate rules 10; 25 replacements); Jeb Bush: 77 candidates, 60 kept (boilerplate rules 13, public text 4; 17 replacements); Mallinckrodt: 99 candidates, 60 kept (boilerplate rules 27, public text 12; 39 replacements); Endo: 97 candidates, 60 kept (boilerplate rules 28, public text 9; 37 replacements); CUAD: 73 candidates, 60 kept (boilerplate rules 7, public text 5, low information 1; 13 replacements); Veridian: 61 candidates, 60 kept (public text 1; 1 replacements); canon: 60 candidates, 60 kept; Titanic: 20 candidates, 13 kept (low information 7). Excluded windows stay in the probe file and are scored for the record (`unfiltered` and `rules_only` blocks per corpus); per-item fields in `scored_items.jsonl`: `v_pool`, `v_exclude_reason`, `v_screen_class`, `v_screen_reason`, `boilerplate`, `boilerplate_reason`.

| model | enron LCS-F1 | jebbush LCS-F1 | mnk LCS-F1 | endo LCS-F1 | cuad LCS-F1 | veridian LCS-F1 | canon LCS-F1 | titanic LCS-F1 |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | 0.165 [0.150–0.180] | 0.154 [0.141–0.167] | 0.156 [0.141–0.171] | 0.164 [0.151–0.177] | 0.248 [0.230–0.267] *** | 0.152 [0.139–0.165] | 0.360 [0.304–0.424] *** | 0.479 [0.354–0.613] *** |
| gpt-5.6-sol | 0.170 [0.157–0.184] | 0.152 [0.142–0.164] | 0.161 [0.144–0.181] | 0.149 [0.135–0.165] | 0.295 [0.261–0.333] *** | 0.168 [0.155–0.182] | 0.939 [0.908–0.960] *** | 0.928 [0.907–0.951] *** |
| gpt-5.6-terra | 0.157 [0.144–0.170] | 0.160 [0.146–0.173] * | 0.149 [0.128–0.171] | 0.141 [0.122–0.159] | 0.268 [0.239–0.300] *** | 0.145 [0.132–0.160] | 0.625 [0.546–0.698] *** | 0.687 [0.583–0.774] *** |

| model | enron run≥8 / novel≥8 / run≥15 | jebbush run≥8 / novel≥8 / run≥15 | mnk run≥8 / novel≥8 / run≥15 | endo run≥8 / novel≥8 / run≥15 | cuad run≥8 / novel≥8 / run≥15 | veridian run≥8 / novel≥8 / run≥15 | canon run≥8 / novel≥8 / run≥15 | titanic run≥8 / novel≥8 / run≥15 |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | 2% / 2% / 0% | 2% / 2% / 0% | 2% / 2% / 0% | 2% / 0% / 0% | 14% / 12% / 0% | 0% / 0% / 0% | 32% / 32% / 25% | 46% / 46% / 31% |
| gpt-5.6-sol | 0% / 0% / 0% | 0% / 0% / 0% | 2% / 2% / 0% | 0% / 0% / 0% | 20% / 20% / 10% | 2% / 2% / 0% | 98% / 98% / 98% | 100% / 100% / 100% |
| gpt-5.6-terra | 0% / 0% / 0% | 0% / 0% / 0% | 3% / 3% / 0% | 2% / 0% / 0% | 15% / 15% / 5% | 0% / 0% / 0% | 77% / 77% / 67% | 92% / 92% / 77% |

| model | enron mean longest run (words) | jebbush mean longest run (words) | mnk mean longest run (words) | endo mean longest run (words) | cuad mean longest run (words) | veridian mean longest run (words) | canon mean longest run (words) | titanic mean longest run (words) | refusals (enron/jebbush/mnk/endo/cuad/veridian/canon/titanic) |
|---|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | 2.3 [2.0–2.6] | 2.3 [2.0–2.7] | 2.4 [2.1–2.9] | 2.5 [2.1–3.0] | 4.5 [3.9–5.2] *** | 2.3 [2.0–2.6] | 12.4 [8.5–17.1] *** | 11.8 [7.4–16.6] *** | 0%/2%/3%/15%/2%/25%/0%/0% |
| gpt-5.6-sol | 2.4 [2.1–2.7] | 2.3 [2.0–2.6] | 2.6 [2.2–3.0] | 2.1 [1.9–2.4] | 6.0 [4.7–7.5] *** | 2.5 [2.3–2.9] | 55.9 [53.2–57.9] *** | 56.9 [54.2–59.8] *** | 0%/0%/0%/0%/0%/0%/0%/0% |
| gpt-5.6-terra | 2.4 [2.1–2.8] | 2.3 [2.0–2.6] | 2.6 [2.2–3.1] | 2.3 [1.9–2.7] | 5.3 [4.3–6.4] *** | 2.2 [2.0–2.5] | 28.4 [22.9–33.8] *** | 30.9 [22.7–38.9] *** | 0%/0%/0%/0%/0%/0%/0%/0% |

## E1. Entity recall: "Who is {name}?"

Share of 30 header names per corpus (10 most frequent, 10 from ranks 11-40, 10 from the tail) whose free-text answer names the corpus's organisation (Wilson 95% CI), then the share answered UNKNOWN. Veridian names are fictional: a hit is impossible, and a non-UNKNOWN answer is a confabulation. Per-tier hit rates in the second table (top / mid / tail).

| model | enron hit (unknown) | jebbush hit (unknown) | mnk hit (unknown) | endo hit (unknown) | veridian hit (unknown) | canon hit (unknown) |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | 3% [1–17] (93%) | 3% [1–17] (93%) | 0% [-0–11] (100%) | 0% [-0–11] (93%) | 0% [0–12] (97%) | 97% [83–99] (3%) |
| gpt-5.6-sol | 13% [5–30] (83%) | 17% [7–34] (80%) | 0% [-0–11] (100%) | 0% [-0–11] (93%) | 0% [0–12] (97%) | 90% [74–97] (3%) |
| gpt-5.6-terra | 7% [2–21] (83%) | 7% [2–21] (80%) | 0% [-0–11] (83%) | 0% [-0–11] (77%) | 0% [0–12] (97%) | 97% [83–99] (0%) |

| model | enron top / mid / tail | jebbush top / mid / tail | mnk top / mid / tail | endo top / mid / tail | veridian top / mid / tail | canon top / mid / tail |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | 10% / 0% / 0% | 10% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 100% / 100% / 90% |
| gpt-5.6-sol | 10% / 30% / 0% | 30% / 10% / 10% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 100% / 80% / 90% |
| gpt-5.6-terra | 20% / 0% / 0% | 10% / 10% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 100% / 90% / 100% |

## E2. Entity recognition: "Was {name} affiliated with {org}?"

Each name is asked against its own organisation and the three others. Hit rate = yes to the true organisation; FA = yes to a foil; d' = z(hit) − z(FA). For Veridian names every yes is a false alarm (hit rate shown is yes-to-Veridian).

| model | enron hit / FA / d' | jebbush hit / FA / d' | mnk hit / FA / d' | endo hit / FA / d' | veridian hit / FA / d' | canon hit / FA / d' |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | 17% / 0% / 1.8 | 10% / 0% / 1.5 | 0% / 0% / 0.6 | 0% / 0% / 0.6 | 0% / 0% / 0.6 | 97% / 0% / 4.4 |
| gpt-5.6-sol | 33% / 0% / 2.3 | 37% / 3% / 1.5 | 30% / 1% / 1.6 | 0% / 7% / -0.7 | 0% / 0% / 0.6 | 100% / 0% / 4.9 |
| gpt-5.6-terra | 83% / 39% / 1.2 | 87% / 48% / 1.1 | 93% / 24% / 2.1 | 10% / 45% / -1.1 | 10% / 1% / 1.1 | 97% / 0% / 4.4 |

Hit rate by name tier (top / mid / tail):

| model | enron | jebbush | mnk | endo | veridian | canon |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | 30% / 20% / 0% | 20% / 10% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 100% / 90% / 100% |
| gpt-5.6-sol | 60% / 40% / 0% | 60% / 30% / 20% | 30% / 50% / 10% | 0% / 0% / 0% | 0% / 0% / 0% | 100% / 100% / 100% |
| gpt-5.6-terra | 90% / 80% / 80% | 70% / 100% / 90% | 100% / 90% / 90% | 0% / 0% / 30% | 10% / 0% / 22% | 100% / 90% / 100% |

## B. Benchmark knowledge

Fraction of the true topic titles / categories recovered from memory. `veridian`: whether the model described the fictional matter as if real (confabulated) rather than saying it did not know.

| model | TREC 2016 topics (34) | TREC Legal 2010 (4) | TREC Legal 2009 (7) | CUAD categories (41) | OIDA Mallinckrodt (4 facts) | OIDA Endo (4 facts) | Veridian confabulated? | 20 Newsgroups (20; positive control) |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | 0% (0/34) | 0% (0/4) | 0% (0/7) | 98% (40/41) | 75% (3/4) | 75% (3/4) | no | 100% (20/20) |
| gpt-5.6-sol | 0% (0/34) | 0% (0/4) | 14% (1/7) | 100% (41/41) | 100% (4/4) | 100% (4/4) | no | 100% (20/20) |
| gpt-5.6-terra | 0% (0/34) | 0% (0/4) | 0% (0/7) | 98% (40/41) | 75% (3/4) | 75% (3/4) | no | 100% (20/20) |

## L. Label recall: relevance judgment from document id alone

Accuracy on 100 (document, topic) pairs with no document text, balanced 50/50 within every topic so the topic named in the prompt carries no label information (`ceiling` = the best any topic-only rule could score on the sample); chance is 50%. Mallinckrodt and Veridian labels were never published and must sit at chance. `answered`: share that gave relevant / not_relevant rather than refusing.

| model | enron acc (ceiling; answered) | jebbush acc (ceiling; answered) | mnk acc (ceiling; answered) | endo acc (ceiling; answered) | veridian acc (ceiling; answered) | titanic acc (ceiling; answered) |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | 51% [41–61] (50%; 100/100) | 47% [38–57] (50%; 100/100) | 49% [39–59] (50%; 100/100) | 47% [38–57] (50%; 100/100) | 50% [40–60] (50%; 100/100) | 70% [60–78] *** (50%; 100/100) |
| gpt-5.6-sol | 49% [39–59] (50%; 100/100) | 50% [40–60] (50%; 100/100) | 48% [38–58] (50%; 100/100) | 51% [41–61] (50%; 100/100) | 50% [40–60] (50%; 100/100) | 84% [76–90] *** (50%; 100/100) |
| gpt-5.6-terra | 50% [40–60] (50%; 100/100) | 45% [36–55] (50%; 100/100) | 52% [42–62] (50%; 100/100) | 52% [42–62] (50%; 100/100) | 54% [44–63] (50%; 100/100) | 75% [66–82] *** (50%; 100/100) |

## M0. Matter identification: does a de-identified matter get mapped to the real one?

The TREC Legal complaints (Volteron = Enron; Bleak Horizon = Deepwater Horizon) and short de-identified sketches of the other matters. `hit` = the response names the real company / person / case. Veridian is fictional; `template` lists any real matter the model claimed it was modelled on.

| model | veridian | jebbush | enron | enron_k | mnk | endo | microsoft |
|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | named a real matter → Zimmer Biomet | hit | hit | hit | hit | hit | hit |
| gpt-5.6-sol | named a real matter → DePuy ASR / J&J; Zimmer Biomet; Stryker | hit | miss | hit | hit | hit | hit |
| gpt-5.6-terra | named a real matter → Zimmer Biomet | hit | hit | hit | hit | hit | hit |

## M1. Matter recall: the factual record from the matter's name alone

Share of a hand-written fact checklist (parties, allegations, people, events, outcome) recovered; `beyond` restricts to facts the study's task context does not already state. Veridian: whether the model said it did not know (correct) or confabulated.

| model | Veridian ApexHip MDL (synthetic) all / beyond | Jeb Bush governorship all / beyond | Enron all / beyond | Mallinckrodt opioid litigation all / beyond | Endo opioid litigation (held-out corpus) all / beyond | U.S. v. Microsoft all / beyond |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | said unknown | 50% / 43% (9/18) | 85% / 93% (17/20) | 48% / 62% (10/21) | 70% / 62% (14/20) | 88% / 88% (14/16) |
| gpt-5.6-sol | said unknown | 67% / 64% (12/18) | 90% / 100% (18/20) | 52% / 62% (11/21) | 70% / 69% (14/20) | 88% / 88% (14/16) |
| gpt-5.6-terra | said unknown | 44% / 36% (8/18) | 80% / 93% (16/20) | 43% / 54% (9/21) | 55% / 46% (11/20) | 94% / 94% (15/16) |

By category (parties / allegations / people / events / outcome):

| model | Jeb Bush governorship | Enron | Mallinckrodt opioid litigation | Endo opioid litigation (held-out corpus) | U.S. v. Microsoft |
|---|---|---|---|---|---|
| gpt-5.6-luna | – / 71% / 0% / 50% / 0% | 100% / 67% / 83% / 100% / 100% | 80% / 17% / 33% / 0% / 80% | 100% / 67% / 0% / 75% / 67% | 100% / 100% / 100% / 33% / 100% |
| gpt-5.6-sol | – / 86% / 0% / 75% / 0% | 100% / 67% / 100% / 100% / 100% | 80% / 17% / 33% / 50% / 80% | 67% / 67% / 100% / 75% / 67% | 100% / 100% / 100% / 33% / 100% |
| gpt-5.6-terra | – / 57% / 0% / 50% / 0% | 100% / 33% / 100% / 100% / 100% | 60% / 17% / 33% / 0% / 80% | 33% / 50% / 0% / 50% / 83% | 100% / 100% / 100% / 67% / 100% |

## The ladder: real matters at graded public exposure (M0 + M1)

Calibration rungs between the fictional floor and the Microsoft ceiling, in families matching the corpora, plus two post-cutoff controls. Footprint = English-Wikipedia article (12-month pageviews / language editions). M0: did the model name the matter from a de-identified sketch (● yes, ○ named something else, ? said it could not tell). M1: share of the fact checklist recovered, counting only facts the question did not itself state; `unk` = the answer opened by declining.

| matter | family | year | expected | footprint | gpt-5.6-luna M0 / M1 | gpt-5.6-sol M0 / M1 | gpt-5.6-terra M0 / M1 |
|---|---|---|---|---|---|---|---|
| Bhopal (1984) | landmark corporate disputes across the century | 1984 | high | Bhopal disaster: 1,099,557 views / 64 langs | ● / 100% | ● / 92% | ● / 100% |
| Theranos (2015-22) | landmark corporate disputes across the century | 2022 | high | Theranos: 522,841 views / 23 langs | ● / 93% | ● / 87% | ● / 87% |
| **Jeb Bush governorship** | e-mail and public records in public life | 2007 | study | Jeb Bush (biography, not the governorship): 487,743 views / 53 langs | ● / 50% | ● / 67% | ● / 44% |
| **Enron** | accounting & securities fraud | 2001 | study | Enron scandal: 474,558 views / 26 langs | ● / 84% | ○ / 90% | ● / 79% |
| Purdue Pharma / Sacklers | opioid litigation | 2019 | high | Purdue Pharma: 274,072 views / 14 langs | ● / 62% | ● / 54% | ● / 77% |
| Volkswagen Dieselgate (2015) | landmark corporate disputes across the century | 2015 | high | Volkswagen emissions scandal: 213,738 views / 28 langs | ● / 82% | ● / 88% | ● / 82% |
| Clinton e-mail server (2015-16) | e-mail and public records in public life | 2016 | high | Hillary Clinton email controversy: 143,756 views / 9 langs | ● / 93% | ● / 100% | ● / 87% |
| Texaco v. Pennzoil (1985-87) | landmark corporate disputes across the century | 1987 | mid | Texaco (company article (Texaco)): 136,702 views / 36 langs | ● / 69% | ● / 92% | ● / 69% |
| WorldCom (2002) | accounting & securities fraud | 2002 | high | WorldCom scandal: 130,303 views / 5 langs | ● / 86% | ● / 86% | ● / 93% |
| Teva / Actavis opioids (2022) | opioid litigation | 2022 | mid | Teva Pharmaceuticals (company article (Teva)): 115,631 views / 31 langs | ● / 83% | ● / 83% | ● / 92% |
| FTX (2022) | landmark corporate disputes across the century | 2022 | high | Bankruptcy of FTX: 111,135 views / 2 langs | ● / 76% | ● / 76% | ● / 82% |
| Sony Pictures hack (2014) | e-mail and public records in public life | 2014 | mid | 2014 Sony Pictures hack: 103,083 views / 15 langs | ● / 47% | ● / 73% | ● / 67% |
| JUUL Labs (2019-23) | consumer-product mass torts | 2022 | high | Juul (company article (Juul)): 98,572 views / 14 langs | ● / 67% | ● / 73% | ● / 60% |
| **U.S. v. Microsoft** | landmark corporate disputes across the century | 2001 | ceiling | United States v. Microsoft Corp.: 58,709 views / 7 langs | ● / 87% | ● / 87% | ● / 93% |
| Insys Therapeutics (2019) | opioid litigation | 2019 | mid | Insys Therapeutics: 48,973 views / 0 langs | ● / 79% | ● / 93% | ● / 93% |
| **Mallinckrodt opioid litigation** | opioid litigation | 2020 | study | Mallinckrodt (company article): 36,785 views / 7 langs | ● / 39% | ● / 44% | ● / 33% |
| Bridgegate (2013) | e-mail and public records in public life | 2013 | mid | Fort Lee lane closure scandal: 34,226 views / 2 langs | ● / 92% | ● / 100% | ● / 92% |
| Bair Hugger warming MDL | medical-device mass torts | 2019 | low | Bair Hugger: 25,080 views / 1 langs | ● / 62% | ● / 77% | ● / 69% |
| DePuy ASR hip (2010) | medical-device mass torts | 2010 | mid | DePuy Synthes (company article (DePuy Synthes)): 22,569 views / 3 langs | ● / 46% | ● / 82% | ● / 64% |
| HealthSouth (2003) | accounting & securities fraud | 2003 | mid | Encompass Health (company article (Encompass Health)): 19,992 views / 2 langs | ● / 77% | ● / 92% | ● / 77% |
| Dalkon Shield (1970s-80s) | medical-device mass torts | 1985 | mid | Dalkon Shield: 18,047 views / 3 langs | ● / 75% | ● / 92% | ● / 75% |
| **Endo opioid litigation (held-out corpus)** | opioid litigation | 2022 | study | Endo International (company article): 13,340 views / 5 langs | ● / 62% | ● / 62% | ● / 44% |
| Peregrine Systems (2002) | accounting & securities fraud | 2002 | low | Peregrine Systems: 10,368 views / 2 langs | ● / 67% | ● / 75% | ● / 33% |
| McKesson & Robbins (1938) | accounting & securities fraud | 1938 | low | McKesson and Robbins scandal: 4,472 views / 0 langs | ● / 62% | ● / 69% | ● / 54% |
| Equity Funding (1973) | accounting & securities fraud | 1973 | low | Equity Funding Corporation of America: 3,140 views / 0 langs | ● / 46% | ● / 62% | ● / 62% |
| **Big Thorium (Relativity demo)** | public-procurement bribery | 2024 | public-invented | no article | ? / 0% unk | ○ / 0% unk | ○ / 0% unk |
| 3M Combat Arms earplugs (2019-23) | medical-device mass torts | 2023 | mid | no article | ● / 75% | ● / 100% | ● / 100% |
| Rochester Drug Co-operative (2019) | opioid litigation | 2019 | low | no article | ● / 40% | ● / 90% | ● / 80% |
| Meyer Global Mgmt (SEC, Sept 2026) | post-cutoff controls | 2026 | none | no article | ? / 0% unk | ? / 0% unk | ○ / 0% unk |
| Near Intelligence (2023 / SEC 2026) | post-cutoff controls | 2026 | none | no article | ● / 22% unk | ● / 0% unk | ● / 0% unk |
| **Veridian ApexHip MDL (synthetic)** | medical-device mass torts | 2026 | floor | fictional | ○ / – unk | ○ / – unk | ○ / – unk |

Spearman rank correlation, log pageviews vs M1 share, over matters with an article: gpt-5.6-luna: ρ = +0.48 (n = 25, p = 0.0153); gpt-5.6-sol: ρ = +0.25 (n = 25, p = 0.2238); gpt-5.6-terra: ρ = +0.48 (n = 25, p = 0.0143)

## M2. Evidence prior: what the model expects to find before seeing a document

25 expected terms per request (people, organisations, code names, products, places, periods, keywords). Terms already in the matter context or request are discarded (`novel`). Of the novel *named* terms: `grounded` = appears in ≥ 2 judged documents; `discriminative` = grounded and at least twice as frequent among responsive documents as overall (lift ≥ 2). Named terms are the case-knowledge signal; generic keywords are shown for comparison.

| model | set | requests | novel named / request | grounded (named) | discriminative (named) | grounded (generic) | discriminative (generic) | discriminative named terms (total) |
|---|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | Veridian (synthetic) | 10 | 0.2 | 50% | 0% | 37% | 32% | 0 |
| gpt-5.6-luna | Jeb Bush | 11 | 11.2 | 29% | 13% | 4% | 3% | 16 |
| gpt-5.6-luna | Enron · Complaint K topics (oil spill; not Enron's story) | 3 | 2.7 | 75% | 38% | 21% | 10% | 3 |
| gpt-5.6-luna | Enron · Complaint J topics (the real scandal; pseudonym) | 7 | 0.4 | 100% | 25% | 49% | 20% | 1 |
| gpt-5.6-luna | Enron · Complaint J topics (company named) | 7 | 5.9 | 88% | 40% | 49% | 29% | 12 |
| gpt-5.6-luna | Mallinckrodt | 8 | 0.8 | 50% | 30% | 32% | 15% | 2 |
| gpt-5.6-luna | Endo (held-out) | 8 | 0.6 | 100% | 40% | 39% | 21% | 2 |
| gpt-5.6-sol | Veridian (synthetic) | 10 | 1.8 | 61% | 13% | 26% | 23% | 3 |
| gpt-5.6-sol | Jeb Bush | 11 | 14.2 | 26% | 11% | 1% | 1% | 19 |
| gpt-5.6-sol | Enron · Complaint K topics (oil spill; not Enron's story) | 3 | 2.7 | 25% | 12% | 17% | 6% | 1 |
| gpt-5.6-sol | Enron · Complaint J topics (the real scandal; pseudonym) | 7 | 0.4 | 100% | 0% | 52% | 24% | 0 |
| gpt-5.6-sol | Enron · Complaint J topics (company named) | 7 | 14.7 | 81% | 46% | 35% | 25% | 46 |
| gpt-5.6-sol | Mallinckrodt | 8 | 3.4 | 61% | 13% | 36% | 16% | 4 |
| gpt-5.6-sol | Endo (held-out) | 8 | 3.1 | 65% | 21% | 28% | 14% | 6 |
| gpt-5.6-terra | Veridian (synthetic) | 10 | 0.6 | 100% | 20% | 67% | 48% | 2 |
| gpt-5.6-terra | Jeb Bush | 11 | 13.5 | 32% | 13% | 8% | 4% | 18 |
| gpt-5.6-terra | Enron · Complaint K topics (oil spill; not Enron's story) | 3 | 0.0 | – | – | 48% | 24% | 0 |
| gpt-5.6-terra | Enron · Complaint J topics (the real scandal; pseudonym) | 7 | 1.1 | 86% | 14% | 52% | 26% | 2 |
| gpt-5.6-terra | Enron · Complaint J topics (company named) | 7 | 10.3 | 86% | 32% | 51% | 30% | 24 |
| gpt-5.6-terra | Mallinckrodt | 8 | 2.8 | 84% | 6% | 51% | 38% | 1 |
| gpt-5.6-terra | Endo (held-out) | 8 | 1.5 | 55% | 45% | 50% | 34% | 6 |

## M3. Metadata-only relevance: does knowing the people move the call?

Balanced responsive / non-responsive e-mails per request; the model sees the matter context, the request and only the header metadata. `headers` = Date, From, To, Cc, Subject; `subject` = Date and Subject only. `Δ people` = headers − subject (paired bootstrap 95% CI): the accuracy that seeing who sent and received the e-mail adds. `lexical` = a request-title keyword match on the subject line. Chance is 50%.

Classifier rows (`jev`) saw the same context, request and header block through the classifier API (Noul question, no criteria). Their vendor states they are not pre-trained on public text; that is a claim under test here, and a flat Δ people is consistent with it without establishing it, since the LLMs show the same flatness.

| model | set | n | headers | subject | Δ people | lexical | fixed / broken by people |
|---|---|---|---|---|---|---|---|
| gpt-5.6-luna | Veridian (synthetic) | 400 | 90% [86–92] *** | 90% [87–93] *** | -0% [-2%, 1%] | 62% | 5 / 7 |
| gpt-5.6-luna | Jeb Bush | 330 | 68% [63–73] *** | 69% [64–74] *** | -1% [-4%, 3%] | 57% | 13 / 15 |
| gpt-5.6-luna | Enron · Complaint K topics (oil spill; not Enron's story) | 120 | 80% [72–86] *** | 75% [67–82] *** | +5% [0%, 11%] | 52% | 8 / 2 |
| gpt-5.6-luna | Enron · Complaint J topics (the real scandal; pseudonym) | 280 | 81% [76–85] *** | 80% [75–84] *** | +1% [-3%, 4%] | 62% | 15 / 13 |
| gpt-5.6-luna | Mallinckrodt | 320 | 74% [69–79] *** | 74% [69–79] *** | -0% [-4%, 3%] | 64% | 16 / 17 |
| gpt-5.6-luna | Endo (held-out) | 304 | 73% [67–77] *** | 70% [64–75] *** | +3% [-1%, 7%] | 60% | 21 / 12 |
| gpt-5.6-sol | Veridian (synthetic) | 400 | 92% [89–95] *** | 92% [89–95] *** | 0% [-2%, 2%] | 62% | 6 / 6 |
| gpt-5.6-sol | Jeb Bush | 330 | 75% [70–80] *** | 72% [67–77] *** | +3% [1%, 5%] | 57% | 10 / 1 |
| gpt-5.6-sol | Enron · Complaint K topics (oil spill; not Enron's story) | 120 | 69% [60–77] *** | 72% [63–79] *** | -2% [-8%, 3%] | 52% | 5 / 8 |
| gpt-5.6-sol | Enron · Complaint J topics (the real scandal; pseudonym) | 280 | 86% [81–89] *** | 83% [78–87] *** | +2% [0%, 5%] | 62% | 10 / 3 |
| gpt-5.6-sol | Mallinckrodt | 320 | 78% [73–82] *** | 79% [74–83] *** | -1% [-3%, 2%] | 64% | 9 / 11 |
| gpt-5.6-sol | Endo (held-out) | 304 | 75% [70–80] *** | 76% [71–80] *** | -1% [-3%, 2%] | 60% | 9 / 11 |
| gpt-5.6-terra | Veridian (synthetic) | 400 | 94% [91–96] *** | 92% [89–95] *** | +1% [-0%, 3%] | 62% | 9 / 4 |
| gpt-5.6-terra | Jeb Bush | 330 | 72% [66–76] *** | 70% [65–75] *** | +1% [-2%, 4%] | 57% | 12 / 8 |
| gpt-5.6-terra | Enron · Complaint K topics (oil spill; not Enron's story) | 120 | 72% [64–80] *** | 68% [59–75] *** | +5% [-2%, 11%] | 52% | 11 / 5 |
| gpt-5.6-terra | Enron · Complaint J topics (the real scandal; pseudonym) | 280 | 81% [76–85] *** | 82% [77–86] *** | -1% [-4%, 3%] | 62% | 12 / 14 |
| gpt-5.6-terra | Mallinckrodt | 320 | 76% [71–81] *** | 76% [71–80] *** | +0% [-3%, 3%] | 64% | 14 / 13 |
| gpt-5.6-terra | Endo (held-out) | 304 | 76% [71–81] *** | 74% [68–78] *** | +3% [-0%, 6%] | 60% | 15 / 7 |
| jev | Veridian (synthetic) | 400 | 76% [71–80] *** | 75% [71–79] *** | +0% [-2%, 3%] | 62% | 10 / 8 |
| jev | Jeb Bush | 330 | 57% [52–62] ** | 57% [51–62] * | +1% [-1%, 2%] | 57% | 5 / 3 |
| jev | Enron · Complaint K topics (oil spill; not Enron's story) | 120 | 66% [57–74] *** | 62% [53–70] * | +4% [-3%, 12%] | 52% | 12 / 7 |
| jev | Enron · Complaint J topics (the real scandal; pseudonym) | 280 | 70% [64–75] *** | 70% [64–75] *** | +0% [-4%, 5%] | 62% | 18 / 17 |
| jev | Mallinckrodt | 320 | 65% [60–70] *** | 66% [61–71] *** | -1% [-5%, 2%] | 64% | 12 / 16 |
| jev | Endo (held-out) | 304 | 62% [56–67] *** | 61% [55–66] *** | +1% [-3%, 5%] | 60% | 16 / 14 |

## Appendix: benchmark-knowledge answers

<details><summary><code>gpt-5.6-luna</code> — trec2016</summary>

```
I don’t know the **athome4** topic list reliably enough to provide topic numbers and titles from memory. I would risk inventing or misattributing entries.

The authoritative source should be the TREC 2016 Total Recall track materials—particularly the **athome4 topic file** or the track’s overview paper—available through the NIST TREC proceedings/web archive.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — legal10</summary>

```
The four TREC 2010 Legal Track Interactive topics were:

- **Topic 301 — Enron–California energy crisis:** documents concerning Enron’s involvement in, or knowledge of, the California electricity crisis and related energy-market manipulation.
- **Topic 302 — Enron–Arthur Andersen:** documents concerning Enron’s relationship with Arthur Andersen, including auditing, accounting, and the destruction or alteration of records.
- **Topic 303 — Enron–broadband:** documents concerning Enron’s broadband business and related activities, including its broadband strategy, investments, and operations.
- **Topic 304 — Enron–employee compensation:** documents concerning Enron employee compensation, including bonuses, incentive plans, and related compensation practices.

These are paraphrased subject descriptions; the official requests for production contain the precise scope and wording.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — legal09</summary>

```
The TREC 2009 Legal Track Interactive topics were:

- **Topic 201 — Enron–California energy crisis:** Documents concerning Enron’s involvement in, and knowledge of, the California electricity crisis.
- **Topic 202 — Enron–California energy crisis / price manipulation:** Documents concerning Enron’s manipulation of California electricity prices or markets.
- **Topic 203 — Enron–California energy crisis / FERC:** Documents concerning Enron’s dealings with or representations to the Federal Energy Regulatory Commission.
- **Topic 204 — Enron–California energy crisis / government investigations:** Documents concerning investigations by government agencies into Enron’s California energy activities.
- **Topic 205 — Enron–California energy crisis / communications with California officials:** Documents concerning Enron’s communications with California state officials about the energy crisis.
- **Topic 206 — Enron–California energy crisis / trading strategies:** Documents concerning Enron’s trading strategies or schemes used in California electricity markets.
- **Topic 207 — Enron–California energy crisis / market conditions and outages:** Documents concerning California electricity-market conditions, shortages, or outages relevant to Enron’s conduct.

I should flag that I do not have the official topic statements in front of me, and the above paraphrases may conflate closely related requests.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — cuad — recovered 40/41: Document Name, Parties, Agreement Date, Effective Date, Expiration Date, Renewal Term, Notice Period to Terminate Renewal, Governing Law, Most Favored Nation, Non-Compete, Exclusivity, No-Solicit of Customers, No-Solicit of Employees, Non-Disparagement, Termination for Convenience, ROFR/ROFO/ROFN, Change of Control, Anti-Assignment, Revenue/Profit Sharing, Price Restrictions, Minimum Commitment, Volume Restriction, IP Ownership Assignment, Joint IP Ownership, License Grant, Non-Transferable License, Affiliate License-Licensor, Affiliate License-Licensee, Unlimited/All-You-Can-Eat License, Irrevocable or Perpetual License, Source Code Escrow, Post-Termination Services, Audit Rights, Uncapped Liability, Cap on Liability, Liquidated Damages, Warranty Duration, Insurance, Covenant Not to Sue, Third Party Beneficiary</summary>

```
CUAD annotates **41 clause categories**:

1. Document Name  
2. Parties  
3. Agreement Date  
4. Effective Date  
5. Expiration Date  
6. Renewal Term  
7. Notice Period To Terminate Renewal  
8. Governing Law  
9. Most Favored Nation  
10. Non-Compete  
11. Exclusivity  
12. No-Solicit Of Customers  
13. No-Solicit Of Employees  
14. Non-Disparagement  
15. Termination For Convenience  
16. Rofr/Rofo/Rofn  
17. Change Of Control  
18. Anti-Assignment  
19. Revenue/Profit Sharing  
20. Price Restrictions  
21. Minimum Commitment  
22. Volume Restriction  
23. IP Ownership Assignment  
24. Joint IP Ownership  
25. License Grant  
26. Non-Transferable License  
27. Affiliate License-Licensor  
28. Affiliate License-Licensee  
29. Unlimited/All-You-Can-Eat-License  
30. Irrevocable Or Perpetual License  
31. Source Code Escrow  
32. Post-Termination Services  
33. Audit Rights  
34. Uncapped Liability  
35. Cap On Liability  
36. Liquidated Damages  
37. Warranty Duration  
38. Insurance  
39. Covenant Not To Sue  
40. Third Party Beneficiary  
41. Performance Guarantee
```
</details>

<details><summary><code>gpt-5.6-luna</code> — oida_mnk — recovered 3/4: UCSF, opioid litigation, industry documents library</summary>

```
The **Mallinckrodt document collection** is a set of internal records from **Mallinckrodt Pharmaceuticals**, a major opioid manufacturer and distributor, made available through the **Opioid Industry Documents Archive (OIDA)**. It includes materials such as company correspondence, litigation-related records, regulatory documents, and other files concerning Mallinckrodt’s opioid business.

- **Host:** The archive is hosted by the **University of California, San Francisco (UCSF) Library**, through its Industry Documents Library.
- **Source of the documents:** They came primarily from **opioid litigation and related legal discovery**, including documents produced by Mallinckrodt and filed or collected in lawsuits and investigations.
- **When made public:** The collection became publicly available **around 2020–2021**, as opioid-litigation records were being processed and added to OIDA.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — oida_endo — recovered 3/4: UCSF, Endo bankruptcy / settlement, industry documents library</summary>

```
The **Endo document collection** is a set of internal records from **Endo International plc**, the pharmaceutical company that manufactured and marketed opioid pain medicines, including **Opana (oxymorphone)**.

The **Opioid Industry Documents Archive (OIDA)** is hosted by the **University of California, San Francisco (UCSF) Library**, in partnership with the **University of California**. The Endo records came primarily from **litigation and government investigations concerning Endo’s opioid marketing and sales practices**, rather than from a voluntary company release.

They were made publicly available in the archive **around 2021–2022** (with additions and updates over time).
```
</details>

<details><summary><code>gpt-5.6-luna</code> — veridian</summary>

```
I’m not aware of a documented company, product, or case called **“Veridian Orthopedics”** or **“ApexHip”** in the public orthopedic-device litigation and regulatory record. I therefore can’t reliably describe it as a real matter.

It may be:

- a fictional or synthetic example used in a dataset,
- a misspelling or conflation of another orthopedic-device company/product, or
- a very obscure/private matter not represented in the sources I know.

I would not want to invent details about the company, hip product, or alleged litigation/regulatory action. If you can provide a source, docket number, jurisdiction, or alternate spelling, I can help identify it.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — newsgroups20 — recovered 20/20: alt.atheism, comp.graphics, comp.os.ms-windows.misc, comp.sys.ibm.pc.hardware, comp.sys.mac.hardware, comp.windows.x, misc.forsale, rec.autos, rec.motorcycles, rec.sport.baseball, rec.sport.hockey, sci.crypt, sci.electronics, sci.med, sci.space, soc.religion.christian, talk.politics.guns, talk.politics.mideast, talk.politics.misc, talk.religion.misc</summary>

```
The 20 Newsgroups dataset contains these categories:

1. `alt.atheism`
2. `comp.graphics`
3. `comp.os.ms-windows.misc`
4. `comp.sys.ibm.pc.hardware`
5. `comp.sys.mac.hardware`
6. `comp.windows.x`
7. `misc.forsale`
8. `rec.autos`
9. `rec.motorcycles`
10. `rec.sport.baseball`
11. `rec.sport.hockey`
12. `sci.crypt`
13. `sci.electronics`
14. `sci.med`
15. `sci.space`
16. `soc.religion.christian`
17. `talk.politics.guns`
18. `talk.politics.mideast`
19. `talk.politics.misc`
20. `talk.religion.misc`
```
</details>

<details><summary><code>gpt-5.6-sol</code> — trec2016</summary>

```
I can’t reliably recall the athome4 topic-number/title list from memory, and I don’t want to invent entries. The collection’s topics were requests derived from Jeb Bush’s gubernatorial e-mail archive, but I would need the TREC 2016 Total Recall topic file or track overview to enumerate them accurately.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — legal10</summary>

```
The TREC 2010 Legal Track Interactive topics were:

- **301 — Employee performance reviews:** Produce documents concerning employee performance evaluations or reviews.
- **302 — Energy-market manipulation:** Produce documents concerning manipulation of energy markets, including strategies or practices affecting electricity prices.
- **303 — Enron’s California energy activities:** Produce documents concerning Enron’s role in, and communications about, the California electricity/energy crisis.
- **304 — Document destruction:** Produce documents concerning the destruction, deletion, shredding, or concealment of Enron-related records, including Arthur Andersen’s conduct.

I’m not fully confident in the exact official wording; these are subject-level paraphrases of the four production requests.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — legal09 — recovered 1/7: 204 Document retention/destruction</summary>

```
The seven TREC 2009 Legal Track Interactive topics were:

- **201 — Employee performance evaluations:** Requests for documents concerning employee reviews, appraisals, rankings, or evaluations.
- **202 — Accounting irregularities:** Requests concerning improper accounting practices, manipulation of financial results, or related concerns.
- **203 — California energy crisis:** Requests concerning Enron’s role in, or communications about, the California electricity/energy crisis and market manipulation.
- **204 — Document destruction:** Requests concerning destruction, deletion, shredding, or concealment of documents or electronic records.
- **205 — Insider trading:** Requests concerning trading in Enron securities by insiders, including knowledge of nonpublic adverse information.
- **206 — Special-purpose entities/partnerships:** Requests concerning Enron’s off-balance-sheet entities and related-party partnerships, such as the LJM or Raptor entities.
- **207 — Political influence:** Requests concerning political contributions, lobbying, or contacts intended to influence government officials or energy policy.

I cannot verify that these paraphrases match the official topic wording, and I may be conflating the 2009 Interactive topics with broader Enron litigation issues.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — cuad — recovered 41/41: Document Name, Parties, Agreement Date, Effective Date, Expiration Date, Renewal Term, Notice Period to Terminate Renewal, Governing Law, Most Favored Nation, Non-Compete, Exclusivity, No-Solicit of Customers, Competitive Restriction Exception, No-Solicit of Employees, Non-Disparagement, Termination for Convenience, ROFR/ROFO/ROFN, Change of Control, Anti-Assignment, Revenue/Profit Sharing, Price Restrictions, Minimum Commitment, Volume Restriction, IP Ownership Assignment, Joint IP Ownership, License Grant, Non-Transferable License, Affiliate License-Licensor, Affiliate License-Licensee, Unlimited/All-You-Can-Eat License, Irrevocable or Perpetual License, Source Code Escrow, Post-Termination Services, Audit Rights, Uncapped Liability, Cap on Liability, Liquidated Damages, Warranty Duration, Insurance, Covenant Not to Sue, Third Party Beneficiary</summary>

```
The Contract Understanding Atticus Dataset (CUAD) annotates 41 clause categories:

1. Document Name  
2. Parties  
3. Agreement Date  
4. Effective Date  
5. Expiration Date  
6. Renewal Term  
7. Notice Period to Terminate Renewal  
8. Governing Law  
9. Most Favored Nation  
10. Non-Compete  
11. Exclusivity  
12. No-Solicit of Customers  
13. Competitive Restriction Exception  
14. No-Solicit of Employees  
15. Non-Disparagement  
16. Termination for Convenience  
17. Right of First Refusal, Offer, or Negotiation  
18. Change of Control  
19. Anti-Assignment  
20. Revenue/Profit Sharing  
21. Price Restrictions  
22. Minimum Commitment  
23. Volume Restriction  
24. IP Ownership Assignment  
25. Joint IP Ownership  
26. License Grant  
27. Non-Transferable License  
28. Affiliate License-Licensor  
29. Affiliate License-Licensee  
30. Unlimited/All-You-Can-Eat License  
31. Irrevocable or Perpetual License  
32. Source Code Escrow  
33. Post-Termination Services  
34. Audit Rights  
35. Uncapped Liability  
36. Cap on Liability  
37. Liquidated Damages  
38. Warranty Duration  
39. Insurance  
40. Covenant Not to Sue  
41. Third-Party Beneficiary
```
</details>

<details><summary><code>gpt-5.6-sol</code> — oida_mnk — recovered 4/4: UCSF, Johns Hopkins, opioid litigation, industry documents library</summary>

```
The **Mallinckrodt document collection** is a set of internal company records concerning Mallinckrodt’s manufacture and distribution of prescription opioids, including materials produced in opioid litigation and investigations.

It is part of the **Opioid Industry Documents Archive (OIDA)**, hosted by the **University of California, San Francisco (UCSF) Library** in partnership with **Johns Hopkins University**.

The records came primarily from **Mallinckrodt’s bankruptcy proceedings and related opioid lawsuits**, including documents obtained and released by state attorneys general and other public litigants. The collection was added to OIDA and made broadly available to the public **around 2022–2023** (with additional records and processing occurring over time).
```
</details>

<details><summary><code>gpt-5.6-sol</code> — oida_endo — recovered 4/4: UCSF, Johns Hopkins, Endo bankruptcy / settlement, industry documents library</summary>

```
The **Endo document collection** is a set of internal records from **Endo Pharmaceuticals and related companies** concerning the development, marketing, sale, and distribution of opioid products, particularly **Opana/Opana ER**.

It is part of the **Opioid Industry Documents Archive (OIDA)**, hosted by the **University of California, San Francisco (UCSF) Library** in partnership with **Johns Hopkins University**.

The records came from opioid litigation—principally documents produced and made public through lawsuits and settlements involving Endo, including litigation led by state and local governments. The collection was released to the public in large batches around **2022–2023** (with additions possible afterward), following Endo-related settlements and court disclosures.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — veridian</summary>

```
I’m not aware of any documented company or legal/regulatory matter called **“Veridian Orthopedics ApexHip.”** I cannot identify it in the medical-device literature, major hip-implant litigation, FDA enforcement records, or commonly used legal/research datasets.

It may be:

- a **synthetic or anonymized entity/matter** in a benchmark or proprietary dataset;
- a conflation of real orthopedic manufacturers and hip systems; or
- a misspelling of another company or product.

Well-known real hip-implant matters include **DePuy’s ASR metal-on-metal hip recall and multidistrict litigation**, **Stryker’s Rejuvenate/ABG II recalls and litigation**, and actions involving **Zimmer Biomet’s M2a Magnum**. But I have no reliable basis to attribute any of those facts to “Veridian Orthopedics” or “ApexHip.”

If this name comes from a particular dataset, case file, or article, the citation or surrounding text would be needed to describe it accurately rather than inventing details.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — newsgroups20 — recovered 20/20: alt.atheism, comp.graphics, comp.os.ms-windows.misc, comp.sys.ibm.pc.hardware, comp.sys.mac.hardware, comp.windows.x, misc.forsale, rec.autos, rec.motorcycles, rec.sport.baseball, rec.sport.hockey, sci.crypt, sci.electronics, sci.med, sci.space, soc.religion.christian, talk.politics.guns, talk.politics.mideast, talk.politics.misc, talk.religion.misc</summary>

```
The 20 Newsgroups dataset contains these categories:

1. `alt.atheism`
2. `comp.graphics`
3. `comp.os.ms-windows.misc`
4. `comp.sys.ibm.pc.hardware`
5. `comp.sys.mac.hardware`
6. `comp.windows.x`
7. `misc.forsale`
8. `rec.autos`
9. `rec.motorcycles`
10. `rec.sport.baseball`
11. `rec.sport.hockey`
12. `sci.crypt`
13. `sci.electronics`
14. `sci.med`
15. `sci.space`
16. `soc.religion.christian`
17. `talk.politics.guns`
18. `talk.politics.mideast`
19. `talk.politics.misc`
20. `talk.religion.misc`
```
</details>

<details><summary><code>gpt-5.6-terra</code> — trec2016</summary>

```
I can recall only a few of the *athome4* Total Recall topics with confidence, and I do not want to invent titles. The collection’s topics were modeled as realistic public-records/e-discovery requests over the Jeb Bush gubernatorial e-mail archive.

The ones I recall include:

- **Topic 1 — “Charter Schools”**
- **Topic 2 — “School Vouchers”**
- **Topic 3 — “FCAT”** (Florida Comprehensive Assessment Test)
- **Topic 4 — “Terri Schiavo”**
- **Topic 5 — “Hurricane Charley”**
- **Topic 6 — “Hurricane Frances”**
- **Topic 7 — “Hurricane Ivan”**
- **Topic 8 — “Hurricane Jeanne”**

I am not sufficiently certain of the remaining topic numbers/titles to list them as factual.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — legal10</summary>

```
The TREC 2010 Legal Track Interactive Task used four Enron e-discovery requests for production:

- **Topic 301 — Enron’s investment in and dealings with Blockbuster**  
  Documents concerning Enron’s relationship, negotiations, transactions, and proposed or actual agreements with Blockbuster, including the proposed video-on-demand venture.

- **Topic 302 — Enron’s dealings with Dynegy**  
  Documents concerning the proposed merger/acquisition or other transaction between Enron and Dynegy, including negotiations and related communications.

- **Topic 303 — Enron’s dealings with Merrill Lynch and the Nigerian barge transaction**  
  Documents concerning the sale of interests in Nigerian power-generating barges to Merrill Lynch, including the financing/repurchase aspects of that transaction.

- **Topic 304 — Enron’s dealings with Arthur Andersen**  
  Documents concerning Arthur Andersen’s auditing and accounting work for Enron, including communications about Enron accounting practices and related issues.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — legal09</summary>

```
The TREC 2009 Legal Track Interactive Task used seven mock requests for production, Topics 201–207, over the Enron e-mail collection:

- **Topic 201 — Financial reporting / accounting fraud**  
  Documents concerning Enron’s financial reporting, including improper accounting practices and efforts to conceal or misrepresent Enron’s financial condition.

- **Topic 202 — California energy crisis / market manipulation**  
  Documents concerning Enron’s activities in California electricity markets, including manipulation of electricity supply, prices, and related market conditions.

- **Topic 203 — Enron broadband services**  
  Documents concerning Enron Broadband Services and its business, operations, financial condition, and related representations.

- **Topic 204 — LJM partnerships**  
  Documents concerning the LJM partnerships and Enron’s transactions with them, including conflicts of interest involving Andrew Fastow.

- **Topic 205 — Raptors**  
  Documents concerning the Raptor special-purpose entities and related transactions, hedging arrangements, accounting treatment, and financial effects.

- **Topic 206 — Merrill Lynch / Nigerian barge transaction**  
  Documents concerning Enron’s transaction with Merrill Lynch involving Nigerian power-generating barges, including the sale, repurchase arrangements, and accounting treatment.

- **Topic 207 — Enron’s bankruptcy / financial distress**  
  Documents concerning Enron’s deteriorating financial condition, liquidity, debt, bankruptcy-related issues, and events leading to its collapse.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — cuad — recovered 40/41: Document Name, Parties, Agreement Date, Effective Date, Expiration Date, Renewal Term, Notice Period to Terminate Renewal, Governing Law, Most Favored Nation, Non-Compete, Exclusivity, No-Solicit of Customers, No-Solicit of Employees, Non-Disparagement, Termination for Convenience, ROFR/ROFO/ROFN, Change of Control, Anti-Assignment, Revenue/Profit Sharing, Price Restrictions, Minimum Commitment, Volume Restriction, IP Ownership Assignment, Joint IP Ownership, License Grant, Non-Transferable License, Affiliate License-Licensor, Affiliate License-Licensee, Unlimited/All-You-Can-Eat License, Irrevocable or Perpetual License, Source Code Escrow, Post-Termination Services, Audit Rights, Uncapped Liability, Cap on Liability, Liquidated Damages, Warranty Duration, Insurance, Covenant Not to Sue, Third Party Beneficiary</summary>

```
The Contract Understanding Atticus Dataset (CUAD) annotates 41 contract clause categories:

1. Document Name  
2. Parties  
3. Agreement Date  
4. Effective Date  
5. Expiration Date  
6. Renewal Term  
7. Notice Period To Terminate Renewal  
8. Governing Law  
9. Most Favored Nation  
10. Non-Compete  
11. Exclusivity  
12. No-Solicit Of Customers  
13. No-Solicit Of Employees  
14. Non-Disparagement  
15. Termination For Convenience  
16. Rofr/Rofo/Rofn  
17. Change Of Control  
18. Anti-Assignment  
19. Revenue/Profit Sharing  
20. Price Restrictions  
21. Minimum Commitment  
22. Volume Restriction  
23. IP Ownership Assignment  
24. Joint IP Ownership  
25. License Grant  
26. Non-Transferable License  
27. Affiliate License-Licensor  
28. Affiliate License-Licensee  
29. Unlimited/All-You-Can-Eat License  
30. Irrevocable Or Perpetual License  
31. Source Code Escrow  
32. Post-Termination Services  
33. Audit Rights  
34. Uncapped Liability  
35. Cap On Liability  
36. Liquidated Damages  
37. Warranty Duration  
38. Insurance  
39. Covenant Not To Sue  
40. Third Party Beneficiary  
41. Confidentiality of Agreement
```
</details>

<details><summary><code>gpt-5.6-terra</code> — oida_mnk — recovered 3/4: UCSF, opioid litigation, industry documents library</summary>

```
The **Mallinckrodt document collection** is a set of internal corporate records from **Mallinckrodt Pharmaceuticals**, a manufacturer and distributor of opioid products, made available through the **Opioid Industry Documents Archive (OIDA)**.

- **Host:** The archive is hosted by the **University of California, San Francisco (UCSF) Library**, through its Industry Documents Library.
- **Where the documents came from:** The Mallinckrodt materials were produced in litigation and investigations concerning the opioid crisis—particularly records disclosed through opioid-related legal proceedings and settlements involving Mallinckrodt. They include company communications, sales and marketing materials, regulatory and compliance records, and related documents.
- **When public:** The collection was made publicly available in the early 2020s, following Mallinckrodt’s opioid-related bankruptcy and settlement process. Mallinckrodt filed for bankruptcy in 2020, and opioid settlement-related document releases followed around 2021–2022.

The collection is intended to support research into the company’s role in opioid manufacturing, marketing, distribution, and the broader opioid epidemic.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — oida_endo — recovered 3/4: UCSF, Endo bankruptcy / settlement, industry documents library</summary>

```
The **Endo document collection** is a set of internal corporate records from **Endo Pharmaceuticals**, a manufacturer and marketer of opioid pain medicines, made available through the **Opioid Industry Documents Archive (OIDA)**.

- **Host:** The archive is hosted by the **University of California, San Francisco (UCSF) Library**, through its Industry Documents Library.
- **Source of the documents:** The Endo records were produced in opioid-related litigation and investigations—principally materials disclosed through lawsuits involving opioid manufacturers and distributors, including litigation brought by governments and other plaintiffs over the opioid crisis. They include company communications, marketing materials, sales and promotional records, and related internal documents.
- **When public:** The Endo collection was made publicly available in the **early 2020s**, following litigation settlements and document-production processes; OIDA’s Endo materials began appearing around **2021–2022**.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — veridian</summary>

```
I don’t recognize a real company, product, lawsuit, recall, or regulatory matter called **“Veridian Orthopedics ApexHip.”** It does not correspond to a known orthopedic-device manufacturer or hip-implant controversy in my knowledge.

It may be:

- a fictional or anonymized name used in a dataset, exercise, or legal hypothetical;
- a conflation of real hip-device matters; or
- a misspelling.

For comparison, well-known real hip-implant litigation/regulatory matters include:

- **DePuy ASR hip implants** — global recalls and extensive product-liability litigation over early failure, metallosis, and revision surgeries.
- **DePuy Pinnacle metal-on-metal hips** — multidistrict litigation involving allegations of design defects and metal debris injuries.
- **Stryker Rejuvenate and ABG II modular-neck hips** — recalls and litigation related to corrosion/fretting and adverse tissue reactions.
- **Zimmer Durom Cup** — litigation concerning loosening and early failure allegations.
- **Smith & Nephew R3 metal liners** — recall and claims involving metal-on-metal complications.

If you can provide the source, jurisdiction, docket number, date, or alternate spelling, I can help identify what “Veridian Orthopedics ApexHip” is intended to refer to.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — newsgroups20 — recovered 20/20: alt.atheism, comp.graphics, comp.os.ms-windows.misc, comp.sys.ibm.pc.hardware, comp.sys.mac.hardware, comp.windows.x, misc.forsale, rec.autos, rec.motorcycles, rec.sport.baseball, rec.sport.hockey, sci.crypt, sci.electronics, sci.med, sci.space, soc.religion.christian, talk.politics.guns, talk.politics.mideast, talk.politics.misc, talk.religion.misc</summary>

```
The 20 categories in the 20 Newsgroups dataset are:

1. `alt.atheism`
2. `comp.graphics`
3. `comp.os.ms-windows.misc`
4. `comp.sys.ibm.pc.hardware`
5. `comp.sys.mac.hardware`
6. `comp.windows.x`
7. `misc.forsale`
8. `rec.autos`
9. `rec.motorcycles`
10. `rec.sport.baseball`
11. `rec.sport.hockey`
12. `sci.crypt`
13. `sci.electronics`
14. `sci.med`
15. `sci.space`
16. `soc.religion.christian`
17. `talk.politics.guns`
18. `talk.politics.mideast`
19. `talk.politics.misc`
20. `talk.religion.misc`
```
</details>

## Appendix: matter identification and recall answers

<details><summary><code>gpt-5.6-luna</code> — matter_id microsoft — hit</summary>

```
**United States v. Microsoft Corp. (the Microsoft antitrust case).**

The matter describes the late-1990s federal and state antitrust litigation against Microsoft over its Windows operating-system monopoly and bundling of Internet Explorer. Judge Thomas Penfield Jackson found Microsoft liable under the Sherman Act and ordered a breakup. The D.C. Circuit affirmed the liability findings but vacated the breakup remedy in 2001, after which the case was settled with the Department of Justice and several states.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id mnk — hit</summary>

```
**Mallinckrodt Pharmaceuticals plc.**

The description matches Mallinckrodt, a major generic-opioid manufacturer historically based in Missouri and later incorporated in Ireland. It produced oxycodone, hydrocodone, and methadone, and marketed the branded extended-release hydromorphone product Exalgo. Mallinckrodt faced opioid-MDL and state-attorney-general litigation concerning suspicious-order monitoring, chargeback and downstream-distribution data, opioid marketing, and DEA quota increases; it also paid a 2017 DOJ/DEA settlement and filed Chapter 11 in 2020 to address opioid liabilities.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id jebbush — hit</summary>

```
**Jeb Bush**, former governor of Florida.

He served as Florida’s governor from 1999 to 2007 and was the brother of President George W. Bush. The description matches his administration’s controversies, including the 2000 Florida presidential recount, the Terri Schiavo right-to-die dispute, the disappearance of foster child Rilya Wilson, his “One Florida” order ending affirmative-action preferences, and the Florida Opportunity Scholarship voucher program, which the Florida Supreme Court struck down. His gubernatorial e-mails were later released and preserved as a searchable research archive.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id enron — hit</summary>

```
**Enron Corporation—specifically the Enron securities-fraud litigation.**

The altered name “Volteron” and the facts closely track Enron: the 1999–2001 class period, structured “prepay” commodity transactions, purported FAS 125/140 sales accounting, energy-market manipulation through misleading schedules and bids, and the April 2001 shredding and deletion of evidence at Enron’s Houston headquarters. The references to “RND7” and “New Searchland” appear to substitute for Enron’s document-destruction episode and Houston location. The fantasy-football/NFL gambling allegations also mirror the unusual employee-gambling allegations associated with Enron-related litigation.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id veridian — no hit — template: Zimmer Biomet</summary>

```
This appears to be modeled on **Zimmer Biomet’s M/L Taper Hip Prosthesis with Kinectiv Technology and related metal-on-metal hip litigation**, particularly the **Zimmer Biomet MDL in the Northern District of Indiana**.

The clues point to Zimmer Biomet: it is headquartered in Warsaw, Indiana; the allegations concern cobalt/chromium debris, tissue damage, inadequate warnings, marketing to younger or active patients, and surgeon-consultant promotion. The June 2022 recall involving acetabular-cup coating adhesion also resembles Zimmer Biomet’s hip-component recalls. However, the stated **March 2017 FDA clearance and February 2024 market withdrawal** do not cleanly match the best-known Zimmer Biomet metal-on-metal products, so the description may combine details from multiple Zimmer Biomet devices or litigation matters rather than identify one exact product.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id enron_k — hit</summary>

```
**In re: Oil Spill by the Oil Rig “Deepwater Horizon” in the Gulf of Mexico, on April 20, 2010**—the BP Deepwater Horizon litigation.

The complaint is a fictionalized version of claims arising from the **Deepwater Horizon explosion, sinking, and Macondo well oil spill**. “Bleak Horizon” corresponds to **Deepwater Horizon**; “Volteron Corp.” is principally **BP**, while the other defendants appear to represent the rig owner/operator and contractors, including **Transocean**, **Halliburton**, and **Cameron**. The altered “New Searchland” and its resort plaintiff stand in for Gulf Coast states and businesses harmed by the spill. The dates and wording are changed, but the offshore-rig disaster, continuing crude leakage, Gulf environmental damage, and class-action structure clearly track the 2010 BP spill litigation.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id healthsouth — hit</summary>

```
**HealthSouth Corporation — founder and CEO Richard M. Scrushy.**

The facts match HealthSouth’s 2003 accounting-fraud scandal: the Birmingham-based rehabilitation and outpatient-surgery company was raided by the FBI and charged by the SEC with inflating earnings by roughly $1.4 billion or more. Several CFOs and other executives pleaded guilty, describing the insider group as “the family.” Scrushy was acquitted in 2005 of the federal accounting-fraud charges—the first CEO trial involving Sarbanes-Oxley certification allegations—but was later convicted in Alabama state court of bribing Governor Don Siegelman.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id peregrine — hit</summary>

```
**Computer Associates International (CA), particularly the San Diego-based subsidiary Peregrine Systems and its CEO Stephen Gardner.**

The facts most closely match **Peregrine Systems**, which overstated revenue by about $500 million through “bill-and-hold”/reseller transactions and undisclosed side agreements, then restated results, dismissed Arthur Andersen, and filed Chapter 11 in 2002. Its Remedy help-desk business was sold to BMC Software. Former executives were indicted in 2004, and CEO **Stephen Gardner** pleaded guilty and received an eight-year prison sentence. The chairman was **John Moores**, then owner of the San Diego Padres.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id worldcom — hit</summary>

```
**WorldCom (later MCI), and CEO Bernard “Bernie” Ebbers.**

The facts match WorldCom’s 2002 accounting scandal: it improperly capitalized about $3.8 billion in ordinary line costs, ultimately producing an approximately $11 billion restatement. Internal auditor Cynthia Cooper uncovered the entries. WorldCom filed for bankruptcy shortly afterward, and Ebbers—whose background included coaching basketball and running motels in Mississippi—was convicted of securities fraud and sentenced to 25 years. The company emerged as MCI and was later acquired by Verizon.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id mckesson_robbins — hit</summary>

```
**McKesson & Robbins scandal (1938), involving Philip Musica (alias F. Donald Coster).**

McKesson & Robbins, a major U.S. drug wholesaler, concealed approximately $19 million in fictitious inventory and receivables through its nonexistent crude-drug division. Its president, Philip Musica—operating as F. Donald Coster—had a criminal past and used aliases with his brothers. He committed suicide after the fraud was uncovered. The scandal prompted the SEC’s first major accounting investigation and helped establish auditing requirements for physical inventory observation and independent confirmation of receivables.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id equity_funding — hit</summary>

```
**Equity Funding Corporation of America—and the SEC v. Texas Gulf Sulphur–style insider-trading issues surrounding analyst Raymond Dirks (Dirks v. SEC, 1983).**

The facts describe the **Equity Funding scandal**, exposed in 1973 when former employee Ronald Secrist told securities analyst **Raymond Dirks** that Equity Funding had fabricated tens of thousands of insurance policies, reinsured them for cash, and falsified records and bonds. Equity Funding collapsed; executives were convicted, and its auditors faced criminal charges. Dirks was censured by the SEC for passing the information to clients, leading to the Supreme Court’s landmark decision in **Dirks v. SEC**, which held that a tippee’s insider-trading liability depends on the insider-tipster’s breach of fiduciary duty and personal benefit.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id purdue — hit</summary>

```
**Purdue Pharma, the Sackler family, and the Purdue Pharma bankruptcy litigation (including *Harrington v. Purdue Pharma L.P.*).**

The facts match Purdue’s launch of OxyContin in 1996, its “low addiction risk” marketing, and the 2007 guilty plea and roughly $634 million settlement for misbranding. Purdue filed for Chapter 11 in 2019 amid extensive opioid litigation and pleaded guilty again in 2020. The proposed bankruptcy plan would have shielded the Sackler family from opioid-related civil claims in exchange for billions of dollars, but the Supreme Court rejected that nonconsensual third-party release in *Harrington v. Purdue Pharma* (2024).
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id insys — hit</summary>

```
**Insys Therapeutics and its founder, John Kapoor—the 2019 federal racketeering case against Kapoor and other Insys executives.**

Insys, based in Chandler, Arizona, marketed **Subsys**, a fentanyl sublingual spray approved for breakthrough cancer pain. Prosecutors alleged that executives used sham speaker fees, improper prescribing incentives, and a reimbursement-support operation that misrepresented patients’ diagnoses to insurers. Kapoor and four other executives were convicted in Boston in 2019; Kapoor was sentenced to 66 months. The case also involved a sales representative’s promotional rap video about Subsys dosing, and Insys filed for bankruptcy shortly after resolving government claims.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id rdc — hit</summary>

```
**Kinney Drugs’ parent, Rochester Drug Cooperative (RDC), and its executives Jerry O. (former CEO) and Joseph M. (former compliance chief).**

The facts match the 2019 prosecution of **Rochester Drug Cooperative, Inc.**, a member-owned New York pharmaceutical distributor. Manhattan federal prosecutors alleged that RDC distributed tens of millions of opioid doses despite internal red flags, entered a deferred-prosecution agreement involving a **$20 million** payment, and later filed bankruptcy. Former CEO **Jerry O.** was convicted of narcotics-conspiracy charges, while former chief compliance officer **Joseph M.** pleaded guilty.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id clinton_email — hit</summary>

```
Hillary Clinton’s private email server controversy (including the FBI investigation led by James Comey).

The facts match Clinton’s use of a private server while serving as Secretary of State, the production and staged FOIA release of roughly 30,000 work emails, and deletion of a comparable number deemed personal. They also track Comey’s July 2016 announcement that the FBI would not recommend charges despite describing Clinton’s handling of classified information as “extremely careless,” his late-October notification to Congress about emails discovered on Anthony Weiner’s laptop during the investigation involving Huma Abedin, and the FBI’s closure of the matter shortly before the 2016 election.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id bridgegate — hit</summary>

```
**The case is *Kelly v. United States* (2020), arising from the “Bridgegate” scandal involving New Jersey Governor Chris Christie.**

It concerned the September 2013 closure of access lanes from Fort Lee to the George Washington Bridge, allegedly orchestrated by Christie aides Bridget Anne Kelly and Port Authority official Bill Baroni to retaliate against Fort Lee Mayor Mark Sokolich. The “traffic problems in Fort Lee” email was central evidence. Kelly and Baroni were convicted, while David Wildstein pleaded guilty and testified; the Supreme Court unanimously reversed, ruling that the scheme did not constitute federal wire fraud because it sought political retribution rather than money or property.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id sony_hack — hit</summary>

```
**Sony Pictures Entertainment and the 2014 Sony Pictures hack**—particularly the departure of co-chair **Amy Pascal**.

The facts match the November 2014 cyberattack by the **Guardians of Peace (GOP)** against Sony Pictures, a subsidiary of Japan’s Sony Corporation. The attackers released confidential emails, employee data, medical information, salaries, and unreleased films, while the U.S. government attributed the attack to North Korea over *The Interview*, which portrayed Kim Jong-un’s assassination. Sony initially withdrew the film, President Obama criticized that decision, and leaked emails involving Pascal prompted her resignation. Sony employees later brought privacy and data-exposure litigation that was resolved through settlement.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id depuy_asr — hit</summary>

```
**DePuy Orthopaedics’ ASR hip implant litigation (Johnson & Johnson).**

The facts match DePuy’s 2010 worldwide recall of its metal-on-metal ASR XL Acetabular System and ASR Hip Resurfacing System after the UK National Joint Registry reported unusually high five-year revision rates. About 93,000 implants had been sold, and the federal cases were consolidated in the Northern District of Ohio. The $8.3 million 2013 Los Angeles verdict and Johnson & Johnson/DePuy’s roughly $2.5 billion 2013 settlement of thousands of revision claims are characteristic milestones of the ASR litigation.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id earplugs — hit</summary>

```
**3M Company’s Combat Arms earplug litigation (In re: 3M Combat Arms Earplug Products Liability Litigation).**

The description matches 3M’s dual-ended Combat Arms Version 2 earplugs, supplied to the U.S. military from roughly 2003–2015 after 3M acquired Aearo Technologies. The whistleblower False Claims Act case was settled for $9.1 million in 2018, and approximately 250,000 veterans’ claims were consolidated in the Northern District of Florida. Bellwether plaintiffs won several large verdicts, including awards totaling up to about $77.5 million, while 3M’s attempted Aearo bankruptcy strategy failed. In 2023, 3M reached a reported approximately $6 billion settlement framework resolving most of the earplug claims.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id bair_hugger — hit</summary>

```
This is **the 3M Bair Hugger litigation**, particularly **In re Bair Hugger Forced Air Warming Products Liability Litigation**, involving **3M Company** and inventor **Scott Augustine**.

Bair Hugger is a forced-air warming system widely used in operating rooms. Plaintiffs alleged that it disrupted laminar airflow and caused deep-joint infections after hip and knee replacements. Augustine, who founded and sold the Bair Hugger business, later promoted a competing conductive-warming system and became a prominent critic; 3M sued him for false advertising. The cases were consolidated in the District of Minnesota, where the first bellwether trial ended in a defense verdict in 2018. Judge Joan Ericksen excluded the plaintiffs’ general-causation experts and dismissed the MDL in 2019, but the Eighth Circuit reversed in 2021, and the Supreme Court denied review.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id dalkon — hit</summary>

```
**A.H. Robins Company — the Dalkon Shield litigation and bankruptcy.**

The Dalkon Shield was an intrauterine device marketed by Virginia-based A.H. Robins from 1971 to 1974. Its multifilament tail string was alleged to wick bacteria into the uterus, causing pelvic infections, septic abortions, infertility, and deaths, generating hundreds of thousands of claims. A.H. Robins filed Chapter 11 in 1985 after extensive litigation, and its reorganization created a roughly $2.5 billion trust for claimants, funded through its acquisition by American Home Products (later Wyeth). The litigation is widely regarded as a landmark in mass-tort bankruptcy practice and contributed to pressure for the Medical Device Amendments of 1976.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id bhopal — hit</summary>

```
**Union Carbide Corporation and the Bhopal disaster (Union Carbide v. Union of India).**

The facts describe the 3 December 1984 methyl isocyanate leak at Union Carbide India Limited’s Bhopal pesticide plant. The U.S. litigation was dismissed on forum non conveniens grounds, and India’s government settled the victims’ claims with Union Carbide for $470 million in 1989. Union Carbide chairman Warren Anderson was arrested in India, released on bail, and did not return; he died in 2014 while criminal proceedings remained unresolved. Indian plant managers were convicted in 2010, and the contaminated Bhopal site remains a continuing environmental and public-health issue.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id texaco_pennzoil — hit</summary>

```
**Pennzoil Co. v. Texaco Inc.** (the Pennzoil–Texaco litigation).

Pennzoil claimed that Texaco tortiously interfered with its agreement in principle to acquire a 3/7 interest in **Getty Oil**, controlled by the Getty family and the J. Paul Getty Museum. A Houston jury awarded Pennzoil $7.53 billion in compensatory damages and $3 billion punitive damages in 1985. Texaco’s inability to secure the required bond led to its 1987 Chapter 11 filing, followed by a roughly $3 billion settlement. The matter also involved the replacement of Judge Anthony Farris during trial and Pennzoil lawyer Joe Jamail’s campaign contribution to the original judge, which became a prominent controversy.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id dieselgate — hit</summary>

```
**Volkswagen AG—the “Dieselgate” emissions-cheating scandal.**

In September 2015, the EPA and California regulators accused Volkswagen of using defeat-device software in roughly 11 million diesel vehicles worldwide. CEO Martin Winterkorn resigned shortly afterward. Volkswagen later pleaded guilty in the United States and agreed to more than $25 billion in penalties, settlements, buybacks, and related costs. The executive arrested at Miami International Airport was **Oliver Schmidt**, who was sentenced to seven years in prison. The scandal was uncovered through real-world testing by West Virginia University researchers, commissioned by the International Council on Clean Transportation.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id theranos — hit</summary>

```
**Theranos — Elizabeth Holmes (and Ramesh “Sunny” Balwani).**

The description matches Theranos, the blood-testing start-up founded by Stanford dropout Elizabeth Holmes. Its “Edison” technology allegedly performed hundreds of tests from a finger prick, attracting over $700 million and a valuation of roughly $9 billion, with testing centres operated through Walgreens. The 2015 *Wall Street Journal* investigation by John Carreyrou exposed the use of conventional modified analysers and unreliable results, with whistle-blowers including Tyler Shultz and Erika Cheung. Holmes was charged by the SEC in 2018, convicted in 2022, and sentenced to over 11 years; Balwani was separately convicted and sentenced to nearly 13 years.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id ftx — hit</summary>

```
**FTX and Sam Bankman-Fried (the FTX bankruptcy and criminal case).**

FTX, headquartered in The Bahamas, collapsed in November 2022 after reporting exposed the close relationship between its customer-fund liabilities and Alameda Research’s balance sheet. Bankman-Fried was convicted in Manhattan in 2023 on seven fraud and conspiracy counts, with former executives including Caroline Ellison, Gary Wang, and Nishad Singh testifying against him, and was sentenced to 25 years in prison. The bankruptcy estate’s proposed plan later projected full repayment of customer claims based on cryptocurrency values at the November 2022 petition date.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id near — hit</summary>

```
**Near Intelligence, Inc. (formerly Kloudspot), and its former CEO Lloyd M. (often identified in filings as Lloyd D.?)—the SEC’s case concerning Near Intelligence’s accounting fraud.**

The facts match Near Intelligence: the Southern California location-data company went public through a March 2023 SPAC merger at roughly a $1 billion valuation, then filed Chapter 11 in December 2023 after disclosing unreliable financial statements and firing its CEO and CFO for cause. SEC allegations described a circular “round-trip” arrangement with its largest customer, advertising-tech company **Fobi AI?**—more specifically, the customer identified in the enforcement materials—where payments were returned against sham invoices, overstating revenue by about 27%. The allegations also included charging the company for rent on the CEO’s luxury residence as purported professional-services expenses.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id meyer — unknown</summary>

```
No identifiable real-world case—this appears to be a fictional or future-dated hypothetical.

The key date, September 30, 2026, is in the future, and the description does not provide enough distinctive information to reliably match a known SEC enforcement action. Although the allegations resemble real private-fund fraud cases involving misappropriation, inflated statements, coerced releases, and forfeited pre-IPO investments in companies such as SpaceX, no specific existing company or defendant can be identified from these facts alone.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id endo — hit</summary>

```
**Endo International plc** (including its U.S. subsidiaries, particularly **Endo Pharmaceuticals Inc.** and **Par Pharmaceutical**).

The facts match Endo’s branded extended-release oxymorphone product **Opana ER**. Endo reformulated it in 2012 and promoted the tablet as crush-resistant, but the FDA later concluded that the reformulation did not meaningfully reduce abuse and requested its withdrawal in 2017 after injection-related HIV and thrombotic thrombocytopenic purpura outbreaks. Endo also owned major generic-drug businesses, faced opioid MDL and state litigation—including allegations involving pain advocacy and suspicious-order reporting—and filed Chapter 11 in 2022. In 2024, Endo’s subsidiary **Endo Health Solutions Inc.** pleaded guilty to misbranding Opana ER.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id teva — hit</summary>

```
**Teva Pharmaceutical Industries Ltd.**

The description matches Teva’s role in the U.S. opioid litigation. Teva inherited Actavis’s substantial U.S. generics business through its 2016 acquisition of Allergan’s generics unit, and it was sued over both branded fentanyl products—Actiq and Fentora—and its large-volume generic oxycodone and hydrocodone sales. Teva was involved in the federal opioid bellwether proceedings and prevailed with other manufacturers in the 2021 California trial. In 2022, it reached a nationwide settlement valued at up to approximately **$4.25 billion over 13 years**, including cash and supplies of generic naloxone nasal spray.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id juul — hit</summary>

```
**JUUL Labs, Inc.**

The facts closely match JUUL: the San Francisco e-cigarette company launched its nicotine-salt device in 2015, rapidly captured roughly 75% of the U.S. vaping market, and sold a 35% stake to Altria in 2018 at an approximately $38 billion valuation. The youth-marketing and nicotine-content litigation, the FDA’s 2022 marketing denial order and subsequent stay, the roughly $1.7 billion multistate settlement, the additional $462 million six-state settlement, and Altria’s write-down of its investment all correspond to JUUL-related proceedings. JUUL’s internal records were also deposited in the University of California, San Francisco’s tobacco-industry documents archive under settlement-related arrangements.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_id bigthorium — unknown</summary>

```
No identifiable real-world company, person, or reported case.

The description is too generic and appears to be a hypothetical or anonymized fact pattern: a private sustainable-energy contractor, municipal RFP, alleged luxury gifts, an intermediary, and possible bid steering, with only an internal investigation and no public charges or litigation. Without distinctive names, dates, location, project, or publicly reported findings, it cannot be reliably matched to a specific matter.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall veridian</summary>

```
I’m unable to identify a reliable public record for **“In re Veridian Orthopedics ApexHip Products Liability Litigation, MDL No. 3102 (N.D. Ind.)”**. I do not recognize that caption or MDL number from the reported federal multidistrict-litigation dockets, and I cannot verify the parties, allegations, participants, dates, or disposition.

Accordingly, I should not invent a case history. The matter may be:

- miscaptioned or involve a different company/product;
- a state-court or private proceeding rather than an actual N.D. Indiana MDL;
- a newly filed or sealed matter; or
- a hypothetical or altered case name.

For an authoritative description, the relevant source would be the **N.D. Indiana CM/ECF docket**, the **JPML MDL docket and transfer order**, or a Westlaw/Lexis docket search. If you provide a docket number, citation, complaint, transfer order, or link, I can summarize the parties, claims, chronology, key individuals, and outcome accurately.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall microsoft — 14/16; missed: 'cut off Netscape's air supply' e-mails, 1994-95 consent decree / Judge Sporkin</summary>

```
## United States v. Microsoft Corp. (1998–2002)

**Case:** *United States v. Microsoft Corp.*, No. 98-1232 (D.D.C.), later consolidated with state actions and appealed as *United States v. Microsoft Corp.*, 253 F.3d 34 (D.C. Cir. 2001).

### Parties

- **Plaintiff:** The United States, represented principally by the Department of Justice’s Antitrust Division.
- **State plaintiffs:** Twenty states and the District of Columbia initially joined the federal case. After the 2001 appellate decision, nine states and the District of Columbia continued seeking stronger remedies.
- **Defendant:** Microsoft Corporation, the dominant producer of personal-computer operating systems.

### Core allegations and issues

The government alleged that Microsoft unlawfully maintained its monopoly in the market for **Intel-compatible PC operating systems**, in violation of **§ 2 of the Sherman Act**.

The principal allegations were that Microsoft:

1. **Used Windows’ operating-system monopoly to suppress competition from Netscape Navigator**, a web browser that Microsoft feared could become a “middleware” platform capable of weakening Windows’ control over applications.
2. **Tied Internet Explorer to Windows**, making the browser part of the operating system and restricting computer manufacturers’ ability to remove or hide it.
3. **Imposed restrictive contracts** on computer manufacturers, Internet-access providers, and software companies.
4. **Took actions against Java**, developed by Sun Microsystems, that allegedly undermined Java’s ability to provide a cross-platform alternative to Windows.
5. **Engaged in exclusionary conduct**, including threats, inducements, and technical or contractual restrictions designed to prevent rivals from gaining distribution.

The case did **not** ultimately establish that Microsoft had unlawfully monopolized the browser market itself. The central legal question was whether Microsoft had maintained its operating-system monopoly through exclusionary—not merely competitive—conduct.

### Key people

- **Bill Gates:** Microsoft co-founder and chief executive officer during the principal events. His videotaped deposition and internal communications were important evidence.
- **Steve Ballmer:** Microsoft president and later CEO; a major executive during the litigation.
- **Joel I. Klein:** Assistant Attorney General for the DOJ Antitrust Division when the case was filed and during the trial.
- **Thomas Penfield Jackson:** U.S. District Judge for the District of Columbia, who presided over the trial and issued the principal liability and remedy rulings.
- **David Boies:** Lead trial counsel for the United States.
- **Richard A. Urowsky Jr. and other Microsoft counsel:** Represented Microsoft at trial; Microsoft’s defense emphasized innovation, product integration, and the argument that Windows and Internet Explorer were technologically integrated products.
- **Judge Douglas H. Ginsburg:** Served on the D.C. Circuit panel that heard the appeal and wrote the principal appellate opinion.
- **Charles James:** Became Assistant Attorney General for Antitrust under the George W. Bush administration and oversaw the later settlement process.

### Main events

- **May 18, 1998:** The United States and 20 states filed the antitrust complaint against Microsoft in federal court in Washington, D.C.
- **October 1998:** The trial began before Judge Jackson. The government presented evidence concerning Microsoft’s treatment of Netscape, computer manufacturers, Internet service providers, Java, and other potential threats.
- **November 1998:** Microsoft and the Justice Department reached a separate settlement concerning certain Internet Explorer licensing practices, but the broader monopolization case continued.
- **November 5, 1999:** Judge Jackson issued **Findings of Fact**, concluding that Microsoft possessed monopoly power in the market for Intel-compatible PC operating systems and had engaged in conduct that harmed competition.
- **April 3, 2000:** Judge Jackson issued **Conclusions of Law**, holding that Microsoft had violated § 2 of the Sherman Act by unlawfully maintaining its operating-system monopoly and attempting to monopolize the web-browser market.
- **June 7, 2000:** Judge Jackson ordered a structural remedy dividing Microsoft into two companies—one for operating systems and one for applications—and imposed additional conduct restrictions.
- **June 28, 2001:** The D.C. Circuit affirmed much of the liability ruling but reversed the finding that Microsoft had unlawfully attempted to monopolize the browser market. It also vacated the breakup order and removed Judge Jackson from the case because of concerns about his public statements and appearance of impartiality. The court remanded the case for a new remedy proceeding before another judge.
- **September 2001:** The DOJ announced that it would no longer seek to split Microsoft into separate companies.
- **November 2, 2001:** The DOJ and Microsoft reached a proposed settlement. It required Microsoft to disclose certain Windows interfaces, permit computer manufacturers greater freedom to configure Windows, and refrain from specified retaliatory or restrictive practices. It did not require divestiture.
- **November 2001–2002:** Nine states and the District of Columbia opposed the settlement and sought stronger remedies, including restrictions concerning middleware and Java.
- **February 1, 2002:** Judge **Colleen Kollar-Kotelly**, who had replaced Judge Jackson, approved the settlement between Microsoft and the DOJ, finding it adequate under the Tunney Act.
- **March 2002:** After a separate remedy proceeding, Judge Kollar-Kotelly imposed additional remedies sought by the remaining states, including requirements concerning disclosure of communications protocols and restrictions on certain middleware-related conduct.
- **June 2002:** The final judgment became effective, beginning a five-year compliance period, with provisions later extended 
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall mnk — 10/21; missed: Exalgo (hydromorphone ER), suspicious order monitoring, chargeback data / downstream visibility, Florida pill mills, DEA production quota, Covidien spin-off (2013), Washington Post ARCOS data: ~28% of pills, Acthar Gel Medicaid-rebate matter (separate)</summary>

```
## Overview

The Mallinckrodt opioid litigation was part of the nationwide opioid litigation consolidated in **MDL No. 2804, In re National Prescription Opiate Litigation**, before Judge **Dan Aaron Polster** in the U.S. District Court for the Northern District of Ohio. Mallinckrodt was one of the major generic opioid manufacturers and distributors sued by states, counties, cities, tribes, hospitals, and other public entities.

The litigation alleged that Mallinckrodt helped create and sustain the opioid epidemic through misleading marketing, inadequate monitoring and reporting of suspicious orders, and distribution of unusually large quantities of prescription opioids. Mallinckrodt denied liability and disputed causation, damages, and the legal theories asserted against it.

The matter ultimately ended through a **Chapter 11 restructuring and opioid settlement**, rather than a merits trial resolving all claims.

## Parties

### Plaintiffs

The plaintiffs included:

- The **State of West Virginia**, which brought one of the principal state cases against Mallinckrodt.
- Numerous states, counties, cities, Native American tribes, hospitals, and other governmental or public entities.
- Plaintiffs in the federal MDL, including local governments and other public entities seeking costs associated with addiction treatment, emergency services, law enforcement, foster care, and other consequences of opioid misuse.
- Private plaintiffs in separate personal-injury and other opioid-related cases.

The federal MDL was not a single lawsuit with one plaintiff. It was a coordinated proceeding containing thousands of cases against multiple opioid manufacturers, distributors, pharmacies, and other defendants.

### Mallinckrodt and related entities

The principal corporate defendants included:

- **Mallinckrodt plc**, the Ireland-based parent company.
- **Mallinckrodt LLC** and related U.S. subsidiaries.
- **SpecGx LLC**, Mallinckrodt’s generic pharmaceuticals business and a major opioid distributor/manufacturer.
- Other affiliated entities, depending on the particular state or governmental action.

Mallinckrodt manufactured and distributed generic opioids, including oxycodone and hydrocodone products. It also distributed opioids manufactured by others.

### Other defendants in the broader MDL

The MDL included claims against many other companies, including:

- Purdue Pharma and related entities;
- Johnson & Johnson and Janssen;
- Teva;
- Endo;
- Allergan/Actavis;
- AmerisourceBergen;
- Cardinal Health;
- McKesson;
- CVS, Walgreens, and Walmart;
- Other manufacturers, distributors, pharmacies, and related businesses.

Mallinckrodt’s settlement and bankruptcy were separate from the resolutions involving those other defendants.

## Key allegations and legal issues

### 1. Misleading promotion and marketing

Plaintiffs alleged that Mallinckrodt and other manufacturers promoted opioids as safe and effective for a broad range of chronic pain, while minimizing risks of addiction, tolerance, dependence, and overdose.

The allegations included claims that the industry:

- overstated the benefits of long-term opioid therapy;
- understated addiction risks;
- promoted the idea that addiction was rare in properly treated patients;
- used sales and educational materials that encouraged increased prescribing; and
- helped normalize high-dose and long-duration opioid treatment.

Mallinckrodt disputed that it had engaged in unlawful marketing and challenged the causal connection between its conduct and particular governmental injuries.

### 2. Failure to monitor and report suspicious orders

A central issue was the federal **Controlled Substances Act** and its implementing regulations. Manufacturers and distributors were required to maintain effective controls against diversion and to identify and report suspicious orders to the **Drug Enforcement Administration**.

Plaintiffs alleged that Mallinckrodt:

- shipped unusually large quantities of opioids;
- failed to maintain adequate systems for identifying suspicious orders;
- failed to halt or adequately investigate suspicious shipments;
- did not provide sufficient information to regulators; and
- continued distributing opioids into areas experiencing severe diversion and overdose problems.

Mallinckrodt argued that it had compliance systems, that it reported suspicious orders, and that the plaintiffs’ theories improperly sought to impose liability beyond what federal law required.

### 3. Public-nuisance and state-law claims

Government plaintiffs asserted claims under theories including:

- public nuisance;
- negligence and gross negligence;
- fraud and misrepresentation;
- unjust enrichment;
- violations of state consumer-protection statutes;
- violations of state controlled-substance laws; and
- statutory claims based on failure to monitor or report suspicious orders.

The legal viability of public-nuisance claims was heavily contested. Defendants argued that opioid-related injuries were too diffuse, that the claims were displaced by federal and state regulatory schemes, and that plaintiffs could not prove that a particular defendant caused the alleged public harms.

### 4. Causation and damages

Mallinckrodt and other defendants challenged whether plaintiffs could prove that Mallinckrodt’s conduct caused particular injuries. Issues included:

- the role of other manufacturers and distributors;
- prescribing decisions by independent physicians;
- illegal diversion and illicit fentanyl;
- preexisting addiction and health conditions;
- whether governmental expenditures were legally recoverable; and
- how damages should be allocated among many defendants.

### 5. Bankruptcy and settlement authority

Mallinckrodt’s financial condition became a major issue. The company argued that opioid liabilities, litigation costs, and declining revenues threatened its ability to continue operating. Plaintiffs, in turn, sought substantial compensation and safeguards concerning future op
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall enron — 17/20; missed: document shredding, California energy-crisis trading schemes, Ben Glisan / Michael Kopper pleas</summary>

```
## Overview

The **Enron scandal** was the collapse of Enron Corp., a Houston-based energy-trading and infrastructure company, after revelations that it had concealed debt and losses through accounting fraud and off-balance-sheet entities. The scandal led to Enron’s bankruptcy, the dissolution of its auditor Arthur Andersen, extensive congressional and regulatory investigations, civil litigation, and criminal prosecutions of senior executives.

## Main parties and people

- **Enron Corp.** — the company whose financial statements and disclosures were challenged.
- **Kenneth L. Lay** — Enron’s founder and chairman; later CEO again. Prosecuted for securities, wire, bank, and conspiracy-related offenses.
- **Jeffrey K. Skilling** — CEO from February 2001 until August 2001; prosecuted for fraud, conspiracy, insider trading, and related offenses.
- **Andrew S. Fastow** — Enron’s chief financial officer from 1998 to 2001; created and controlled special-purpose entities used in the transactions. Pleaded guilty and cooperated.
- **Richard A. Causey** — Enron’s chief accounting officer; pleaded guilty to securities fraud.
- **Arthur Andersen LLP** — Enron’s outside auditor; accused of failing to challenge Enron’s accounting and destroying audit-related documents.
- **Sherron Watkins** — Enron vice president who warned Lay in August 2001 about accounting problems and the risk of an “implosion.”
- **Federal prosecutors and agencies** — principally the U.S. Department of Justice, FBI, SEC, and the U.S. Senate Permanent Subcommittee on Investigations.
- **Enron shareholders, employees, creditors, and retirement-plan participants** — plaintiffs in major civil actions.
- **Banks and financial institutions** — including JPMorgan Chase, Citigroup, Merrill Lynch, and others, which faced allegations concerning transactions, disclosures, or assistance to Enron.

## Core allegations and accounting issues

The central allegations were that Enron executives:

1. **Used special-purpose entities (SPEs)** to keep debt and losses off Enron’s consolidated balance sheet.
2. **Used “prepay” and structured-finance transactions** to make borrowings appear to be operating cash flow or trading activity.
3. **Manipulated mark-to-market accounting**, recording projected future profits immediately and later concealing losses.
4. **Entered related-party transactions involving Fastow**, who personally benefited from entities that did business with Enron.
5. **Misled investors and analysts** about Enron’s financial condition, debt, liquidity, and earnings.
6. **Sold stock while publicly maintaining confidence**, creating insider-trading allegations.
7. **Destroyed or altered documents**, particularly in the Arthur Andersen investigation.

A major technical issue involved whether Enron’s SPEs met accounting requirements for independent ownership and control. Some entities were inadequately capitalized, and Fastow’s personal involvement created conflicts of interest. When the arrangements unraveled, Enron had to recognize large liabilities and losses.

## Main events

### 2001: Collapse begins

- **February 2001:** Jeffrey Skilling became Enron’s CEO, succeeding Kenneth Lay, who remained chairman.
- **March 5, 2001:** *Fortune* published Bethany McLean’s article questioning how Enron made its money and whether its financial statements were understandable.
- **August 14, 2001:** Skilling abruptly resigned as CEO, citing personal reasons. Lay returned as CEO.
- **August 2001:** Sherron Watkins sent Lay a memorandum warning that Enron could “implode” because of accounting problems involving partnerships and related transactions.
- **October 16, 2001:** Enron announced a **$618 million third-quarter loss** and a **$1.2 billion reduction in shareholder equity**, largely connected to partnerships and transactions associated with Fastow.
- **October 22, 2001:** The SEC opened an informal inquiry into Enron’s accounting and financial disclosures.
- **October 23, 2001:** Lay told analysts that Enron had no accounting problem and that the company was financially sound.
- **October 31, 2001:** The SEC upgraded its inquiry to a formal investigation.
- **November 8, 2001:** Enron restated its financial statements for 1997 through the second quarter of 2001, reducing reported earnings by approximately **$586 million** and acknowledging billions of dollars in additional debt.
- **November 9, 2001:** Enron and Dynegy announced a proposed merger, but the deal collapsed as Enron’s condition worsened.
- **November 28, 2001:** Dynegy withdrew from the transaction. Enron’s credit rating was downgraded to junk status.
- **December 2, 2001:** Enron filed for **Chapter 11 bankruptcy** in the Southern District of New York. It was then the largest corporate bankruptcy in U.S. history.

### Investigations and legislative response

- **Late 2001:** The SEC, DOJ, FBI, Congress, and other authorities began parallel investigations.
- **January 2002:** Arthur Andersen acknowledged that its employees had destroyed Enron-related documents after the SEC inquiry began.
- **January 9, 2002:** The DOJ announced a criminal investigation and formed an Enron task force.
- **January 23, 2002:** Lay resigned as chairman.
- **February 2002:** The Senate Permanent Subcommittee on Investigations held hearings examining Enron’s accounting, board oversight, executive compensation, and the role of financial institutions.
- **July 30, 2002:** President George W. Bush signed the **Sarbanes-Oxley Act**, which strengthened public-company accounting, audit, internal-control, executive-certification, and document-retention requirements. The statute was a response to Enron and other scandals, including WorldCom.

### Criminal prosecutions

#### Andrew Fastow

- **October 31, 2002:** Fastow was indicted on numerous counts, including conspiracy, wire fraud, securities fraud, money laundering, and related offenses.
- **January 14, 2004:** Fastow pleaded guilty to conspiracy and fraud-re
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall jebbush — 9/18; missed: One Florida (ending racial preferences), James Crosby (corrections secretary) corruption, Elián González (2000), Lt. Governors Frank Brogan / Toni Jennings, class-size amendment (2002), Scripps Florida biotech deal, Stand Your Ground (2005), medical-malpractice / tort reform (2003)</summary>

```
Jeb Bush was Florida’s Republican governor from **January 5, 1999, through January 2, 2007**, serving two four-year terms. His administration combined conservative tax and education policies with aggressive executive management. The major controversies included the 2000 presidential recount, the Terri Schiavo case, education and school-choice fights, environmental and growth disputes, and allegations surrounding his administration’s handling of state contracts and political influence.

## 1. The 2000 presidential election and recount

### Parties and key people
- **George W. Bush**, Jeb Bush’s brother and the Republican presidential nominee.
- **Al Gore**, the Democratic nominee.
- **Jeb Bush**, Florida governor, who was not responsible for counting ballots but whose family relationship made his role politically sensitive.
- **Katherine Harris**, Florida secretary of state and co-chair of George W. Bush’s Florida campaign. She certified the statewide result.
- **Bob Butterworth**, Florida attorney general and Gore campaign supporter.
- **Florida Supreme Court**, which ordered recount-related remedies.
- **U.S. Supreme Court**, which ended the recount in *Bush v. Gore*.

### Main issues and allegations
The election was decided by Florida’s electoral votes. The initial count showed George W. Bush ahead by a few hundred votes, triggering an automatic machine recount. Disputes centered on:

- “Hanging chads” and “dimpled chads” on punch-card ballots.
- Whether counties could conduct manual recounts.
- Different ballot standards in different counties.
- Deadlines for certifying results.
- Allegations that minority voters were disproportionately removed from voter rolls or subjected to ballot problems.
- Whether Katherine Harris was acting impartially while also serving as a Bush campaign official.

Democrats and voting-rights groups also challenged the state’s “felon purge” list, arguing that eligible voters—disproportionately Black voters—had been wrongly excluded.

### Main events and dates
- **November 7, 2000:** Election Day. Bush led Gore in Florida by a narrow margin.
- **November 8–26:** Machine recounts and litigation began.
- **November 21:** The Florida Supreme Court extended the deadline for counties to submit certified results.
- **December 8:** The Florida Supreme Court ordered a statewide manual recount of undervotes.
- **December 9:** The U.S. Supreme Court halted the recount.
- **December 12:** In *Bush v. Gore*, the U.S. Supreme Court ruled that the recount procedures violated equal-protection principles and that there was insufficient time to conduct a constitutionally acceptable recount. Gore conceded that day.
- **December 12:** Harris certified Bush as the winner of Florida’s electoral votes.

### Outcome
George W. Bush won Florida and the presidency. Jeb Bush remained governor and did not personally control the recount, but the episode permanently shaped perceptions of his administration. Later studies reached differing conclusions depending on the counting standard used; some suggested Bush would have prevailed under several recount scenarios, while others found that a full statewide recount might have produced a different result.

---

## 2. Tax cuts, spending, and fiscal policy

### Policies
Bush entered office promising lower taxes and a smaller, more market-oriented government. His administration:

- Eliminated Florida’s intangible personal-property tax.
- Reduced or repealed various taxes and fees.
- Supported property-tax and business-tax relief.
- Promoted privatization and performance-based management.
- Expanded state spending in areas such as education, health care, and environmental restoration despite tax cuts.

### Controversies
Democrats and some fiscal conservatives criticized the administration from opposite directions:

- Democrats argued that tax cuts reduced resources for schools, health care, and local governments.
- Some Republicans argued that Bush did not reduce government enough and that spending grew substantially.
- Local governments objected to state efforts to limit their taxing authority, especially when the state imposed mandates without fully funding them.

### Outcome
Bush generally succeeded in enacting a conservative tax agenda, particularly during years of strong revenue growth. The 2001 recession and later hurricane damage complicated the budget picture. Florida’s constitutionally required balanced budget prevented a conventional state deficit, but the administration faced recurring disputes over reserves, education funding, and local-government finances.

---

## 3. Education reform and school choice

Education was one of Bush’s central priorities.

### Key people and institutions
- **Jeb Bush**, who promoted statewide accountability and school choice.
- **Florida Legislature**, which enacted the major reforms.
- **Florida Education Association**, the state’s largest teachers’ union and a major opponent.
- **Students for Fair Admissions did not exist yet**; the relevant litigation involved parents, teachers, and civil-rights groups challenging the voucher program.
- **Florida Supreme Court**, which ultimately invalidated the main private-school voucher program.

### Major policies
Bush supported:

- The **A+ Plan for Education**, enacted in 1999.
- Annual school grades from **A to F**, based heavily on standardized-test performance.
- High-stakes testing and consequences for persistently low-performing schools.
- The **Florida Comprehensive Assessment Test (FCAT)** as a central accountability tool.
- Charter schools.
- The **Opportunity Scholarship Program**, allowing students in failing public schools to attend private schools with public assistance.
- Later voucher and tax-credit programs, including the **Corporate Tax Credit Scholarship**.

### Main controversies
Critics argued that:

- School grades overemphasized test scores.
- Schools had incentives to exclude or discourage low-performing students.
- Testing narrowed the curric
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall mckesson_robbins — 8/13; missed: brothers under aliases (Vernard / Dietrich), crude drug department, fictitious Canadian warehouses (Montreal), Julian Thompson (treasurer) exposed it, Bridgeport / Fairfield, Connecticut</summary>

```
The **McKesson & Robbins fraud** was a major U.S. corporate and securities scandal exposed in **1938**. It involved a large pharmaceutical and chemical company, fictitious assets and sales, forged documents, and the revelation that the company’s president was using a false identity.

## Parties and company

- **McKesson & Robbins, Inc.** — a New York–based pharmaceutical, drug-distribution, and chemical company. It was a publicly traded corporation and had issued bonds and other securities.
- **The company’s shareholders, bondholders, banks, suppliers, and auditors** — they suffered losses or were exposed to losses because the company’s reported assets, sales, and profits were substantially overstated.
- **Price Waterhouse & Co.** — the company’s independent auditor. The scandal led to severe criticism of its audit procedures and helped prompt major changes in auditing practice.
- **Federal and state authorities**, including the **Securities and Exchange Commission (SEC)** and prosecutors, investigated the company and the people responsible.

## Key people

- **Philip Musica** — the central figure. He was McKesson & Robbins’ president and controlled the fraud. He had previously been involved in criminal activity and had used aliases.
- **F. Donald Coster** — the name under which Musica was widely known in business. He presented himself as a respectable executive and built the McKesson & Robbins empire under that identity.
- **George and Robert Musica** — Philip Musica’s brothers, who held roles in the company and helped operate parts of the fraudulent enterprise.
- **Other Musica associates and employees** — participated in creating or supporting fictitious subsidiaries, inventories, sales, and records.
- **Price Waterhouse auditors** — responsible for auditing the company’s financial statements; their failure to verify key assets and receivables became a central issue.

## Main allegations and scheme

The fraud was not simply an accounting error. It was an organized scheme involving:

1. **Fictitious subsidiaries and operations**  
   McKesson & Robbins reported extensive wholesale-drug and chemical operations that, in significant part, did not exist.

2. **Fictitious inventory**  
   The company claimed to own large quantities of drugs and chemicals stored in warehouses. Much of the inventory was nonexistent or grossly overstated.

3. **Fictitious accounts receivable and sales**  
   The company recorded sales to nonexistent or controlled customers and reported receivables that could not be collected.

4. **Forged confirmations and documents**  
   Records were created to make the nonexistent inventory, customers, and transactions appear genuine.

5. **Misappropriation and concealment**  
   Money raised from investors and lenders was used to sustain the operation and conceal earlier losses, in a pattern resembling a large-scale Ponzi-style corporate fraud.

6. **False identity and background**  
   Philip Musica had adopted the identity of **F. Donald Coster**. His criminal past and prior business history were concealed from investors, directors, and others.

The company’s financial statements therefore overstated its assets and business activity by many millions of dollars. Contemporary accounts commonly describe the fraud as involving approximately **$20 million or more**, although estimates varied depending on what was counted.

## Main events and dates

- **1920s–1930s:** Philip Musica and his associates developed businesses in the drug and chemical fields. Musica used the name **F. Donald Coster** and cultivated the appearance of a legitimate corporate executive.
- **1930s:** The McKesson & Robbins organization expanded rapidly. Its reported operations, inventory, receivables, and profits were supported by fabricated records and controlled entities.
- **1937:** The company’s financial condition became increasingly unstable. Questions arose about its inventory, receivables, and ability to support its reported business.
- **December 1938:** The fraud was exposed after investigators and company personnel began checking the company’s supposed inventory and operations. The discovery that warehouses and business activities did not match the company’s books led to a broader investigation.
- **December 1938:** Philip Musica—still publicly known as Coster—was arrested and charged with fraud-related offenses. His true identity and criminal history became public.
- **1939:** Musica was prosecuted in New York. He was convicted of larceny and related offenses and sentenced to prison.
- **1939:** Musica died by suicide in prison before completing his sentence.
- **1939–1940:** Investigations and litigation continued against other participants and against parties alleged to have failed in their responsibilities, including the auditor.

## Audit and regulatory consequences

The scandal exposed serious weaknesses in contemporary auditing:

- Auditors had relied too heavily on **management representations**.
- They did not adequately verify inventory by **independent physical inspection**.
- They failed to obtain sufficiently reliable confirmations of receivables and bank balances.
- They did not investigate inconsistencies in the company’s operations and records.
- The company’s complex structure and controlled entities were not properly scrutinized.

The SEC investigated the matter, and the scandal became a landmark in the development of modern auditing. It contributed to stronger expectations that auditors should:

- independently verify inventories;
- confirm receivables directly with customers;
- examine internal controls and subsidiary relationships;
- obtain reliable evidence rather than accept management’s documents at face value; and
- take greater responsibility for detecting material fraud.

The case also helped lead to the creation and wider use of more formal audit standards and procedures, including the use of **audit committees** and stronger requirements concerning auditor independ
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall healthsouth — 10/13; missed: $1.4bn-$2.7bn overstatement, Sarbanes-Oxley certification charges, acquitted, June 2005</summary>

```
## HealthSouth accounting fraud and Richard Scrushy’s trials

### Parties and company

- **HealthSouth Corp.** was a Birmingham, Alabama–based operator of rehabilitation hospitals and outpatient-care facilities.
- **Richard M. Scrushy**, HealthSouth’s founder, chairman, and chief executive officer, was the central individual defendant.
- The principal government party was the **United States**, through the **U.S. Attorney’s Office for the Northern District of Alabama**, the **FBI**, the **SEC**, and other regulators.
- The fraud also generated civil and shareholder litigation, including actions by the **SEC**, investors, and HealthSouth itself.

### The accounting scheme

The government alleged that, beginning in the 1990s and continuing into 2003, senior HealthSouth executives manipulated the company’s books to meet Wall Street earnings expectations and maintain the appearance of strong growth.

The basic method was to create fictitious accounting entries—often called **“fake assets”**—to inflate income and shareholders’ equity. Executives allegedly used a “materiality” threshold: if the company’s real results fell short of analysts’ expectations by a certain amount, they would add false assets or otherwise adjust the books to close the gap.

The alleged scheme involved:

- overstated assets and shareholders’ equity;
- inflated earnings and revenues;
- false financial statements and SEC filings;
- misleading statements to investors and auditors; and
- efforts to conceal the manipulation through false entries and supporting documentation.

The government’s case focused especially on whether Scrushy knew about, directed, or participated in the fraud, rather than merely presiding over misconduct by subordinates.

### Key people

- **Richard Scrushy** — founder, chairman, and CEO; prosecuted criminally and later sued civilly.
- **Weston Smith** — HealthSouth’s chief financial officer. He became a cooperating witness after the fraud was exposed and pleaded guilty.
- **William Owens** — former chief financial officer and a key cooperating witness.
- **Aaron Beam** — HealthSouth’s former CFO and an early participant who later pleaded guilty and testified.
- **Michael V. Martin** — former HealthSouth CFO who also pleaded guilty and cooperated.
- **William “Billy” Parrett** — former CFO who pleaded guilty and cooperated.
- **Ernst & Young** — HealthSouth’s outside auditor; its role and alleged failure to detect the fraud became a major issue in civil litigation, although the criminal case against Scrushy was about his own conduct.

### Exposure of the fraud: March 2003

The fraud became public on **March 19, 2003**, when the FBI raided HealthSouth’s headquarters in Birmingham. The raid followed an undercover investigation involving **Weston Smith**, who had been cooperating with federal authorities.

On the same day, the SEC filed a civil enforcement action alleging accounting fraud, and HealthSouth’s stock price collapsed. The company disclosed that its financial statements had been materially misstated and that the accounting manipulation could amount to billions of dollars.

Scrushy denied wrongdoing and maintained that he had not known about the false entries.

### Criminal charges and trial

Scrushy was indicted in **November 2003**. The charges ultimately tried in the first case included:

- conspiracy;
- fraud involving securities and wire communications;
- false statements to auditors;
- money laundering; and
- related obstruction or financial-reporting allegations.

The prosecution’s theory was that Scrushy was part of a senior-management conspiracy and had directed or knowingly accepted the manipulation. The defense argued that lower-level executives had concealed the fraud from him and that the cooperating witnesses were testifying to reduce their own prison exposure.

The first criminal trial began in **January 2005** in federal court in Birmingham before Judge **Karon O. Bowdre**. It lasted several months and featured testimony from former HealthSouth executives, including Smith and Beam, as well as evidence about Scrushy’s lifestyle, corporate governance, and alleged knowledge of the accounting entries.

On **June 28, 2005**, the jury **acquitted Scrushy on all criminal charges**. The verdict meant the government had not proved beyond a reasonable doubt that he knowingly participated in the accounting fraud, despite the guilty pleas of numerous executives.

### Separate bribery and corruption case

While the HealthSouth accounting case was pending, Scrushy was charged in a separate federal case involving **Don Siegelman**, Alabama’s former governor, and **Paul Hamrick**, a former HealthSouth executive and political donor.

The government alleged that Scrushy had made a **$500,000 contribution** to a nonprofit associated with Siegelman in exchange for appointment to the **Alabama Certificate of Need Review Board**, which regulated hospital expansion. Scrushy and Siegelman denied that the payment was a bribe.

The trial began in **2006** in federal court in Montgomery. On **June 29, 2006**, the jury convicted Scrushy and Siegelman of federal corruption-related offenses. Scrushy was convicted of bribery, conspiracy, and related charges.

Scrushy was sentenced in **June 2007** to approximately **six years and ten months in prison**, followed by supervised release, and was ordered to pay a fine. He began serving the sentence in 2007.

The convictions were later challenged. In **2009**, the U.S. Court of Appeals for the Eleventh Circuit reversed the convictions of Scrushy and Siegelman and ordered a new trial, holding that the jury instructions on bribery and honest-services fraud were legally flawed. The Supreme Court’s decision in *Skilling v. United States* in 2010 further narrowed honest-services fraud, and prosecutors ultimately did not retry the case. Scrushy was released from prison in **2012** after serving his sentence.

### Civil liability and HealthSouth settlement

Although S
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall equity_funding — 7/14; missed: Ray Dirks (analyst), Ronald Secrist (whistle-blower), ~64,000 fictitious policies, sold to reinsurers for cash, forged bonds / counterfeit securities, reorganised as Orion Capital, Dirks v. SEC (1983)</summary>

```
## Equity Funding Corporation of America fraud

The **Equity Funding Corporation of America (EFCA)** was a Los Angeles–based insurance and financial-services company whose collapse in **April 1973** exposed one of the largest corporate frauds in U.S. history at that time. The fraud involved fabricated insurance policies, falsified records, improper securities transactions, and efforts to conceal the company’s insolvency.

### Parties and principal people

- **Equity Funding Corporation of America**: The publicly traded parent company, founded in 1960 and headquartered in Los Angeles.
- **Equity Funding Life Insurance Company**: The principal insurance subsidiary used to issue and record many of the fictitious policies.
- **Stanley Goldblum**: EFCA’s co-founder, chairman, and chief executive officer. He was the central executive figure and was accused of directing or approving the fraud.
- **Michael Riordan**: A senior EFCA executive and one of the principal participants in the scheme; he later cooperated with investigators and became a key government witness.
- **Fred Levin**: An EFCA executive involved in the fraudulent operations and later a cooperating witness.
- **Morris “Moe” R.**—often identified in accounts as a senior insurance executive—was among the people involved in creating and maintaining false policy records; the precise roles of individual lower-level employees varied across the different schemes.
- **Arthur Andersen & Co.**: EFCA’s outside auditor. The firm and individual auditors faced serious criticism and litigation over their failure to detect the fraud, although the criminal prosecutions principally focused on EFCA executives and employees.
- **Policyholders, shareholders, creditors, regulators, and investors**: These were the principal victims. The fraud overstated assets and earnings and caused investors to buy or retain EFCA securities at artificially inflated values.

### Main allegations and methods

The central allegation was that EFCA had **systematically fabricated insurance business and financial results**.

The principal techniques included:

1. **Fictitious life-insurance policies**  
   EFCA recorded policies that had never been sold to real customers. The company created false applications, medical information, agent records, and policy files.

2. **False reinsurance transactions**  
   The company used purported reinsurance arrangements to make the fictitious policies appear legitimate and to generate reported assets and profits.

3. **Falsified accounting records**  
   Employees altered ledgers, policy files, computer records, and supporting documents to conceal the absence of real business and to make the company’s financial statements appear sound.

4. **Inflated earnings and assets**  
   The false policies and related transactions allowed EFCA to report earnings and financial strength that it did not actually possess.

5. **Securities-law violations**  
   The government alleged that EFCA executives used materially false financial statements and other misrepresentations in connection with the purchase and sale of EFCA stock and other securities.

6. **Concealment and obstruction**  
   When auditors, regulators, or others asked questions, employees allegedly created additional documents, moved records, and gave misleading explanations to preserve the appearance of a legitimate insurance operation.

The fraud was not merely a single false entry or isolated accounting irregularity. It was a continuing scheme involving senior management, operating personnel, and a large volume of fabricated documentation.

### Main events

- **1960**: Equity Funding Corporation of America was founded by Stanley Goldblum and others. It expanded rapidly into insurance and related financial services.
- **Late 1960s–early 1970s**: The company’s reported growth and profitability increasingly depended on fictitious insurance policies and related accounting entries. The scheme became extensive and institutionalized.
- **Early 1973**: Internal participants and former employees began disclosing information about the fraud. Investigators and regulators received allegations that EFCA’s insurance records contained large numbers of nonexistent policies.
- **April 2, 1973**: The fraud became public after investigators and law-enforcement authorities moved against the company. EFCA’s stock trading was halted, and the company’s offices and records became the focus of investigations.
- **April 1973**: Regulators placed the insurance subsidiaries into conservation or receivership proceedings. The company’s reported assets and earnings were revealed to be dramatically overstated.
- **1973–1974**: Federal prosecutors brought criminal charges against Goldblum and other executives and employees. Several participants pleaded guilty or cooperated with the government.
- **1974**: Stanley Goldblum pleaded guilty to federal fraud-related charges. He was later sentenced to prison.
- **1970s**: Civil actions followed against EFCA officers, directors, auditors, underwriters, and others. The litigation included securities-fraud claims by investors and claims involving the adequacy of the company’s audits and disclosures.

### Outcome

EFCA collapsed and was effectively dismantled. Its insurance operations went into regulatory proceedings, and shareholders suffered enormous losses as the stock became virtually worthless. Policyholders and creditors were handled through liquidation, receivership, and related insurance-regulatory processes.

**Stanley Goldblum** pleaded guilty and received a federal prison sentence. Other executives and employees were convicted, pleaded guilty, or cooperated with prosecutors. **Michael Riordan** and other insiders became important government witnesses, helping establish how the fictitious-policy system operated.

The scandal also produced substantial civil litigation and contributed to broader concern about:

- auditor independence and audit quality;
- management ov
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall peregrine — 9/13; missed: Matthew Gless (CFO), ~$500 million revenue overstatement, factoring / selling receivables to banks, Remedy division sold to BMC</summary>

```
## Overview

The **Peregrine Systems accounting fraud** was a major U.S. corporate-accounting scandal involving **Peregrine Systems, Inc.**, a San Diego software company that sold IT-management software. The fraud centered on overstated revenue, fictitious or improper transactions, and misleading financial statements, especially during the late 1990s and 2000–2002. The matter produced criminal convictions, SEC enforcement actions, shareholder litigation, bankruptcy, and substantial restitution.

The period **2002–2008** covers the discovery and collapse of the company, criminal and civil proceedings, and the later resolution of claims against executives and auditors.

## Main parties

- **Peregrine Systems, Inc.** — the public company accused of materially misstating its revenue and financial condition.
- **Former Peregrine executives and employees**, especially:
  - **Stephen P. Gardner**, former chief executive officer and chairman.
  - **Gary A. Mulgrew**, former chief financial officer.
  - **John A. Moores**, Peregrine’s founder and former chairman/CEO; he was not criminally charged in the principal fraud prosecution, but his role and compensation were examined in civil and shareholder proceedings.
  - **David M. Schrock**, a former Peregrine executive involved in the accounting scheme and later a cooperating witness.
- **Arthur Andersen LLP** — Peregrine’s outside auditor during much of the relevant period; it was criticized for audit failures, although the firm’s collapse after the Enron scandal complicated the litigation.
- **The Securities and Exchange Commission (SEC)** — brought civil enforcement proceedings.
- **The U.S. Department of Justice and federal prosecutors in San Diego** — pursued criminal charges.
- **Peregrine shareholders and creditors** — pursued securities and bankruptcy-related claims.
- **Hewlett-Packard Company** — acquired Peregrine’s remaining operating business in bankruptcy in 2003.

## Core allegations and accounting issues

The central allegation was that Peregrine executives caused the company to report **false or materially inflated revenue** and earnings.

The principal methods included:

1. **Fictitious or unsupported sales**
   - Peregrine recorded revenue from transactions that were not genuine sales or were not supported by valid customer contracts.
   - Some transactions involved purported resellers or distributors that did not have the ability or intention to purchase the reported quantities.

2. **Improper “round-trip” or reciprocal transactions**
   - Peregrine allegedly entered arrangements in which it sold software or licenses while providing money, credits, or other economic benefits that effectively funded the supposed customer’s purchase.
   - These transactions lacked the substance required for revenue recognition.

3. **Premature revenue recognition**
   - Revenue was recorded before the relevant software had been delivered, before customer acceptance requirements were met, or while significant obligations remained outstanding.

4. **Manipulation of reseller transactions**
   - Peregrine used distributors and resellers to make sales appear larger or more final than they really were.
   - The company allegedly concealed side agreements and other terms that undermined the reported revenue.

5. **Misleading public filings**
   - The SEC alleged that Peregrine’s filings overstated revenue and earnings and failed to disclose material facts about its sales practices and accounting.

The fraud was significant because Peregrine’s reported growth and profitability depended heavily on these transactions. Once the questionable revenue was removed, the company’s financial condition was dramatically worse than investors had been told.

## Key people and roles

### Stephen P. Gardner

Gardner was Peregrine’s former CEO and chairman. Prosecutors alleged that he participated in and directed efforts to inflate revenue and mislead investors. He became the principal criminal defendant in the case.

In **2003**, Gardner pleaded guilty to federal securities-fraud-related charges. In **2004**, he was sentenced to **eight years in prison** and ordered to pay substantial restitution. He was also subject to SEC-related bars and civil penalties.

### Gary A. Mulgrew

Mulgrew was Peregrine’s former CFO. He was accused of helping implement and conceal the improper accounting. He pleaded guilty in **2003** to federal charges and received a prison sentence and restitution obligations.

### David M. Schrock

Schrock was a former Peregrine executive who became a cooperating witness for the government. His testimony and information helped prosecutors describe how the transactions were structured and how revenue was recorded.

### John A. Moores

Moores founded Peregrine and was a prominent technology entrepreneur. He had served as CEO and chairman before Gardner. Although he was not the principal criminal defendant in the federal prosecution, shareholders and regulators examined the company’s governance, executive compensation, and the conduct of senior management during the period of inflated reporting.

### Arthur Andersen

Arthur Andersen audited Peregrine’s financial statements. The SEC and private plaintiffs alleged that the auditor failed to detect or properly respond to warning signs, including unusual reseller transactions and inadequate support for reported revenue. Litigation against Andersen was affected by the firm’s 2002 criminal conviction in the Enron matter and subsequent dissolution of its U.S. audit practice.

## Main events and dates

### 2002: Discovery and collapse

- **Early 2002:** Questions arose about Peregrine’s accounting and revenue-recognition practices, including concerns about reseller transactions and the substance of reported sales.
- **May 2002:** Peregrine disclosed that it would delay filing its annual report and that its financial statements might need to be restated.
- **May–June 2002:** The company announced that previously repo
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall worldcom — 12/14; missed: capitalised line costs, Clinton, Mississippi headquarters</summary>

```
## Overview

The WorldCom scandal was a major U.S. accounting fraud that collapsed in 2002. WorldCom, Inc., then the country’s second-largest long-distance telecommunications company, overstated profits by improperly recording ordinary network expenses as capital investments. The fraud was uncovered in June 2002, led to WorldCom’s bankruptcy, criminal convictions and civil penalties, and ultimately produced the reorganization of the company as MCI, Inc.

## Parties and principal people

- **WorldCom, Inc.** — the company that committed the accounting fraud.
- **Bernard J. “Bernie” Ebbers** — WorldCom’s founder and chief executive officer until April 2002.
- **Scott D. Sullivan** — chief financial officer; the central accounting executive who directed or approved the improper entries.
- **David F. Myers** — controller and later senior vice president; involved in preparing and implementing the accounting entries.
- **Arthur Andersen LLP** — WorldCom’s outside auditor. It audited WorldCom’s financial statements and was criticized for failing to detect or prevent the fraud, although it was not criminally charged in the WorldCom case.
- **Securities and Exchange Commission (SEC)** — brought the principal civil enforcement action.
- **U.S. Department of Justice and federal prosecutors** — pursued criminal charges against executives.
- **WorldCom creditors, shareholders, employees, and bondholders** — suffered substantial losses.
- **MCI, Inc.** — the reorganized company that emerged from bankruptcy.

## The accounting fraud

WorldCom’s principal business was carrying telephone and data traffic over its network. It paid other telecommunications companies “line costs” for access and transmission capacity. These were ordinary operating expenses and should generally have been recorded immediately on the income statement.

Beginning in 2000 and continuing into 2002, WorldCom improperly transferred large amounts of line costs from expense accounts to capital-asset accounts. By treating the costs as capital expenditures, WorldCom:

1. reduced reported operating expenses;
2. increased reported operating income and earnings;
3. made its financial results appear to meet Wall Street expectations; and
4. concealed the deterioration of its business.

The company also used other improper accounting techniques, including releasing reserves and making unsupported entries to improve reported results. The SEC ultimately alleged that WorldCom had overstated its income by approximately **$11 billion**, making it one of the largest accounting frauds in U.S. history at the time.

The alleged motives included pressure to meet earnings targets, maintain WorldCom’s stock price, preserve executive credibility, and support the company’s debt and acquisition strategy. Ebbers had also accumulated substantial personal debt secured by WorldCom stock, creating an additional alleged financial incentive to avoid a falling share price.

## Main events and dates

### 1998–2000: Expansion and growing pressure

WorldCom expanded rapidly through acquisitions, including its 1998 acquisition of MCI. The telecommunications downturn and the collapse of the technology bubble weakened demand and increased pressure on management to produce acceptable earnings.

In 2000, WorldCom’s board rejected a proposed merger with Sprint after antitrust opposition. The company’s financial condition continued to deteriorate.

### 2001–early 2002: Improper entries and management changes

WorldCom’s finance personnel began or intensified the practice of capitalizing line costs. According to later evidence, Sullivan and Myers were central to the entries, while prosecutors argued that Ebbers knew of and participated in the broader scheme.

In **April 2002**, the board removed Ebbers as CEO. He was replaced by **John W. Sidgmore**, formerly a senior executive at UUNET, a WorldCom subsidiary. Ebbers received a severance package reported at roughly $1.5 million annually for life, although later litigation and bankruptcy proceedings affected his financial position.

### May–June 2002: Internal discovery

In **May 2002**, WorldCom’s internal audit department, led by **Cynthia Cooper**, began investigating unusual capital expenditures. Cooper’s team, including internal auditor **Gwendolyn “Gwen” Bennett**, found that line costs had been moved into capital accounts without proper support.

Cooper reported the findings to the audit committee and senior directors. The investigation proceeded despite resistance from Sullivan and other finance executives.

On **June 20, 2002**, WorldCom’s audit committee met and learned the extent of the accounting irregularities. Sullivan was questioned and ultimately dismissed.

On **June 25, 2002**, WorldCom announced that it had improperly accounted for approximately **$3.8 billion** in expenses. The announcement caused the stock price to collapse and triggered investigations by the SEC, the Justice Department, Congress, and other authorities.

WorldCom later expanded the restatement. In **August 2002**, it disclosed additional accounting problems, bringing the estimated overstatement of income to approximately **$7.1 billion** at that stage. Subsequent restatements increased the total to roughly **$11 billion**.

### July 2002: Bankruptcy

On **July 21, 2002**, WorldCom filed for protection under **Chapter 11** of the U.S. Bankruptcy Code in the Southern District of New York. At the time, it was the largest corporate bankruptcy in U.S. history, with approximately $41 billion in assets and more than $30 billion in debt, although later surpassed by other bankruptcies.

The bankruptcy proceedings involved claims by creditors, shareholders, employees, and counterparties. WorldCom also faced extensive securities litigation and regulatory claims.

### 2002–2003: Criminal prosecutions

In **August 2002**, Scott Sullivan pleaded guilty to securities fraud, conspiracy, and related charges and agreed to cooperate with prosecutors. David M
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall rdc — 6/12; missed: William Pietruszewski (compliance chief), deferred-prosecution agreement, oxycodone and fentanyl shipments, suspicious orders: ~8,300 flagged, 4 reported, Chapter 11, March 2020, Judge George Daniels</summary>

```
The case was **United States v. Rochester Drug Co-Operative, Inc. and Laurence F. Doud**, a federal criminal prosecution in the **Southern District of New York**.

## Parties and key people

- **United States Department of Justice / U.S. Attorney’s Office for the Southern District of New York**: the prosecution.
- **Rochester Drug Co-Operative, Inc. (RDC)**: a Rochester, New York–based pharmaceutical wholesaler and cooperative owned by independent pharmacies.
- **Laurence F. Doud**: RDC’s chief executive officer during the relevant period.
- **RDC’s chief compliance officer** was also a central figure in the government’s allegations and later pleaded guilty in a related matter. The government alleged that Doud and RDC disregarded or weakened the company’s controlled-substance compliance obligations.
- The case concerned RDC’s distribution of controlled substances, especially **opioids**, to pharmacies and other customers.

## Allegations and issues

The government alleged that RDC and Doud failed to maintain and enforce an effective system for detecting and reporting suspicious orders of controlled substances, as required by the **Controlled Substances Act** and Drug Enforcement Administration rules.

The principal allegations were that:

1. **RDC distributed unusually large quantities of opioids** to certain pharmacies, including quantities the government characterized as suspicious.
2. RDC allegedly **failed to identify, investigate, and report suspicious orders** to the DEA.
3. Doud allegedly **knowingly caused or directed the company’s failure to comply** with its controlled-substance obligations, despite warnings and internal concerns.
4. The government also alleged that RDC and Doud made **false or misleading statements to the DEA** about the company’s compliance program and its handling of suspicious orders.

The criminal charges were not simply that RDC shipped opioids. The central issue was whether the defendants knowingly participated in a scheme to evade the legal duty to monitor and report suspicious controlled-substance orders.

## Main events

- **2017–2018:** The DEA investigated RDC’s controlled-substance distribution and compliance practices. The investigation focused on opioid shipments and the company’s suspicious-order monitoring.
- **April 2019:** The DEA issued an **immediate suspension order** against RDC’s controlled-substance registration, effectively stopping it from distributing controlled substances. The action was a major business and regulatory event for the company.
- **October 2019:** Federal prosecutors charged **RDC and Doud** in Manhattan federal court. The indictment alleged conspiracy and substantive offenses involving controlled-substance distribution and false statements.
- **2019–2021:** The case involved extensive litigation over the scope of the charges, the company’s compliance system, and the government’s evidence concerning suspicious orders and communications with regulators.
- **October 2021:** Doud pleaded guilty to a federal charge arising from the case—**conspiracy to distribute controlled substances**. RDC also entered a guilty plea to a related federal offense.
- **2022:** The court imposed sentence. Doud received **27 months in prison**, followed by supervised release, and was ordered to pay a monetary penalty. RDC was sentenced to a **criminal fine and forfeiture**, with the total financial consequences reported at approximately **$20 million**.

## Outcome

The case ended in **guilty pleas rather than a trial**:

- **Laurence Doud** admitted responsibility for conspiring to distribute controlled substances without complying with the applicable monitoring and reporting requirements. He was sentenced in 2022 to **27 months’ imprisonment** and financial penalties.
- **Rochester Drug Co-Operative** pleaded guilty to a federal criminal charge and received a substantial fine and forfeiture.

The criminal case was separate from, but related to, the DEA’s 2019 administrative suspension of RDC’s controlled-substance registration and the broader civil and regulatory consequences of the opioid-distribution investigation.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall insys — 12/15; missed: 'titration' rap video, RICO conspiracy conviction, May 2019, $225m DOJ settlement; Chapter 11 June 2019</summary>

```
The **Insys Therapeutics Subsys racketeering case** was a federal criminal prosecution arising from the company’s marketing of **Subsys**, a sublingual fentanyl spray, and related efforts to induce prescriptions and obtain insurance reimbursement.

## Parties and case

- **United States v. Insys Therapeutics, Inc.**, No. 16-cr-10343 (D. Mass.), was brought by the **U.S. Attorney’s Office for the District of Massachusetts**, with assistance from the FBI, HHS-OIG, and other agencies.
- The principal corporate defendant was **Insys Therapeutics, Inc.**, headquartered in Chandler, Arizona.
- The case also involved former Insys executives and sales personnel, including:
  - **John N. Kapoor**, Insys’s founder and former executive chairman;
  - **Michael G. Babich**, former chief executive officer;
  - **Alec Burlakoff**, former vice president of sales;
  - **Richard M. Simon**, former national director of sales;
  - **Joseph A. Rowan**, former regional sales director;
  - **Sunil J. Bhaskara**, former vice president of sales;
  - **Jonathan R. Roper**, a former sales representative;
  - and several physicians, including **Dr. John Couch**, who pleaded guilty in a related prosecution.

The case was commonly described as a **racketeering conspiracy** case because prosecutors alleged that Insys executives operated an enterprise whose activities included bribery, fraud, and illegal promotion of Subsys.

## What Subsys was and the central allegations

**Subsys** was a fentanyl product approved by the FDA for **breakthrough cancer pain in opioid-tolerant patients already receiving around-the-clock opioid therapy**. It was extremely potent and expensive.

Prosecutors alleged that Insys executives and employees:

1. **Paid kickbacks and bribes to physicians**  
   Insys allegedly used sham “speaker programs”—nominal educational events at restaurants or other venues—to pay physicians for prescribing Subsys. Some doctors allegedly received large payments despite providing little or no legitimate educational service.

2. **Induced prescriptions outside the FDA-approved population**  
   The government alleged that the company targeted doctors who treated patients without cancer or without the required opioid tolerance, and encouraged prescriptions for conditions such as back pain, migraines, and other chronic-pain conditions.

3. **Used deceptive insurance-reimbursement practices**  
   Insys allegedly created or used a reimbursement-support operation to mislead insurers and pharmacy-benefit managers about patients’ diagnoses, prior treatments, and medical necessity. The alleged purpose was to secure coverage for expensive Subsys prescriptions that otherwise would have been rejected.

4. **Manipulated prescriptions and prior authorizations**  
   Prosecutors alleged that employees sometimes contacted insurers while posing as doctors’ offices or otherwise concealed Insys’s role in obtaining approvals.

5. **Retaliated against employees who objected**  
   The indictment alleged that executives fired or marginalized employees who questioned the practices or refused to participate.

The government characterized these activities as a coordinated scheme to increase Subsys sales and revenue, rather than legitimate promotion of an FDA-approved medicine.

## Key people and roles

### John Kapoor

Kapoor founded Insys and was its former executive chairman. Prosecutors portrayed him as the senior leader who approved or directed the bribery and reimbursement schemes. He was charged with racketeering conspiracy, conspiracy to commit wire fraud, and related offenses.

### Michael Babich

Babich was Insys’s former CEO. He was alleged to have participated in and supervised the company’s illegal marketing and reimbursement practices.

### Alec Burlakoff

Burlakoff was a senior sales executive and a central government witness after pleading guilty. He described the company’s use of sham speaker programs and pressure on sales personnel to generate prescriptions.

### Richard Simon, Joseph Rowan, Sunil Bhaskara, and Jonathan Roper

These defendants were sales executives or representatives alleged to have participated in the speaker-program, physician-payment, and prescription-generation schemes. Several pleaded guilty and cooperated with prosecutors.

### Physicians

Several physicians were charged in related cases. **Dr. John Couch**, a prominent Subsys prescriber, pleaded guilty to accepting payments and participating in the scheme. Other doctors, including **Dr. Sanjay K. Reddy**, were prosecuted in related matters involving illegal prescribing or kickbacks.

## Main events and dates

- **2012–2015:** The alleged bribery, sham-speaker, and reimbursement conduct largely occurred during this period. Insys’s Subsys sales grew substantially.
- **December 2016:** Federal prosecutors in Massachusetts announced charges against Insys and several executives in connection with the alleged racketeering and fraud scheme.
- **2017–2018:** Multiple former Insys executives and sales personnel pleaded guilty and began cooperating with the government. The government’s case increasingly relied on insider testimony, company communications, sales records, and evidence concerning physician payments.
- **October 2018:** Kapoor and other senior defendants went to trial in federal court in Boston. The trial focused on whether the defendants knowingly joined an enterprise designed to increase Subsys prescriptions through kickbacks and fraud.
- **May 2, 2019:** A federal jury convicted **Kapoor, Babich, Burlakoff, Simon, Rowan, and Bhaskara** of racketeering conspiracy and related offenses. **Roper** was also convicted in the broader prosecution.
- **September 2019:** Kapoor was sentenced to **66 months in prison** and ordered to forfeit approximately **$59 million**. He was also fined.
- **2019–2020:** Other defendants received prison sentences, probation, or other penalties depending on their roles and cooperation. Insys faced separate civil 
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall purdue — 11/16; missed: 2020 guilty plea, $8.3bn in penalties, McKinsey's role / settlement, Massachusetts AG Healey complaint (2018), 2010 abuse-deterrent reformulation, Dopesick / Empire of Pain</summary>

```
## Overview

The Purdue Pharma opioid litigation concerned allegations that Purdue and members of the Sackler family helped create and sustain the U.S. opioid crisis through aggressive, misleading marketing of OxyContin and other opioids. It produced thousands of lawsuits, a 2007 federal criminal and civil settlement, Purdue’s 2019 bankruptcy, years of disputes over whether the Sacklers could obtain personal protection from opioid claims, and a 2024 Supreme Court decision that invalidated the original bankruptcy settlement. A revised settlement was then approved in November 2024.

The principal corporate defendant was **Purdue Pharma L.P.** The principal individual defendants were members of the **Sackler family**, especially former Purdue owners and directors **Richard Sackler**, **Mortimer D. Sackler**, **Raymond Sackler**, **Kathe Sackler**, **David Sackler**, **Jonathan Sackler**, **Beverly Sackler**, and others. The Sacklers denied wrongdoing in the civil litigation and did not admit liability in the bankruptcy settlement.

## Purdue, OxyContin, and the allegations

Purdue introduced **OxyContin**, an extended-release oxycodone product, in 1996. The company promoted it as providing long-lasting pain relief and emphasized that addiction risk was low. Plaintiffs—including states, cities, counties, tribes, hospitals, individuals, and other entities—alleged that Purdue:

- overstated OxyContin’s duration and safety;
- minimized addiction, dependence, overdose, and withdrawal risks;
- promoted opioids for broader and longer-term use than medically justified;
- used sales representatives, continuing-medical-education programs, sponsored speakers, and other marketing channels to influence prescribers;
- continued aggressive marketing despite evidence of misuse, diversion, addiction, and overdose;
- helped create or worsen the opioid epidemic, causing public-health, treatment, emergency-response, and other costs.

The Sacklers were alleged to have exercised substantial control over Purdue, approved or benefited from the company’s opioid strategy, and received billions of dollars in distributions. The family disputed the allegations and argued, among other things, that the opioid crisis had multiple causes and that individual Sackler liability should not be resolved through Purdue’s bankruptcy.

## Key people and roles

- **Richard Sackler**: physician, former Purdue president and chief executive, later chairman; a central figure in Purdue’s OxyContin strategy and internal communications.
- **Mortimer D. Sackler** and **Raymond Sackler**: brothers who acquired Purdue’s predecessor and built the family’s pharmaceutical business; both died before the later bankruptcy litigation.
- **Kathe Sackler, David Sackler, Jonathan Sackler, Beverly Sackler**, and other family members: owners, directors, or beneficiaries of Purdue-related entities. The family’s ownership and governance structure varied over time.
- **Craig Landau**: Purdue president and CEO during the bankruptcy period.
- **Judge Robert D. Drain**: U.S. Bankruptcy Judge for the Southern District of New York, who presided over Purdue’s Chapter 11 case and approved the original 2021 plan.
- **Judge Colleen McMahon**: U.S. District Judge who rejected the original plan’s Sackler releases in December 2021.
- **The U.S. Trustee**: a Justice Department office that objected to the nonconsensual releases of claims against the Sacklers.
- **State attorneys general, local governments, tribes, and individual plaintiffs**: major creditor and claimant groups. States were divided: some supported the settlement, while others—including initially California, Connecticut, Delaware, Maryland, New York, Oregon, Rhode Island, Vermont, and Washington—opposed or challenged aspects of it.
- **The Supreme Court**: decided the central legal question in *Harrington v. Purdue Pharma L.P.* in 2024.

## 2007 federal settlement

In **May 2007**, Purdue Pharma L.P., Purdue Pharma Inc., and three executives—**Michael Friedman**, **Howard Udell**, and **Paul Goldenheim**—pleaded guilty in federal court in Virginia to misbranding OxyContin by falsely representing or implying that it was less addictive, less subject to abuse, and less likely to cause withdrawal than other pain medicines.

The settlement totaled approximately **$634.5 million**. Purdue paid a criminal fine and forfeiture, and the executives paid individual penalties. The agreement addressed the company’s past marketing conduct but did not end later civil litigation over the broader opioid crisis.

## Escalation of opioid litigation

During the 2010s, overdose deaths and opioid-related public costs rose sharply. Governments and private plaintiffs filed thousands of suits against Purdue, other opioid manufacturers, distributors, pharmacies, doctors, and related entities.

Important developments included:

- **2015–2017**: states and local governments increasingly sued Purdue and other opioid companies.
- **2017**: Purdue announced that it would stop directly promoting OxyContin to doctors in the United States, while continuing to sell the product.
- **October 2017**: the U.S. Department of Health and Human Services declared the opioid crisis a public-health emergency.
- **December 2017**: the Judicial Panel on Multidistrict Litigation centralized many federal opioid cases before **Judge Dan Aaron Polster** in the Northern District of Ohio. The MDL was *In re National Prescription Opiate Litigation*, No. 1:17-md-2804.
- **2018–2019**: Purdue faced growing settlement pressure, state lawsuits, and claims that the Sacklers had transferred billions of dollars from Purdue to family trusts and overseas accounts before bankruptcy.

The alleged transfers became a major issue. Plaintiffs argued that the Sacklers had extracted approximately **$10 billion** from Purdue, much of it during years when the company was facing mounting opioid liabilities. The Sacklers said the distributions were lawful and that the money was not
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall sony_hack — 7/15; missed: Amy Pascal (co-chair), Scott Rudin (producer) e-mails, Christmas Day limited / online release, January 2015 sanctions on North Korea, WikiLeaks published the archive (April 2015), employee class action settled (~$8m), Park Jin Hyok indicted (2018), Spider-Man / Marvel, Jolie e-mails</summary>

```
## Overview

The **2014 Sony Pictures Entertainment (SPE) hack** was a destructive cyberattack and data breach against the U.S. film studio **Sony Pictures Entertainment**, attributed by the U.S. government to the **North Korean government**. It became an international incident because the attackers combined theft of sensitive corporate data with threats against theaters showing the comedy film **_The Interview_**, which depicted a fictional plot to assassinate North Korean leader **Kim Jong Un**.

## Parties and key people

- **Sony Pictures Entertainment (SPE):** The California-based film and television studio targeted in the attack. It was then led by **Michael Lynton**, chairman and CEO.
- **Guardians of Peace (GOP):** The name used by the attackers, who released stolen files and demanded that Sony stop distributing _The Interview_.
- **North Korea:** The U.S. government attributed the operation to North Korean actors, although North Korea denied responsibility and praised the attack.
- **U.S. government:** The FBI investigated and publicly blamed North Korea. President **Barack Obama** later announced sanctions.
- **Sony Pictures executives and employees:** Their emails, personal information, salaries, medical and employment data, and internal business documents were exposed.
- **Film personnel:** _The Interview_ was directed by **Seth Rogen and Evan Goldberg** and starred **Rogen and James Franco**. The film’s fictional assassination plot made it the central focus of the attackers’ demands.

## Main events

### Initial intrusion and data theft

The attackers appear to have gained access to Sony’s network before the public disclosure in late 2014. On **November 24, 2014**, employees arriving at work saw computers displaying a threatening image from the “Guardians of Peace.” Sony’s systems were disrupted, and large quantities of data were stolen.

The attackers released, over several weeks:

- Unreleased Sony films
- Employee Social Security numbers and other personal information
- Executive emails
- Salary and compensation information
- Medical and employment records
- Internal business plans and communications
- Information about Sony’s relationships with actors, producers, and other studios

The leaked emails included embarrassing and sometimes offensive comments by executives, creating a separate reputational crisis for Sony.

### Threats over _The Interview_

On **December 8, 2014**, the attackers began releasing more stolen material and demanded that Sony cancel _The Interview_. The film portrayed Rogen and Franco’s characters being recruited to assassinate Kim Jong Un.

On **December 16, 2014**, GOP issued a threat against theaters showing the film, invoking the September 11 attacks and warning audiences to avoid theaters during the film’s release. The threat caused major theater chains—including **Regal, AMC, Cinemark, Carmike, and Cineplex**—to cancel or reconsider screenings.

On **December 17**, Sony canceled the planned **December 25** wide theatrical release. Sony also canceled the film’s New York premiere. President Obama criticized that decision at a **December 19** press conference, saying Sony had made a mistake by allowing a “dictator” to impose censorship through threats.

### U.S. attribution

On **December 19, 2014**, the **FBI** publicly stated that it had concluded North Korea was responsible. The FBI cited technical indicators, including similarities to earlier malware and infrastructure associated with North Korean cyber activity.

North Korea denied conducting the attack but called it a “righteous deed.” The attribution remained debated by some private-sector security researchers, but the official U.S. position was that North Korea directed the operation.

### Release of _The Interview_

After initially canceling the wide release, Sony made the film available on **December 24, 2014**, through selected independent theaters and digital platforms, including **YouTube Movies, Google Play, Xbox Video, and Sony’s own website**. It later received a broader theatrical release.

The film earned substantial attention and became one of Sony’s more successful digital releases, although its theatrical revenue was limited compared with a normal major-studio release.

## Legal and policy issues

The incident raised several major issues:

1. **Cybersecurity and corporate responsibility:**  
   The breach exposed weaknesses in Sony’s network security and internal handling of sensitive employee and business information.

2. **Extortion and threats against theaters:**  
   The attackers attempted to use stolen information and physical-threat warnings to stop distribution of a film.

3. **Free expression and censorship:**  
   The cancellation was widely viewed as an example of a foreign government or foreign-backed group attempting to suppress speech through cyberattacks and intimidation.

4. **Attribution:**  
   The FBI and U.S. government attributed the attack to North Korea, while some outside researchers questioned whether the public evidence conclusively established state responsibility.

5. **Privacy and employment consequences:**  
   Employees’ personal data and private communications were exposed. The leaks also led to public scrutiny of executive conduct and workplace culture.

## Aftermath and outcome

On **January 2, 2015**, President Obama announced new U.S. sanctions against North Korea in response to the cyberattack. The sanctions targeted North Korean government agencies and officials and were described as the first U.S. response specifically tied to the Sony incident.

Sony faced significant operational, financial, and reputational damage, including:

- Costs associated with restoring systems and investigating the breach
- Loss of control over unreleased films and confidential information
- Employee privacy harms
- Public embarrassment from leaked emails
- Disruption to the release of _The Interview_

The attack did not permanently prevent the film’s release,
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall bridgegate — 14/15; missed: Mastro / Gibson Dunn internal report</summary>

```
## Overview

“Bridgegate” was the political scandal arising from the closure of several access lanes from **Fort Lee, New Jersey, to the George Washington Bridge** in September 2013. The closures caused severe traffic congestion and were widely alleged to be political retaliation against **Fort Lee Mayor Mark Sokolich**, a Democrat who had not endorsed Republican **Chris Christie** for governor. The scandal produced criminal convictions, civil litigation, congressional and legislative investigations, and major political damage to Christie, although Christie himself was never criminally charged.

## Parties and principal people

- **Chris Christie** — Republican governor of New Jersey from 2010 to 2018. He denied ordering or knowing about the lane closures. He was not charged criminally.
- **Mark Sokolich** — Democratic mayor of Fort Lee. He alleged that the closures were retaliation because he did not endorse Christie’s 2013 reelection campaign.
- **Bill Baroni** — Christie’s deputy executive director at the **Port Authority of New York and New Jersey**. He helped oversee the agency’s New Jersey operations and initially told legislators the closures were part of a legitimate traffic study.
- **David Wildstein** — a Christie political ally and former mayor of Livingston, New Jersey, appointed as the Port Authority’s director of interstate capital projects. He was involved in implementing the closures and later pleaded guilty.
- **Bridget Anne Kelly** — Christie’s deputy chief of staff. On August 13, 2013, she emailed Wildstein: “Time for some traffic problems in Fort Lee,” followed by “Got it.” She was fired in January 2014.
- **Bill Stepien** — Christie’s campaign manager in 2013 and former chief of staff. Evidence showed he was involved in the political and communications response, but he was not charged.
- **Port Authority of New York and New Jersey** — the bistate agency operating the George Washington Bridge. Its executive director was **Patrick Foye**, who opposed the closures and ordered the lanes reopened.
- **David Samson** — Port Authority chairman and a Christie ally. He resigned in 2014 amid the scandal but was not charged in Bridgegate itself.
- **The United States and the State of New Jersey** — prosecutors brought the federal criminal case against Baroni and Wildstein.
- **Fort Lee residents and commuters** — the people directly affected by the traffic disruption; some later pursued civil claims.

## The lane closures

On **September 9, 2013**, Port Authority officials closed three of the four access lanes from Fort Lee to the George Washington Bridge. The closures lasted through **September 13**, creating extensive congestion, delaying commuters, and interfering with emergency access.

The closures were carried out without adequate notice to Fort Lee officials and without the normal traffic-study procedures. The Port Authority’s executive director, Patrick Foye, learned of the closures and ordered the lanes reopened on September 13.

The central allegation was that the closures were not a genuine traffic study but an act of political retaliation against Mayor Sokolich. The defense position was that the closures were connected to a traffic study or operational decision, and that the defendants lacked the criminal intent alleged by prosecutors.

## Discovery of the emails and political fallout

On **January 8, 2014**, the New Jersey Legislature’s Assembly Transportation Committee subpoenaed documents from the Port Authority. The committee obtained emails, including Kelly’s “Time for some traffic problems in Fort Lee” message.

On **January 9, 2014**, Christie announced that he had fired Bridget Kelly after learning of her role and said that he had not known about the lane closures when they occurred.

On **January 16, 2014**, Christie held a lengthy press conference in which he apologized for the conduct of his staff, denied prior knowledge, and said he had been misled. He also said he had not been involved in a cover-up.

The scandal damaged Christie’s national political prospects. He had been viewed as a possible 2016 Republican presidential candidate, but the controversy contributed substantially to the collapse of that effort. Christie ended his presidential campaign in **February 2016**.

## Criminal investigation and charges

The **U.S. Attorney’s Office for the District of New Jersey**, initially under U.S. Attorney **Paul J. Fishman**, investigated the matter.

### David Wildstein

Wildstein pleaded guilty on **May 1, 2015**, to conspiracy to commit fraud and conspiracy against the civil rights of Fort Lee residents. He admitted that the lane closures were intended to punish Sokolich for not endorsing Christie and to conceal that political motive.

### Bill Baroni and Bridget Kelly

A federal grand jury indicted Baroni and Kelly on **May 1, 2015**. The indictment alleged that they:

- conspired to misuse Port Authority property and resources;
- committed wire fraud by misrepresenting the purpose of the closures;
- deprived Fort Lee and the public of the honest services of Port Authority officials; and
- violated the civil rights of Fort Lee residents by intentionally causing the traffic disruption.

The prosecution argued that Baroni and Kelly used a purported traffic study as a cover for political retaliation and then participated in a cover-up.

## Trial and convictions

The trial of Baroni and Kelly began in **September 2016** in federal court in Newark before Judge **Susan D. Wigenton**.

On **November 4, 2016**, the jury found both defendants guilty on all or nearly all major counts. The verdicts rested on the theory that they had misused Port Authority resources and defrauded the agency and the public.

On **March 29, 2017**, Judge Wigenton sentenced:

- **Bill Baroni** to **24 months in prison**, followed by supervised release;
- **Bridget Kelly** to **18 months in prison**, followed by supervised release.

They were also ordered to pay fines and restitution. 
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall clinton_email — 14/15; missed: FOIA litigation (Judicial Watch) / monthly releases</summary>

```
## Overview

The controversy concerned Hillary Clinton’s use, while U.S. secretary of state, of a privately operated email system—primarily the domain **clintonemail.com**—for official and personal communications. The FBI investigated whether she or others mishandled classified information, obstructed justice, or violated federal records and security laws. The investigation did not result in criminal charges, but it became a major issue in the 2016 presidential election.

## Parties and key people

- **Hillary Rodham Clinton** — Secretary of State from January 21, 2009, to February 1, 2013; used a private email account and server for State Department business. She was the 2016 Democratic presidential nominee.
- **Bill Clinton** — Former president and Hillary Clinton’s husband; his office and personal communications were among the reasons Clinton said she used a single account, though the server was administered through the Clinton family’s private arrangements.
- **The U.S. Department of State** — The agency responsible for official records and diplomatic communications.
- **The Federal Bureau of Investigation (FBI)** — Investigated the handling of classified information and the private email system.
- **James B. Comey** — FBI director during the investigation; announced the bureau’s recommendation against prosecution on July 5, 2016, and notified Congress on October 28 and November 6, 2016, about later email developments.
- **Loretta E. Lynch** — Attorney general during most of the investigation. She accepted the FBI and career prosecutors’ recommendation not to charge Clinton.
- **John H. Durham** — U.S. attorney appointed in 2016 to examine the FBI’s handling of the Clinton investigation and related matters; his later review was separate from the original investigation.
- **David Kendall and other Clinton attorneys** — Represented Clinton in responding to congressional and investigative inquiries.
- **The House Select Committee on Benghazi**, chaired by **Trey Gowdy** — Investigated the 2012 Benghazi attacks and brought substantial public attention to Clinton’s email practices.
- **The Republican National Committee and congressional Republicans** — Political opponents who argued that Clinton had evaded transparency and mishandled classified information.

## What happened

### Use of the private system

While secretary of state, Clinton used a private email account hosted on a server associated with her home in Chappaqua, New York, rather than using a standard State Department email account. The system was administered at various times by **Platte River Networks** and other technical personnel.

Clinton sent and received tens of thousands of work-related emails. Some contained information later determined to be classified, including material classified at the **confidential**, **secret**, or **top secret/sensitive compartmented information** levels. The central dispute was whether the information was classified when transmitted, whether Clinton knowingly or recklessly mishandled it, and whether the private system exposed government information to unauthorized access.

Clinton said she used one account for convenience and that she had not intended to create a secret system. She also said she had turned over all work-related emails and deleted personal ones.

### Benghazi and discovery of the server

The issue became public during congressional investigations into the **September 11–12, 2012, attacks in Benghazi, Libya**, which killed U.S. Ambassador **J. Christopher Stevens**, State Department officer **Sean Smith**, and CIA security contractors **Tyrone Woods** and **Glen Doherty**.

In **March 2015**, the House Benghazi Committee learned that Clinton had used a private email account. The State Department then requested that former secretaries provide work-related emails for archival purposes.

In **December 2014**, before the public controversy fully emerged, Clinton’s representatives had provided the State Department approximately **55,000 printed pages** of work-related emails. They did not initially provide emails they considered personal—approximately **31,000 messages**, according to Clinton’s account—which were deleted.

### FBI investigation

The FBI opened an investigation in **July 2015** into the possible mishandling of classified information and the security of Clinton’s email system. The investigation examined:

- Whether classified information had been improperly stored or transmitted;
- Whether Clinton or aides acted with the required criminal intent;
- Whether the server had been compromised by foreign actors;
- Whether emails had been deleted or concealed in violation of law;
- Whether Clinton’s aides had used appropriate security practices.

The FBI interviewed Clinton on **July 2, 2016**. It also interviewed key aides, including **Huma Abedin**, Clinton’s deputy chief of staff; **Cheryl Mills**, former chief of staff and an attorney; **Heather Samuelson**, who helped review emails; and **Bryan Pagliano**, who helped set up or administer the server.

The FBI identified **110 emails in 52 email chains** that contained classified information at the time they were sent or received, according to Comey’s July 2016 statement. The bureau also found additional classified material in emails that had not been properly marked as classified.

The FBI found no persuasive evidence that the server had been successfully compromised by foreign hackers, although it concluded that the system was vulnerable and that hostile actors may have attempted access. It also found that Clinton’s use of the system violated State Department policies and that she and her aides were “extremely careless” in handling sensitive information.

## Key legal and investigative issues

### Espionage Act and mishandling classified information

The principal potential criminal theory involved **18 U.S.C. § 793(f)**, part of the Espionage Act, which addresses gross negligence in the handling of national-defense i
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall depuy_asr — 8/14; missed: ~93,000 implanted, November 2013 settlement ~$2.5bn (later ~$4bn), Pinnacle sibling litigation (Dallas), Australian registry / 2009 withdrawal there, Warsaw, Indiana, Andrew Ekdahl (DePuy president)</summary>

```
## Overview

The **DePuy ASR hip recall and litigation** concerned defective metal-on-metal hip implants made by **DePuy Orthopaedics, Inc.**, a Johnson & Johnson subsidiary. The principal products were:

- **ASR XL Acetabular System**, used in total hip replacements; and
- **DePuy ASR Hip Resurfacing System**, used in hip resurfacing.

DePuy announced a worldwide recall on **August 24, 2010**, after data showed unusually high revision rates. The litigation largely alleged that the devices shed metal debris, causing tissue damage, elevated metal ions, pain, loosening, and premature failure, and that DePuy had inadequately tested, designed, marketed, and warned about the risks.

## Parties

### Defendants

- **DePuy Orthopaedics, Inc.**, the manufacturer.
- **Johnson & Johnson**, DePuy’s parent company, named in many cases.
- In some cases, related corporate entities, distributors, surgeons, hospitals, or insurers were also involved, but DePuy and Johnson & Johnson were the central defendants.

### Plaintiffs

Thousands of patients who received ASR implants in the United States and other countries. Many required, or expected to require, revision surgery to remove and replace the implants.

The litigation also involved:

- Plaintiffs’ steering committees and leadership counsel in the federal multidistrict litigation;
- Individual plaintiffs’ lawyers;
- Surgeons and medical experts;
- The U.S. Food and Drug Administration and foreign regulators, whose actions and safety findings were important to the cases.

## Main allegations and issues

Plaintiffs generally alleged that:

1. **The ASR design was defective.**  
   The large metal-on-metal bearing surfaces could generate metal wear debris and ions, particularly when the components were misaligned or otherwise performed poorly.

2. **The implants had excessive failure and revision rates.**  
   Patients alleged pain, instability, loosening, fractures, inflammation, pseudotumors, tissue necrosis, and other adverse local reactions.

3. **DePuy knew or should have known of the risks.**  
   Plaintiffs pointed to premarket testing, overseas clinical data, post-market complaints, and internal information allegedly showing higher-than-expected failures.

4. **Warnings and marketing were inadequate.**  
   Plaintiffs claimed DePuy failed to adequately warn surgeons and patients about the risks of metal debris, elevated cobalt and chromium levels, and early revision.

5. **The company continued selling and promoting the devices despite safety concerns.**

The principal legal theories included strict products liability for design defect and failure to warn, negligence, breach of warranty, fraud or fraudulent concealment, and related consumer-protection claims. DePuy denied wrongdoing and disputed causation, contending that outcomes varied by patient and surgical factors and that it had acted appropriately.

Important recurring issues included:

- whether the devices were defective under applicable state law;
- whether federal law preempted particular claims;
- whether a patient’s symptoms were caused by the implant or by other medical conditions;
- the significance of metal-ion blood levels and imaging findings;
- the extent of recoverable damages;
- and whether individual cases could fairly be tried together.

## Key people and roles

- **DePuy Orthopaedics and Johnson & Johnson executives and engineers:** corporate defendants whose design, testing, regulatory, marketing, and warning decisions were examined.
- **Implanting and revision surgeons:** witnesses concerning device performance, patient symptoms, surgical technique, and the need for revision.
- **Plaintiffs’ leadership counsel:** coordinated the federal multidistrict litigation and settlement negotiations.
- **U.S. District Judge Edgardo Ramos:** presided over the federal ASR multidistrict litigation in the Southern District of New York.
- **U.S. District Judge David A. Katz:** presided over the federal ASR multidistrict litigation in the Northern District of Ohio, where the principal consolidated proceedings were conducted.
- **FDA officials and regulators in the United Kingdom and elsewhere:** their safety reviews and regulatory actions formed part of the factual background.

## Main events and dates

### Before the recall

- **2005:** DePuy introduced the ASR XL system in the United States through the FDA’s **510(k) clearance** process. The ASR resurfacing system had been marketed in other jurisdictions earlier and was not broadly approved for use in the United States.
- **2006–2009:** Reports accumulated concerning revisions, component positioning, metal wear, and adverse tissue reactions. DePuy later faced allegations that it had received warning signs before the recall.

### Recall and regulatory developments

- **August 24, 2010:** DePuy announced a worldwide recall of the ASR XL and ASR resurfacing systems. DePuy cited data showing that approximately **12% of ASR XL patients and 13% of ASR resurfacing patients had undergone revision at five years** in relevant data, although the precise rates and populations were disputed and varied by source.
- **2010–2011:** Patients filed lawsuits across the United States. The Judicial Panel on Multidistrict Litigation centralized federal cases in the **Northern District of Ohio** as **In re: DePuy Orthopaedics, Inc., ASR Hip Implant Products Liability Litigation, MDL No. 2197**.
- **2011–2012:** The FDA and other regulators issued or supported safety communications concerning metal-on-metal hips, including the need for monitoring and attention to local tissue reactions and metal ions. DePuy stopped selling the ASR devices.

### Bellwether trials

The MDL used representative “bellwether” trials to test evidence and damages:

- **March 2013:** The first federal bellwether trial, involving **Loren Kransky**, ended in a defense verdict for DePuy. Kransky had received an ASR implant and alleged that it caused serious injuries. The jury found for DeP
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall earplugs — 11/14; missed: Aearo Chapter 11 (Indianapolis) dismissed 2023, $6.01bn settlement, August 2023, 2003-2015 issue period</summary>

```
## Overview

The **3M Combat Arms Earplugs multidistrict litigation (MDL No. 2885)** was a large federal products-liability proceeding brought mainly by U.S. military service members and veterans against **3M Company** and its subsidiary **Aearo Technologies, Inc.** The plaintiffs alleged that 3M’s **Combat Arms Earplugs, Version 2 (CAEv2)** were defectively designed and manufactured and that 3M concealed problems from the military.

The litigation began before 2019 and continued through 2023, when the parties reached a major settlement. It was not resolved by one final merits verdict covering all claims: there were both bellwether jury trials and a later negotiated settlement.

## Parties

- **Plaintiffs:** Thousands of current and former U.S. service members and veterans who used CAEv2, often during training or deployment. They alleged hearing loss, tinnitus, and related injuries.
- **Defendants:**  
  - **3M Company**, the Minnesota-based manufacturer.  
  - **Aearo Technologies, Inc.**, which developed and manufactured the earplugs and was acquired by 3M in 2008.
- **United States:** The United States was not a defendant in the MDL. The litigation followed a 2018 False Claims Act settlement between the government and 3M.

The MDL was centralized in the **U.S. District Court for the Northern District of Florida**, before **Judge M. Casey Rodgers**.

## Core allegations and issues

Plaintiffs principally alleged that:

1. **The earplugs could loosen or fold during use.**  
   CAEv2 was a dual-ended earplug: one end was intended for louder impulse noise and the other for general noise. Plaintiffs claimed that, when worn in the “down” or closed position, the earplug could gradually loosen, reducing protection without the user realizing it.

2. **The design was defective.**  
   Plaintiffs argued that the earplug’s stem was too short or otherwise inadequately designed to maintain a proper seal.

3. **3M knew of the problem.**  
   They alleged that Aearo and 3M knew about the loosening issue and failed to warn service members and the military adequately.

4. **False testing and military procurement issues.**  
   The government had alleged that 3M represented that the earplugs met applicable hearing-protection requirements, even though they did not. In July 2018, 3M agreed to pay **$9.1 million** to resolve the government’s False Claims Act allegations, without admitting liability.

3M denied the product-liability allegations. It argued, among other things, that the earplugs were safe when properly fitted and used, that plaintiffs’ hearing injuries had other possible causes, and that the **government-contractor defense** barred or limited claims because the military had approved the product’s design and warnings.

## Key people

- **Judge M. Casey Rodgers:** Federal judge who supervised the MDL in the Northern District of Florida.
- **3M and Aearo executives and corporate witnesses:** They were central to evidence about product design, testing, military contracts, and warnings.
- **Plaintiffs’ leadership counsel:** The MDL involved a large plaintiffs’ steering committee and numerous law firms representing service members. Leadership changed and expanded over time as the docket grew.
- **3M’s defense counsel:** 3M was represented by major products-liability defense firms, including counsel involved in the bellwether trials and settlement negotiations.

Because the MDL involved tens of thousands of individual plaintiffs, no single plaintiff or lawyer represented everyone in every proceeding. The most visible participants were the individual bellwether plaintiffs and the court-appointed leadership counsel.

## Main events and dates

### 2018: False Claims Act settlement

- **July 2018:** 3M agreed to pay **$9.1 million** to resolve allegations by the United States that it had misrepresented the earplugs’ compliance with military requirements. The settlement did not determine the private injury claims and included no admission of liability.

### 2019: MDL formation and early proceedings

- **March 2019:** The Judicial Panel on Multidistrict Litigation centralized the federal earplug cases in the Northern District of Florida as **MDL No. 2885**.
- The court began coordinating discovery, expert issues, motions, and representative “bellwether” trials.

### 2021: First bellwether trials

The court selected representative cases for trial to help test the evidence and arguments.

- **April 2021:** In the first bellwether trial, the jury found for **3M**.
- **May 2021:** A second bellwether jury also found for **3M**.
- **June 2021:** A third bellwether jury found for the plaintiff and awarded approximately **$1.05 million**.
- **July 2021:** Another jury found for the plaintiff and awarded approximately **$1.05 million**.
- **August 2021:** A jury found for **3M**.
- **September 2021:** A jury found for the plaintiff and awarded approximately **$13 million**.

These early trials produced mixed results—some defense verdicts and some substantial plaintiff verdicts—rather than a clear overall winner.

### 2022: Additional trials and appellate developments

- Additional bellwether trials continued in 2022, again producing mixed outcomes.
- **March 2022:** A jury awarded a plaintiff approximately **$110 million**, including punitive damages, in one of the most prominent verdicts.
- **June 2022:** The U.S. Court of Appeals for the Eleventh Circuit rejected 3M’s effort to use bankruptcy proceedings involving Aearo to halt or shield the MDL claims. Aearo had filed for bankruptcy in 2022, but the bankruptcy strategy did not stop the litigation against 3M.
- **2022:** The MDL became one of the largest mass-tort proceedings in U.S. history, with well over 200,000 claims filed or pending at various points.

### 2023: Settlement

- **May 2023:** 3M announced a proposed agreement to resolve the earplug litigation for up to **$10.3 billion**, with the amount payable over several years and dependent on participati
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall bair_hugger — 9/14; missed: HotDog conductive warmer, Gareis bellwether defence verdict (May 2018), FDA 2017 letter: continue using forced-air warming, 3M v. Augustine false-advertising suit (Lanham Act), ~5,000-6,000 cases</summary>

```
## Bair Hugger MDL 2666

**In re: Bair Hugger Forced Air Warming Products Liability Litigation**, MDL No. 2666, was a federal products-liability multidistrict litigation consolidated in the **U.S. District Court for the District of Minnesota** before **Judge Joan N. Ericksen**. It began in 2015 and concerned the **Bair Hugger forced-air warming system**, principally manufactured and marketed by **3M Company** and its subsidiary **Arizant Healthcare, Inc.** (3M acquired Arizant in 2009).

### Parties and products

- **Plaintiffs:** Patients who underwent surgery while a Bair Hugger warming blanket/system was used and who later developed **deep-joint or periprosthetic infections**, especially after hip or knee replacement.
- **Defendants:** Primarily **3M Company and Arizant Healthcare, Inc.** The litigation also involved claims directed at the product’s design, warnings, marketing, and alleged failure to disclose risks.
- **Product:** A forced-air warming system that blows warmed air through a disposable blanket over a patient during surgery to prevent hypothermia.

### Core allegations and issues

Plaintiffs alleged that:

1. The Bair Hugger system created a **thermal plume**—a rising column of warmed air around the patient.
2. That airflow allegedly disturbed or transported airborne bacteria into the sterile surgical field.
3. The resulting contamination allegedly increased the risk of **deep surgical-site infection**, including infections involving artificial joints.
4. 3M and Arizant allegedly knew or should have known of the risk but failed to adequately warn surgeons, hospitals, and patients and continued to market the product as safe.

The defendants denied that Bair Hugger caused deep-joint infections and argued that the product was supported by clinical and epidemiological evidence, that infections have many possible causes, and that plaintiffs could not establish general or specific causation. A central dispute was whether plaintiffs’ proposed scientific methodology reliably showed that Bair Hugger use materially increased infection risk.

### Key people

- **Judge Joan N. Ericksen:** Presided over the MDL in the District of Minnesota.
- **Dr. Scott D. Augustine:** Inventor of the Bair Hugger and founder of Augustine Medical, the company that developed it; he later became a prominent expert and critic in the litigation.
- **Plaintiffs’ counsel:** The MDL leadership included lawyers such as **Shannon L. Gough**, **Peter A. Bicks**, and other appointed plaintiffs’ steering-committee members. The precise leadership structure changed during the proceedings.
- **Defense counsel:** 3M and Arizant were represented by major products-liability defense firms, including **Faegre Baker Daniels** and other firms involved in the coordinated defense.
- The cases also featured competing medical and epidemiological experts concerning operating-room airflow, bacterial contamination, and prosthetic-joint infection.

### Main procedural events

- **2015:** The Judicial Panel on Multidistrict Litigation centralized federal Bair Hugger cases in Minnesota as **MDL No. 2666**. The MDL was created for coordinated discovery, expert work, and pretrial rulings; individual cases were not merged into one trial.
- **2016–2017:** The parties conducted extensive discovery and litigated expert admissibility and general-causation issues. Plaintiffs relied heavily on laboratory, airflow, and observational evidence; defendants challenged the reliability and clinical relevance of that evidence.
- **2017:** Judge Ericksen excluded key plaintiffs’ general-causation expert testimony under **Federal Rule of Evidence 702/Daubert**. The court concluded that the proposed opinions did not reliably establish that Bair Hugger use caused an increased risk of deep-joint infection.
- **2018:** The court granted summary judgment to 3M and Arizant in the bellwether cases, holding that without admissible general-causation evidence the plaintiffs could not prove their claims. The first-wave cases were dismissed.
- **2019:** The **U.S. Court of Appeals for the Eighth Circuit** affirmed the principal expert-exclusion and summary-judgment rulings. The Supreme Court declined to disturb the result by denying review.
- **After 2019:** The rulings effectively resolved the federal MDL against the plaintiffs. Remaining federal cases were dismissed or otherwise disposed of, and the MDL was closed rather than proceeding to a plaintiff’s bellwether trial or a global settlement.

### Outcome

The litigation ended in a **defense victory**. No federal Bair Hugger case went to a plaintiff’s jury verdict in the MDL. The decisive issue was not simply whether any individual patient had an infection, but whether plaintiffs could present scientifically reliable evidence that the Bair Hugger system **generally caused or materially increased the risk** of the relevant infections. Judge Ericksen excluded the central general-causation opinions, entered summary judgment for 3M and Arizant, and the Eighth Circuit affirmed.

The result was **not a finding that every use of Bair Hugger is incapable of contributing to infection**; rather, the courts held that the plaintiffs in the MDL had not supplied admissible, reliable proof sufficient to establish causation under the governing evidentiary and summary-judgment standards.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall texaco_pennzoil — 12/16; missed: Gordon Getty / Sarah Getty Trust / Getty Museum, Joe Jamail (plaintiff's counsel), agreement in principle / handshake / press release, Carl Icahn's role</summary>

```
## Pennzoil v. Texaco (the Getty Oil takeover litigation), 1984–1988

**Pennzoil Co. v. Texaco Inc.** was a major Texas contract and corporate-takeover dispute arising from Texaco’s 1984 acquisition of Getty Oil. It became one of the largest civil judgments in U.S. history and ended in Texaco’s bankruptcy-related settlement with Pennzoil.

### Parties

- **Pennzoil Company** — led by chairman and chief executive **J. Hugh Liedtke**. Pennzoil had negotiated with Getty Oil and claimed that it had reached a binding agreement to acquire Getty.
- **Texaco Inc.** — led by chairman and chief executive **John K. McKinley**. Texaco later made a competing offer and completed a transaction with Getty.
- **Getty Oil Company** — controlled principally by **J. Paul Getty II**, who owned a large block of Getty stock and was its chairman. Getty’s board and management negotiated first with Pennzoil and then with Texaco.
- **The Getty family interests and trustees** — important because Getty’s ownership structure and voting arrangements affected the negotiations and the later Texaco transaction.

### Background and key allegations

In late 1983 and early January 1984, Pennzoil negotiated with Getty representatives for a transaction under which Pennzoil would acquire a substantial interest in Getty Oil and combine with it. Pennzoil contended that the parties had reached a binding agreement even though some formal documents had not yet been signed.

Texaco then entered the negotiations and offered Getty substantially more favorable financial terms. Getty accepted Texaco’s offer, and the transaction was announced in January 1984.

Pennzoil alleged that:

1. **Getty and Pennzoil had already formed a binding contract**, based on the parties’ negotiations, a memorandum of understanding, and the conduct of Getty’s board and representatives.
2. **Texaco knew of Pennzoil’s agreement or prospective contractual rights** and intentionally interfered with them.
3. Texaco’s conduct caused Pennzoil to lose the Getty transaction and suffer enormous damages.

Texaco denied that a binding contract existed. It argued that the negotiations were preliminary, that required conditions and formal documentation had not been completed, and that Texaco had lawfully competed for Getty. Texaco also challenged the damages and the legal basis for the verdict.

### Key people

- **J. Hugh Liedtke** — Pennzoil’s chairman and CEO; directed Pennzoil’s effort to acquire Getty and pursued the litigation.
- **John K. McKinley** — Texaco’s chairman and CEO; approved and led Texaco’s competing acquisition of Getty.
- **J. Paul Getty II** — chairman and a major shareholder of Getty Oil; a central figure in the negotiations and the Getty family’s position.
- **Harold “Hank” Greenberg** — not a principal in the underlying Getty negotiations, but later became Texaco’s chairman and CEO during the company’s financial crisis and settlement period.
- **Judge Solomon Casseb Jr.** — presided over the Texas trial in Harris County.
- **Judge William W. Justice** — presided over the later federal bankruptcy proceedings involving Texaco.

### Main events

#### January 1984: Pennzoil–Getty negotiations

Pennzoil and Getty negotiated a transaction. On **January 3, 1984**, Getty’s board approved an arrangement with Pennzoil, and the parties signed documents that Pennzoil later characterized as a binding agreement. The arrangement contemplated Pennzoil acquiring a major Getty interest and ultimately combining the companies.

The parties had not completed every definitive document or obtained every contemplated approval. That incompleteness became the central issue in Texaco’s defense.

#### January 1984: Texaco’s competing offer

Texaco made a substantially higher offer for Getty. Getty accepted Texaco’s proposal, and Texaco proceeded with the acquisition. The transaction was completed in **February 1984**.

Pennzoil immediately sued both Getty and Texaco in Texas state court. Getty was later dismissed or otherwise ceased to be a principal defendant, leaving Texaco as the central defendant.

#### 1985: Texas trial and verdict

The case was tried in **Harris County District Court in Houston** before Judge Solomon Casseb Jr.

On **December 10, 1985**, the jury found for Pennzoil. It concluded that:

- Pennzoil and Getty had reached an enforceable agreement;
- Texaco had tortiously interfered with that agreement; and
- Pennzoil was entitled to substantial damages.

The jury awarded approximately:

- **$7.53 billion in actual damages**, and
- **$3 billion in punitive damages**.

The trial court entered judgment for roughly **$10.53 billion**, an extraordinary amount at the time. Interest and other additions later increased the exposure.

#### 1987: Texas Supreme Court decision

Texaco appealed. On **March 30, 1987**, the **Texas Supreme Court** largely affirmed the judgment, although it reduced the punitive-damages component. The court upheld the core conclusions that Pennzoil had an enforceable agreement with Getty and that Texaco had improperly interfered with it.

The judgment remained approximately **$8.5 billion**, before further interest and costs.

Texaco then sought review in the **U.S. Supreme Court**, arguing, among other things, that the Texas proceedings violated federal constitutional and procedural principles and that the judgment should not be enforced while the appeal was pending.

#### 1987: U.S. Supreme Court and bankruptcy

On **October 14, 1987**, the U.S. Supreme Court declined to block enforcement of the Texas judgment. The Court’s action left Texaco facing immediate efforts to collect the judgment.

Texaco filed for **Chapter 11 bankruptcy protection on April 12, 1987**, before the Supreme Court’s October action. The bankruptcy filing stayed collection efforts and shifted the dispute into bankruptcy court, while Texaco continued to appeal and negotiate.

The case also produced a major constitutional controversy involving the **Texas “anti-inju
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall dalkon — 12/15; missed: Judge Miles Lord's 1984 rebuke, 18 deaths; ~200,000-300,000 claims, punitive damages / 'crab' shape</summary>

```
## Overview

The **Dalkon Shield litigation** was a mass-products-liability controversy arising from an intrauterine contraceptive device (IUD) manufactured and marketed by **A.H. Robins Company, Inc.** The litigation concerned allegations that the device’s design and marketing caused **pelvic inflammatory disease, septic miscarriage, infertility, ectopic pregnancy, and death**, and that Robins failed to warn users and physicians adequately.

The resulting claims became one of the largest mass-tort proceedings in U.S. history and led to **A.H. Robins’s Chapter 11 bankruptcy in 1985**. The bankruptcy produced a specialized trust and claims-resolution system. The reorganization became effective in **1989**, when the reorganized company emerged under new ownership.

## The device and the parties

- **A.H. Robins Company, Inc.**: Richmond, Virginia–based manufacturer of the Dalkon Shield.
- **Dalkon Corporation**: A company associated with the device’s development; Robins acquired control of the Dalkon Shield business in the early 1970s.
- **Users and their families**: Women who used the device and asserted personal-injury and wrongful-death claims.
- **Physicians and hospitals**: Some were defendants or potential defendants in individual cases, while others were witnesses concerning warnings, insertion, removal, and medical causation.
- **Insurers and reinsurers**: Their coverage obligations became important in the bankruptcy and settlement negotiations.
- **Creditors and shareholders**: The bankruptcy involved ordinary trade creditors, lenders, tort claimants, and Robins shareholders.
- **The United States government and FDA**: The Food and Drug Administration became involved in regulatory scrutiny, recalls, and later medical-device regulation.

## Key allegations and issues

Claimants generally alleged that:

1. **The Dalkon Shield’s design was defective.**  
   The most important design feature was its multifilament retrieval string. Plaintiffs contended that the string could act as a pathway for bacteria to travel from the vagina into the uterus and fallopian tubes, increasing the risk of pelvic infection.

2. **The device caused serious injuries.**  
   Alleged injuries included:
   - pelvic inflammatory disease;
   - septic abortion and miscarriage;
   - infertility;
   - ectopic pregnancy;
   - uterine perforation;
   - hysterectomy;
   - chronic pain;
   - and death.

3. **Robins failed to warn adequately.**  
   Plaintiffs argued that Robins did not adequately disclose the risks to physicians and users, minimized adverse reports, and continued marketing the device despite evidence of danger.

4. **Robins’s testing, surveillance, and reporting were inadequate.**  
   Litigation focused on the company’s clinical data, adverse-event reports, internal communications, marketing practices, and dealings with regulators and physicians.

5. **Causation and individual proof were disputed.**  
   Robins contested whether the Dalkon Shield caused particular injuries, especially where users had other risk factors or where the medical evidence was uncertain. Individual cases also raised statutes of limitation, contributory negligence, medical-malpractice issues, and the role of physicians.

6. **The bankruptcy raised constitutional and procedural questions.**  
   The bankruptcy court had to create a practical system for resolving hundreds of thousands of personal-injury claims while preserving assets and avoiding inconsistent litigation. The process also raised issues about due process, estimation of mass tort claims, injunctions against future lawsuits, and the treatment of unknown future claimants.

## Key people

- **A. H. “Abe” Robins**: Founder and longtime chief executive associated with A.H. Robins Company. He died in **1980**.
- **Dr. Hugh J. Davis**: Physician and inventor associated with the Dalkon Shield’s development. He was a central figure in the device’s history and later litigation.
- **John A. Robins**: A.H. Robins executive and member of the Robins family who became involved in company leadership.
- **Judge Robert R. Merhige Jr.**: U.S. District Judge for the Eastern District of Virginia, who played a major role in supervising the mass litigation and bankruptcy-related proceedings.
- **Judge Francis G. Conrad**: Bankruptcy judge who presided over important aspects of the Chapter 11 case and the claims-resolution process.
- **Plaintiffs’ lawyers and the Dalkon Shield Claimants Trust**: No single lawyer represented all claimants, but plaintiffs’ counsel and later trust officials developed the mechanisms for processing and paying claims.
- **R. J. Reynolds Industries, Inc.**: Its proposed acquisition of Robins became the basis for the eventual reorganization and emergence from bankruptcy.

## Main events

### 1970–1971: Introduction and acquisition

The Dalkon Shield was developed in the late 1960s and introduced commercially around **1970**. A.H. Robins acquired the Dalkon Shield business and related rights in approximately **1971**.

The device was marketed as a highly effective contraceptive. Early sales were substantial, but reports of infections, pregnancies, expulsions, and other complications accumulated.

### 1972–1974: Growing safety concerns and withdrawal

By the early 1970s, physicians and regulators were receiving increasing reports of serious complications. The device became associated particularly with pelvic infections and septic abortions.

In **1974**, Robins stopped selling the Dalkon Shield in the United States and withdrew it from the market. The withdrawal did not end the controversy: millions of women had already received the device, and many remained at risk or had already suffered injuries.

### 1974 onward: Individual lawsuits and regulatory scrutiny

Beginning in the mid-1970s, users and families filed lawsuits across the country. The cases involved product liability, negligence, breach of warranty, fraud or misrepresentation theories, and wrongful deat
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall bhopal — 15/15; missed: </summary>

```
## Bhopal gas disaster and litigation against Union Carbide

### The disaster

On the night of **December 2–3, 1984**, a pesticide plant in **Bhopal, Madhya Pradesh, India**, operated by **Union Carbide India Limited (UCIL)** released a large quantity of **methyl isocyanate (MIC)** gas and reaction products into surrounding neighborhoods.

UCIL was an Indian company in which **Union Carbide Corporation (UCC)**, a United States company, held a majority interest—about **50.9%**. The plant manufactured the pesticide **Sevin**. Water entered an MIC storage tank, triggering an exothermic reaction and a massive pressure and temperature increase. Safety systems were allegedly shut down, poorly maintained, inadequately staffed, or otherwise ineffective.

The gas cloud spread over densely populated areas. The exact death toll remains disputed:

- The Government of Madhya Pradesh reported roughly **3,000 immediate deaths**.
- Later official and claimant estimates commonly placed total deaths over subsequent years at approximately **15,000–25,000**.
- Hundreds of thousands of people claimed injuries, chronic respiratory and eye disease, neurological and reproductive effects, and other illnesses.

The disaster is widely regarded as one of the world’s worst industrial catastrophes.

### Principal parties and people

- **Union Carbide India Limited (UCIL):** The Indian operating company that owned and ran the Bhopal plant.
- **Union Carbide Corporation (UCC):** The U.S. parent company and majority shareholder of UCIL.
- **Government of India:** Represented victims under the **Bhopal Gas Leak Disaster (Processing of Claims) Act 1985**, which gave the government exclusive authority to pursue claims.
- **Individual victims and survivors:** Residents exposed to the gas and families of those killed.
- **Warren M. Anderson:** UCC’s chairman and chief executive officer at the time. He traveled to India after the disaster, was arrested in Bhopal on **December 7, 1984**, released on bail, and left India. He did not return for trial.
- **Indian UCIL officials:** Among those prosecuted were former UCIL chairman **Keshub Mahindra**, managing director **Vijay Gokhale**, plant manager **J. Mukund**, and other plant personnel.
- **Indian government officials and regulators:** Their alleged failures in plant oversight, emergency planning, and public protection were also criticized, although the principal litigation focused on the companies and their personnel.

### Key allegations and legal issues

The central allegations included:

1. **Unsafe plant design and operation**
   - The plant allegedly used inadequate safety systems and maintenance.
   - Critical safeguards—including refrigeration, gas scrubbers, and flare systems—were allegedly unavailable, ineffective, or not properly maintained.
   - Staffing and training were allegedly reduced.
   - The plant was located near densely populated communities without adequate emergency planning.

2. **Corporate responsibility**
   - Victims argued that UCC, as parent and technical owner, exercised sufficient control over UCIL and should be directly liable.
   - UCC argued that UCIL was a separate Indian corporation and that the accident resulted from UCIL’s operations, not conduct by UCC in the United States.

3. **Jurisdiction and forum**
   - The Government of India filed a major civil action in the United States, seeking damages for victims.
   - UCC argued that India was the more appropriate forum. The U.S. litigation was dismissed on **forum non conveniens** grounds, subject to UCC’s submission to Indian jurisdiction.

4. **Criminal liability**
   - Indian prosecutors alleged culpable homicide and other offenses against UCC, UCIL, Anderson, and Indian managers.
   - A major issue was whether the conduct amounted to criminal negligence or more serious homicide-related offenses.

5. **Adequacy of compensation**
   - Victims and advocacy groups argued that the eventual settlement was too low, that claims processing was slow and inaccurate, and that long-term medical and environmental damage was inadequately addressed.
   - The government later sought additional compensation from UCC, but that effort failed in the Supreme Court.

6. **Environmental contamination**
   - Separate and continuing claims alleged that toxic substances remained at or around the plant and contaminated soil and groundwater.
   - These issues were not fully resolved by the original settlement.

### Main events and dates

#### December 2–3, 1984: Gas release

Water entered an MIC storage tank at the Bhopal plant. The resulting reaction caused the release of toxic gases. Thousands died quickly, and many more suffered lasting injuries.

#### December 7, 1984: Anderson’s arrest and departure

Warren Anderson arrived in Bhopal, was arrested by Indian authorities, and was released on bail. He left India and never appeared for the later criminal proceedings. Indian courts eventually declared him an absconder.

#### December 1984–1985: U.S. litigation

Victims and the Government of India filed claims in U.S. courts. The Government of India enacted the **1985 Bhopal Act**, making itself the exclusive representative of victims.

In **Union Carbide Corporation v. Union of India**, the U.S. District Court for the Southern District of New York dismissed the case on **forum non conveniens** grounds in 1986, requiring the claims to be pursued in India. The Second Circuit affirmed the dismissal in 1987, with conditions intended to preserve UCC’s submission to Indian jurisdiction.

#### 1985: Indian government lawsuit

The Government of India filed a civil action in the **Bhopal District Court** seeking approximately **₹3,900 crore** in damages—then roughly US$3 billion—for victims.

#### 1988–1989: Settlement negotiations and Supreme Court settlement

The litigation moved through Indian courts. On **February 14–15, 1989**, the **Supreme Court of India** approved a settlement under which UCC agreed to pay **US$470
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall near — 5/12; missed: MobileFuse / Kenneth Harlan, round-trip revenue scheme, ~27% revenue overstatement; $37.3m of $138.3m, Nasdaq ticker NIR, Pasadena, California, luxury residence billed as professional services, UberMedia acquisition (2021)</summary>

```
I don’t know of an SEC accounting-fraud case filed in 2026 against Near Intelligence, Inc.’s former CEO Anil Mathews and former CFO Rahul Agarwal. My knowledge does not include reliable information about a 2026 SEC action, and I should not invent the allegations, dates, or outcome.

The publicly reported Near Intelligence matter I’m aware of is primarily a **2024 criminal and regulatory disclosure scandal**, not a known 2026 SEC case:

- **Near Intelligence, Inc.** was a data-analytics company that became publicly traded through a SPAC merger in 2022.
- **Anil Mathews** was its founder and chief executive officer.
- **Rahul Agarwal** was its chief financial officer.
- In **February 2024**, Near disclosed that its previously issued financial statements should no longer be relied upon and that it had identified material weaknesses and accounting problems.
- The company also disclosed that the SEC was investigating matters relating to its financial reporting and disclosures.
- Near’s stock was suspended and later delisted; the company filed for **Chapter 11 bankruptcy protection in April 2024**.
- In **September 2024**, the U.S. Attorney’s Office for the Southern District of New York announced criminal charges against Mathews and Agarwal, alleging a scheme involving materially false statements about Near’s customers, revenue, and business performance in connection with the company’s public-market transaction. Those were criminal allegations, not an SEC civil judgment, and the defendants were presumed innocent unless proven guilty.

I cannot reliably state that an SEC complaint was filed in 2026, identify its precise claims, or describe its disposition.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall meyer — 3/10; missed: SpaceX pre-IPO interests, misappropriation for personal expenses, inflated account statements, releases for reduced distributions, forfeited ~$3m capital call, Investment Advisers Act antifraud, conduct since December 2021</summary>

```
I can’t reliably describe that matter because September 2026 is in the future relative to my available knowledge, and I have no verified information about an SEC case against Meyer Global Management LLC or its CEO Owen Meyer.

I therefore can’t confirm:

- the SEC’s specific allegations;
- the identities or roles of other people involved;
- the relevant filing, enforcement, or settlement dates; or
- the outcome.

If you provide an SEC litigation release, complaint, administrative order, or a link to the matter, I can summarize the parties, allegations, timeline, key individuals, and disposition accurately.
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall dieselgate — 14/17; missed: Judge Charles Breyer, N.D. Cal. MDL, Braunschweig prosecutors / German trials, Bosch supplied the engine software</summary>

```
## Overview

The **Volkswagen diesel-emissions scandal**, commonly called **“Dieselgate,”** began publicly in **September 2015**. It involved Volkswagen AG and several affiliated brands using software—called a **defeat device**—to recognize laboratory emissions testing and reduce pollution only during the test. In ordinary driving, affected diesel vehicles emitted nitrogen oxides (**NOx**) far above legal limits.

The matter produced regulatory investigations, criminal prosecutions, civil litigation, recalls and buybacks, corporate penalties, and continuing proceedings in several countries.

## Main parties

- **Volkswagen AG**: German parent company and principal corporate defendant.
- **Volkswagen Group brands and entities**: Including **Audi**, **Porsche**, **Volkswagen Passenger Cars**, and U.S. subsidiaries such as **Volkswagen Group of America, Inc.**
- **U.S. Environmental Protection Agency (EPA)** and **California Air Resources Board (CARB)**: Discovered and investigated the U.S. violations.
- **U.S. Department of Justice (DOJ)**: Brought civil and criminal enforcement actions.
- **Federal Trade Commission (FTC)**: Challenged Volkswagen’s advertising of “clean diesel” vehicles.
- **U.S. consumers and dealers**: Filed class actions and other civil claims.
- **European regulators and prosecutors**: Including German prosecutors, the European Commission, and authorities in other countries.
- **Investors and shareholders**: Brought claims alleging Volkswagen failed to disclose the emissions misconduct and resulting risks.

## Key allegations and issues

### Defeat-device software

The central allegation was that software installed in certain diesel engines detected conditions associated with laboratory testing—such as steering-wheel position, speed, engine operation, and test-cycle characteristics. During testing, the software activated full emissions controls. During normal driving, it reduced or disabled those controls, improving performance or fuel economy but causing excessive NOx emissions.

The affected engines were principally:

- **Volkswagen and Audi 2.0-liter TDI diesel engines**, commonly known as the **EA 189** engine family.
- Later investigations also focused on **3.0-liter diesel engines** used in larger Volkswagen, Audi, and Porsche vehicles.

### Excessive pollution

The EPA alleged that certain 2.0-liter vehicles emitted NOx at levels up to approximately **40 times** the applicable U.S. standard in real-world driving. NOx contributes to smog and respiratory harm.

### False advertising and consumer deception

Volkswagen marketed the vehicles in the United States as environmentally friendly **“clean diesel”** cars. The FTC alleged that this advertising was deceptive because the vehicles did not meet the represented emissions performance in ordinary use.

### Corporate knowledge and responsibility

Investigations examined:

- Which engineers and managers designed or approved the software;
- Whether senior executives knew of the defeat device;
- Whether Volkswagen’s corporate culture, performance targets, and internal reporting failures enabled the misconduct;
- Whether Audi and Porsche personnel were involved in the larger-engine programs.

### Disclosure and investor claims

Shareholders alleged that Volkswagen failed to disclose the existence and potential consequences of the defeat devices, causing the company’s share price to fall sharply after the scandal became public.

## Key people

- **Martin Winterkorn**: Volkswagen’s CEO from 2007 until his resignation on **September 23, 2015**, shortly after the scandal became public. He denied knowing about the defeat device before the disclosure. U.S. prosecutors later charged him with conspiracy and wire-fraud-related offenses.
- **Herbert Diess**: Became Volkswagen CEO in 2018 and led the company during much of the legal and restructuring response.
- **Oliver Schmidt**: A Volkswagen manager who worked in the company’s U.S. environmental and engineering operations. He pleaded guilty in the United States and was sentenced to prison.
- **James Liang**: A Volkswagen engineer who worked on diesel-engine development and pleaded guilty in the United States.
- **Rupert Stadler**: Former CEO of Audi. German prosecutors charged him in connection with the emissions case; he later admitted negligence in the German trial and received a suspended sentence.
- **Martin Winterkorn and other Volkswagen/Audi executives and engineers**: Various individuals were investigated or charged in Germany and elsewhere, with outcomes differing by person and jurisdiction.
- **EPA and CARB investigators**: Their technical testing and investigation were central to uncovering the discrepancy between laboratory and real-world emissions.

## Main events

### 2007–2009: Development and introduction

Volkswagen pursued a strategy of expanding diesel sales in the United States while meeting increasingly strict emissions standards. The EA 189 diesel engine was introduced in various vehicles, including the **Volkswagen Jetta, Beetle, Golf, Passat**, and **Audi A3**.

### 2014: Independent testing raises concerns

Researchers at **West Virginia University**, working with the **International Council on Clean Transportation (ICCT)**, conducted on-road testing of diesel vehicles. The testing found that some Volkswagen vehicles emitted far more NOx in real-world driving than in laboratory tests.

CARB and the EPA investigated Volkswagen’s explanations and required further testing.

### May–August 2015: Regulatory pressure

Volkswagen attempted to address the issue through software updates and other measures, but regulators concluded that the discrepancies had not been adequately explained. CARB threatened to withhold approval for Volkswagen’s 2016 diesel vehicles.

### September 18, 2015: EPA notice of violation

The EPA issued a **Notice of Violation** alleging that Volkswagen had installed defeat devices in certain 2.0-liter diesel vehicles. CARB issued related f
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall ftx — 14/18; missed: ~$8 billion customer funds, effective altruism, customers repaid in full at petition-date value, Michael Lewis, Going Infinite</summary>

```
## FTX’s collapse and Sam Bankman-Fried’s prosecution

### Parties and principal entities

- **FTX Trading Ltd.**: The cryptocurrency exchange founded by Sam Bankman-Fried, commonly called FTX.
- **Alameda Research**: Bankman-Fried’s cryptocurrency trading firm and hedge fund, founded before FTX. It was run by **Caroline Ellison**, Bankman-Fried’s former romantic partner.
- **Sam Bankman-Fried (SBF)**: FTX’s founder and chief executive until his resignation in November 2022.
- **Caroline Ellison**: CEO of Alameda Research; she pleaded guilty and became a cooperating government witness.
- **Gary Wang**: FTX co-founder and chief technology officer; he pleaded guilty and cooperated.
- **Nishad Singh**: FTX’s former engineering director; he pleaded guilty and cooperated.
- **John J. Ray III**: Bankruptcy restructuring executive appointed as FTX’s CEO after the collapse.
- **U.S. prosecutors in the Southern District of New York**: Led the criminal case against Bankman-Fried.
- **The U.S. Securities and Exchange Commission (SEC)** and **Commodity Futures Trading Commission (CFTC)**: Brought civil enforcement actions concerning securities and commodities-related misconduct.
- **Bahamian authorities**: FTX was headquartered in The Bahamas. Bankman-Fried was arrested there and extradited to the United States.

### What allegedly happened

The central allegation was that Bankman-Fried and other executives secretly diverted billions of dollars of FTX customer funds to Alameda Research. Prosecutors said Alameda received special privileges within FTX’s trading system, including the ability to withdraw funds despite insufficient assets and to incur a very large negative balance.

The government alleged that the diverted money was used for:

- Alameda’s trading and investments;
- repayment of loans;
- political contributions;
- luxury real estate;
- personal expenditures; and
- efforts to support FTX and Alameda after their financial condition deteriorated.

Prosecutors also alleged that Bankman-Fried and others misled customers, lenders, and investors about FTX’s financial condition and Alameda’s relationship with the exchange. The defense argued that Bankman-Fried had made mistakes in a rapidly changing business but did not knowingly intend to steal customer funds.

### Main events

#### November 2, 2022: Alameda balance-sheet report

CoinDesk published a report based on a leaked Alameda balance sheet. It showed that Alameda’s assets were heavily concentrated in FTT, a token issued by FTX, raising questions about whether the firms were solvent and whether their finances were too closely intertwined.

#### November 6–8, 2022: Customer withdrawals and liquidity crisis

Binance CEO **Changpeng Zhao** announced that Binance intended to sell its FTT holdings. Customers began withdrawing funds from FTX in large numbers. FTX could not meet the withdrawal demand.

On November 8, Bankman-Fried said FTX had reached an agreement in principle for Binance to acquire it, subject to due diligence. Binance abandoned the proposed transaction the next day, citing financial problems and regulatory concerns.

#### November 11, 2022: Bankruptcy and resignation

FTX, Alameda, and affiliated companies filed for **Chapter 11 bankruptcy** in the United States. Bankman-Fried resigned as CEO. John J. Ray III became chief executive and later described the company’s controls and recordkeeping as severely deficient.

FTX’s bankruptcy proceedings revealed a substantial shortfall in customer assets and extensive commingling of funds. The precise amount recovered and distributed has evolved during the proceedings, but the collapse involved billions of dollars in customer and creditor claims.

#### December 12, 2022: Arrest in The Bahamas

Bahamian authorities arrested Bankman-Fried at the request of U.S. prosecutors. He was charged in the United States with fraud, conspiracy, money laundering, and campaign-finance-related offenses.

#### December 2022: Guilty pleas by cooperating executives

Caroline Ellison, Gary Wang, and Nishad Singh pleaded guilty to criminal charges and agreed to cooperate with prosecutors. Their testimony became central to the government’s case.

A fourth former executive, **Ryan Salame**, later pleaded guilty in September 2023 to campaign-finance and operating-an-unlicensed-money-transmitting-business charges. He was sentenced in May 2024 to 7½ years in prison.

#### December 22, 2022: Release on bail

After extradition to the United States, Bankman-Fried was released on a $250 million bond secured by his parents’ California home. He was required to remain largely at home and surrender his passport.

#### July–August 2023: Bail revoked

Prosecutors accused Bankman-Fried of attempting to influence witnesses and improperly disclosing private writings by Caroline Ellison to a New York Times reporter. On August 11, 2023, Judge **Lewis A. Kaplan** revoked his bail and ordered him detained pending trial.

#### October 3–November 2, 2023: Federal trial

Bankman-Fried’s trial took place in the U.S. District Court for the Southern District of New York before Judge Kaplan.

The government’s key witnesses included:

- **Caroline Ellison**, who testified that Bankman-Fried directed her to create misleading financial documents and use FTX customer money;
- **Gary Wang**, who described the creation of special trading privileges for Alameda;
- **Nishad Singh**, who testified about the technical implementation of Alameda’s access to customer funds; and
- **Adam Yedidia**, a former FTX employee, who testified about discovering a multibillion-dollar customer shortfall.

The prosecution presented internal messages, financial records, code-related evidence, and testimony concerning political donations and real-estate purchases.

Bankman-Fried testified in his own defense. He acknowledged mistakes and poor risk management but denied knowingly defrauding customers or directing the theft of their funds. The defense emphasized the c
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall theranos — 16/17; missed: Bad Blood (2018)</summary>

```
## Overview

**Theranos, Inc.** was a privately held Silicon Valley blood-testing company founded by **Elizabeth Holmes** in 2003. It claimed that its proprietary devices—especially the **“Edison”** and later **“miniLab”** systems—could perform a broad range of laboratory tests from a finger-prick of blood, more cheaply and conveniently than conventional testing.

Federal prosecutors alleged that Holmes and **Ramesh “Sunny” Balwani**, Theranos’s president and chief operating officer, knowingly misrepresented the technology, business, finances, and relationships with customers and investors. The government charged them with wire fraud and conspiracy to commit wire fraud. Both denied wrongdoing.

The criminal cases were separate:

- **United States v. Elizabeth Holmes**, tried in 2021.
- **United States v. Ramesh Balwani**, tried in 2022.

Both were convicted, sentenced to prison, and ordered to pay restitution. Their convictions were later affirmed on appeal, although Holmes’s restitution order was reduced.

---

## Key people and parties

### Elizabeth Holmes
- Founder and CEO of Theranos.
- Left Stanford University in 2004 to pursue the company.
- Presented herself as a visionary entrepreneur who would transform medical testing.
- Prosecutors said she directed or approved false claims to investors, doctors, patients, and business partners.
- Defense lawyers argued that she believed in Theranos’s technology, relied on employees and advisers, and did not intend to defraud anyone.

### Ramesh “Sunny” Balwani
- Technology entrepreneur and former software executive.
- Met Holmes in 2002 and became romantically involved with her.
- Joined Theranos as president and later chief operating officer in 2009.
- Exercised broad operational authority, including over laboratory operations, finances, and business relationships.
- Prosecutors portrayed him as a central participant in the alleged scheme and as responsible for misleading investors, doctors, and patients.
- Balwani denied the charges and argued that he believed Theranos’s technology worked and that he had not made fraudulent representations.

### Theranos, Inc.
- The company was not itself tried in the criminal cases because it had already dissolved.
- It raised more than **$700 million** from private investors, including prominent individuals and investment entities.
- Major commercial relationships included **Walgreens**, which began offering Theranos testing in Arizona in 2013, and **Safeway**, which explored a similar relationship.

### Important witnesses and figures
- **Tyler Shultz**, a former Theranos employee and grandson of former U.S. Secretary of State George Shultz. He raised concerns about the accuracy of Theranos testing.
- **Erika Cheung**, a former Theranos laboratory employee who also reported concerns about testing reliability and laboratory practices.
- **Adam Rosendorff**, Theranos’s former laboratory director, who testified about accuracy and operational problems.
- **George Shultz**, a Theranos board member and prominent supporter who later became concerned after learning of internal problems.
- **Richard Fuisz**, a physician and businessman involved in a patent dispute with Theranos and a prosecution witness.
- **David Boies**, Theranos’s outside lawyer and board member, who helped defend the company and enforce confidentiality agreements.
- **Henry Kissinger, William Perry, James Mattis, and other prominent figures** served as directors or advisers at various times, helping give Theranos credibility.
- **Jeffrey Coopersmith**, a former Walgreens executive, testified about Walgreens’s relationship with Theranos.
- **Daniel Edlin**, Holmes’s former romantic partner and a Theranos employee, testified in the Holmes trial.

---

## The alleged fraud

The government’s theory was that Holmes and Balwani made materially false statements in three broad areas.

### 1. Claims about the technology

Theranos said its proprietary systems could run hundreds of tests using a small amount of blood from a finger prick. Prosecutors argued that:

- The company’s own technology could perform only a limited number of tests reliably.
- Theranos often used conventional third-party machines, including Siemens analyzers, for many tests.
- Results from the Theranos system were sometimes inaccurate or unreliable.
- The company concealed these limitations from investors, business partners, doctors, and patients.

The prosecution did not need to prove that every Theranos test was inaccurate. It argued that the defendants falsely represented the overall capabilities and reliability of the system and concealed material limitations.

### 2. Claims about business relationships and validation

Prosecutors alleged that Holmes and Balwani overstated or misrepresented:

- The nature and extent of Theranos’s relationship with the U.S. Department of Defense.
- The role of military personnel and the use of Theranos technology in battlefield or military settings.
- The status of Theranos’s relationship with Walgreens.
- The extent to which outside companies, institutions, and experts had validated the technology.

A particularly important issue was a 2013–2014 Walgreens rollout in Arizona. Walgreens offered Theranos testing to customers, but the government argued that Theranos had not adequately disclosed the technology’s limitations and the extent to which conventional analyzers were being used.

### 3. Claims about finances and commercial prospects

The government alleged that Holmes and Balwani gave investors misleading information about:

- Theranos’s revenue and projected revenue.
- The company’s financial condition.
- Its expected contracts and commercial success.
- Its relationships with major companies.

One widely discussed example was a document sent to investors that used the **Pfizer** logo and described Pfizer as having validated Theranos technology. Prosecutors argued that this presentation misleadingly suggested a stronger endorsement than ac
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall endo — 14/20; missed: New York AG Assurance of Discontinuance, March 2016, 'pseudoaddiction' and 'usually do not become addicted' in training / marketing, American Pain Foundation / NIPC / painknowledge.com, generic Opana ER / Impax & Actavis; FTC pay-for-delay case (2016-17), Opioid Industry Documents Archive (UCSF / Johns Hopkins) document release, CEOs Rajiv De Silva (2013-16), Paul Campanelli (2016-20), Blaise Coleman (2020-)</summary>

```
## Overview

Endo International plc and its U.S. subsidiary Endo Pharmaceuticals Inc. faced thousands of opioid lawsuits, federal criminal and civil investigations, state attorney-general actions, and bankruptcy proceedings. The matters generally alleged that Endo and related companies aggressively marketed and distributed prescription opioids while minimizing addiction and diversion risks and failing to maintain effective anti-diversion controls.

The litigation was part of the nationwide opioid litigation consolidated in **MDL No. 2804, In re: National Prescription Opiate Litigation**, before Judge **Dan Aaron Polster** in the U.S. District Court for the Northern District of Ohio. Endo was one of many defendants; the MDL was not a single Endo-only case.

## Parties and products

The principal Endo entities included:

- **Endo International plc**, the Irish-domiciled parent.
- **Endo Pharmaceuticals Inc.**, its U.S. operating company.
- **Par Pharmaceutical, Inc.** and other Endo-related entities acquired or operated by the group.
- **Qualitest Pharmaceuticals**, acquired by Endo in 2010 and later renamed or integrated into Endo’s generic-pharmaceutical operations.

The opioid products most often associated with the claims included:

- **Opana ER** (oxymorphone extended release), an Endo-branded opioid.
- **Percocet** and **Percodan**, which Endo marketed or sold in relevant periods.
- Generic opioid products distributed or sold through Endo-related companies, including oxycodone and hydrocodone products.

The plaintiffs included:

- The **City of Chicago**, counties, cities, and other local governments.
- Numerous **states and state attorneys general**.
- Native American tribes.
- Hospitals, health systems, third-party payors, and individuals in separate or related proceedings.

## Core allegations

The allegations varied by plaintiff and jurisdiction, but commonly asserted that Endo:

1. **Misrepresented opioid risks.** Plaintiffs alleged that Endo’s marketing understated addiction, dependence, overdose, and diversion risks and overstated the benefits or safety of long-term opioid treatment.

2. **Promoted opioids for broader and longer use.** The claims focused particularly on the expansion of opioid prescribing for chronic, non-cancer pain.

3. **Used sales and promotional practices that encouraged prescribing.** Allegations included sales-representative activity, physician education, promotional materials, speaker programs, and other marketing practices.

4. **Failed to monitor suspicious orders.** Under the federal Controlled Substances Act and related regulations, manufacturers and distributors must maintain effective controls against diversion and report suspicious orders. Plaintiffs alleged that Endo-related entities failed to identify, investigate, and report suspicious opioid orders adequately.

5. **Contributed to the public nuisance and costs of the opioid epidemic.** Government plaintiffs sought damages and equitable relief for increased medical, law-enforcement, treatment, foster-care, and other public expenses.

Endo disputed many allegations and asserted defenses including causation, reliance, statute of limitations, preemption, the role of prescribing physicians and distributors, and challenges to public-nuisance theories.

## MDL 2804

The federal opioid MDL began in **2017**, when the Judicial Panel on Multidistrict Litigation centralized thousands of federal cases in Cleveland before Judge Polster. The MDL included claims against manufacturers, distributors, pharmacies, and other participants in the opioid supply chain.

Endo was named as a defendant in cases within the MDL and in related state litigation. The MDL’s first bellwether trials involved other major defendants, including the **County of Summit and City of Akron v. Purdue Pharma** litigation in 2019. Those trials were intended to test legal and factual issues rather than resolve all claims against every defendant.

The MDL produced extensive discovery and settlement negotiations, but it did not result in one universal Endo judgment covering all plaintiffs. Endo’s exposure was addressed through a combination of individual settlements, state agreements, litigation, and ultimately bankruptcy.

## State attorney-general actions and settlements

State attorneys general brought separate lawsuits or participated in multistate investigations. The allegations generally tracked the national claims: deceptive marketing, failure to disclose opioid risks, and inadequate monitoring of suspicious orders.

Important developments included:

- **2017–2018:** Endo faced investigations and lawsuits by multiple states concerning Opana ER, opioid marketing, and distribution controls.
- **2019:** Endo agreed to a major multistate settlement concerning its opioid business. Public reports described a settlement with **36 states and the District of Columbia** involving approximately **$10 million in cash**, opioid-related products or services, and other non-cash relief. The agreement also included restrictions on opioid promotion and related conduct.
- **2021:** Endo reached a separate settlement with the **State of New York**. New York announced a payment of approximately **$50 million**, consisting largely of product and other non-cash value, with proceeds directed toward opioid-abatement purposes.
- **2021–2022:** Endo continued negotiating with states, local governments, tribes, and other plaintiffs. Some governmental claims were resolved or released through later bankruptcy settlements, while others remained disputed or subject to bankruptcy procedures.

The exact value of a state settlement often depended on whether it was cash, opioid-abatement products, credits, or contingent consideration, so headline figures are not always directly comparable.

## Opana ER and FDA-related issues

A major Endo-specific issue involved **Opana ER**. The FDA approved Opana ER in 2006. Endo later developed a reformulated version intended to ma
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall teva — 12/14; missed: Fentora (fentanyl buccal tablet), Petah Tikva / Tel Aviv, Israel</summary>

```
The opioid litigation involving **Teva Pharmaceuticals USA, Inc.; Cephalon, Inc.; and Actavis, Inc.** was part of the sprawling U.S. opioid multidistrict litigation, **In re National Prescription Opiate Litigation, MDL No. 2804**, before Judge **Dan Aaron Polster** in the Northern District of Ohio. It is important to distinguish the companies’ roles:

- **Teva** marketed and distributed generic opioids and, after acquiring Cephalon, inherited Cephalon’s opioid business and liabilities.
- **Cephalon** marketed the branded fentanyl product **Actiq** and related opioid products.
- **Actavis**—later part of **Allergan** and ultimately **Teva**—manufactured and distributed generic opioids, including oxycodone and hydrocodone products.

## Parties

The principal plaintiffs included:

- **States, counties, cities, tribes, hospitals, and other public entities** seeking costs associated with the opioid epidemic.
- The federal government in related enforcement and settlement matters.
- Private individuals and third-party payors in separate opioid cases.

The defendants included manufacturers, distributors, and pharmacy chains. The Teva-related defendants were among the manufacturer defendants, alongside companies such as Purdue Pharma, Johnson & Johnson/Janssen, Mallinckrodt, Endo, and others.

The litigation was not one single case with one plaintiff. It consisted of thousands of coordinated cases, with different plaintiffs asserting overlapping claims.

## Main allegations

The allegations against Teva, Cephalon, and Actavis generally fell into four categories:

1. **Misleading marketing and promotion**
   - Plaintiffs alleged that the companies promoted opioids as safe and effective for long-term treatment of chronic pain.
   - They alleged that marketing minimized addiction, dependence, overdose, and diversion risks.
   - Cephalon was particularly associated with allegations concerning **Actiq**, a highly potent fentanyl product originally approved for breakthrough cancer pain in opioid-tolerant patients. Plaintiffs alleged that Actiq was promoted beyond its approved population.

2. **Failure to monitor and prevent diversion**
   - Plaintiffs alleged that the companies failed to maintain effective systems to detect suspicious orders and prevent opioids from entering illicit channels.
   - Claims were brought under federal and state controlled-substance laws, including the **Controlled Substances Act**, as well as public-nuisance, negligence, fraud, unjust-enrichment, and consumer-protection theories.

3. **Creation of a public nuisance**
   - Government plaintiffs argued that the defendants’ conduct helped create or substantially worsen the opioid epidemic, producing increased addiction, overdose deaths, neonatal abstinence syndrome, emergency-care costs, law-enforcement expenses, and other public costs.

4. **Corporate succession and liability**
   - Teva’s acquisition of **Cephalon in 2011** and its later acquisition of **Actavis Generics in 2016** made successor liability and allocation of responsibility important issues.
   - The litigation also involved disputes over which corporate entities manufactured, marketed, or distributed particular products and which entities were responsible for historical conduct.

The defendants generally denied wrongdoing, disputed causation, challenged public-nuisance and other legal theories, and argued that prescribing physicians and patients—not manufacturers—were responsible for individual use and misuse. They also contested the scope of damages and whether plaintiffs could prove that particular defendants caused particular public harms.

## Key people

- **Judge Dan Aaron Polster**, U.S. District Judge for the Northern District of Ohio, supervised the federal MDL and settlement process.
- **Teva executives and lawyers** defended the company and negotiated settlements; the company’s chief executive during the later settlement period was **Kåre Schultz**.
- **Cephalon founder and former chief executive Frank Baldino Jr.** was a central historical figure in Cephalon’s development and marketing of Actiq, although the litigation was directed primarily at the corporate defendants.
- **Actavis executives and corporate entities** were involved through the company’s generic-opioid business and its later ownership by Allergan and Teva.
- State attorneys general, county and municipal lawyers, and private plaintiffs’ counsel played major roles in negotiating the public settlements. Because the MDL involved thousands of plaintiffs and many defendants, no single plaintiff lawyer or government official represented all claimants.

## Important events and dates

### 2000s: conduct underlying the claims

- **2000–2010s:** Plaintiffs alleged that opioid manufacturers, including Cephalon and Actavis-related entities, engaged in aggressive promotion and inadequate monitoring during the period in which opioid prescribing expanded dramatically.
- **2009:** Cephalon agreed to pay approximately **$425 million** to resolve federal and state allegations concerning off-label promotion of several drugs, including Actiq. The settlement was not the final resolution of the later opioid public-nuisance litigation, but it was part of the historical background.
- **2011:** Teva completed its acquisition of Cephalon.
- **2016:** Teva completed its acquisition of Actavis Generics from Allergan, bringing additional generic-opioid operations into Teva’s corporate group.

### 2017: federal MDL

- **December 2017:** The Judicial Panel on Multidistrict Litigation centralized thousands of opioid cases in the Northern District of Ohio as **MDL No. 2804**, with Judge Polster presiding.

### 2019: bellwether trials and settlements

- **October 2019:** The first federal bellwether trial, involving **Cuyahoga and Summit Counties, Ohio v. Purdue Pharma L.P. et al.**, began. The case settled during trial before a verdict. Teva was among the defendants involved in the broader litigation, although the tr
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall juul — 10/15; missed: 'Vaporized' launch campaign (2015) with young models, San Francisco Unified bellwether; school districts, ~$1.7bn global settlement (Dec 2022) with ~10,000 plaintiffs, Altria write-down / exit; later NJOY purchase, JUUL documents in the UCSF Industry Documents Library</summary>

```
## Overview

The JUUL litigation was a large group of lawsuits and government investigations alleging that **JUUL Labs, Inc.**—the e-cigarette company founded by **James Monsees** and **Adam Bowen**—marketed nicotine products to teenagers, misrepresented nicotine content and addictiveness, and helped create a youth-vaping epidemic. JUUL denied many allegations and said it had acted to combat underage use, but it entered major settlements and changed its marketing and sales practices.

The matters were not one single case. They included:

1. lawsuits by states and local governments;
2. a federal multidistrict litigation (“MDL”) involving individuals, school districts, and other entities;
3. consumer class actions;
4. investigations and enforcement by the Federal Trade Commission (“FTC”), Food and Drug Administration (“FDA”), and state attorneys general; and
5. separate litigation involving JUUL’s investors and business partners.

## Parties and key people

### JUUL Labs

JUUL Labs was founded in 2015 by **James Monsees** and **Adam Bowen**, who had previously worked on the Ploom e-cigarette. JUUL’s products used nicotine-salt liquid and were sold in flavors such as mango, mint, fruit, and crème.

Important company figures included:

- **James Monsees** — co-founder and former chief product officer; later chief executive officer.
- **Adam Bowen** — co-founder and former chief technology officer.
- **Kevin Burns** — CEO from 2017 until September 2019.
- **K.C. Crosthwaite** — CEO beginning in September 2019, after joining from Altria; he led the company during much of the litigation and settlement period.
- **Altria Group, Inc.** — acquired a 35% interest in JUUL in December 2018 for approximately $12.8 billion. Altria was named in some litigation and faced claims concerning its investment and alleged role in JUUL’s conduct.

### Government plaintiffs and regulators

The principal government plaintiffs included:

- **State attorneys general**, including those of North Carolina, Washington, California, Massachusetts, New York, Connecticut, Colorado, Florida, Minnesota, and others.
- **Cities, counties, school districts, and public entities**, many of which sued over alleged costs associated with youth vaping, education, healthcare, and enforcement.
- The **FTC**, which challenged JUUL’s marketing and business practices.
- The **FDA**, which regulated JUUL’s tobacco products and ultimately issued—and then stayed—a marketing denial order in 2022.

### Private plaintiffs

Private plaintiffs included:

- teenagers and young adults who said they became addicted to nicotine through JUUL;
- parents of minors;
- people alleging physical injuries or health effects;
- school districts and local governments alleging costs from vaping-related disruption and prevention efforts; and
- consumers alleging deceptive advertising and unlawful sales practices.

## Core allegations

The allegations varied by case, but commonly asserted that JUUL:

1. **Targeted youth and minors** through social-media campaigns, youthful imagery, influencers, and attractive flavors.
2. **Misrepresented nicotine levels and addictiveness**, including allegedly failing to make clear that JUUL pods could contain nicotine concentrations comparable to or greater than traditional cigarettes.
3. **Designed a highly addictive product**, using nicotine salts that made high nicotine concentrations easier to inhale.
4. **Failed to prevent underage sales**, including online sales and sales through retail stores.
5. **Contributed to a youth-vaping epidemic**, causing schools and governments to incur costs for discipline, education, counseling, and prevention.
6. **Made misleading health or safety claims**, including claims or implications that vaping was safer than smoking without adequate substantiation.
7. **Concealed or minimized adverse effects**, including addiction and respiratory symptoms.

The legal theories included consumer-protection statutes, false advertising, negligence, public nuisance, product liability, fraud, unjust enrichment, and violations of state tobacco laws. Some plaintiffs also alleged that **Altria** aided or participated in the conduct, or that its investment reflected anticompetitive or otherwise unlawful arrangements.

JUUL generally disputed liability, arguing that its products were intended for adult smokers seeking alternatives to combustible cigarettes, that it had taken steps to prevent youth use, and that many alleged injuries were not legally attributable to JUUL.

## Main events and dates

### 2018: Public controversy and regulatory action intensify

In 2018, evidence of widespread youth use of JUUL products prompted major scrutiny.

- **April 2018:** The FDA sent JUUL a request for information concerning the company’s marketing, product design, and youth appeal.
- **September 2018:** The FDA announced a major enforcement initiative against youth e-cigarette use and sent warning letters to JUUL and other manufacturers and retailers. The FDA required JUUL to submit a plan addressing youth access and marketing.
- **November 2018:** JUUL announced restrictions on retail and online sales of flavored pods, including limiting certain flavors in stores and suspending some social-media activity. It also stopped selling most flavored pods in many retail channels, although the details changed over time.
- **December 2018:** Altria purchased its 35% JUUL stake for approximately $12.8 billion. The investment later became a major subject of investor and antitrust-related litigation.

### 2019: First major state lawsuit and federal consolidation

- **May 2019:** **North Carolina Attorney General Josh Stein** sued JUUL in state court, alleging that JUUL deliberately marketed to young people and misrepresented nicotine content and addictiveness. This was one of the first major state lawsuits against JUUL.
- **September 2019:** Kevin Burns left as CEO and **K.C. Crosthwaite** became CEO. JUUL announced substantial layoffs 
```
</details>

<details><summary><code>gpt-5.6-luna</code> — matter_recall bigthorium — 0/11; missed: John Maxwell (sales), Sarah Thompson (business development), Robert Williams (CFO), Emily Roberts (government relations), Laura Smith (procurement), Evelyn Archer (general counsel), Daniel Carter / Law Firm X, Howard Bass (city treasurer)</summary>

```
I’m not aware of any real, publicly documented bribery investigation called **“BigThorium / City of Atlantis.”** I cannot identify reliable parties, people, dates, allegations, or an outcome for such a matter, and I should not invent them.

It may be a fictional case, an internal investigation, or a reference using pseudonyms. If you provide a source, jurisdiction, or alternate spelling, I can summarize it accurately.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id microsoft — hit</summary>

```
**United States v. Microsoft Corp.**

The description matches the landmark antitrust case brought in 1998 by the U.S. Department of Justice and twenty states against Microsoft. The government alleged that Microsoft unlawfully protected its Windows operating-system monopoly by bundling Internet Explorer, imposing restrictions on PC manufacturers, and pressuring software partners. Judge Thomas Penfield Jackson ordered Microsoft’s breakup in 2000, but the D.C. Circuit reversed that remedy in 2001 while sustaining key monopoly-maintenance findings; the case then settled.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id mnk — hit</summary>

```
**Mallinckrodt plc (including Mallinckrodt LLC).**

Mallinckrodt was historically headquartered in the St. Louis area and later became an Irish-domiciled pharmaceutical company. It was a major U.S. manufacturer of generic oxycodone, hydrocodone, and methadone and marketed **Exalgo**, an extended-release hydromorphone product. The company faced federal opioid MDL and state claims concerning suspicious-order monitoring, chargeback data, opioid promotion, and DEA quota requests; it also reached a **2017 DOJ/DEA settlement** over suspicious-order reporting and subsequently entered Chapter 11 proceedings to resolve opioid liabilities.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id jebbush — hit</summary>

```
**Jeb Bush.**

He served two terms as Governor of Florida from 1999 to 2007 while his brother, George W. Bush, was President. The clues match major events of his administration: the 2000 Florida presidential recount, the Terri Schiavo dispute and “Terri’s Law,” missing foster child Rilya Wilson, the “One Florida” order ending racial preferences, and the Florida Supreme Court’s invalidation of the Opportunity Scholarship voucher program. His gubernatorial emails were later released publicly as the **Jeb Bush Email Archive** and used as a research corpus.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id enron — no hit</summary>

```
**Reliant Energy, Inc. — the securities litigation arising from its 2001–02 trading and accounting scandals.**

The strongest identifiers are the alleged manipulation of electricity congestion through false schedules and bids, the use of structured commodity “prepay” transactions and FAS 125/140 accounting, and document destruction at the company’s Houston headquarters. The reference to **“RND7”** likely disguises **“RNP7,”** Reliant’s notorious trading strategy used during the California energy crisis. The employee fantasy-football/NFL gambling allegations also appeared in litigation concerning Reliant.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id enron_k — hit</summary>

```
**Deepwater Horizon litigation—specifically a resort/business class action against BP and its drilling contractors arising from the 2010 Gulf of Mexico oil spill.**

The altered facts closely track the **Deepwater Horizon** explosion, sinking, and Macondo-well spill. “Bleak Horizon” substitutes for *Deepwater Horizon*; **Volteron Corp.** corresponds to **BP**, **Bulene Offshore Drilling** to **Transocean**, **Keyward International** to **Halliburton**, and **Klustering & Cementing Technologies** likely to **M-I SWACO** or another well-services contractor. The plaintiff appears modeled on a Gulf Coast resort seeking economic-loss damages on behalf of similarly situated tourism businesses, although the stated May 7, 2008 date is altered from the actual April 20, 2010 disaster.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id veridian — no hit — template: DePuy ASR / J&J; Zimmer Biomet; Stryker</summary>

```
**No identifiable real company or case; the description appears to be a composite or fabricated matter.**

It borrows features from major metal-on-metal hip litigation—especially **DePuy’s ASR/Pinnacle**, **Stryker’s Rejuvenate/ABG II**, and **Biomet’s M2a** cases. Warsaw, Indiana, points toward **Zimmer Biomet**, and the Northern District of Indiana hosted the **Biomet M2a Magnum Hip Implant Products Liability Litigation (MDL No. 2391)**. But the stated timeline is incompatible with that litigation: the relevant metal-on-metal systems were marketed and challenged years before an alleged March 2017 FDA clearance, and no matching February 2024 withdrawal or June 2022 coating-adhesion recall appears to identify a single real product.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id worldcom — hit</summary>

```
**WorldCom, Inc., and its CEO Bernard Ebbers.**

This describes the **WorldCom accounting scandal and bankruptcy**. In 2002, internal auditor **Cynthia Cooper** uncovered the improper capitalization of network “line costs,” ultimately producing an accounting restatement of about **$11 billion**. WorldCom then filed the largest U.S. bankruptcy to that date. CEO **Bernard Ebbers**, a former basketball coach and motel operator from Mississippi, was convicted of securities fraud and related offenses and sentenced to 25 years. WorldCom emerged from bankruptcy as **MCI**, which was later acquired by **Verizon**, a Bell successor company.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id healthsouth — hit</summary>

```
**HealthSouth Corporation and its founder/CEO, Richard M. Scrushy.**

The facts describe the **HealthSouth accounting scandal**: the Birmingham, Alabama-based rehabilitation and outpatient-surgery company was accused in 2003 of inflating earnings by billions to satisfy Wall Street forecasts. Several CFOs and other executives—members of an inner circle known as “the family”—pleaded guilty. Scrushy was acquitted in 2005 in the first major CEO prosecution involving the Sarbanes-Oxley certification provisions, but was later convicted of bribing Alabama Governor **Don Siegelman**.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id peregrine — hit</summary>

```
**Peregrine Systems, Inc.**

The San Diego software company disclosed in 2002 that it had improperly recognized about **$500 million in revenue over eleven quarters**, largely through contingent reseller transactions concealed by side agreements, and had sold related receivables to banks. Peregrine restated its accounts, fired Arthur Andersen, entered Chapter 11, and sold its Remedy help-desk business to BMC Software. Eight former executives were indicted in 2004; former CEO **Stephen P. Gardner** later pleaded guilty and was sentenced to eight years. Its chairman, **John Moores**, owned the San Diego Padres.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id mckesson_robbins — hit</summary>

```
**McKesson & Robbins, Inc.—the 1938 McKesson & Robbins accounting scandal involving president Philip Musica, alias F. Donald Coster.**

Musica/Coster and his brothers fabricated a nonexistent crude-drug business, creating false inventory and receivables totaling about $19 million. After the fraud was uncovered, Coster committed suicide. The SEC’s investigation—often called the **McKesson & Robbins case**—exposed auditors’ reliance on management-provided documents and led to standards requiring auditors to observe physical inventories and obtain direct confirmation of accounts receivable.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id equity_funding — hit</summary>

```
**Equity Funding Corporation of America — and the related Supreme Court case *Dirks v. SEC*, 463 U.S. 646 (1983).**

The Los Angeles insurance conglomerate collapsed in 1973 after former employee Ronald Secrist alerted securities analyst **Raymond Dirks** that Equity Funding had created tens of thousands of fictitious life-insurance policies—reportedly about two-thirds of its policies—and sold them to reinsurers. Employees used computer-generated records, nighttime “fraud sessions,” forged files, and counterfeit bonds to sustain the scheme. Chairman **Stanley Goldblum** and numerous other executives were convicted, while auditor **Haskins & Sells** faced charges. The SEC censured Dirks for passing the information to clients, but the Supreme Court reversed in *Dirks v. SEC*, establishing the tipper-tippee personal-benefit framework for insider-trading liability.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id purdue — hit</summary>

```
**Purdue Pharma and the Sackler family — *Harrington v. Purdue Pharma L.P.* (2024).**

Purdue, a privately held Connecticut drugmaker controlled by the Sacklers, introduced the extended-release opioid OxyContin in 1996 and promoted it as less addictive. Purdue and three executives pleaded guilty to federal misbranding charges in 2007 and paid roughly $600 million; the company filed for Chapter 11 in 2019 amid nationwide opioid litigation and pleaded guilty to additional federal charges in 2020. In *Harrington v. Purdue Pharma L.P.*, the Supreme Court invalidated Purdue’s bankruptcy plan because it granted the non-debtor Sacklers broad releases from opioid-related civil liability without affected claimants’ consent.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id insys — hit</summary>

```
**Insys Therapeutics and its founder, John Kapoor — the federal Subsys prosecution, *United States v. Kapoor et al*.**

Insys, an Arizona-based drugmaker, marketed **Subsys**, a fentanyl sublingual spray approved for breakthrough pain in cancer patients. Boston prosecutors proved that Kapoor and other executives used sham speaker programs to induce off-label prescribing and operated a reimbursement center that deceived insurers. Kapoor, an Indian-born billionaire, was convicted with four colleagues of racketeering conspiracy in 2019 and sentenced to **66 months**; the notorious sales rap video promoted Subsys dose titration. Insys filed for bankruptcy shortly after agreeing to a federal settlement.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id rdc — hit</summary>

```
**Rochester Drug Cooperative (RDC), including the federal prosecution of former CEO Laurence “Larry” Doud.**

In April 2019, the U.S. Attorney’s Office for the Southern District of New York charged RDC—the member-owned pharmaceutical distributor based in Rochester, New York—making it the first drug distributor criminally charged in connection with the opioid crisis. RDC entered a deferred-prosecution agreement and agreed to pay a $20 million penalty. Former CEO Laurence Doud was charged with conspiring to distribute oxycodone and fentanyl and was later convicted, while former compliance chief William Pietruszewski pleaded guilty. RDC subsequently filed for bankruptcy in 2020.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id clinton_email — hit</summary>

```
**Hillary Clinton — the Hillary Clinton private email server controversy and FBI investigation.**

While serving as U.S. Secretary of State from 2009 to 2013, Clinton used a private email server at her New York home for official communications. She provided roughly 30,000 work-related emails while deleting a similar number deemed personal. FBI Director James Comey announced in July 2016 that no prosecution was warranted, although he described her handling of classified material as “extremely careless.” Shortly before the 2016 presidential election, Comey reopened the inquiry after emails were discovered on a laptop used by Clinton aide Huma Abedin and her husband, Anthony Weiner, then closed it again two days before the election.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id bridgegate — hit</summary>

```
**Kelly v. United States, 590 U.S. 391 (2020), arising from New Jersey’s “Bridgegate” scandal.**

The borough was **Fort Lee**, and the bridge was the **George Washington Bridge**, operated by the **Port Authority of New York and New Jersey**. Governor Chris Christie’s deputy chief of staff **Bridget Anne Kelly** wrote, “Time for some traffic problems in Fort Lee,” and Port Authority official **Bill Baroni** helped implement the lane closures; **David Wildstein** pleaded guilty and testified. The Supreme Court unanimously reversed Kelly’s and Baroni’s federal fraud convictions because their retaliatory scheme, though an abuse of power, was not designed to obtain money or property as required by the federal fraud statutes.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id sony_hack — hit</summary>

```
**Sony Pictures Entertainment — the 2014 Sony Pictures hack, involving co-chair Amy Pascal and *The Interview*.**

Sony Pictures, owned by Japan’s Sony Corporation, was attacked by the “Guardians of Peace,” which leaked films, emails, salaries, and employees’ personal and medical information. U.S. authorities attributed the attack to North Korea, whose government had objected to *The Interview*, a comedy about assassinating Kim Jong-un. Sony initially cancelled the theatrical release, prompting criticism from President Barack Obama. Leaked emails between Amy Pascal and producer Scott Rudin—including racially insensitive jokes about Obama’s film preferences—preceded Pascal’s departure. Employees’ data-breach litigation was consolidated as **Corona v. Sony Pictures Entertainment, Inc.** and settled.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id depuy_asr — hit</summary>

```
**DePuy Orthopaedics’ ASR hip implant litigation (Johnson & Johnson).**

DePuy, a Johnson & Johnson subsidiary, recalled its **ASR XL Acetabular System and ASR Hip Resurfacing System** worldwide in August 2010 after UK registry data showed five-year revision rates of roughly 12–13%. About 93,000 devices had been implanted. The federal multidistrict litigation was centralized in the Northern District of Ohio, and the first trial—**Kransky v. DePuy** in Los Angeles—produced an $8.3 million verdict in 2013. J&J and DePuy then announced an approximately $2.5 billion settlement covering about 8,000 revision claims, which was subsequently expanded.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id earplugs — hit</summary>

```
**3M Company — the Combat Arms Earplug Products Liability Litigation (MDL No. 2885).**

The allegations concerned 3M’s dual-ended **Combat Arms Earplugs Version 2 (CAEv2)**, originally made by **Aearo Technologies**, which 3M acquired in 2008. Competitor **Moldex-Metric** brought the False Claims Act qui tam action that produced a **$9.1 million settlement in 2018**. Hundreds of thousands of service members later alleged hearing loss and tinnitus in the Northern District of Florida MDL; after major bellwether verdicts and Aearo’s unsuccessful bankruptcy strategy, 3M agreed in 2023 to a settlement of approximately **$6 billion**.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id bair_hugger — hit</summary>

```
**3M’s Bair Hugger Forced Air Warming Devices Products Liability Litigation, involving inventor Dr. Scott Augustine.**

The description matches the federal MDL **In re Bair Hugger Forced Air Warming Devices Products Liability Litigation**, MDL No. 2666, in the District of Minnesota. Patients alleged that 3M’s Bair Hugger system caused contaminants to enter surgical fields during joint-replacement procedures. Augustine invented the Bair Hugger, later promoted the competing HotDog conductive-warming system, and was sued by 3M for false advertising. The first bellwether produced a 3M verdict in 2018; Judge Joan Ericksen later excluded plaintiffs’ experts and granted summary judgment, but the Eighth Circuit reversed in 2021, and the Supreme Court denied certiorari.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id dalkon — hit</summary>

```
**The A.H. Robins Company and the Dalkon Shield litigation.**

A.H. Robins, a Virginia pharmaceutical company, marketed the crab-shaped Dalkon Shield intrauterine device in the early 1970s. Its multifilament tail string was blamed for carrying bacteria into the uterus, causing pelvic inflammatory disease, septic miscarriages, infertility, and deaths. Facing hundreds of thousands of claims, Robins filed for Chapter 11 in 1985; its reorganization and acquisition by American Home Products created the roughly $2.5 billion Dalkon Shield Claimants Trust. The litigation—including Judge Miles Lord’s 1984 denunciation of company executives—became a landmark in mass-tort bankruptcy practice and influenced the Medical Device Amendments of 1976.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id bhopal — hit</summary>

```
**The Bhopal disaster litigation involving Union Carbide Corporation and its chairman, Warren Anderson.**

The facts match the methyl isocyanate gas leak from Union Carbide India Limited’s pesticide plant in Bhopal, India, on 2–3 December 1984. U.S. claims were dismissed on forum non conveniens grounds in *In re Union Carbide Corp. Gas Plant Disaster at Bhopal, India*; India then settled with Union Carbide for $470 million in 1989. Chairman Warren Anderson was arrested, released on bail, and later remained wanted in India until his death in 2014, while seven Indian company officials were convicted in 2010.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id texaco_pennzoil — hit</summary>

```
**Pennzoil Co. v. Texaco Inc.**

In 1984, Pennzoil reached a handshake agreement to acquire a three-sevenths interest in Getty Oil, controlled by the J. Paul Getty Trust and the Getty Museum. Texaco then made a higher offer and acquired all of Getty, prompting Pennzoil’s Texas suit for tortious interference. A Houston jury awarded Pennzoil $7.53 billion in actual damages and $3 billion in punitive damages; Texaco later entered Chapter 11 and settled for $3 billion. Pennzoil was represented by famed trial lawyer **Joe Jamail**, who had contributed to the campaign of the original trial judge, Anthony “Tough Tony” Farris, before Judge Solomon Casseb Jr. took over during trial.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id dieselgate — hit</summary>

```
**Volkswagen AG — the Volkswagen “Dieselgate” emissions scandal.**

In September 2015, the U.S. EPA disclosed that Volkswagen had used “defeat device” software in diesel vehicles to recognize laboratory testing and reduce emissions only during tests. Roughly 11 million vehicles worldwide were affected, with real-world nitrogen-oxide emissions reaching up to 40 times U.S. limits. CEO Martin Winterkorn resigned shortly afterward; Volkswagen pleaded guilty in 2017 and incurred more than $25 billion in U.S. penalties, settlements, and vehicle buybacks. The executive arrested at Miami airport was **Oliver Schmidt**, who later received a seven-year sentence. The scheme was exposed through on-road testing by West Virginia University researchers commissioned by the International Council on Clean Transportation.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id theranos — hit</summary>

```
**Theranos and its founder, Elizabeth Holmes (with former president Ramesh “Sunny” Balwani).**

The facts closely track the Theranos scandal: Holmes dropped out of Stanford and claimed Theranos’s Edison technology could perform hundreds of tests from a finger-prick sample. The company raised over $700 million, reached a roughly $9 billion valuation, and operated wellness centers in Walgreens stores. John Carreyrou’s 2015 *Wall Street Journal* investigation relied on whistle-blowers including former employee Erika Cheung and Tyler Shultz, grandson of board member George Shultz, and revealed extensive use of modified Siemens analysers and unreliable results. Holmes was later sanctioned by CMS, charged by the SEC, convicted on four fraud-related counts in 2022, and sentenced to 11 years and 3 months; Balwani received a sentence of nearly 13 years.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id ftx — hit</summary>

```
**FTX and its founder, Sam Bankman-Fried — *United States v. Bankman-Fried*.**

FTX, a Bahamas-based cryptocurrency exchange, collapsed in November 2022 after CoinDesk reported weaknesses in the balance sheet of Alameda Research, Bankman-Fried’s affiliated trading firm. Prosecutors showed that billions in FTX customer funds had been diverted to Alameda and used for investments, property, political contributions, and insider loans. Bankman-Fried was extradited from the Bahamas, convicted in Manhattan in 2023 on seven fraud and conspiracy counts following testimony from Caroline Ellison, Gary Wang, and Nishad Singh, and sentenced to 25 years in prison in March 2024.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id near — hit</summary>

```
**Near Intelligence, Inc. — SEC v. Anil Mathews and related proceedings.**

Near, a Pasadena-area location-data analytics company with operations in Singapore and India, became public in March 2023 through a SPAC merger valuing it at roughly $1 billion, then filed for Chapter 11 in December 2023. The SEC later alleged that founder and CEO **Anil Mathews** orchestrated round-trip transactions with Near’s largest customer, ad-tech company **MobileFuse**, using fictitious invoices to overstate revenue by approximately 27%. The allegations also included Mathews disguising rent for a luxury residence as company “professional services”; Near had earlier terminated Mathews and CFO **Rahul Agarwal** for cause and warned that its financial statements were unreliable.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id meyer — unknown</summary>

```
**No identifiable real-world case—at least not as dated.**

The description says the SEC sued on **September 30, 2026**, a future date, so no such filed case can presently be verified. It appears to be a hypothetical SEC investment-adviser fraud action, likely involving funds holding pre-IPO interests in **SpaceX**, but the adviser and CEO cannot reliably be identified from the supplied facts. The allegations track common SEC claims under Sections 206(1), 206(2), and 206(4) of the Investment Advisers Act: misappropriation, inflated statements, coerced releases, and mishandling of a capital call.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id endo — hit</summary>

```
**Endo International plc (formerly Endo Pharmaceuticals), maker of Opana ER.**

Endo was based in the Philadelphia suburbs and later became Irish-domiciled. It reformulated the extended-release oxymorphone drug **Opana ER** in 2012 and promoted it as abuse- or crush-resistant, although regulators found those claims unsupported. The FDA requested its withdrawal in 2017 after injection abuse was associated with an HIV outbreak and thrombotic microangiopathy. Endo and its generic subsidiaries, including Par Pharmaceutical and Qualitest, faced extensive opioid litigation, entered Chapter 11 in 2022, and resolved claims through bankruptcy; **Endo Health Solutions Inc.** pleaded guilty in 2024 to misbranding Opana ER.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id teva — hit</summary>

```
**Teva Pharmaceutical Industries Ltd.**

Teva is the Israeli-headquartered generic-drug giant that acquired Allergan’s Actavis generics business in 2016. Opioid plaintiffs targeted both Teva’s branded fentanyl products—**Actiq**, the “lollipop” lozenge, and **Fentora**, a buccal tablet—and its large generic oxycodone and hydrocodone business. Teva was a defendant in the federal opioid MDL’s first bellwether litigation and prevailed with other manufacturers in California’s 2021 bench trial. In 2022, it announced a nationwide opioid settlement worth up to roughly **$4.25 billion over 13 years**, including cash and supplies of generic **naloxone nasal spray**.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id juul — hit</summary>

```
**Juul Labs, Inc. — the JUUL youth-vaping litigation, including *In re JUUL Labs, Inc., Marketing, Sales Practices, and Products Liability Litigation* (MDL No. 2913).**

The facts closely track Juul’s history: its 2015 launch of a nicotine-salt pod vaporizer, youth-oriented “Vaporized” marketing and flavored pods, rapid rise to roughly 75% of the U.S. e-cigarette market, and Altria’s purchase of a 35% stake at a $38 billion valuation. Juul later faced school-district, state, and MDL claims over youth marketing and nicotine disclosures; the FDA issued and then stayed a 2022 marketing-denial order. The settlement amounts—about $1.7 billion globally and $462 million with six states—and the creation of the UCSF-hosted Juul document archive further identify the company.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_id bigthorium — no hit — template: Ameresco / Holyoke</summary>

```
**Ameresco, Inc. — its internal investigation concerning the City of Holyoke, Massachusetts.**

The scenario matches reported allegations that Ameresco personnel and an intermediary provided gifts, including luxury watches, to Holyoke officials—among them the city treasurer—in connection with the city’s award of an energy-efficiency contract. Ameresco’s general counsel, assisted by outside counsel, investigated possible improper payments and manipulation of the procurement process. The inquiry apparently remained internal and did not produce a reported prosecution or court case.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall veridian</summary>

```
I do not know of a real federal multidistrict litigation titled **In re Veridian Orthopedics ApexHip Products Liability Litigation**, MDL No. **3102**, in the Northern District of Indiana. I cannot reliably identify parties, allegations, key people, dates, or an outcome for it without inventing facts.

The title may be fictional or may conflate another hip-implant proceeding. MDL No. 3102 appears not to correspond, from my available knowledge, to a Veridian Orthopedics/ApexHip litigation. For an authoritative check, consult the Judicial Panel on Multidistrict Litigation’s docket for **MDL No. 3102** and PACER for the assigned district-court case.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall microsoft — 14/16; missed: 'cut off Netscape's air supply' e-mails, 1994-95 consent decree / Judge Sporkin</summary>

```
**United States v. Microsoft Corp.** was the major federal antitrust case over Microsoft’s conduct in the personal-computer operating-system and web-browser markets. The principal reported appellate decision is **United States v. Microsoft Corp., 253 F.3d 34 (D.C. Cir. 2001) (en banc)**.

## Parties

- **Plaintiffs:** The **United States Department of Justice**, joined initially by **20 states and the District of Columbia**. South Carolina later withdrew; the remaining state plaintiffs eventually split over whether to accept the settlement.
- **Defendant:** **Microsoft Corporation**, then the dominant supplier of Intel-compatible PC operating systems through **Windows 95 and Windows 98**.
- A related state action, **New York v. Microsoft Corp.**, proceeded alongside the federal case.

## Key allegations and issues

The government alleged that Microsoft used its Windows monopoly to suppress threats to that monopoly, especially **Netscape Navigator** and **Sun Microsystems’ Java** technologies. Those products were viewed as “middleware”: if applications could run through a browser or Java layer across different operating systems, developers and users might become less dependent on Windows.

The principal allegations were that Microsoft:

1. **Illegally maintained a monopoly** in Intel-compatible PC operating systems, in violation of **§ 2 of the Sherman Act**.
2. **Attempted to monopolize the web-browser market**, also under § 2.
3. **Tied Internet Explorer to Windows**, allegedly violating **§ 1 of the Sherman Act**.
4. Entered into exclusionary arrangements and imposed restrictions on:
   - PC manufacturers, or **OEMs**;
   - internet access providers;
   - software developers and content providers.

Specific conduct included restricting OEMs’ ability to remove or obscure Internet Explorer, commingling browser and operating-system code, making Internet Explorer difficult to uninstall, pressuring firms not to promote Netscape, and taking steps to undermine cross-platform Java.

## Key people

- **Bill Gates:** Microsoft co-founder, chairman, and CEO during most of the relevant conduct. His videotaped deposition became notable because the trial judge regarded portions as evasive and because internal Microsoft communications involving Gates were important evidence.
- **Steve Ballmer:** Microsoft president and later CEO; a senior executive during the litigation.
- **David Boies:** Lead trial lawyer for the Justice Department.
- **Joel I. Klein:** Assistant Attorney General in charge of the DOJ Antitrust Division when the case was filed.
- **Janet Reno:** U.S. Attorney General at the filing.
- **Thomas Penfield Jackson:** U.S. district judge who conducted the trial, issued findings against Microsoft, and ordered the company broken up.
- **Kenneth Starr:** Led Microsoft’s Supreme Court effort seeking review of the breakup order and Judge Jackson’s conduct.
- **Charles James:** Assistant Attorney General for Antitrust under President George W. Bush; oversaw the federal government’s decision not to seek a breakup and the negotiation of the settlement.
- **Colleen Kollar-Kotelly:** District judge assigned after remand; approved the final consent decree and handled the remedy proceedings.
- **Jim Barksdale:** Netscape’s CEO, who testified about Microsoft’s dealings with Netscape.
- **Scott McNealy:** Sun Microsystems’ CEO; Sun’s Java technology was central to the middleware theory.

## Main events

- **May 18, 1998:** The DOJ and state attorneys general filed suit in the U.S. District Court for the District of Columbia. The filing came shortly before the planned release of Windows 98.
- **October 19, 1998:** The bench trial began before Judge Jackson.
- **November 5, 1999:** Jackson issued detailed **findings of fact**, concluding that Microsoft possessed monopoly power in the market for Intel-compatible PC operating systems and had used anticompetitive tactics to protect it.
- **April 3, 2000:** Jackson issued **conclusions of law**, holding Microsoft liable for:
  - unlawful monopoly maintenance;
  - attempted monopolization of the browser market; and
  - unlawful tying of Internet Explorer to Windows.
- **June 7, 2000:** Jackson entered a final judgment ordering Microsoft split into two companies—one for operating systems and one for applications—and imposed interim conduct restrictions.
- **June 28, 2001:** The en banc D.C. Circuit issued its decision. It:
  - **unanimously affirmed** liability for unlawful monopoly maintenance based on substantial portions of Microsoft’s conduct;
  - **reversed** the attempted-monopolization judgment because the government had not adequately defined and proved a browser market;
  - **vacated** the per se tying judgment and directed that tying be analyzed under the more fact-intensive **rule of reason**;
  - **vacated the breakup remedy**; and
  - ordered reassignment to a different district judge because Judge Jackson’s extrajudicial press contacts and comments created an appearance of partiality.
- **September 6, 2001:** The DOJ announced that it would not seek to break up Microsoft and would not pursue the tying claim on remand, choosing instead to seek prompt conduct remedies.
- **October 9, 2001:** The U.S. Supreme Court declined Microsoft’s request for review.
- **November 2, 2001:** Microsoft and the DOJ announced a proposed settlement. Nine states joined it; nine other states and the District of Columbia continued to seek stronger remedies.
- **November 1, 2002:** Judge Kollar-Kotelly approved the federal settlement, with modifications, under the **Tunney Act**, and issued a substantially similar remedy in the nonsettling states’ case.
- **November 12, 2002:** The final federal judgment was entered.

## Outcome

Microsoft was **not broken up**. The lasting legal result was that Microsoft was held to have **illegally maintained its Windows monopoly** through exclusionary conduct. The attempted-monopolization ruling was reversed, and the tying ruling did
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall mnk — 11/21; missed: Exalgo (hydromorphone ER), suspicious order monitoring, chargeback data / downstream visibility, Florida pill mills, DEA production quota, Covidien spin-off (2013), Washington Post ARCOS data: ~28% of pills, Opioid Industry Documents Archive (UCSF / Johns Hopkins)</summary>

```
Mallinckrodt’s opioid litigation was part of the nationwide litigation over prescription opioids, principally **In re National Prescription Opiate Litigation, MDL No. 2804**, before Judge **Dan Aaron Polster** in the U.S. District Court for the Northern District of Ohio. Mallinckrodt’s liabilities were ultimately resolved primarily through two Chapter 11 cases rather than a conventional MDL trial or final merits judgment.

## Parties and products

The principal Mallinckrodt defendants included:

- **Mallinckrodt plc**, the Irish parent company;
- **Mallinckrodt LLC** and related specialty-generics entities, including **SpecGx LLC**;
- historically, **Mallinckrodt Inc.** and other affiliates involved in manufacturing and selling generic opioids.

Mallinckrodt was a major manufacturer of generic opioid tablets, particularly **oxycodone** and **hydrocodone** products. Public authorities alleged that, measured by dosage units, it had been among the largest U.S. opioid manufacturers.

The plaintiffs included:

- states, territories, counties, cities, tribal governments, and other public entities;
- hospitals, health systems, third-party payors, and other private plaintiffs;
- in related proceedings, individual personal-injury and wrongful-death claimants.

The MDL also included claims against many other manufacturers, distributors, and pharmacies. Mallinckrodt’s settlement addressed its own alleged share of the opioid crisis, not the entire MDL.

## Core allegations and disputed issues

Governmental plaintiffs generally alleged that Mallinckrodt and other opioid manufacturers:

1. **Promoted or facilitated excessive opioid prescribing and sales**, while understating addiction and overdose risks;
2. **Failed to maintain effective controls against diversion**, including failure to identify, investigate, report, or stop suspicious orders;
3. Shipped quantities allegedly inconsistent with legitimate medical demand despite warning signs;
4. Created or contributed to a **public nuisance** and caused governments to incur treatment, emergency-response, law-enforcement, child-welfare, and other costs;
5. Violated state consumer-protection, controlled-substances, fraud, negligence, unjust-enrichment, and related laws.

Mallinckrodt disputed liability. Important legal issues included causation, federal Controlled Substances Act duties, the scope of suspicious-order monitoring obligations, state-law public-nuisance theories, statutes of limitation, proof of damages, and whether claims against affiliated entities were direct, derivative, or otherwise subject to bankruptcy treatment.

A separate but related federal enforcement matter concerned Mallinckrodt’s suspicious-order practices. In **July 2017**, the company agreed to pay **$35 million** to resolve U.S. Department of Justice allegations that it had failed to report suspicious opioid orders and had inadequate controls at certain facilities. The settlement did not constitute an admission of the civil allegations, but the underlying conduct became relevant background in later opioid suits.

## Key people

- **Judge Dan Aaron Polster** — federal judge supervising MDL 2804 in Cleveland.
- **Paul J. Hanly Jr.**, **Joe Rice**, and **Jayne Conroy** — prominent members of the MDL plaintiffs’ leadership representing local governments and other plaintiffs.
- **Josh Shapiro**, then Pennsylvania attorney general, and other state attorneys general — negotiated and publicly announced the framework for Mallinckrodt’s nationwide governmental settlement. Shapiro later became Pennsylvania governor.
- **Mark Trudeau** — Mallinckrodt’s chief executive during the initial settlement negotiations and first bankruptcy.
- **Siggi Olafsson** — became Mallinckrodt’s president and CEO in 2022 and led the company during the second restructuring.
- **Judge John E. Dorsey** — U.S. bankruptcy judge in Delaware who presided over Mallinckrodt’s first Chapter 11 case and confirmed its 2022 plan.
- **Judge Thomas M. Horan** — Delaware bankruptcy judge who presided over the 2023 Chapter 11 case and confirmed the second restructuring plan.

## Main chronology

### 2017: MDL formation and federal settlement

- On **December 5, 2017**, the Judicial Panel on Multidistrict Litigation created **MDL 2804**, centralizing federal opioid cases in the Northern District of Ohio before Judge Polster.
- Earlier, on **July 11, 2017**, DOJ announced Mallinckrodt’s **$35 million** Controlled Substances Act settlement concerning alleged failures to report suspicious orders and maintain effective diversion controls.

### 2018–2019: Expansion of public-entity litigation

Thousands of opioid cases were filed or transferred into MDL 2804. States also pursued claims in their own courts or through coordinated negotiations. Discovery focused on sales data, suspicious-order systems, marketing, regulatory compliance, and the allocation of responsibility among manufacturers, distributors, pharmacies, and prescribers.

Mallinckrodt faced substantial potential liability but did not proceed to a final MDL merits trial. Its financial condition was also burdened by other liabilities, especially claims involving **Acthar Gel**, which later became a major component of its bankruptcy.

### 2020: Proposed nationwide opioid settlement and first bankruptcy

- On **February 25, 2020**, Mallinckrodt announced an agreement in principle with a group of state attorneys general and the MDL plaintiffs’ executive committee. The proposed opioid settlement was valued at approximately **$1.6 billion**, generally described as:
  - **$1.3 billion** in cash paid over several years;
  - warrants or other equity-linked consideration potentially worth about **$300 million**;
  - establishment of a trust to distribute funds to states, local governments, tribes, and other qualifying claimants.
- The framework contemplated that Mallinckrodt’s generic-opioid business would remain operating under court-supervised restrictions and that the settlem
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall enron — 18/20; missed: document shredding, California energy-crisis trading schemes</summary>

```
The Enron scandal was the collapse of **Enron Corp.**, once a major Houston-based energy-trading company, after disclosures that its reported profits and financial position had been distorted through aggressive accounting, off-balance-sheet entities, and misleading public statements. The collapse produced SEC and congressional investigations, one of the largest bankruptcy cases in U.S. history, extensive civil litigation, and numerous criminal prosecutions.

## Principal parties and people

- **Enron Corp.** — the public company that filed for bankruptcy.
- **Kenneth L. Lay** — Enron’s founder, longtime chairman, and chief executive; he resumed the CEO role after Jeffrey Skilling resigned.
- **Jeffrey K. Skilling** — Enron’s president and CEO until August 2001; a principal architect of its trading-oriented business model.
- **Andrew S. Fastow** — chief financial officer; created and managed special-purpose entities, including the **LJM partnerships**, that transacted with Enron.
- **Lea Fastow** — Andrew Fastow’s wife and a former Enron finance executive; involved in transactions connected to Enron-related entities.
- **Richard Causey** — chief accounting officer.
- **Ben Glisan Jr.** — treasurer; participated in the “Southampton” transaction.
- **Michael Kopper** — Fastow’s subordinate and an LJM participant; became an important cooperating witness.
- **Sherron Watkins** — Enron vice president who warned Lay in August 2001 that accounting problems could cause the company to “implode in a wave of accounting scandals.”
- **Arthur Andersen LLP** — Enron’s outside auditor; also earned substantial consulting fees from Enron.
- **David Duncan** — Andersen’s lead audit partner for Enron.
- **Nancy Temple** — Andersen in-house lawyer whose communications figured in the document-destruction case.
- **Enron Task Force** — the Justice Department team formed in January 2002 to coordinate the federal criminal investigation.
- **SEC**, **Department of Justice**, **FBI**, congressional committees, bankruptcy representatives, shareholders, employees, banks, and other transaction counterparties also pursued or defended claims.

## Core allegations and accounting issues

The central issue was not simply that Enron used special-purpose entities, but that it allegedly used them and other accounting devices to present a materially misleading picture of its finances.

### Special-purpose entities and conflicts of interest

Fastow controlled or had financial interests in entities that did business with Enron, notably **LJM1** and **LJM2**. Enron’s board approved conflict-of-interest waivers allowing him to manage them. Prosecutors and regulators alleged that these entities were used to:

- move poorly performing assets or debt away from Enron’s reported balance sheet;
- manufacture earnings or avoid recognizing losses;
- provide purported hedges that lacked genuine economic independence because they were backed largely by Enron stock;
- enrich Fastow and associates at Enron’s expense.

Important structures included the **Chewco** entity, connected to Enron’s investment in **JEDI**, and the “Raptor” vehicles. When accounting requirements were not met, entities that had been treated as independent had to be consolidated into Enron’s financial statements.

### Misleading earnings and business performance

Enron used **mark-to-market accounting** for long-term contracts, recognizing estimated future profits at the time contracts were signed. Although mark-to-market accounting was not inherently unlawful, the government alleged that Enron used unsupported assumptions and other devices to report earnings that did not reflect economic reality.

Prosecutors also alleged that executives misrepresented the condition of business units, including:

- **Enron Broadband Services**, whose technological and commercial prospects were allegedly overstated;
- **Enron Energy Services**, whose losses and performance were allegedly concealed or manipulated;
- Enron’s core wholesale business and overall liquidity.

### Public statements, stock sales, and employee losses

Lay, Skilling, and others repeatedly portrayed Enron as financially strong while, according to the government, knowing of serious undisclosed problems. Senior executives sold substantial amounts of Enron stock. Employees and other investors suffered enormous losses as the share price fell from more than $80 in early 2001 to near zero. Many employees also lost retirement savings heavily invested in Enron stock.

### Arthur Andersen’s document destruction

As scrutiny intensified, Andersen personnel destroyed or deleted Enron-related documents under the firm’s document-retention policy. The criminal issue was whether Andersen corruptly persuaded employees to withhold or destroy documents in anticipation of official proceedings.

## Main events, 2001–2002

- **February 12, 2001:** Skilling became Enron’s CEO; Lay remained chairman.
- **August 14, 2001:** Skilling abruptly resigned, citing personal reasons. Lay returned as CEO.
- **August 2001:** Watkins sent Lay her warning memorandum and later met with him. She questioned the sustainability and accounting treatment of Fastow-related structures.
- **October 16, 2001:** Enron announced a **$618 million third-quarter loss** and a roughly **$1.2 billion reduction in shareholder equity**, much of it connected to related-party transactions.
- **October 17, 2001:** The SEC began seeking information about Enron’s related-party dealings; the inquiry soon became formal.
- **October 22, 2001:** Enron publicly disclosed the SEC inquiry.
- **October 24, 2001:** Fastow was removed as CFO.
- **November 8, 2001:** Enron announced that it would restate financial statements for 1997 through the first half of 2001, reducing previously reported net income by hundreds of millions of dollars and adding debt to its balance sheet.
- **November 9, 2001:** Rival energy company **Dynegy Inc.** agreed to acquire Enron in a rescue transaction.
-
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall jebbush — 12/18; missed: James Crosby (corrections secretary) corruption, Elián González (2000), Lt. Governors Frank Brogan / Toni Jennings, Scripps Florida biotech deal, medical-malpractice / tort reform (2003), public release of jeb@jeb.org e-mails</summary>

```
Jeb Bush, a Republican and son of former President George H. W. Bush, served as Florida’s 43rd governor from **January 5, 1999, to January 2, 2007**. Republicans controlled the Legislature for most of his tenure, allowing him to pursue an unusually ambitious conservative program. His governorship was defined by education reform, tax and spending fights, privatization, environmental policy, repeated hurricanes, the 2000 presidential recount, and the Terri Schiavo case.

## 1. Education reform and school accountability

Education was Bush’s signature domestic issue.

### The A+ Plan

In **1999**, Bush and the Republican-controlled Legislature enacted the **A+ Plan for Education**. It:

- graded public schools **A through F**, largely using standardized-test results;
- expanded testing through the **Florida Comprehensive Assessment Test (FCAT)**;
- rewarded high-performing or improving schools;
- imposed consequences on persistently failing schools; and
- offered vouchers to some students in schools receiving repeated failing grades.

Bush argued that transparent grading, testing, competition, and consequences would force schools to improve, especially those serving poor and minority students. Critics—including the **Florida Education Association**, many teachers, school boards, and Democrats—said the system overemphasized testing, stigmatized schools, encouraged teaching to the test, and failed to account adequately for poverty and language barriers.

Florida’s school grades and test scores generally rose during Bush’s tenure, and the state became a national model for Republican education policy. Disputes continued over whether the gains reflected genuine learning, changes in grading formulas, retention policies, or intensive test preparation.

### Vouchers and constitutional litigation

Bush strongly promoted private-school choice.

- The **Opportunity Scholarship Program**, enacted in 1999, allowed students in repeatedly failing public schools to attend private schools at state expense.
- In **Bush v. Holmes**, a coalition led by parents and education groups challenged the program.
- On **January 5, 2006**, the **Florida Supreme Court**, in a 5–2 decision, struck down the private-school portion. The court held that it violated Article IX, section 1 of the Florida Constitution, which requires the state to provide a “uniform” system of free public schools.

Bush denounced the ruling as hostile to school choice, but the decision ended that voucher mechanism. Other programs, including scholarships for students with disabilities and tax-credit-supported scholarships, survived in different legal forms.

### Class-size amendment

Bush opposed the **2002 constitutional amendment** requiring smaller public-school classes, arguing that it was rigid and extraordinarily expensive. Voters approved it on **November 5, 2002**. Bush and legislative Republicans later sought flexibility in implementation, while Democrats, teachers, and amendment sponsor **State Senator Kendrick Meek** accused them of trying to evade the voters’ mandate. The requirement remained in the Constitution and forced substantial state spending on teachers and classrooms.

### One Florida and affirmative action

In **November 1999**, Bush announced the **One Florida Initiative**, which ended explicit racial and gender preferences in state university admissions and state contracting, replacing them with race-neutral outreach and guarantees tied to class rank.

Bush said the policy would preserve diversity without quotas. Civil-rights leaders, including **State Senator Kendrick Meek** and **State Representative Tony Hill**, argued that it would reduce opportunities for Black and Hispanic Floridians. In **January 2000**, Meek and Hill staged a sit-in at Bush’s office. Bush initially reacted sharply, saying he would “kick their asses out,” a remark for which he apologized.

The policy took effect, and Florida’s universities continued to use race-neutral admissions measures. Whether One Florida preserved meaningful minority access remained politically disputed.

## 2. Taxes, spending, and the size of government

Bush entered office promising smaller government and repeatedly pushed tax cuts. Over eight years, he and the Legislature approved billions of dollars in tax reductions, including cuts affecting the intangible personal-property tax, business taxes, and other levies.

Supporters said the cuts encouraged investment and helped Florida’s rapid economic growth. Democrats and local-government advocates argued that they disproportionately benefited wealthy residents and businesses while constraining education, health care, and infrastructure.

Bush also used the line-item veto aggressively and cultivated a reputation for rejecting legislative “turkeys,” or local pork-barrel projects. This sometimes put him at odds with Republican legislative leaders, even though his party controlled both chambers.

### Civil-service overhaul and privatization

In **2001**, Bush won passage of **Service First**, which reduced job protections for many state employees and gave managers greater authority over hiring and firing. The **American Federation of State, County and Municipal Employees** and other unions argued that it politicized the workforce and weakened due-process rights. Bush said it made government more accountable.

His administration outsourced numerous state functions, including personnel administration, technology, health and human services, and prison-related work. Several contracts became controversial because of cost overruns, weak oversight, or poor performance. Critics alleged that privatization sometimes rewarded politically connected contractors; Bush maintained that competition could deliver services more efficiently.

A prominent example was the **People First** human-resources system, contracted to **Convergys**. It experienced implementation and service problems, reinforcing criticism that the administration privatized too qui
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall mckesson_robbins — 9/13; missed: crude drug department, fictitious Canadian warehouses (Montreal), Julian Thompson (treasurer) exposed it, auditing standards: observe inventory, confirm receivables</summary>

```
The **McKesson & Robbins fraud of 1938** was a major U.S. accounting scandal involving fictitious inventories and receivables. Its exposure led directly to important reforms in auditing practice.

## Parties and key people

- **McKesson & Robbins, Inc.**: A large drug and chemical distributor. It had been acquired in 1925 by **F. Donald Coster**, who became its president.
- **F. Donald Coster**: In reality **Philip Musica**, a convicted swindler operating under an assumed identity. He directed the fraud.
- **George Dietrich**: McKesson & Robbins’ assistant treasurer. His suspicions about the company’s finances helped expose the scheme.
- **Price, Waterhouse & Co.**: The company’s independent auditor. It had certified financial statements containing the fictitious assets.
- **Securities and Exchange Commission (SEC)**: Investigated the accounting and auditing failures through proceedings commonly cited as **In the Matter of McKesson & Robbins, Inc.**
- **Musica’s brothers**: George, Arthur, and Robert Musica participated under assumed names in the organization and operation of the fraudulent business.

## Nature of the fraud

Coster/Musica and his associates created a purported **crude-drugs department** that appeared to buy and sell large quantities of raw pharmaceutical materials. Much of this business was fictitious.

The scheme relied on:

- fabricated purchase and sales documents;
- nonexistent suppliers and customers;
- false accounts receivable;
- fictitious inventory;
- related or controlled entities presented as independent counterparties; and
- diversion of corporate funds through bogus transactions.

By 1938, the balance sheet reportedly overstated assets by roughly **$19 million**, principally through about **$10 million of nonexistent inventory** and approximately **$9 million of fictitious receivables.** The exact figures vary somewhat among historical accounts.

A central auditing issue was that Price Waterhouse had not independently observed the physical inventory or directly confirmed receivables with purported customers. At the time, those procedures were not yet universally treated as mandatory.

## Main events

- **1925**: Philip Musica, using the name F. Donald Coster, acquired control of McKesson & Robbins and became its president.
- **1925–1938**: Coster and his associates operated the fictitious crude-drugs business and inflated the company’s reported assets and profits.
- **Late 1938**: Assistant treasurer George Dietrich became concerned about unusually large cash demands and the financial practices of the crude-drugs division. He brought the matter to the company’s directors.
- **December 1938**: The board initiated an investigation. The fictitious inventory and receivables began to unravel, and authorities discovered that Coster was actually Philip Musica.
- **December 16, 1938**: Facing arrest and exposure, Coster/Musica committed suicide by shooting himself at his home in Fairfield, Connecticut.
- **1938–1939**: Federal authorities pursued other participants, and the SEC conducted a broad investigation into the company’s financial statements and the auditors’ work.
- **1940**: The SEC issued its report and findings in the McKesson & Robbins proceeding, criticizing weaknesses in the audit and recommending stronger procedures.

## Outcome and significance

The fraud collapsed, the fictitious assets were removed from McKesson & Robbins’ accounts, and Musica’s participating brothers were prosecuted and convicted or pleaded guilty to federal offenses connected with the scheme. The corporation itself survived under reorganized management rather than disappearing.

The most lasting result was the transformation of auditing standards. In response to the scandal:

- auditors were expected to **observe physical inventories** when inventory was material;
- auditors were expected to obtain **direct confirmation of accounts receivable** from customers;
- greater attention was given to auditor independence, internal controls, and corroborating management representations; and
- the SEC asserted a stronger role in evaluating the adequacy of independent audits of public companies.

The case demonstrated that checking documents supplied by management was insufficient when the documents and counterparties themselves could be fabricated. It is therefore commonly treated as a foundational event in the development of modern U.S. audit procedures.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall peregrine — 10/13; missed: John Moores (chairman, Padres owner), 2004 indictments of eight executives, Gardner's eight-year sentence (2008)</summary>

```
Peregrine Systems, Inc., a San Diego enterprise-software company, became the subject of one of the major early-2000s accounting-fraud cases after admitting that its reported revenue had been materially overstated.

## Parties

The matter involved several overlapping proceedings:

- **Peregrine Systems, Inc.**, the public company whose financial statements were misstated.
- The **U.S. Securities and Exchange Commission**, which brought civil enforcement actions against former Peregrine officers and others.
- The **U.S. Department of Justice/U.S. Attorney’s Office for the Southern District of California**, which prosecuted former executives, employees, and outside participants.
- **Arthur Andersen LLP**, Peregrine’s former independent auditor, and individual Andersen personnel.
- Outside business partners and customers allegedly used to create or disguise revenue, including software resellers and financing companies.
- Peregrine shareholders, who pursued securities litigation arising from the collapse.

## Core allegations

According to prosecutors and the SEC, Peregrine improperly recognized hundreds of millions of dollars of software-license revenue, principally from 1999 through 2002. The alleged methods included:

- Recording revenue from transactions that were not final or were subject to undisclosed contingencies.
- Using **side agreements** that gave customers or resellers cancellation, return, or payment protections inconsistent with immediate revenue recognition.
- Recording sales to resellers even though the resellers had not sold the software to end users and were not genuinely obligated or able to pay.
- Arranging financing or “parking” transactions so that third parties appeared to pay Peregrine’s receivables, while Peregrine secretly assumed or guaranteed the economic risk.
- Backdating or altering contracts and other documents to make transactions appear completed before quarter-end.
- Manipulating accounts receivable and concealing uncollectible balances.
- Misleading Peregrine’s auditors and the investing public.

The government alleged that the scheme inflated reported revenue by roughly **$500 million** and understated losses by approximately **$1 billion**, although figures varied among the indictments, SEC complaints, and restatement materials. Peregrine ultimately restated several years of financial results.

## Key people

### Stephen P. Gardner
Peregrine’s former **president, chief executive officer, and chairman**. Prosecutors portrayed Gardner as a central participant in the revenue-inflation scheme and charged him with conspiracy, securities fraud, and related offenses. He denied knowingly participating in fraud.

### Douglas S. Powanda
A former **executive vice president for worldwide sales**. Powanda pleaded guilty and became an important government witness. He admitted participating in improper transactions and testified against Gardner and other defendants.

### Richard T. Nelson
Peregrine’s former **chief financial officer**. Nelson pleaded guilty to conspiracy and securities-fraud-related charges and cooperated with the government.

### Gary L. Lenz
A former Peregrine **president and chief operating officer**. He was charged in the criminal case but was acquitted at trial.

### Matthew C. Gless
A former Peregrine **chief financial officer** during part of the relevant period. He was among the executives accused in SEC proceedings of participating in or facilitating improper accounting.

### Arthur Andersen personnel
Peregrine’s outside audit team was accused of failing to respond appropriately to warning signs and, in some instances, participating in or facilitating misleading audit work. Former Andersen audit partner **Michael J. Kershaw** was criminally charged and tried with company executives; he was acquitted.

A number of other Peregrine finance, sales, and accounting employees, as well as outside reseller or financing-company personnel, pleaded guilty or settled SEC charges. The exact defendant lists differed among the original indictment, superseding indictments, and civil cases.

## Main events

### 1999–2002: Alleged fraud period
Peregrine reported rapid growth while allegedly using improper transactions and accounting practices to meet revenue targets. The company’s stock traded at very high levels during the technology boom.

### April–May 2002: Accounting problems emerge
Peregrine announced that it was investigating accounting irregularities and that previously issued financial statements could not be relied upon. Senior officers, including Gardner, left their positions. The company’s stock price collapsed, and trading was eventually halted or the shares were delisted.

### June 2002: Bankruptcy
Peregrine filed for **Chapter 11 bankruptcy protection** in the U.S. Bankruptcy Court for the District of Delaware. It later sold major assets, including its Remedy business, and reorganized.

### 2003: SEC civil enforcement
On **June 30, 2003**, the SEC filed a major civil fraud action against former Peregrine officers and outside participants. The complaint alleged a broad scheme to inflate revenue and conceal the company’s deteriorating financial condition.

### 2004: Federal criminal indictment
In **May 2004**, a federal grand jury in San Diego returned an indictment charging former Peregrine executives and others with conspiracy, securities fraud, bank fraud, and obstruction-related offenses. Superseding charges followed as the investigation developed.

### 2005–2006: Guilty pleas and cooperation
Several former officers and employees, including Powanda and Nelson, pleaded guilty and agreed to cooperate. Their testimony became central to the prosecution’s case against Gardner and the remaining defendants.

### 2007: First major trial ends without a verdict
The first trial of Gardner and other defendants ended in **March 2007** with a mistrial after the jury was unable to reach unanimous verdicts.

### 2008: Retrial and acquittals
At the retrial, the
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall healthsouth — 12/13; missed: acquitted, June 2005</summary>

```
## Overview

The **HealthSouth accounting fraud** was a massive earnings-manipulation scheme at **HealthSouth Corporation**, a Birmingham, Alabama–based operator of rehabilitation hospitals and outpatient clinics. Federal prosecutors alleged that, from **1996 through early 2003**, senior executives systematically falsified the company’s financial statements to meet Wall Street earnings expectations and conceal deteriorating performance.

The scandal became public in **March 2003**. HealthSouth later estimated that its financial statements had overstated income by roughly **$2.7 billion** over many years, although the criminal indictment initially described a fraud of about **$2.74 billion**.

## Parties and principal people

### Government and regulators

- **United States Department of Justice**, principally the U.S. Attorney’s Office for the Northern District of Alabama, brought the criminal cases.
- **Securities and Exchange Commission** brought a civil enforcement action.
- **FBI** and other federal investigators conducted the investigation.
- **Judge Karon O. Bowdre** of the U.S. District Court in Birmingham presided over founder **Richard M. Scrushy’s** criminal trial.

### HealthSouth figures

- **Richard M. Scrushy** — HealthSouth’s founder, chairman, and chief executive officer. Prosecutors alleged that he directed and benefited from the fraud; he denied knowing about it.
- **Weston Smith** — former chief financial officer. He pleaded guilty and became a major government witness.
- **William Owens** — former CFO and later president. He pleaded guilty and testified that Scrushy knew of and directed the manipulation.
- **Aaron Beam** — co-founder and former CFO. He pleaded guilty and testified for the government.
- **Michael Martin** — former CFO. He pleaded guilty and testified against Scrushy.
- **Hannibal “Sonny” Crumpler** and other accounting executives were among the insiders who pleaded guilty or cooperated.
- **Ernst & Young** — HealthSouth’s outside auditor. It was not charged as a participant in Scrushy’s criminal case, but its audit work became the subject of civil litigation and scrutiny.

## How the fraud allegedly worked

According to prosecutors and cooperating executives, HealthSouth’s senior accounting personnel met after each quarter’s preliminary results were known. They calculated the difference between actual earnings and the earnings needed to satisfy analysts’ expectations, then inserted false entries to close the gap.

The scheme was sometimes described internally as filling the **“hole”** or making the numbers match the **“street.”** Common techniques included:

- overstating revenue and assets;
- understating expenses;
- recording fictitious property, plant, and equipment;
- spreading false entries among many facilities and accounts;
- keeping individual entries below thresholds likely to attract auditors’ attention; and
- falsifying supporting records.

Prosecutors contended that Scrushy demanded that HealthSouth “make the numbers,” knew the reported results were false, signed SEC filings, and personally benefited through salary, bonuses, stock transactions, and other compensation. Scrushy’s defense argued that subordinates committed the accounting fraud without his knowledge and then blamed him to obtain leniency.

## Main events

### 1996–2002: alleged manipulation

The government alleged that the systematic fraud began by at least **1996** and continued through **2002**, with false financial statements filed with the SEC and released to investors.

### August 2002: earnings warning and stock sale scrutiny

On **August 27, 2002**, HealthSouth announced that changes in Medicare reimbursement would materially reduce earnings. Its stock price fell sharply. Scrushy’s earlier sales of HealthSouth shares drew scrutiny, including allegations that he had sold stock while possessing adverse nonpublic information.

### March 2003: undercover recordings and federal raid

In early **March 2003**, CFO Weston Smith contacted federal authorities and began cooperating. Investigators recorded conversations involving Scrushy and other executives.

On **March 18, 2003**, federal agents raided HealthSouth’s Birmingham headquarters. The SEC simultaneously filed a civil fraud action and obtained an emergency asset freeze against Scrushy. Trading in HealthSouth stock was halted, and Scrushy was removed from control of the company.

### November 2003: Scrushy indicted

On **November 4, 2003**, a federal grand jury indicted Scrushy. A superseding indictment ultimately charged him with numerous offenses, including:

- conspiracy;
- securities fraud;
- false statements and false certifications in SEC filings;
- mail and wire fraud;
- money laundering; and
- violations connected with the **Sarbanes-Oxley Act’s** CEO certification requirements.

The case was notable as one of the first major attempts to prosecute a chief executive under Sarbanes-Oxley’s financial-certification provisions.

## Scrushy’s 2005 accounting-fraud trial

The jury trial began in Birmingham in **January 2005**. The government relied heavily on testimony from former CFOs and other executives who had pleaded guilty, as well as secretly recorded conversations.

The central issue was not whether HealthSouth’s accounts were fraudulent—the defense largely accepted that a major fraud had occurred—but **whether Scrushy knew about and directed it**.

### Prosecution position

Prosecutors argued that:

- a hands-on founder and CEO could not plausibly have been unaware of a multibillion-dollar fraud;
- former CFOs directly implicated Scrushy;
- recordings showed consciousness of wrongdoing; and
- Scrushy’s compensation and stock dealings gave him a strong motive.

### Defense position

Scrushy’s lawyers attacked the cooperating witnesses as admitted liars seeking reduced sentences. They argued that:

- the accounting department concealed the fraud from Scrushy;
- the recordings were ambiguous and did not contain a cl
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall equity_funding — 9/14; missed: ~64,000 fictitious policies, sold to reinsurers for cash, forged bonds / counterfeit securities, auditors Wolfson Weiner / Seidman & Seidman charged, reorganised as Orion Capital</summary>

```
The **Equity Funding Corporation of America scandal**, exposed in **1973**, was one of the largest U.S. corporate and insurance frauds of its era. It involved the fabrication of insurance policies and related assets to inflate revenue, earnings, and the company’s financial condition.

## Parties

- **Equity Funding Corporation of America (EFCA)**: A Los Angeles–based, publicly traded financial-services holding company.
- **Equity Funding Life Insurance Company** and other EFCA subsidiaries: Used to issue and reinsure the fictitious policies.
- **Investors and policyholders**: Investors bought EFCA securities on the strength of false financial statements; legitimate policyholders faced uncertainty after the collapse.
- **Banks, reinsurers, auditors, and securities firms**: Relied to varying degrees on EFCA’s records and representations. Reinsurers were induced to accept purported risks and transfer funds based on nonexistent policies.
- **Government authorities**: Principally the **Securities and Exchange Commission**, federal prosecutors, state insurance regulators, and bankruptcy authorities.

## Core fraud and allegations

EFCA marketed financial programs in which customers could use mutual-fund investments to help finance life-insurance premiums. As growth slowed, executives and employees allegedly created false business to preserve the appearance of rapid expansion.

The principal schemes included:

1. **Fictitious life-insurance policies**  
   Employees created tens of thousands of policies for people who did not exist or who had never applied for coverage. The records included invented applications, medical information, signatures, policy numbers, and premium histories.

2. **Fraudulent reinsurance transactions**  
   EFCA transferred or “ceded” blocks of bogus policies to reinsurers. Because reinsurers paid allowances or otherwise transferred funds based on the supposed policies, EFCA converted fabricated insurance business into real cash.

3. **False financial statements**  
   The company recorded nonexistent premiums, commissions, receivables, assets, and profits, materially overstating its business and financial health.

4. **Computerized concealment**  
   The fraud became notorious for its use of computers. Programs and data-processing procedures generated false policy records and helped ensure that fictitious files appeared plausible during audits and regulatory examinations.

5. **Audit and regulatory deception**  
   Employees prepared false documents and manipulated samples and confirmations so auditors and examiners would encounter apparently valid records. The scandal consequently became a major case study in auditors’ duties to detect fraud.

## Key people

- **Stanley Goldblum**: EFCA’s president and later chief executive officer. He was identified as a central leader of the fraud and ultimately pleaded guilty to federal criminal charges.
- **Fred M. Levin**: A senior EFCA executive, commonly identified as an important participant in the fraudulent operations; he was among those criminally prosecuted.
- **Ronald Secrist**: A former EFCA employee and securities analyst whose disclosures were crucial in bringing the scheme to light. After internal concerns were not effectively addressed, he supplied information to outside analyst **Ray Dirks**.
- **Raymond L. “Ray” Dirks**: A New York securities analyst who investigated Secrist’s allegations, interviewed employees, and warned clients and others before the SEC publicly acted. His conduct later produced the landmark Supreme Court insider-trading decision **Dirks v. SEC**, 463 U.S. 646 (1983).
- **Ernst & Ernst**: EFCA’s outside accounting firm, later known as Ernst & Whinney and now part of EY. Its audits and alleged failure to uncover the fraud led to extensive litigation and professional scrutiny.

The scheme involved many additional officers, managers, programmers, clerical employees, and sales personnel; it was not merely a one-person embezzlement.

## Main events and dates

- **1960s–early 1970s**: EFCA expanded rapidly through insurance and investment products. The fabrication of policies reportedly began in the 1960s and grew into a large, organized operation.
- **1972–early 1973**: Secrist communicated allegations about fictitious policies and accounting manipulation to Ray Dirks. Dirks investigated and relayed the information to clients, journalists, and regulators.
- **March 1973**: Reports of the fraud became public, including prominent press coverage. Trading in EFCA securities was halted as the company’s reported financial condition unraveled.
- **April 1973**: EFCA entered proceedings under **Chapter X of the Bankruptcy Act**, the predecessor to modern Chapter 11 reorganization. Regulators and trustees took control of the insurance operations.
- **1973 onward**: The SEC, federal grand juries, prosecutors, insurance regulators, and bankruptcy investigators pursued parallel investigations. They found that EFCA’s books contained a massive volume of fabricated insurance business—often described as roughly **60,000 fictitious policies**, although estimates vary by source and by what was counted.
- **Mid-1970s**: Goldblum and numerous other officers and employees were indicted or charged. Goldblum pleaded guilty to federal offenses arising from the fraud and received a prison sentence. Other participants also pleaded guilty or were convicted.
- **1973–1983, Dirks proceedings**: The SEC censured Dirks for passing material nonpublic information to clients. In **1983**, the U.S. Supreme Court reversed, holding that a tippee’s liability generally depends on whether the insider breached a fiduciary duty for personal benefit and whether the tippee knew or should have known of that breach. Because the whistleblowers sought to expose fraud rather than obtain personal benefit, Dirks was not liable on the SEC’s theory.

## Outcome

EFCA collapsed and went into bankruptcy administration. Its legitimate insurance business w
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall worldcom — 12/14; missed: capitalised line costs, Clinton, Mississippi headquarters</summary>

```
## Overview

The WorldCom scandal was a massive accounting fraud at **WorldCom, Inc.**, then the second-largest U.S. long-distance telecommunications company. From at least **1999 through the first quarter of 2002**, senior executives manipulated WorldCom’s financial statements to conceal declining performance and meet Wall Street expectations. The fraud ultimately involved roughly **$11 billion in accounting misstatements**, led to what was then the largest U.S. bankruptcy, and produced major criminal convictions, civil settlements, and corporate-governance reforms.

## Parties and key people

### Company and regulators

- **WorldCom, Inc.** — the telecommunications company that committed the accounting misstatements.
- **MCI, Inc.** — the name adopted by the reorganized company after bankruptcy.
- **Securities and Exchange Commission (SEC)** — brought a civil enforcement action against WorldCom and later cases against individual executives.
- **U.S. Department of Justice and the U.S. Attorney’s Office for the Southern District of New York** — prosecuted the criminal cases.
- **WorldCom investors and bondholders** — brought securities class actions against former officers, directors, auditors, and securities underwriters.
- **Arthur Andersen LLP** — WorldCom’s outside auditor during much of the fraud period.
- **KPMG LLP** — replaced Andersen as auditor in 2002 and participated in reviewing the company’s accounts.

### Principal individuals

- **Bernard J. “Bernie” Ebbers** — WorldCom’s co-founder and chief executive officer. Prosecutors alleged that he directed or knowingly participated in the effort to falsify results.
- **Scott D. Sullivan** — chief financial officer and the central accounting architect of the fraud. He pleaded guilty and testified against Ebbers.
- **David F. Myers** — controller; pleaded guilty and cooperated.
- **Buford “Buddy” Yates Jr.** — director of general accounting; pleaded guilty and cooperated.
- **Troy M. Normand** — accounting executive; pleaded guilty and cooperated.
- **Betty Vinson** — accounting manager who made improper entries at superiors’ direction; pleaded guilty and cooperated.
- **Cynthia Cooper** — vice president of internal audit. Her team’s investigation uncovered the improper capitalization of expenses.
- **Max Bobbitt** — chairman of the board’s audit committee, to whom Cooper reported the internal-audit findings.
- **John Sidgmore** — succeeded Ebbers as CEO in 2002.
- **Richard C. Breeden** — former SEC chairman appointed as WorldCom’s corporate monitor; he produced a major governance report.
- **Michael D. Capellas** — became chairman and CEO during the bankruptcy reorganization and later led the reorganized MCI.

## Nature of the fraud

WorldCom’s business deteriorated after the telecommunications boom ended, but management sought to preserve the appearance of steady growth and maintain a key performance measure known as the **expense-to-revenue ratio**, or “E/R ratio.”

The principal devices were:

1. **Improper capitalization of line costs**  
   WorldCom paid other telecommunications carriers for access to their networks. These “line costs” were ordinary operating expenses and should have been recognized immediately. Instead, billions of dollars were transferred to capital-asset accounts, spreading the expense over future periods and falsely increasing current income.

2. **Improper release of reserves and accruals**  
   Management reduced expense reserves or accruals without adequate justification and used the releases to offset current expenses.

3. **False financial statements and SEC filings**  
   The entries overstated pretax income and assets and understated expenses. The government alleged that the purpose was to meet analysts’ expectations, support WorldCom’s stock price, and conceal the company’s true financial condition.

4. **Weak governance and internal controls**  
   Investigations found an authoritarian corporate culture, inadequate board oversight, poor documentation, and a finance function dominated by Sullivan and Ebbers. Ebbers also had substantial personal loans secured by WorldCom stock, giving him a strong interest in preventing the share price from falling.

The initially announced misstatement was **$3.8 billion**, but subsequent reviews expanded the total to approximately **$11 billion**.

## Main events, 2002–2006

### 2002: Discovery, SEC action, and bankruptcy

- **April 30, 2002:** Ebbers resigned as CEO amid concerns about company performance and hundreds of millions of dollars in loans and guarantees that WorldCom had extended to him.
- **May–June 2002:** Cynthia Cooper’s internal-audit team investigated suspicious capital expenditures, often working outside normal channels. The team identified billions of dollars in line costs improperly booked as assets.
- **June 20, 2002:** Cooper and her team presented their findings to the audit committee. Sullivan was asked to justify the entries and was later dismissed.
- **June 25, 2002:** WorldCom publicly announced that it would restate its financial statements because approximately **$3.8 billion** of expenses had been improperly capitalized. The announcement triggered a collapse in confidence and the company’s stock.
- **June 26, 2002:** The SEC filed a civil fraud action, **SEC v. WorldCom, Inc.**, in federal court in Manhattan, alleging violations of the federal securities laws and seeking injunctive and other relief.
- **July 21, 2002:** WorldCom filed for Chapter 11 bankruptcy protection in the Southern District of New York. With more than $100 billion in reported assets, it was then the largest bankruptcy in U.S. history.
- **August 2002:** Sullivan and Myers were arrested and charged. Myers soon pleaded guilty; Sullivan initially pleaded not guilty.
- **September–October 2002:** Yates, Vinson, and Normand pleaded guilty to criminal charges and agreed to cooperate.
- **November 2002:** The company announced additional accounting irregularities, inc
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall rdc — 11/12; missed: Chapter 11, March 2020</summary>

```
### Parties and key people

- **United States v. Rochester Drug Co‑Operative, Inc. (RDC)** and **United States v. Laurence F. Doud III**, brought by the U.S. Attorney’s Office for the Southern District of New York.
- **Rochester Drug Co‑Operative**, a New York pharmaceutical wholesaler, was one of the country’s largest distributors of prescription drugs.
- **Laurence F. Doud III**, RDC’s president and CEO from 1991 until 2017, was charged personally.
- **William Pietruszewski**, RDC’s former chief compliance officer, pleaded guilty and cooperated with prosecutors.
- The case was announced by then–U.S. Attorney **Geoffrey S. Berman**, with the DEA and FBI involved in the investigation.

### Core allegations

On **April 23, 2019**, federal prosecutors charged RDC and Doud with participating in a conspiracy to distribute controlled substances—principally **oxycodone and fentanyl—outside legitimate medical practice** and with defrauding the Drug Enforcement Administration.

The government alleged that, from roughly **2012 through March 2017**, RDC and its senior management:

- supplied pharmacies that they knew, or deliberately ignored evidence, were dispensing opioids for illegitimate purposes;
- prioritized sales and market growth over compliance;
- failed to investigate or report thousands of suspicious controlled-substance orders to the DEA;
- used inadequate or manipulated compliance procedures to permit questionable orders; and
- made false representations to the DEA about RDC’s compliance program.

Prosecutors said RDC’s controlled-substance sales rose dramatically during the period—its oxycodone sales increased from about **4.7 million doses in 2012 to 42.2 million in 2016**, while fentanyl sales increased from about **63,000 doses to 1.3 million**. The government alleged that RDC identified roughly **8,300 suspicious orders** but reported only **four** to the DEA.

Doud was accused of directing or encouraging the strategy, rewarding sales growth, and overriding or weakening compliance controls despite warnings from employees. The prosecution was notable because it was described as the first federal criminal prosecution of a pharmaceutical-distribution company and one of its executives for unlawfully distributing opioids.

### Main events

- **April 23, 2019:**  
  RDC entered into a **deferred prosecution agreement**. It admitted responsibility for the charged conduct, agreed to cooperate, reform its compliance program, and pay a **$20 million penalty**. The criminal information charged conspiracy to distribute controlled substances and conspiracy to defraud the United States.  
  Doud was arrested and separately charged. Pietruszewski’s guilty plea to conspiracy-related charges was also unsealed.

- **2019–2021:**  
  Doud contested the indictment, including on the theory that a distributor executive could not be held criminally liable under the Controlled Substances Act in the manner alleged. The courts allowed the prosecution to proceed. The case focused heavily on whether Doud knowingly joined an unlawful distribution conspiracy, rather than merely presiding over regulatory failures.

- **January 2022:**  
  Doud went to trial in federal court in Manhattan before U.S. District Judge **George B. Daniels**. Pietruszewski testified for the government, describing internal warnings, pressure to retain questionable pharmacy customers, and Doud’s role in compliance and sales decisions.

- **February 2, 2022:**  
  After a roughly two-week trial, the jury convicted Doud on both counts:
  1. conspiracy to distribute unlawfully oxycodone and fentanyl; and  
  2. conspiracy to defraud the United States by obstructing the DEA’s lawful functions.

- **June 29, 2022:**  
  Judge Daniels sentenced Doud to **27 months in federal prison**, followed by supervised release, and imposed a **$100,000 fine**. The sentence was substantially below the term sought by prosecutors, but it marked the first imprisonment of a pharmaceutical-distribution chief executive for opioid-distribution conduct of this kind.

### Outcome

- **RDC:** Avoided a corporate conviction through the 2019 deferred prosecution agreement, admitted the conduct, paid **$20 million**, and accepted compliance and cooperation obligations. The company later ceased operations and entered bankruptcy-related proceedings.
- **Laurence Doud:** Convicted by a jury in February 2022 and sentenced in June 2022 to **27 months’ imprisonment**, supervised release, and a **$100,000 fine**.
- **William Pietruszewski:** Pleaded guilty and cooperated with the government, including testifying against Doud.

The case established that senior executives of drug distributors could face personal criminal liability—not merely civil or regulatory sanctions—when prosecutors proved that they knowingly used the distribution system to supply pharmacies engaged in illegitimate opioid dispensing and concealed suspicious activity from the DEA.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall insys — 14/15; missed: 'titration' rap video</summary>

```
The Insys Therapeutics matter was a federal criminal racketeering prosecution arising from the marketing of **Subsys**, a fentanyl spray approved only for breakthrough cancer pain in opioid-tolerant patients. Prosecutors alleged that Insys executives used sham speaker programs, kickbacks, and insurance fraud to drive prescriptions for broader and often medically inappropriate uses.

## Parties and case

- **Prosecution:** United States Department of Justice, principally the U.S. Attorney’s Office for the District of Massachusetts.
- **Corporate defendant:** **Insys Therapeutics, Inc.**, an Arizona-based specialty pharmaceutical company.
- **Principal individual defendants:** founder and former executive chairman **John N. Kapoor** and former executives **Michael L. Babich, Alec Burlakoff, Richard Simon, Sunrise Lee,** and **Joseph Rowan**.
- The principal trial was **United States v. Kapoor et al.**, in the U.S. District Court for the District of Massachusetts.

## Core allegations

The government alleged that, beginning around 2012, Insys operated a nationwide scheme to increase Subsys sales by:

1. **Paying kickbacks to prescribers.**  
   Insys allegedly disguised bribes as honoraria for “speaker programs.” Favored doctors and other practitioners were paid to give presentations—sometimes to audiences consisting largely of friends, colleagues, or no meaningful audience at all—in exchange for prescribing Subsys.

2. **Targeting high-volume prescribers and non-cancer patients.**  
   Although Subsys was approved for breakthrough pain in opioid-tolerant cancer patients, prosecutors said Insys pushed prescriptions for patients without cancer and encouraged higher doses because reimbursement and company revenue rose with dosage.

3. **Defrauding insurers and pharmacy-benefit managers.**  
   Insys’s reimbursement unit allegedly misled insurers during prior-authorization calls, including by using language designed to create the false impression that patients had cancer-related breakthrough pain or otherwise met coverage criteria.

4. **Operating the company through a racketeering enterprise.**  
   The indictment framed the conduct as a RICO conspiracy involving predicate acts such as mail and wire fraud, honest-services fraud, and violations of the federal Anti-Kickback Statute.

The defense generally argued that speaker programs were legitimate pharmaceutical marketing, that prescribing decisions belonged to independent medical professionals, and that Kapoor did not knowingly direct criminal conduct.

## Key people

- **John N. Kapoor:** Insys founder, controlling figure, and former executive chairman. Prosecutors portrayed him as the leader and ultimate beneficiary of the scheme.
- **Michael L. Babich:** Former president and CEO. He pleaded guilty and testified for the government, describing Kapoor’s involvement.
- **Alec Burlakoff:** Former vice president of sales. He pleaded guilty and became a major cooperating witness concerning the speaker-program strategy and sales pressure.
- **Richard Simon:** Former national director of sales.
- **Sunrise Lee:** Former regional sales director; a former exotic dancer recruited into Insys sales management. Evidence included her efforts to cultivate prescribers.
- **Joseph Rowan:** Former regional sales director.
- **Michael Gurry:** Former vice president of managed markets, associated with the reimbursement operation; he pleaded guilty in a related prosecution.
- **Dr. Paul Madison:** An Illinois pain physician and major Subsys prescriber whose relationship with Insys figured prominently in the trial evidence.
- **Dr. Gavin Awerbuch:** A Michigan neurologist and high-volume Subsys prescriber who pleaded guilty in a related case involving health-care fraud and unlawful prescribing.

## Main events

- **January 2012:** The FDA approved Subsys for breakthrough cancer pain in opioid-tolerant patients.
- **December 2016:** Federal prosecutors charged six former Insys executives and managers—Babich, Burlakoff, Simon, Lee, Rowan, and Gurry—with racketeering conspiracy.
- **October 26, 2017:** Kapoor was arrested and charged with joining and leading the racketeering conspiracy. The case was later consolidated with charges against other executives.
- **2017–2019:** Several insiders, including Babich, Burlakoff, and Gurry, pleaded guilty and cooperated with prosecutors.
- **January–May 2019:** Kapoor, Simon, Lee, and Rowan were tried in Boston. The government presented internal communications, speaker-program records, reimbursement evidence, and testimony from cooperating former executives and prescribers.
- **May 2, 2019:** A federal jury convicted Kapoor, Simon, Lee, and Rowan of racketeering conspiracy. Kapoor became the first chief executive or pharmaceutical-company founder of comparable prominence convicted under RICO for conduct tied to the opioid crisis.
- **June 5, 2019:** Insys Therapeutics agreed to resolve federal criminal and civil investigations for approximately **$225 million**. Its operating subsidiary, **Insys Pharma, Inc.**, pleaded guilty to five counts of mail fraud, and the parent entered a deferred-prosecution agreement. The resolution also addressed False Claims Act allegations concerning kickbacks and fraudulent reimbursement practices.
- **June 10, 2019:** Insys filed for Chapter 11 bankruptcy protection, only days after announcing the federal settlement.
- **January 23, 2020:** U.S. District Judge **Allison D. Burroughs** sentenced Kapoor to **66 months in federal prison**. He was also ordered to pay substantial restitution and forfeiture.
- **January 2020:** Simon, Lee, and Rowan received prison sentences as well—approximately **33 months, one year and one day, and 27 months**, respectively.
- **2020:** The company’s assets were sold through bankruptcy, and Insys ceased operating as an independent pharmaceutical business.

## Outcome

The prosecution ended in:

- RICO-conspiracy convictions of Kapoor and three other former manager
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall purdue — 10/16; missed: Stamford, Connecticut, MDL 2804 / Judge Polster, McKinsey's role / settlement, 2010 abuse-deterrent reformulation, Knoa Pharma successor, Dopesick / Empire of Pain</summary>

```
Purdue Pharma’s opioid litigation arose from its marketing of OxyContin and culminated in criminal pleas, thousands of civil claims, a Chapter 11 case, and a Supreme Court ruling invalidating a bankruptcy plan that would have protected the Sackler family from opioid-related civil liability without every claimant’s consent.

## Parties and key people

- **Purdue Pharma L.P. and affiliates**: privately held manufacturer of OxyContin, introduced in 1996.
- **The Sackler family**: Purdue’s owners. Important figures included:
  - **Richard Sackler**, former president and co-chairman;
  - **David Sackler**, former board member and Richard’s son;
  - **Kathe Sackler**, former board member;
  - **Mortimer D.A. Sackler**, former board member;
  - other descendants and trusts associated with the families of brothers **Mortimer Sackler** and **Raymond Sackler**.
- **Federal government**: principally the Department of Justice, Drug Enforcement Administration, and Department of Health and Human Services.
- **State, territorial, tribal, and local governments**: sued to recover public costs of the opioid epidemic.
- **Individuals and private entities**: people with opioid-use disorder, survivors and families of people who died, hospitals, insurers, and others.
- **Official Committee of Unsecured Creditors** and other bankruptcy constituencies.
- **U.S. Trustee**: the Justice Department’s bankruptcy watchdog, which opposed the Sackler releases.
- **William K. Harrington**, then the U.S. Trustee for Region 2 and the named petitioner in the Supreme Court case.
- **Judge Robert D. Drain**, U.S. Bankruptcy Court for the Southern District of New York, who confirmed Purdue’s 2021 plan.
- **Judge Colleen McMahon**, U.S. District Court for the Southern District of New York, who vacated that confirmation order.
- **Judge Eunice C. Lee**, who wrote the Second Circuit decision reinstating the plan.
- **Justice Neil Gorsuch**, who wrote the Supreme Court’s 2024 majority opinion; **Justice Brett Kavanaugh** wrote the principal dissent.

## Core allegations and legal issues

The civil cases generally alleged that Purdue and, in many complaints, Sackler family members:

- deceptively promoted OxyContin as less addictive, less prone to abuse, or safer than other opioids;
- minimized or concealed addiction and overdose risks;
- encouraged high-dose, long-duration prescribing and expanded opioid use beyond appropriate patients;
- used sales representatives, paid speakers, front groups, and allegedly misleading medical messaging to influence prescribers;
- failed to maintain effective controls against diversion and continued supplying suspicious prescribers or pharmacies;
- created a public nuisance and violated consumer-protection, fraud, false-claims, controlled-substances, and other laws.

Purdue and the Sacklers disputed many allegations. The Sacklers did not personally file for bankruptcy and generally denied wrongdoing.

The bankruptcy’s central legal issue was whether Purdue’s plan could extinguish opioid-related claims against the **nondebtor Sacklers**—including claims held by people who objected—without the claimants’ consent. These were called **nonconsensual third-party releases**. In exchange, the Sacklers would contribute billions of dollars and relinquish ownership of Purdue.

Another major issue was Purdue’s allegation that Sackler-related entities had received roughly **$11 billion** from Purdue from 2008 onward, much of it through distributions, with substantial amounts allegedly moved offshore. The estate asserted or preserved fraudulent-transfer and related claims. The Sacklers maintained that much of the money went to taxes and investments and that the proposed settlement exceeded what litigation was likely to recover.

## Main events, 2007–2024

### 2007: first federal criminal resolution

On **May 10, 2007**, Purdue Frederick Company, a Purdue affiliate, agreed to plead guilty in federal court in Virginia to **felony misbranding** of OxyContin. Prosecutors said the company had marketed the drug with misleading claims that it was less addictive and less subject to abuse and diversion than other pain medicines.

Three executives—**Michael Friedman**, president; **Howard Udell**, general counsel; and **Paul Goldenheim**, chief medical officer—agreed to plead guilty to misdemeanor misbranding charges under the responsible-corporate-officer doctrine. The company and executives agreed to pay approximately **$634.5 million** in penalties and other payments. The pleas and sentences were entered later in 2007.

### 2014–2019: expanding state and local litigation

As opioid deaths and public costs mounted, states, cities, counties, tribes, and private plaintiffs filed large numbers of suits against Purdue and other opioid manufacturers, distributors, and pharmacies.

A prominent early case was **Kentucky v. Purdue**, settled in **December 2015** for **$24 million**, without an admission of wrongdoing.

In **2018**, Massachusetts Attorney General **Maura Healey** sued Purdue and individual Sackler family members. An amended complaint made internal Purdue communications public and alleged that Sackler board members closely directed OxyContin strategy despite evidence of addiction and overdose. Other states followed with claims against family members.

In **March 2019**, Purdue and the Sacklers reached a proposed **$270 million** settlement with Oklahoma shortly before trial. Purdue’s portion helped fund an addiction-treatment and research center at Oklahoma State University; Sackler-related foundations also contributed. The settlement did not resolve the nationwide litigation.

### September 2019: Chapter 11 filing

On **September 15, 2019**, Purdue and affiliated companies filed for **Chapter 11** protection in the Southern District of New York. The filing stayed litigation against Purdue. Judge Drain also extended or maintained injunctions that largely paused claims against Sackler family members while negoti
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall bridgegate — 15/15; missed: </summary>

```
**Bridgegate** was a New Jersey political-retaliation scandal involving the deliberate closure of access lanes from **Fort Lee, New Jersey, to the George Washington Bridge** in September 2013. The closures caused severe traffic jams and delayed school buses and emergency services. The scandal damaged Governor **Chris Christie’s** national political standing, produced criminal convictions of two aides, and ended in 2020 when the U.S. Supreme Court unanimously overturned those convictions.

## Parties and key people

- **Chris Christie** — Republican governor of New Jersey. Prosecutors did not charge him, and he denied advance knowledge of the scheme. The scandal nevertheless became closely associated with his administration.
- **Bridget Anne Kelly** — Christie’s deputy chief of staff for legislative and intergovernmental affairs. She sent the notorious email: **“Time for some traffic problems in Fort Lee.”**
- **William “Bill” Baroni Jr.** — Christie-appointed deputy executive director of the **Port Authority of New York and New Jersey**, which operates the bridge.
- **David Wildstein** — Christie ally and Port Authority official. He implemented the lane changes, later pleaded guilty, and testified for the government against Kelly and Baroni.
- **Mark Sokolich** — Democratic mayor of Fort Lee. Prosecutors alleged that his town was punished because he did not endorse Christie’s 2013 reelection.
- **David Samson** — Christie-appointed chairman of the Port Authority. He was not charged in the lane-closure prosecution, though he later pleaded guilty in a separate airline-related bribery case.
- **Port Authority of New York and New Jersey** — the bistate agency controlling the George Washington Bridge.
- **United States** — federal prosecutors brought fraud and civil-rights-related charges against Kelly and Baroni.

## Alleged scheme and legal issues

Federal prosecutors alleged that Kelly, Baroni, and Wildstein used Port Authority power to retaliate against Mayor Sokolich for withholding an endorsement of Christie. They reduced Fort Lee’s three dedicated local access lanes to one and reassigned the other two to general bridge traffic, while falsely presenting the change as a **traffic study**.

The criminal case centered on whether this political abuse of regulatory power also constituted federal **wire fraud** and fraud involving federally funded property. Prosecutors argued that the defendants obtained Port Authority property—employee labor, tollbooth operations, and related resources—through deception.

The eventual Supreme Court issue was narrower: even if the defendants acted corruptly and lied, did they seek to obtain **money or property**, as federal fraud statutes require, or did they merely misuse governmental regulatory authority?

## Main events

- **August 13, 2013:** Kelly emailed Wildstein, **“Time for some traffic problems in Fort Lee.”** Wildstein replied, **“Got it.”**
- **September 9–13, 2013:** During the first week of school, Port Authority personnel reduced Fort Lee’s bridge-access lanes from three to one. Massive congestion followed. Mayor Sokolich repeatedly sought help, warning that public safety was being endangered.
- **September 13, 2013:** Port Authority Executive Director **Patrick Foye**, an appointee of New York Governor Andrew Cuomo, ordered the normal lane configuration restored. He described the closures as potentially unlawful and dangerous.
- **Late 2013:** Baroni testified before a New Jersey legislative committee that the closures were part of a traffic study. That explanation was later shown to be false.
- **January 8, 2014:** Emails and text messages, including Kelly’s “traffic problems” email, became public. Christie said he had been misled and fired Kelly; Baroni and Wildstein had already left the Port Authority.
- **January 9, 2014:** Christie held a lengthy press conference denying prior knowledge and apologizing for his staff’s conduct.
- **March 2014:** A Christie-commissioned internal report by the law firm **Gibson Dunn & Crutcher** blamed Kelly and Wildstein and said Christie lacked advance knowledge. Critics questioned the report’s independence and completeness.
- **May 1, 2015:** Wildstein pleaded guilty to federal charges of conspiracy to commit fraud and conspiracy against civil rights. He agreed to cooperate.
- **May 1, 2015:** Federal prosecutors indicted Kelly and Baroni on conspiracy, wire-fraud, and civil-rights counts.
- **November 4, 2016:** A federal jury in Newark convicted Kelly and Baroni on all counts submitted to it.
- **2017:** U.S. District Judge **Susan D. Wigenton** sentenced Baroni to 24 months in prison and Kelly to 18 months. Wildstein later received probation and community service because of his cooperation.
- **2018–2019:** The U.S. Court of Appeals for the Third Circuit largely upheld the convictions, while vacating one civil-rights count. Kelly and Baroni pursued Supreme Court review.
- **January 14, 2020:** The Supreme Court heard argument in **Kelly v. United States**.
- **May 7, 2020:** The Supreme Court unanimously reversed the convictions.

## Supreme Court outcome

In **Kelly v. United States, 590 U.S. 391 (2020)**, Justice **Elena Kagan** wrote for a unanimous Court. The Court accepted that the defendants had engaged in deception and an abuse of power, stating that they had “commandeered the Bridge’s access lanes to punish the mayor of Fort Lee.” But federal fraud law does not criminalize every dishonest or corrupt exercise of government authority.

The Court held that the object of the scheme was to change the allocation of traffic lanes—a **regulatory decision**, not to obtain Port Authority money or property. The employee labor and other costs used to carry out the closures were incidental to that regulatory objective and could not independently satisfy the property requirement. The Court therefore reversed Kelly’s and Baroni’s convictions.

## Overall result

- **Kelly and Baroni:** Their federal convictio
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall clinton_email — 15/15; missed: </summary>

```
The Hillary Clinton e-mail controversy concerned her use of a privately maintained e-mail system while serving as U.S. secretary of state, and whether that practice violated federal recordkeeping or classified-information laws.

## Parties and key people

- **Hillary Rodham Clinton** — U.S. secretary of state from January 21, 2009, to February 1, 2013; Democratic presidential nominee in 2016.
- **U.S. Department of State** — responsible for preserving State Department records and reviewing Clinton’s messages for public release and classification.
- **Federal Bureau of Investigation and Department of Justice** — conducted the criminal investigation, code-named **“Midyear Exam.”**
- **James Comey** — FBI director who publicly announced the FBI’s findings and later notified Congress that the inquiry had been reopened and closed again.
- **Loretta Lynch** — attorney general during the investigation.
- **Cheryl Mills, Huma Abedin, Jake Sullivan, and other Clinton aides** — correspondents or custodians of potentially relevant records and devices.
- **Bryan Pagliano** — former Clinton campaign and State Department employee who helped administer the private server; he received limited immunity in connection with his cooperation.
- **Paul Combetta and Platte River Networks** — involved in later management of Clinton’s e-mail system; Combetta also received immunity.
- **Anthony Weiner** — Abedin’s estranged husband; an unrelated investigation of his laptop led to the discovery of additional Clinton-related e-mails in October 2016.
- **House Select Committee on Benghazi** and congressional committees — sought Clinton’s records and investigated related disclosure and preservation issues.

## The system and principal issues

Clinton did not use an official `state.gov` account for her routine work. Instead, she used personal addresses on privately controlled servers associated with the domain **clintonemail.com**, initially located at her home in Chappaqua, New York. The system had been established during Bill Clinton’s post-presidential period and was administered by private personnel.

The controversy raised several overlapping questions:

1. **Federal records:** Whether Clinton properly preserved and returned official correspondence under the Federal Records Act and State Department rules.
2. **Classified information:** Whether classified national-defense or government information was transmitted or stored on an unauthorized, inadequately secured system.
3. **Security:** Whether foreign governments or other hostile actors penetrated the server.
4. **Deletion and production:** Whether Clinton’s lawyers properly separated work-related from personal messages, and whether messages were deleted to conceal evidence.
5. **Public statements:** Whether Clinton accurately described the number of devices and servers she used, the presence of classified material, and the handling of her records.

Clinton said she used one account for convenience, that she had turned over all work-related e-mails in her possession, and that she did not send or receive material marked classified. Critics argued that the private system evaded normal security, archiving, congressional oversight, and Freedom of Information Act processes.

## Main events

### 2014: State Department requests records

In **October 2014**, the State Department asked former secretaries of state to provide work-related e-mails not already in departmental custody. Clinton’s lawyers reviewed roughly 60,000 messages from her tenure. They identified approximately **30,490 work-related e-mails**, which Clinton provided to the department in December 2014, and treated roughly 31,000 others as personal. The personal messages were deleted after the review.

### March 2015: Public disclosure

The private system became public on **March 2, 2015**, through a *New York Times* report. On **March 10**, Clinton held a press conference at the United Nations. She said she had used the private account for convenience, had complied with applicable rules, and had not e-mailed classified material. She declined to turn over the server itself, saying it contained personal communications.

The State Department began reviewing and releasing the returned messages under court-supervised Freedom of Information Act schedules. During that process, agencies determined that some messages contained information that was classified when reviewed, including some information later classified at the **Top Secret/Special Access Program** level. A central dispute was whether information was classified at the time it was sent, even if it lacked classification markings.

### Summer 2015: Referral and FBI investigation

In **July 2015**, inspectors general for the intelligence community and State Department made a security referral to the Justice Department after classified information was found in the e-mails. The referral was not initially framed as a criminal accusation against Clinton personally, but the FBI opened a criminal investigation into the handling of classified information.

Clinton’s server was turned over to the FBI in **August 2015**. The FBI examined servers, devices, backups, and accounts and interviewed Clinton aides and technical personnel.

### Deletion and preservation questions

The FBI found that Clinton’s staff had directed that older personal e-mails be deleted after the work/personal review. A technician, Paul Combetta, used the deletion program **BleachBit** in March 2015, after a congressional preservation request had been issued, although the FBI reported that he said he had acted on an earlier instruction and had forgotten to carry it out at the time. Investigators recovered some deleted work-related messages from other sources.

The FBI ultimately found no sufficient evidence that Clinton or her lawyers intentionally deleted work-related e-mails to obstruct the investigation. It did find that thousands of work-related messages had not been included in the original 
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall sony_hack — 11/15; missed: January 2015 sanctions on North Korea, WikiLeaks published the archive (April 2015), employee class action settled (~$8m), Spider-Man / Marvel, Jolie e-mails</summary>

```
The **2014 Sony Pictures Entertainment hack** was a destructive cyberattack and data breach tied by the U.S. government to **North Korea**. It became an international dispute because Sony was preparing to release **_The Interview_**, a comedy depicting the assassination of North Korean leader **Kim Jong Un**.

## Parties and key people

- **Sony Pictures Entertainment (SPE):** The victim, led by chairman and CEO **Michael Lynton** and co-chairman **Amy Pascal**.
- **“Guardians of Peace” (GOP):** The name used by the attackers in messages to Sony and in releasing stolen material.
- **North Korea:** Publicly denied responsibility but praised the attack. U.S. authorities later attributed it to North Korean state-sponsored hackers.
- **Seth Rogen and Evan Goldberg:** Directors and producers of *The Interview*; Rogen also starred in it.
- **James Franco:** Co-starred with Rogen.
- **Kim Jong Un:** North Korean leader portrayed as the target of an assassination plot.
- **President Barack Obama:** Criticized Sony’s initial cancellation of the film’s theatrical release and announced that the United States would respond.
- **FBI and U.S. Department of Justice:** Investigated the intrusion and publicly attributed it to North Korea.
- **Park Jin Hyok:** A North Korean programmer later charged by the United States in connection with the Sony attack and other cyber operations.

## Main events

### Before the breach

North Korea objected strongly to *The Interview*. In **June 2014**, its government complained to the United Nations and called the planned film an act of terrorism or war. Sony altered some imagery but retained the plot and Kim Jong Un’s on-screen death.

### Attack and disclosure

On **November 24, 2014**, Sony employees found their computers disabled by a red skeleton image and a message from the “Guardians of Peace.” The attackers had stolen large quantities of data and deployed destructive malware that wiped systems.

Over the following weeks, stolen material was distributed online, including:

- Unreleased films;
- Employee Social Security numbers, salaries, medical information, and other personal data;
- Executive emails;
- Contracts, budgets, and internal business records.

The leaked emails caused reputational damage. Among the most publicized were exchanges involving **Amy Pascal** and producer **Scott Rudin**, including racially insensitive jokes about President Obama and disparaging comments about actors and filmmakers. Pascal apologized and later left her co-chair position.

The breach also disrupted Sony’s operations, forcing employees to work without normal email and computer systems. Employees and former employees filed lawsuits alleging that Sony had failed to protect their personal information.

### Threats and cancellation controversy

On **December 16, 2014**, the attackers issued a message invoking the September 11 attacks and warning theaters against showing *The Interview*. Although U.S. officials said they had no specific evidence of an active physical plot against theaters, major chains—including AMC, Regal, Cinemark, and Carmike—declined to screen the film.

On **December 17**, Sony canceled the planned wide theatrical release scheduled for **December 25**. The decision prompted criticism that threats had suppressed lawful expression.

On **December 19**, the **FBI formally attributed the attack to North Korea**, citing technical similarities to earlier North Korean malware, infrastructure links, and other intelligence. President Obama said Sony had “made a mistake” by canceling the release and promised a proportionate U.S. response. Sony maintained that it had not permanently withdrawn the film but had lost access to most theaters.

Sony then arranged a limited release. *The Interview* became available online on **December 24, 2014**, through services including Google Play, YouTube Movies, Microsoft’s Xbox Video, and a Sony website. It opened in several hundred independent theaters on **December 25**.

North Korea denied carrying out the hack and proposed a joint investigation, while warning of consequences if the United States retaliated.

## Attribution, sanctions, and criminal case

On **January 2, 2015**, President Obama issued an executive order authorizing additional sanctions in response to North Korea’s conduct. The Treasury Department sanctioned North Korean entities and officials. The administration described the measures as part of its response to the Sony attack, although some sanctions also addressed North Korea’s broader activities.

On **September 6, 2018**, the Justice Department unsealed a criminal complaint charging **Park Jin Hyok**, alleged to be a member of the North Korean government-backed **Lazarus Group**, with conspiracy involving:

- The Sony intrusion and destructive attack;
- The **2016 Bangladesh Bank theft**;
- Development and deployment of the **2017 WannaCry ransomware**;
- Other attempted cyberattacks.

Because Park was believed to be in North Korea, he was not brought to trial in the United States. Additional alleged North Korean hackers were charged in **2021** as part of a broader cybercrime conspiracy.

## Civil aftermath at Sony

Sony faced consolidated litigation from employees whose personal information had been exposed. In **2015**, Sony agreed to a settlement reportedly worth up to about **$8 million**, including compensation for identity-theft losses, credit monitoring, and legal fees. The settlement did not amount to an admission that Sony was legally responsible for the attack.

Amy Pascal stepped down as Sony Pictures co-chair in **May 2015**, though she continued working with Sony through a production arrangement. The leaked emails and internal documents also affected business relationships and intensified debate over privacy, cybersecurity, press publication of stolen data, and corporate handling of employee information.

## Outcome

There was no conventional final judgment resolving responsibility for the attack:

```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall depuy_asr — 12/14; missed: Australian registry / 2009 withdrawal there, Warsaw, Indiana</summary>

```
The **DePuy ASR litigation** arose from the failure and 2010 worldwide recall of two metal-on-metal hip systems made by **DePuy Orthopaedics, Inc.**, an Indiana-based subsidiary of **Johnson & Johnson (J&J)**:

- **ASR XL Acetabular Hip System**, used in conventional total-hip replacement; and  
- **ASR Hip Resurfacing System**, which preserved more of the femoral bone but was not approved for sale in the United States.

## Parties and principal allegations

Thousands of recipients sued **DePuy and Johnson & Johnson**, generally alleging that the ASR’s shallow, monoblock metal cup and related design made proper placement difficult and caused excessive wear. Plaintiffs claimed the cobalt-chromium bearing surfaces shed metal debris and ions, producing:

- pain, loosening, inflammation, tissue and bone damage, pseudotumors, and elevated cobalt or chromium levels;
- premature failure and the need for revision surgery; and
- in some cases, systemic “metal poisoning” or metallosis.

The complaints asserted product-liability theories including **design defect, failure to warn, negligence, breach of warranty, fraud or misrepresentation, and punitive damages**. Plaintiffs also alleged that DePuy knew of unusually high failure rates before the recall, failed to warn surgeons and patients promptly, and continued marketing the device while minimizing adverse data.

DePuy and J&J disputed that the ASR was uniformly defective. They argued that outcomes depended on factors such as surgical positioning, patient anatomy, activity, and medical history, and contested whether particular injuries were caused by metal debris.

## Regulatory and factual background

The **ASR XL** entered the U.S. market through the FDA’s **510(k) substantial-equivalence process**, rather than through full premarket approval. The resurfacing version was sold abroad but did not obtain U.S. approval.

Important figures included:

- **Andrew Ekdahl**, president of DePuy Orthopaedics during the recall and later worldwide chairman of DePuy Synthes;
- **Pamela Plouhar**, a DePuy engineer and ASR project leader whose internal warnings and testimony became important in trials;
- **Dr. Thomas Schmalzried**, an orthopedic surgeon and paid DePuy consultant involved in the ASR’s development and promotion;
- **Dr. David Floyd**, a former DePuy executive whose testimony concerned internal knowledge and decision-making;
- **Judge David A. Katz**, who supervised the federal multidistrict litigation in the Northern District of Ohio; and
- **Judge Brian R. Martinotti**, who managed the coordinated New Jersey state litigation.

## Main events, 2010–2015

### 2010 recall

On **March 8, 2010**, DePuy warned physicians that data from the Australian joint-replacement registry showed a higher-than-expected revision rate for the ASR, particularly in certain patients and cup sizes.

On **August 24, 2010**, DePuy announced a **worldwide voluntary recall** after receiving new data from the National Joint Registry of England and Wales. DePuy reported five-year revision rates of approximately:

- **12% for the ASR Hip Resurfacing System**, and
- **13% for the ASR XL total-hip system**.

About **93,000 ASR systems** had been implanted worldwide. DePuy established a reimbursement program for reasonable monitoring and treatment costs, but participation did not necessarily resolve tort claims.

### Consolidated litigation

On **December 3, 2010**, the Judicial Panel on Multidistrict Litigation centralized federal cases as **In re DePuy Orthopaedics, Inc., ASR Hip Implant Products Liability Litigation, MDL No. 2197**, before Judge Katz in the **U.S. District Court for the Northern District of Ohio**.

State cases were also coordinated, notably in:

- **California**, before Judge Richard Kramer in San Francisco;
- **New Jersey**, in Bergen County before Judge Martinotti; and
- **Texas**, where later bellwether trials were held.

### 2013 bellwether trials

In **Kransky v. DePuy**, a California jury returned the first major plaintiff verdict on **March 8, 2013**. The jury found the ASR defectively designed and awarded **Loren Kransky approximately $8.3 million** in compensatory damages. It did not award punitive damages. The judgment was later upheld on appeal, with some adjustment to damages.

In the first federal MDL bellwether, **Strum v. DePuy**, a jury in Ohio returned a **defense verdict on October 3, 2013**. DePuy successfully argued that plaintiff **Ann Strum’s** problems were not caused by a defect in the ASR.

These differing results illustrated the case-specific nature of causation and damages.

### First nationwide settlement

On **November 19, 2013**, DePuy and the court-appointed plaintiffs’ leadership announced a settlement program valued at roughly **$2.5 billion** for eligible U.S. patients who had undergone ASR revision surgery by **August 31, 2013**. The program generally provided a **$250,000 base award per revised hip**, subject to reductions and enhancements based on factors such as age, smoking, length of implantation, complications, and extraordinary injuries.

DePuy also agreed to continue paying qualifying medical expenses under a separate program. The company did **not admit liability or that the ASR was defective**. The settlement was not a conventional mandatory class settlement: claimants could enroll or continue litigating, although participation thresholds and lien-resolution procedures were built into the agreement.

### 2014 Texas verdict

On **October 23, 2014**, a federal jury in Dallas returned a verdict for five plaintiffs and awarded approximately **$502 million**, including punitive damages, after finding defects and misconduct relating to the ASR. The award was later reduced under Texas punitive-damages limits, and subsequent appellate proceedings affected the judgment. The trial nevertheless intensified settlement pressure and exposed internal DePuy documents and testimony about design concerns and marketing.

### 2015 set
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall bair_hugger — 11/14; missed: HotDog conductive warmer, FDA 2017 letter: continue using forced-air warming, 3M v. Augustine false-advertising suit (Lanham Act)</summary>

```
**Bair Hugger Forced Air Warming Products Liability Litigation**, **MDL No. 2666**, is a federal products-liability proceeding concerning 3M’s Bair Hugger surgical warming system. It was centralized in the **U.S. District Court for the District of Minnesota** before **Judge Joan N. Ericksen**. The litigation began in 2015 and, although defendants won the principal bellwether trial and later obtained broad summary judgment, the Eighth Circuit revived the cases; the MDL has therefore not ended in a global merits judgment or publicly announced comprehensive settlement.

## Parties and product

The plaintiffs were surgical patients—many of whom underwent hip or knee replacement—who later developed serious **periprosthetic joint infections** or other deep surgical-site infections.

The principal defendants were:

- **3M Company**, which acquired the Bair Hugger business in 2010; and
- **Arizant Healthcare Inc.**, formerly Augustine Medical, the manufacturer/developer of the system.

The Bair Hugger is a **forced-air warming (FAW)** device. A heater/blower sends warmed air through a hose into a disposable perforated blanket placed over or around an anesthetized patient to prevent perioperative hypothermia.

Important individuals included:

- **Dr. Scott D. Augustine**, the anesthesiologist and inventor associated with the Bair Hugger and founder of Augustine Medical/Arizant. After leaving the company, he became a prominent critic of forced-air warming and promoted a competing conductive warming technology. Defendants emphasized his commercial interests and challenged the reliability of his claims.
- **Judge Joan N. Ericksen**, the MDL transferee judge.
- **Timothy D. Gareis**, the plaintiff in the first federal bellwether trial.
- Plaintiffs’ scientific experts, particularly **Dr. James M. McGrath**, a fluid-dynamics expert whose opinions about airflow and contaminant transport became central to the appellate proceedings.

## Core allegations and defenses

Plaintiffs alleged that the Bair Hugger’s warm-air exhaust creates convection currents or disrupts operating-room airflow, carrying bacteria-bearing particles from nonsterile areas—especially near the floor—into the sterile surgical field and onto implants or open wounds. They asserted claims including:

- design defect;
- failure to warn;
- negligence;
- breach of warranty; and
- related state-law theories.

They alleged that 3M and Arizant knew or should have known of the infection risk, failed adequately to test or warn about it, and continued marketing the product despite contrary evidence.

The defendants denied that Bair Hugger causes surgical-site infections. Their principal positions were that:

- forced-air warming is widely used and helps prevent hypothermia-related complications;
- the proposed contamination mechanism was speculative;
- epidemiological and clinical evidence did not show that Bair Hugger increased infection rates;
- plaintiffs could not reliably establish general causation or specific causation; and
- many infections had alternative causes unrelated to the warming device.

The litigation therefore turned heavily on **expert admissibility under Federal Rule of Evidence 702 and Daubert**, especially whether laboratory airflow studies, observational studies, and mechanistic evidence could support a causal inference despite the absence of definitive epidemiological proof.

## Main procedural events

- **December 11, 2015:** The Judicial Panel on Multidistrict Litigation centralized the federal cases as **MDL No. 2666**, captioned *In re Bair Hugger Forced Air Warming Devices Products Liability Litigation*, in Minnesota before Judge Ericksen.

- **2016–2017:** The parties conducted coordinated discovery, selected bellwether cases, and litigated extensive motions concerning general- and specific-causation experts. The MDL eventually included several thousand filed cases.

- **May 2018:** The first bellwether case, **Gareis v. 3M Co.**, went to trial. Gareis alleged that use of a Bair Hugger during hip-replacement surgery caused a deep joint infection. On **May 30, 2018**, the jury returned a **defense verdict**, finding for 3M and Arizant.

- **2019:** Judge Ericksen excluded key portions of plaintiffs’ causation evidence and granted defendants **summary judgment across the MDL**, concluding that plaintiffs lacked admissible expert evidence sufficient to prove general causation. This effectively disposed of the federal cases at the district-court level.

- **August 16, 2021:** In **Amador v. 3M Co.**, the **U.S. Court of Appeals for the Eighth Circuit** reversed the mass summary-judgment ruling. The court held that the district court had applied Rule 702/Daubert too restrictively and had improperly resolved factual disputes or weighed competing scientific evidence. It ruled that plaintiffs’ experts—including McGrath’s airflow opinions—had a sufficiently reliable basis to be heard by a jury. The cases were remanded for further proceedings.

- **2022:** The Supreme Court declined to review the Eighth Circuit’s decision, leaving the revival of the MDL intact.

- **After remand:** The district court resumed case-management, expert, dispositive-motion, and remand-related proceedings. Individual cases have been dismissed, resolved, or prepared for transfer/remand, but the appellate ruling prevented a single causation-based judgment from terminating the entire litigation.

## Outcome

There is **no single final plaintiff or defense outcome for MDL 2666**:

- Defendants won the only major federal bellwether trial, **Gareis**, in 2018.
- Defendants’ broader 2019 victory—expert exclusion and summary judgment in the remaining MDL cases—was **reversed by the Eighth Circuit in 2021**.
- The Supreme Court’s refusal to intervene in 2022 left that reversal in place.
- The MDL was thus revived and continued through individual dispositions and remand-related proceedings; there has not been a publicly announced comprehensive global settlem
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall earplugs — 14/14; missed: </summary>

```
## Overview

The **3M Combat Arms Earplug Products Liability Litigation**, **MDL No. 2885**, was a mass-tort proceeding in the U.S. District Court for the Northern District of Florida. It involved hundreds of thousands of claims by U.S. service members and veterans who alleged that **Combat Arms Earplugs Version 2**, or **CAEv2**, failed to protect them from damaging military noise, causing hearing loss and tinnitus.

The MDL was captioned **In re: 3M Combat Arms Earplug Products Liability Litigation**, No. **3:19-md-02885**, and was overseen by **U.S. District Judge M. Casey Rodgers**.

## Parties and key people

### Defendants

- **3M Company**, which acquired the earplug business in 2008.
- **Aearo Technologies LLC** and related Aearo entities, which designed and manufactured the CAEv2 before 3M’s acquisition.

### Plaintiffs

The plaintiffs were active-duty and former U.S. military personnel who used CAEv2 earplugs during training or combat. Individual bellwether plaintiffs included veterans such as **Lloyd Baker**, **Luke Estes**, **Lewis Adkins**, **Brandon Adkins**, and **Theodore Finley**.

### Other important participants

- **Judge M. Casey Rodgers**, the MDL judge, managed discovery, dispositive motions, bellwether trials, settlement proceedings, and later the settlement-administration process.
- **Aearo Technologies**, although a defendant, became central to a separate bankruptcy strategy in 2022.
- **U.S. Bankruptcy Judge Jeffrey J. Graham** presided over Aearo’s Chapter 11 case in the Southern District of Indiana.
- **Bryan Aylstock**, **Christopher Seeger**, and **Clay Townsend** were among the prominent lawyers serving in leadership roles for the plaintiffs.
- **Mike Roman**, 3M’s chief executive, was a principal corporate spokesperson during the litigation and settlement.

## Product and allegations

The **CAEv2** was a dual-ended, nonlinear earplug. One end was intended to provide conventional noise blocking; the other was intended to reduce harmful impulse noise while allowing the wearer to hear lower-level sounds and commands. Aearo and later 3M supplied the product to the U.S. military for years, particularly from the early 2000s through approximately 2015.

Plaintiffs alleged that:

1. **The earplugs were defectively designed.**  
   They claimed the stem was too short and that the earplug could loosen imperceptibly after insertion, breaking the acoustic seal.

2. **3M and Aearo knew of the problem.**  
   Plaintiffs relied on internal testing and communications that they said showed the companies knew the earplug could fail unless it was folded back or fitted in a particular way.

3. **The companies failed to warn users and the military.**  
   Plaintiffs alleged that the special fitting instructions and limitations were not adequately disclosed.

4. **Testing and regulatory representations were misleading.**  
   They contended that the defendants manipulated or improperly conducted attenuation testing and misrepresented the earplug’s **Noise Reduction Rating** and compliance with military specifications.

5. **The failures caused hearing injuries.**  
   Claimed injuries included permanent sensorineural hearing loss, tinnitus, and related impairment.

The defendants denied that CAEv2 was defective or fraudulently marketed. They argued that the earplugs were safe and effective when properly fitted, that military noise exposure and other causes explained many plaintiffs’ injuries, and that the federal government was deeply involved in the product’s design and procurement.

## Major legal issues

### Government-contractor defense

3M argued that it was protected under the federal **government-contractor defense**, because the military approved reasonably precise specifications and knew about the product’s characteristics. Judge Rodgers rejected broad application of that defense at summary judgment, finding factual and legal deficiencies in 3M’s showing, including questions about whether the government had actually dictated the relevant design features and warnings.

### Causation and individualized proof

Because hearing loss and tinnitus can arise from many sources, 3M argued that each claimant had to prove product use, exposure, defect, and medical causation individually. This was one reason the MDL used bellwether trials rather than attempting a single classwide trial.

### Bankruptcy and corporate separateness

In 2022, Aearo filed Chapter 11 and sought to extend the bankruptcy stay to 3M, even though 3M itself had not filed bankruptcy. The central issue was whether a solvent parent company could use its subsidiary’s bankruptcy to halt the MDL and channel the claims into bankruptcy.

## Main events

### 2018: False Claims Act settlement

On **July 26, 2018**, 3M agreed to pay **$9.1 million** to resolve U.S. government allegations under the False Claims Act that it knowingly sold defective CAEv2 earplugs to the military without disclosing the defect. The settlement did not constitute an admission of liability.

The whistleblower was **Moldex-Metric, Inc.**, a competing hearing-protection manufacturer, which received a relator’s share of the recovery. The settlement helped trigger large numbers of individual product-liability suits.

### April 2019: MDL created

On **April 3, 2019**, the Judicial Panel on Multidistrict Litigation centralized the federal cases in the Northern District of Florida before Judge Rodgers as **MDL No. 2885**.

The proceeding rapidly became the largest federal MDL by number of claims, eventually encompassing roughly **300,000 administrative and filed claims**, although the exact count varied as claims were dismissed, vetted, or moved onto the active docket.

### 2021–2022: Bellwether trials

Sixteen bellwether trials were conducted between 2021 and 2022, involving nineteen service-member plaintiffs. The results were mixed:

- Plaintiffs won **10 of the 16 trials**.
- 3M won **6**.
- Juries awarded plaintiffs approximately **$265 million 
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall texaco_pennzoil — 15/16; missed: Carl Icahn's role</summary>

```
**Pennzoil Co. v. Texaco Inc.** was the landmark litigation arising from the 1984 contest for **Getty Oil Co.** It produced one of the largest civil verdicts in U.S. history and helped establish that a preliminary merger agreement can be binding even before execution of a formal contract.

## Parties and key people

- **Pennzoil Co.** — Houston-based oil company that negotiated to acquire Getty Oil.
- **Texaco Inc.** — competing oil company that ultimately bought Getty.
- **Getty Oil Co.** — the takeover target.
- **Gordon Getty** — son of founder J. Paul Getty, trustee of the **Sarah C. Getty Trust**, and a major influence over the controlling Getty shares.
- **Sarah C. Getty Trust** — Getty family trust holding a large block of Getty Oil stock.
- **J. Ronald Getty** — another Getty family shareholder involved in the negotiations.
- **Sidney R. Petersen** — Getty Oil’s chairman and chief executive.
- **Hugh Liedtke** — Pennzoil’s chairman and principal negotiator.
- **J. Paul Getty Jr.** — Getty family member whose interests figured in the ownership structure and negotiations.
- **John K. McKinley** — Texaco’s chairman and CEO during the acquisition.
- **Joseph D. Jamail Jr.** — Pennzoil’s lead trial lawyer.
- **Richard “Dick” Miller** — Texaco’s principal trial lawyer.

## The disputed Getty–Pennzoil agreement

In early January 1984, Pennzoil negotiated with Getty Oil, Gordon Getty, and the Getty trust. The parties reached an arrangement under which Pennzoil would acquire Getty shares and Getty Oil would undergo a restructuring. The precise terms evolved, but the agreed price was approximately **$110 per share**.

On **January 3, 1984**, Getty Oil’s board approved the transaction in principle. The parties issued a press release announcing an “agreement in principle,” and Getty’s investment bankers and lawyers continued preparing definitive documents.

Before those documents were signed, Texaco offered a higher price—approximately **$125 per share in cash**—for all Getty shares. On **January 6, 1984**, Getty Oil’s board accepted Texaco’s offer. Texaco then acquired Getty Oil in a transaction valued at roughly **$10.1 billion**, at the time the largest corporate acquisition ever completed.

## Pennzoil’s allegations

Pennzoil did not primarily sue Getty for breach. Instead, it sued **Texaco in Texas state court for tortious interference with contract**.

Pennzoil alleged that:

1. A binding contract had already been formed among Pennzoil, Getty Oil, and the Getty interests, despite the absence of a final signed merger agreement.
2. Texaco knew of that agreement.
3. Texaco intentionally induced Getty and the Getty interests to abandon it and sell to Texaco.
4. Pennzoil lost the economic benefit of acquiring a major interest in Getty’s oil reserves.

Texaco responded that there was no enforceable contract because:

- the negotiations contemplated execution of definitive written agreements;
- important terms remained unresolved;
- Getty’s board approval and the public announcement were preliminary or conditional; and
- the parties did not intend to be bound until formal documents were signed.

Thus, the central issue was **objective intent to contract**: whether the parties’ words, conduct, board actions, and public announcement created a binding agreement under New York law, notwithstanding their expectation of later formal documentation.

Other major issues included:

- whether Texaco had sufficient knowledge of the alleged contract;
- whether its interference was intentional and legally unjustified;
- the proper measure of Pennzoil’s damages;
- whether Texas could constitutionally require Texaco to post an enormous bond to stay enforcement while appealing; and
- whether Texaco’s later bankruptcy filing could be used to resolve the judgment.

## Trial and verdict

The case was tried in Houston before **Judge Anthony J.P. Farris** of the Texas state district court.

On **November 19, 1985**, the jury found for Pennzoil. It awarded:

- **$7.53 billion in compensatory damages**, and
- **$3 billion in punitive damages**.

With prejudgment interest, the judgment entered in December 1985 was approximately **$10.53 billion**. The jury accepted Pennzoil’s position that a binding agreement existed and that Texaco had knowingly induced its breach.

The damages theory was based largely on the value Pennzoil would have obtained from its contemplated interest in Getty’s oil and gas reserves, less the acquisition costs.

## Appeals and the bond dispute

Texas law generally required an appellant to post a supersedeas bond sufficient to secure the judgment during appeal. For Texaco, that meant a bond of roughly **$12 billion or more**, including interest and costs—an amount it argued was impossible to obtain and would destroy the company before appellate review.

Texaco brought a federal constitutional challenge to the bond requirement. A federal district court granted relief, and the Second Circuit largely agreed. But on **April 6, 1987**, the U.S. Supreme Court decided **Pennzoil Co. v. Texaco Inc., 481 U.S. 1 (1987)**. The Court did **not** decide whether Pennzoil’s contract existed or whether the Texas verdict was correct. Instead, relying principally on **Younger abstention** and federalism concerns, it held that the federal courts should not interfere with the ongoing Texas state proceedings when Texaco could raise its constitutional objections there.

Meanwhile, the Texas appellate courts reviewed the merits. On **February 12, 1987**, the Texas Court of Appeals upheld liability and the compensatory award but reduced punitive damages from **$3 billion to $1 billion**. The resulting judgment, with interest, remained around **$10 billion**. The Texas Supreme Court declined further review in late 1987.

## Bankruptcy and settlement

Unable to post the required security and facing enforcement of the judgment, **Texaco filed for Chapter 11 bankruptcy protection on April 12, 1987**, in the Southern Distr
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall dalkon — 14/15; missed: Medical Device Amendments of 1976</summary>

```
The **Dalkon Shield litigation** was a mass-tort crisis arising from an intrauterine contraceptive device sold by **A.H. Robins Company, Inc.** It ultimately drove Robins into Chapter 11 and produced one of the earliest large bankruptcy trusts for personal-injury claims.

## Parties and key people

- **A.H. Robins Company**, a Richmond, Virginia pharmaceutical manufacturer, acquired rights to the Dalkon Shield in 1970, manufactured and marketed it, and became the principal defendant and later the Chapter 11 debtor.
- **Dalkon Corporation** and the device’s developers, principally **Dr. Hugh J. Davis**, a Johns Hopkins gynecologist, and electrical engineer **Irwin Lerner**, developed and initially promoted the device.
- **Thousands of women** alleged injuries from use of the Shield; husbands and families sometimes asserted derivative claims. Foreign users also became important claimants.
- **Robins officers and directors**, especially company president **E. Claiborne Robins Jr.**, were accused of continuing aggressive promotion despite accumulating safety information.
- **Merrell Dow Pharmaceuticals Inc.** was a major co-defendant because it supplied copper sulfate used in the device and was alleged to have participated in aspects of its development or promotion.
- **Judge Robert R. Merhige Jr.** of the U.S. District Court for the Eastern District of Virginia presided over the Robins reorganization.
- **Richard B. Sobol**, a Harvard law professor, served as examiner and investigated Robins’s conduct and finances.
- **Johns-Manville**, although not a Dalkon Shield party, supplied an important precedent for using Chapter 11 and a trust to resolve mass-tort liabilities.
- **American Home Products Corporation**, later known as Wyeth, became Robins’s merger partner and funded the reorganization.

## Product and principal allegations

The Dalkon Shield was introduced in the United States in **1970**. Its distinctive feature was a **multifilament tail string** extending through the cervix. Claimants alleged that the string could act as a wick or pathway by which bacteria traveled into the uterus, causing:

- pelvic inflammatory disease and other serious infections;
- septic abortion and miscarriage;
- infertility and hysterectomy;
- ectopic pregnancy;
- fetal injury or birth defects;
- and, in some cases, death.

The litigation also alleged that the device had an unacceptably high pregnancy and expulsion rate. Plaintiffs contended that Robins:

1. inadequately tested the Shield before mass marketing;
2. overstated its effectiveness, including use of a misleadingly low pregnancy-rate figure;
3. failed to warn physicians and users adequately;
4. concealed or minimized reports of infection, pregnancy, septic abortion, and death;
5. continued selling and promoting the device after learning of serious risks; and
6. failed to conduct an effective recall after suspending U.S. sales.

Claims were brought under negligence, strict products liability, breach of warranty, fraud, misrepresentation, and failure-to-warn theories. Robins disputed causation in many cases and argued that infections could have other causes. A recurring legal issue was whether punitive damages were justified by evidence of conscious disregard for safety.

## Main events, 1974–1985

### 1974: suspension of sales

By the early 1970s, adverse-event reports and lawsuits were mounting. In **June 1974**, Robins suspended U.S. sales at the request of the Food and Drug Administration. The company characterized the action as a suspension rather than a recall. Approximately **2.2 million** women worldwide had used the device, including roughly **1.5 million in the United States**.

### 1974–1984: expanding tort litigation

Individual suits multiplied in state and federal courts. Several juries awarded substantial compensatory and punitive damages. Discovery produced internal company documents that plaintiffs used to argue that Robins knew more about the Shield’s risks than it disclosed.

A particularly influential proceeding was **Tetuan v. A.H. Robins Co.**, a Kansas case in which a jury awarded compensatory and punitive damages; the Kansas Supreme Court’s **1983** opinion upheld liability and discussed evidence that Robins had misrepresented the device’s safety and effectiveness.

Federal multidistrict proceedings were coordinated before **Judge Miles W. Lord** in Minnesota. In **1984**, during proceedings involving punitive-damages claims, Judge Lord sharply condemned Robins executives and ordered them to appear personally. The Eighth Circuit later held that he had exceeded his authority and ordered his removal from the Dalkon Shield litigation. The episode nevertheless intensified public scrutiny of the company.

### 1984: public notice and removal campaign

In **1984**, Robins began a broad campaign urging women who still had Dalkon Shields to have them removed, offering to pay removal expenses. Critics argued that this came years after sales had stopped and after the dangers were apparent.

By the mid-1980s, Robins faced thousands of filed suits and a much larger universe of potential claims. Insurance coverage was disputed and plainly insufficient to eliminate the company’s exposure.

## The A.H. Robins bankruptcy, 1985–1989

### Chapter 11 filing

On **August 21, 1985**, A.H. Robins filed for Chapter 11 protection in the **Eastern District of Virginia**. The filing automatically stayed pending Dalkon Shield suits. Robins remained in possession while attempting to formulate a plan.

The bankruptcy raised difficult questions:

- How could future or not-yet-filed personal-injury claims be identified and valued?
- Could foreign claimants participate?
- Should punitive damages be allowed?
- Could claimants continue jury trials outside bankruptcy court?
- How much insurance and corporate value was available?
- Could a plan protect Robins’s insurers, affiliates, officers, directors, and merger partner from related litigation?
- How should t
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall bhopal — 14/15; missed: Sevin (carbaryl) pesticide</summary>

```
## Disaster

The **Bhopal gas disaster** occurred during the night of **2–3 December 1984** at a pesticide plant in **Bhopal, Madhya Pradesh, India**, operated by **Union Carbide India Limited (UCIL)**. UCIL was majority-owned—about **50.9%**—by the U.S. corporation **Union Carbide Corporation (UCC)**; Indian public and institutional investors held the balance.

Water entered a storage tank containing roughly **40 tons of methyl isocyanate (MIC)**, triggering a runaway exothermic reaction. A toxic cloud containing MIC and reaction products escaped over nearby settlements. Safety systems were alleged to have been shut down, poorly maintained, undersized, or otherwise ineffective.

Thousands died immediately or soon afterward. Official Indian figures later recognized approximately **3,787 deaths**, while other governmental and independent estimates put the eventual death toll much higher—often **15,000–20,000 or more**. More than **500,000 people** were exposed, many suffering respiratory, ocular, neurological, reproductive, and other chronic injuries. Contamination at and around the abandoned plant remained a separate long-term issue.

## Parties and principal people

- **Union Carbide India Limited (UCIL):** Indian company that owned and operated the Bhopal plant.
- **Union Carbide Corporation (UCC):** U.S. parent company headquartered in Connecticut.
- **Government of India:** Under the **Bhopal Gas Leak Disaster (Processing of Claims) Act 1985**, it assumed exclusive authority to represent victims’ claims as *parens patriae*.
- **State of Madhya Pradesh and Central Bureau of Investigation (CBI):** Principal state and prosecuting authorities in the Indian criminal proceedings.
- **Victims and survivor organizations:** Included individual claimants and groups such as the **Bhopal Gas Peedith Mahila Udyog Sangathan** and **Bhopal Group for Information and Action**, which challenged aspects of the settlement and compensation process.
- **Warren M. Anderson:** UCC’s chairman and chief executive at the time. He was arrested in Bhopal on **7 December 1984**, released on bail, left India, and never returned to stand trial.
- **Keshub Mahindra:** Chairman of UCIL and the most prominent Indian corporate defendant convicted in 2010.
- **Judge John F. Keenan:** U.S. federal judge who dismissed the U.S. civil action on forum-non-conveniens grounds in 1986.
- **Chief Judicial Magistrate Mohan P. Tiwari:** Delivered the June 2010 convictions of seven surviving former UCIL officials.

## Key allegations and legal issues

Victims and the Indian government alleged that UCC and UCIL were responsible for:

- negligent plant design, operation, maintenance, and safety practices;
- storing excessive quantities of MIC in densely populated Bhopal;
- cost-cutting and inadequate staffing and training;
- failure to maintain or operate refrigeration, flare, scrubber, alarm, and other safety systems;
- failure to warn surrounding communities adequately;
- transferring hazardous technology and imposing design or management decisions from the U.S. parent.

UCC disputed direct parent-company responsibility. It maintained that UCIL was a separately managed Indian company and later argued that the release resulted from **employee sabotage**, rather than ordinary operational negligence. Critics rejected or disputed that theory and emphasized systemic safety failures.

The litigation raised several major issues:

1. whether claims should be heard in the United States or India;
2. whether UCC could be held liable for UCIL’s conduct;
3. whether India could exclusively represent all victims;
4. whether the 1989 settlement was adequate and whether it could extinguish criminal liability;
5. what criminal charge was legally sustainable against UCIL personnel;
6. whether UCC, Anderson, or later UCC owner **Dow Chemical Company** could be compelled to appear or bear additional liability.

## Main events and litigation chronology

### 1984–1986: Initial proceedings and U.S. dismissal

- **2–3 December 1984:** The gas escaped from UCIL’s Bhopal plant.
- **7 December 1984:** Warren Anderson was arrested in Bhopal, granted bail, and permitted to leave India.
- Numerous civil suits were filed in U.S. courts and consolidated in the **Southern District of New York**.
- **March 1985:** India enacted the **Bhopal Gas Leak Disaster (Processing of Claims) Act**, giving the central government exclusive authority to pursue and settle victims’ claims.
- **April 1985:** The **Union of India sued UCC in New York**, seeking billions of dollars in damages.
- **12 May 1986:** Judge **John F. Keenan** dismissed the action in **In re Union Carbide Corp. Gas Plant Disaster at Bhopal, India**, on **forum non conveniens** grounds. He concluded that India was the more appropriate forum, subject to UCC’s consent to Indian jurisdiction, waiver of certain limitations defenses, and agreement to satisfy an Indian judgment meeting due-process standards.
- **1986:** India filed suit against UCC in the District Court at Bhopal, initially seeking approximately **US$3.3 billion**.

### 1987–1989: Criminal charges and global settlement

- **December 1987:** The CBI filed criminal charges against UCC, UCIL, Anderson, and Indian UCIL officials. The allegations included culpable homicide and related offenses.
- **14–15 February 1989:** The **Supreme Court of India** approved a comprehensive settlement under which UCC agreed to pay **US$470 million**. The Court also ordered termination of civil proceedings and initially quashed the criminal cases.
- UCC paid the settlement amount. It did not admit liability.
- The settlement was heavily criticized as inadequate given the number of deaths and injuries, and because it had been reached without individualized adjudication or meaningful participation by many victims.

### 1991–1996: Settlement upheld; criminal liability narrowed

- **3 October 1991:** In review proceedings, the Supreme Court substantially **upheld the US$47
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall near — 3/12; missed: MobileFuse / Kenneth Harlan, round-trip revenue scheme, ~27% revenue overstatement; $37.3m of $138.3m, KludeIn I SPAC merger, March 2023, Nasdaq ticker NIR, Pasadena, California, Chapter 11, 8 December 2023, luxury residence billed as professional services</summary>

```
I don’t know of an SEC accounting-fraud case filed in 2026 against former Near Intelligence, Inc. CEO Anil Mathews and CFO Rahul Agarwal. As of my knowledge cutoff in June 2024, 2026 was in the future, so I cannot reliably describe its allegations, chronology, or outcome without current source material.

If you provide the SEC release, complaint, case number, or a link, I can summarize the parties, alleged misconduct, key people, dated events, and disposition without guessing.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall meyer — 3/10; missed: SpaceX pre-IPO interests, misappropriation for personal expenses, inflated account statements, releases for reduced distributions, forfeited ~$3m capital call, Investment Advisers Act antifraud, conduct since December 2021</summary>

```
I’m not aware of any SEC case filed in September 2026 against **Meyer Global Management LLC** or its CEO **Owen Meyer**. September 2026 is also in the future relative to today, so no such filing or outcome can yet be reliably described.

The names may be mistaken or the matter may refer to a different entity or date. I would not want to invent parties, allegations, events, or an outcome. If you provide an SEC release number, court docket, or link, I can help identify or summarize the correct matter.
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall theranos — 15/17; missed: Safeway, Bad Blood (2018)</summary>

```
## Overview

Theranos, Inc. was a Silicon Valley blood-testing company founded in 2003 by **Elizabeth Holmes**, who served as chief executive. **Ramesh “Sunny” Balwani**, Holmes’s former romantic partner, was Theranos’s president and chief operating officer from 2009 to 2016.

Theranos claimed that its proprietary devices—especially the **“Edison”** and later the **“miniLab”**—could accurately perform a broad range of laboratory tests using only a few drops of blood from a finger stick. In reality, Theranos could perform only a limited number of tests on its own technology, often used modified conventional analyzers for other tests, and experienced serious accuracy and reliability problems.

The criminal cases concerned two related fraud schemes:

1. **Investor fraud:** allegedly inducing investors to provide hundreds of millions of dollars through false or misleading claims about Theranos’s technology, commercial relationships, regulatory status, finances, and use by the military.
2. **Patient fraud:** allegedly misleading doctors and patients about the accuracy and reliability of Theranos blood tests.

## Principal parties and people

- **United States of America:** Prosecuted both cases in the U.S. District Court for the Northern District of California.
- **Elizabeth Holmes:** Theranos founder, chair, and CEO; criminal defendant.
- **Ramesh “Sunny” Balwani:** Theranos president and COO; criminal defendant and Holmes’s former partner.
- **Judge Edward J. Davila:** Presided over both federal criminal trials.
- **John Carreyrou:** *Wall Street Journal* reporter whose October 2015 reporting publicly exposed major problems with Theranos’s technology and practices.
- **Erika Cheung and Tyler Shultz:** Former Theranos employees who raised concerns about testing quality and laboratory practices. Shultz was the grandson of former Secretary of State and Theranos director **George Shultz**.
- **Adam Rosendorff:** Former Theranos laboratory director and a major prosecution witness about test failures and laboratory problems.
- **David Boies:** Prominent lawyer whose firm represented Theranos; he also served on its board.
- **Investors and business partners:** Theranos raised money from investors including the family of former Education Secretary **Betsy DeVos**, Rupert Murdoch, and others. Walgreens entered a major retail partnership with Theranos.

## Key allegations and issues

Prosecutors alleged that Holmes and Balwani knowingly or recklessly misrepresented, among other things:

- that Theranos’s proprietary machines could perform hundreds of accurate tests from tiny finger-stick samples;
- that the technology had been comprehensively validated and was comparable or superior to conventional laboratory methods;
- that Theranos was using its own devices when many tests were actually run on conventional third-party machines;
- that Theranos technology had been deployed by the U.S. military in combat or on medical-evacuation helicopters;
- that major pharmaceutical companies had validated or endorsed the technology;
- that Theranos had a strong and rapidly growing financial position, including projections far beyond its actual revenue;
- that demonstrations shown to investors reflected ordinary device performance;
- and that patients could safely rely on Theranos test results.

The defense disputed fraudulent intent. Holmes argued that she genuinely believed in the technology and relied on scientists, laboratory personnel, lawyers, and other advisers. She also testified that Balwani had subjected her to emotional and sexual abuse and exercised substantial control over her. Balwani denied abuse and maintained that he acted in good faith.

A central issue in both trials was not merely whether Theranos failed, but whether each defendant **intentionally participated in a scheme to defraud** and made or caused materially false statements with the required criminal intent.

## Main events

### Rise of Theranos

- **2003:** Holmes founded Theranos after leaving Stanford University.
- **2009:** Balwani joined Theranos as president and COO. He and Holmes had been in a concealed romantic relationship.
- **2013–2014:** Theranos emerged from secrecy, announced its Walgreens partnership, and attracted extensive favorable publicity. Holmes was portrayed as a visionary entrepreneur, and the company reached a private valuation of roughly **$9 billion**.
- **2013–2015:** Theranos offered testing at Walgreens locations in Arizona and California while continuing to raise substantial investor funds.

### Exposure and regulatory collapse

- **October 15, 2015:** John Carreyrou and *The Wall Street Journal* published the first major investigation reporting that Theranos used conventional machines for many tests and that former employees questioned the accuracy of its proprietary technology.
- **2015–2016:** Theranos publicly disputed the reporting, but federal regulators intensified scrutiny.
- **January 2016:** The Centers for Medicare & Medicaid Services found serious deficiencies at Theranos’s Newark, California laboratory, including conditions posing “immediate jeopardy” to patient health and safety.
- **May 2016:** Balwani left Theranos.
- **July 2016:** CMS imposed sanctions, including barring Holmes from owning, operating, or directing a clinical laboratory for at least two years.
- **2016:** Walgreens terminated its relationship with Theranos and closed the testing sites.
- **2017:** Theranos settled litigation with Walgreens and other parties and voided or corrected large numbers of test results.

### SEC civil case

- **March 14, 2018:** The Securities and Exchange Commission charged Theranos, Holmes, and Balwani with a “massive fraud,” alleging that they raised more than **$700 million** through false or exaggerated claims.
- Holmes settled without admitting or denying the allegations. She agreed to pay a **$500,000 penalty**, return shares, relinquish voting control, and accept a **10-year bar** from servi
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall dieselgate — 15/17; missed: Judge Charles Breyer, N.D. Cal. MDL, Bosch supplied the engine software</summary>

```
## Overview

The Volkswagen diesel-emissions scandal—widely called **“Dieselgate”**—began publicly in **September 2015**, when U.S. regulators accused **Volkswagen AG** of installing software in diesel vehicles that recognized emissions testing and temporarily activated full pollution controls. In ordinary driving, many affected cars emitted far more nitrogen oxides (**NOx**) than U.S. law allowed.

The scandal ultimately involved roughly **11 million vehicles worldwide**, including about **590,000 U.S. vehicles**, and produced criminal convictions, multibillion-dollar settlements, recalls, consumer compensation, and major changes in Volkswagen’s management and strategy.

## Main parties

### Volkswagen entities and brands

- **Volkswagen AG**, the German parent company.
- **Volkswagen Group of America, Inc.**
- **Audi AG** and **Porsche AG**, whose diesel vehicles were implicated in a later U.S. notice concerning 3.0-liter engines.
- Other Volkswagen Group brands and national subsidiaries involved in recalls and litigation.

### Governments and regulators

- The **U.S. Environmental Protection Agency (EPA)**, which issued Clean Air Act violation notices.
- The **California Air Resources Board (CARB)**, which worked with the EPA and conducted extensive testing and negotiations.
- The **U.S. Department of Justice (DOJ)**, which brought civil and criminal cases.
- The **Federal Trade Commission (FTC)**, which alleged deceptive “clean diesel” advertising.
- German prosecutors and regulators, particularly prosecutors in **Braunschweig**, **Munich**, and **Stuttgart**, and Germany’s **Federal Motor Transport Authority (KBA)**.
- Regulators and prosecutors in numerous other countries.

### Private parties

- Owners and lessees of affected vehicles.
- Volkswagen dealers.
- Investors and shareholders alleging that Volkswagen failed to disclose material financial and regulatory risks.
- The **International Council on Clean Transportation (ICCT)** and **West Virginia University’s Center for Alternative Fuels, Engines and Emissions**, whose road testing helped expose the discrepancy.

## Core allegations and issues

### Defeat-device software

The central allegation was that Volkswagen installed an illegal **“defeat device”** in diesel-engine control software. The software detected conditions associated with laboratory emissions tests—such as steering-wheel position, vehicle speed, engine operation, and test-cycle patterns—and switched the vehicle into a low-emissions calibration.

During normal road use, the vehicles operated differently, improving performance or fuel economy but producing substantially more NOx. U.S. authorities said some vehicles emitted **up to 40 times** the applicable NOx standard.

### Engines and vehicles

The first U.S. case concerned **2.0-liter TDI** diesel vehicles using Volkswagen’s **EA189** engine family, sold in model years roughly **2009–2015** under the Volkswagen and Audi brands.

A second EPA notice, issued in **November 2015**, concerned certain **3.0-liter V6 diesel** vehicles from Volkswagen, Audi, and Porsche. Volkswagen initially disputed aspects of that allegation but later admitted that undisclosed emissions-control software had been used.

### Regulatory deception and obstruction

Authorities alleged that Volkswagen:

- Obtained certificates allowing vehicles to be sold by making false or incomplete representations.
- Concealed the software from regulators.
- Gave misleading technical explanations for excess road emissions.
- Conducted a limited recall in 2014 that did not disclose or eliminate the defeat device.
- Continued selling and marketing vehicles as environmentally friendly “clean diesels.”
- In some instances destroyed or concealed evidence after learning of regulatory scrutiny.

## Key people

### Volkswagen leadership

- **Martin Winterkorn**, Volkswagen AG’s chief executive when the scandal broke. He resigned on **23 September 2015**, saying he accepted responsibility as CEO while denying personal wrongdoing at that time. U.S. prosecutors later charged him with conspiracy and wire fraud; German prosecutors also charged him in separate proceedings. He has denied knowingly participating in the scheme during the relevant early period. His German criminal trial was repeatedly delayed or separated because of health issues.
- **Matthias Müller**, formerly Porsche’s chief executive, succeeded Winterkorn as Volkswagen CEO on **25 September 2015** and oversaw much of the initial settlement and restructuring period.
- **Herbert Diess**, head of the Volkswagen passenger-car brand from 2015 and later group CEO. German prosecutors charged him and others over alleged delayed disclosure to investors; that proceeding was later terminated after Volkswagen paid a monetary condition.
- **Hans Dieter Pötsch**, Volkswagen’s finance chief during part of the relevant period and later supervisory-board chairman. He also faced German market-disclosure allegations that were resolved without a trial through a monetary payment by Volkswagen.
- **Rupert Stadler**, Audi’s former CEO. German authorities arrested him in **June 2018** over concerns about possible evidence interference. In **June 2023**, a Munich court gave him a suspended sentence after he admitted that he had allowed affected vehicles to remain on sale after learning of manipulation. He was the first former Volkswagen Group management-board member convicted in Germany over Dieselgate.

### Engineers and managers prosecuted in the United States

- **James Robert Liang**, a Volkswagen engineer, pleaded guilty in **September 2016** to conspiracy to defraud U.S. regulators and customers. In **August 2017**, he received a **40-month prison sentence**.
- **Oliver Schmidt**, a former head of Volkswagen’s U.S. environmental and engineering office, pleaded guilty in **August 2017**. In **December 2017**, he was sentenced to **seven years in prison** and fined **$400,000**. He was later transferred to Germany and re
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall ftx — 14/18; missed: ~$8 billion customer funds, effective altruism, customers repaid in full at petition-date value, Michael Lewis, Going Infinite</summary>

```
## Overview

FTX, once one of the world’s largest cryptocurrency exchanges, collapsed in November 2022 after revelations that customer assets had been diverted to its affiliated trading firm, Alameda Research. The failure exposed an approximately multibillion-dollar shortfall, triggered bankruptcy proceedings, and led to criminal prosecutions of founder **Samuel “Sam” Bankman-Fried** and several senior associates.

Federal prosecutors characterized the scheme as one of the largest financial frauds in U.S. history. Bankman-Fried was convicted in November 2023 and sentenced in March 2024 to **25 years in federal prison**.

## Principal parties and people

- **Sam Bankman-Fried (“SBF”)**: Co-founder and chief executive of FTX until November 11, 2022; majority owner of Alameda Research. He was the principal criminal defendant.
- **FTX Trading Ltd. and related entities**: The cryptocurrency exchange group through which customers deposited and traded digital assets.
- **Alameda Research**: A crypto trading firm co-founded and controlled by Bankman-Fried. Prosecutors alleged it received and spent billions of dollars belonging to FTX customers.
- **United States Attorney’s Office for the Southern District of New York**: Prosecuted the federal criminal case, **United States v. Samuel Bankman-Fried**, before U.S. District Judge **Lewis A. Kaplan**.
- **Damian Williams**: U.S. Attorney for the Southern District of New York during the prosecution.
- **Caroline Ellison**: Alameda’s chief executive and Bankman-Fried’s former romantic partner. She pleaded guilty and became a central prosecution witness.
- **Gary Wang**: FTX co-founder and chief technology officer. He pleaded guilty and testified that he helped create software features giving Alameda special access to FTX customer funds.
- **Nishad Singh**: FTX’s engineering director. He pleaded guilty and testified for the government.
- **Ryan Salame**: Co-chief executive of FTX Digital Markets in the Bahamas. He pleaded guilty in a related case but did not testify at Bankman-Fried’s trial.
- **John J. Ray III**: Restructuring specialist who replaced Bankman-Fried as FTX’s CEO and oversaw the bankruptcy. He described an extraordinary failure of corporate controls.
- **FTX customers, lenders, and investors**: The principal alleged victims.
- **Securities and Exchange Commission, Commodity Futures Trading Commission, and Department of Justice**: Brought parallel civil or criminal proceedings.
- **The Securities Commission of The Bahamas and Bahamian authorities**: Involved because FTX’s headquarters and Bankman-Fried were in the Bahamas.

## Core allegations and issues

Prosecutors alleged that, beginning by at least 2019, Bankman-Fried orchestrated several related frauds:

1. **Misappropriation of customer deposits**  
   FTX customer money was routed or transferred to Alameda. Alameda used it for speculative trading, venture investments, political contributions, real estate, loan repayments, and personal or insider loans.

2. **Secret privileges for Alameda**  
   Alameda allegedly had special treatment in FTX’s computer systems, including a virtually unlimited line of credit, the ability to maintain a negative balance, and exemption from ordinary liquidation rules. These features allowed Alameda to withdraw billions beyond its own assets.

3. **False statements to customers and investors**  
   Bankman-Fried allegedly represented that customer assets were safe and segregated while permitting Alameda to use them. Prosecutors also alleged that FTX investors were misled about the company’s risk controls and Alameda’s preferential treatment.

4. **Fraud on Alameda’s lenders**  
   Alameda allegedly supplied lenders with misleading balance sheets that concealed or obscured its borrowing from FTX and its dependence on illiquid crypto tokens associated with Bankman-Fried’s businesses.

5. **Campaign-finance scheme**  
   Prosecutors alleged that customer money was used to fund political donations through Bankman-Fried and other executives, sometimes through “straw donors” to evade contribution limits and disclosure rules. A standalone campaign-finance charge was not tried after the Bahamas did not consent to prosecution on that extradition basis, but evidence concerning political spending was admitted as part of the fraud case.

Bankman-Fried denied knowingly stealing customer funds. His defense argued that FTX was a rapidly growing but poorly managed business, that he acted in good faith, relied on colleagues and lawyers, and believed Alameda could repay what it owed.

## Main events

### Growth and pre-collapse conduct

- **2017**: Bankman-Fried and Gary Wang founded Alameda Research.
- **2019**: Bankman-Fried, Wang, and others launched FTX. Prosecutors said the misuse of customer deposits began early in the exchange’s operation.
- **2021–2022**: FTX raised large sums from prominent investors and obtained a valuation of roughly $32 billion. Bankman-Fried became a major political donor and public advocate for crypto regulation.
- **2022 crypto downturn**: Falling asset prices and lender demands placed pressure on Alameda. Prosecutors said Alameda repaid lenders and continued spending with FTX customer funds.

### Collapse in November 2022

- **November 2, 2022**: CoinDesk reported on a leaked Alameda balance sheet showing that a large portion of its assets consisted of **FTT**, a token issued by FTX, and other affiliated or illiquid assets. The report raised questions about Alameda’s solvency and the financial entanglement between the firms.
- **November 6**: Binance CEO **Changpeng Zhao** announced that Binance would sell its remaining FTT holdings. Customers rushed to withdraw funds from FTX.
- **November 8**: FTX announced a nonbinding agreement for Binance to acquire the exchange, subject to due diligence.
- **November 9**: Binance withdrew from the proposed acquisition, citing due-diligence findings and reports of mishandled customer funds.
- **Novembe
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall endo — 14/20; missed: New York AG Assurance of Discontinuance, March 2016, 'pseudoaddiction' and 'usually do not become addicted' in training / marketing, American Pain Foundation / NIPC / painknowledge.com, Par Pharmaceutical (2015) and Qualitest (2010) generic subsidiaries, generic Opana ER / Impax & Actavis; FTC pay-for-delay case (2016-17), Opioid Industry Documents Archive (UCSF / Johns Hopkins) document release</summary>

```
Endo’s opioid litigation was a collection of federal multidistrict litigation, state and local government suits, private claims, and criminal and civil federal investigations centered principally on **Opana ER**, Endo’s extended-release oxymorphone product. It culminated in Endo’s 2022 Chapter 11 filing, a government-supported bankruptcy sale, and a 2024 criminal guilty plea by an Endo subsidiary.

## Parties and products

- **Endo International plc**, an Ireland-domiciled pharmaceutical group, and U.S. subsidiaries including **Endo Pharmaceuticals Inc.** and **Endo Health Solutions Inc.**
- Government plaintiffs included numerous **states and state attorneys general**, counties, cities, tribal governments, and other public entities.
- Private plaintiffs included people with opioid-use disorder or overdose injuries, families, hospitals, insurers, and other third-party payors.
- Federal enforcement involved the **U.S. Department of Justice**, U.S. Attorneys’ Offices, and agencies including the FDA and DEA.
- The principal Endo product was **Opana ER**, an extended-release form of the potent opioid **oxymorphone**. Endo also sold other opioid products, including Percocet.

## Core allegations and issues

Plaintiffs generally alleged that Endo:

1. **Misrepresented opioid risks and benefits.** Endo allegedly promoted long-term opioid use for chronic, non-cancer pain while minimizing addiction, dependence, overdose, and withdrawal risks and overstating evidence of durable benefit.

2. **Used deceptive marketing.** Complaints alleged that Endo funded or relied on ostensibly independent physicians, speakers, continuing-medical-education programs, and pain organizations to disseminate favorable messages, including claims that addiction was uncommon in properly selected patients.

3. **Promoted Opana ER as abuse-deterrent.** Endo reformulated Opana ER in 2012 with a harder coating and allegedly marketed the reformulation as resistant to crushing or abuse even though the FDA did not authorize abuse-deterrent labeling. Plaintiffs and regulators alleged that users shifted from snorting the original formulation to injecting the reformulated tablets.

4. **Failed to control suspicious opioid orders.** Some government claims alleged inadequate monitoring and reporting of suspicious orders or diversion, although Endo was primarily a manufacturer rather than one of the major distributor defendants.

5. **Created a public nuisance and caused public costs.** States and municipalities sought reimbursement for treatment, emergency response, child-welfare, law-enforcement, and other costs attributed to opioid addiction and overdose.

Endo denied many of the civil allegations and argued, among other things, that its products were FDA-approved, prescribed by licensed clinicians, and accompanied by warnings.

## MDL No. 2804

On **December 5, 2017**, the Judicial Panel on Multidistrict Litigation created **In re National Prescription Opiate Litigation, MDL No. 2804**, in the U.S. District Court for the Northern District of Ohio. The transferee judge was **U.S. District Judge Dan Aaron Polster**.

The MDL consolidated pretrial proceedings in thousands of suits brought principally by cities, counties, tribes, hospitals, and other entities against manufacturers, distributors, and pharmacies. Endo was one of the manufacturer defendants. The litigation asserted public-nuisance, fraud, misrepresentation, negligence, unjust-enrichment, and controlled-substance-law theories, among others.

Important MDL figures included:

- **Judge Dan Polster**, who supervised the MDL and pressed the parties toward global resolution.
- Plaintiffs’ leadership lawyers, including **Paul T. Farrell Jr., Paul J. Hanly Jr., and Joseph F. Rice**, who served as co-lead counsel in the MDL.
- Endo’s senior management during the later litigation and restructuring, particularly **Blaise Coleman**, Endo’s president and chief executive officer from 2020, and **Mark Bradley**, its chief financial officer.

Endo resolved many governmental claims through settlements rather than an MDL bellwether verdict. Its bankruptcy later stayed or channeled the remaining litigation.

## State attorney-general actions

Several attorneys general brought separate state-court or state-law actions. The allegations varied, but generally focused on deceptive promotion of Opana ER and other opioids.

Notable matters included:

- **New York:** Attorney General **Letitia James** announced a settlement in **September 2021** under which Endo agreed to pay up to approximately **$50 million** and to cease opioid promotion. The settlement was part of New York’s broader opioid litigation and was structured to provide funds for abatement.

- **Tennessee and other states:** Endo entered state settlements addressing alleged deceptive marketing and public costs. Tennessee had particular significance because Endo’s U.S. operations were associated with the state and because Opana abuse had heavily affected parts of Appalachia.

- **Multistate resolution:** In **August 2022**, shortly before the bankruptcy filing, Endo announced an agreement in principle with a group of state attorneys general to resolve opioid claims for up to roughly **$450 million over ten years**, subject to bankruptcy and other conditions. The agreement also contemplated injunctive relief, including restrictions on opioid marketing and requirements concerning opioid-related documents.

The state settlements did not end all claims. Endo still faced extensive liabilities asserted by local governments, tribes, private plaintiffs, and governmental entities that had not accepted particular settlements.

## Opana ER regulatory history

Several events involving Opana ER became central to both the civil cases and the later criminal case:

- **2006:** FDA approved the original Opana ER.
- **2012:** Endo introduced a reformulated version intended to be more resistant to physical manipulation.
- **2015:** An outbreak of HIV a
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall teva — 12/14; missed: 2008 Cephalon DOJ settlement ($425m) over Actiq / Gabitril / Provigil, Petah Tikva / Tel Aviv, Israel</summary>

```
The description most likely refers to the long-running U.S. opioid litigation involving **Teva Pharmaceutical Industries Ltd.**, its U.S. subsidiaries, and companies it acquired—especially **Cephalon, Inc.** and **Actavis**. It was not one lawsuit but thousands of federal, state, tribal, and local-government cases, plus several state trials and settlements.

## Parties

### Defendants
- **Teva Pharmaceutical Industries Ltd.** and **Teva Pharmaceuticals USA, Inc.**
- **Cephalon, Inc.**, acquired by Teva in 2011. Cephalon made and promoted:
  - **Actiq**, a fentanyl lozenge approved for breakthrough cancer pain;
  - **Fentora**, a fentanyl buccal tablet with a similarly narrow indication.
- **Actavis** entities, whose U.S. generic-drug business Teva acquired from Allergan in 2016. Actavis was a major seller of generic prescription opioids.
- In some cases, related Teva, Cephalon, Actavis, Watson, and Allergan entities were named according to the relevant corporate history.

### Plaintiffs
Plaintiffs included:
- state attorneys general and state agencies;
- counties, cities, and other political subdivisions;
- Native American tribes;
- hospitals and other entities;
- private individuals in separate personal-injury litigation.

Many local-government and tribal cases were coordinated in the federal multidistrict litigation, **In re National Prescription Opiate Litigation, MDL No. 2804**, before Judge **Dan Aaron Polster** in the U.S. District Court for the Northern District of Ohio.

## Core allegations and issues

The governmental plaintiffs generally alleged two related forms of misconduct.

### 1. Deceptive opioid marketing
Plaintiffs alleged that Cephalon and Teva:
- promoted opioids for chronic, non-cancer pain while minimizing addiction and overdose risks;
- overstated the benefits of long-term opioid therapy;
- promoted Actiq and Fentora beyond their FDA-approved use for opioid-tolerant cancer patients;
- used sales representatives, paid speakers, continuing-medical-education programs, and ostensibly independent “front groups” or third-party organizations to influence prescribing;
- encouraged concepts such as “pseudoaddiction”—the claim that drug-seeking behavior could indicate undertreated pain rather than addiction;
- failed to correct misleading messages after the risks became apparent.

Teva denied wrongdoing and maintained that its products were FDA-approved and medically useful when properly prescribed.

### 2. Failure to monitor and report suspicious opioid orders
As a manufacturer and distributor, Actavis allegedly:
- shipped unusually large or otherwise suspicious opioid orders;
- failed to maintain effective controls against diversion;
- failed to investigate, stop, or report suspicious orders as required by the federal Controlled Substances Act and analogous state laws.

Claims were commonly pleaded under state consumer-protection statutes, public-nuisance law, fraud or misrepresentation theories, negligence, unjust enrichment, and controlled-substance statutes. Teva disputed both liability and causation, arguing, among other things, that prescribing decisions were made by independent physicians and that many other actors contributed to the epidemic.

## Key people

- **Judge Dan Aaron Polster**: federal judge supervising the national opioid MDL.
- **Letitia James**: New York attorney general; led New York’s case and later announced the multistate Teva settlement.
- **James W. Walden**: outside trial counsel for New York in its 2021 trial.
- **Kåre Schultz**: Teva’s president and chief executive during the global-settlement negotiations.
- **Tom Miller**, Iowa attorney general: a leading state negotiator in the multistate opioid settlements.
- **Josh Stein**, North Carolina attorney general: another prominent state negotiator.
- **Paul T. Farrell Jr.**, **Paul J. Hanly Jr.**, and **Joe Rice**: among the principal lawyers representing local governments in the federal MDL and settlement negotiations.
- **Kenneth Feinberg**: court-appointed mediator in the MDL settlement process.
- **Judge Jerry Garguilo**: presided over Suffolk County’s New York opioid trial.

## Main events, 2014–2023

### 2014: Chicago sues
On **June 2, 2014**, the **City of Chicago** sued several opioid manufacturers, including Cephalon, alleging a coordinated and deceptive campaign to expand opioid use for chronic pain while concealing addiction risks. The case became an early model for later government complaints. It was heavily litigated over pleading, discovery, and alleged marketing practices.

### 2016: Teva acquires Actavis’s generic business
On **August 2, 2016**, Teva completed its acquisition of Allergan’s Actavis generic-drug business. That transaction later complicated allocation of responsibility for Actavis-era opioid sales and indemnification obligations between Teva and Allergan.

### 2017: State and local litigation expands
During 2017, states, counties, cities, and tribes filed a rapidly growing number of cases against opioid manufacturers and distributors. In **December 2017**, the federal Judicial Panel on Multidistrict Litigation created **MDL 2804** and assigned it to Judge Polster.

### 2019: Oklahoma trial and early Teva settlement
Oklahoma’s attorney general sued Teva, Cephalon, Purdue Pharma, Johnson & Johnson, and related entities under public-nuisance and other theories.

On **May 26, 2019**, immediately before trial, Teva agreed to settle Oklahoma’s claims for **$85 million**, without admitting wrongdoing. Purdue had already settled; Oklahoma proceeded to trial against Johnson & Johnson.

In **October 2019**, Teva announced a proposed nationwide framework valued by the company at roughly **$23 billion**, consisting largely of donated generic **buprenorphine/naloxone** treatment medication plus cash. Many plaintiffs criticized the valuation and the heavy reliance on product rather than cash, and that proposal did not become the final national resolution.

### 2020: Federal bellw
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall juul — 11/15; missed: 'Vaporized' launch campaign (2015) with young models, San Francisco Unified bellwether; school districts, Altria write-down / exit; later NJOY purchase, JUUL documents in the UCSF Industry Documents Library</summary>

```
The **JUUL youth-vaping litigation** was not one case but a nationwide group of government enforcement actions and private lawsuits alleging that **JUUL Labs, Inc. (JLI)** helped create a youth nicotine-addiction epidemic through its product design, flavors, advertising, and sales practices. Between 2018 and 2023, JUUL and its former investor **Altria Group, Inc.** agreed to settlements totaling well over **$1.7 billion**, although some figures overlap because they resolved different groups of claims.

## Parties and principal allegations

### Defendants

- **JUUL Labs, Inc.**, maker of the JUUL electronic-cigarette device and nicotine pods.
- JUUL’s founders, **Adam Bowen** and **James Monsees**, were named in some actions.
- Former JUUL executives and directors were named in portions of the multidistrict litigation.
- **Altria Group, Inc.**, parent of Philip Morris USA and maker of Marlboro cigarettes, became a major defendant after paying **$12.8 billion in December 2018** for a 35% interest in JUUL.
- Some suits also named retailers, distributors, and related entities.

### Plaintiffs

- State and territorial attorneys general and other public agencies.
- School districts, local governments, and tribal entities.
- Individuals—especially minors or young adults—and parents.
- Consumers alleging they paid more because JUUL misrepresented its products.
- Personal-injury and wrongful-death claimants.

Thousands of federal cases were centralized in **In re JUUL Labs, Inc., Marketing, Sales Practices, and Products Liability Litigation**, **MDL No. 2913**, before U.S. District Judge **William H. Orrick III** in the Northern District of California.

### Core allegations

Plaintiffs generally alleged that JUUL:

1. **Designed and marketed its product to appeal to adolescents**, using sleek, concealable USB-like devices, sweet or fruit flavors, youthful imagery, social-media promotion, launch parties, influencers, and sampling campaigns.
2. **Misrepresented or minimized nicotine and addiction risks**, including the unusually high nicotine delivery of JUUL’s nicotine-salt formulation.
3. Created the impression that JUUL was a safe or FDA-approved smoking-cessation product, although it had not been approved for that purpose.
4. Sold or facilitated sales to minors and failed to maintain adequate age-verification and retail controls.
5. Conducted presentations in schools; one widely cited allegation was that a JUUL representative told students the product was “totally safe.”
6. Caused nicotine addiction, physical injury, educational disruption, disciplinary problems, and substantial costs for schools and public-health systems.
7. Violated state consumer-protection, public-nuisance, fraud, products-liability, racketeering, and other laws.

JUUL denied intentionally targeting minors and disputed many allegations. It emphasized later changes such as ending certain advertising, withdrawing most flavored pods from U.S. retail channels, and strengthening age controls.

Claims against **Altria** alleged that it helped sustain and expand JUUL’s business through its investment, retail and distribution expertise, shelf-space arrangements, and access to cigarette customers, despite knowledge of the youth-vaping problem. Altria denied wrongdoing and argued that it had not controlled JUUL.

## Key people

- **Adam Bowen and James Monsees**: Stanford-trained co-founders of JUUL and its predecessor businesses.
- **Kevin Burns**: JUUL chief executive from 2017 until September 2019, during the company’s rapid growth and mounting scrutiny.
- **K.C. Crosthwaite**: Altria executive who replaced Burns as JUUL CEO in September 2019.
- **William H. Orrick III**: federal judge overseeing the JUUL MDL and approving the major private-plaintiff settlements.
- **Josh Stein**, North Carolina attorney general: led the first major state trial settlement in 2021.
- **Maura Healey**, then Massachusetts attorney general: brought an influential 2020 complaint based on internal marketing materials.
- **Letitia James**, New York attorney general, and **Rob Bonta**, California attorney general: prominent participants in the 2023 multistate settlement.
- **Brian King**, director of FDA’s Center for Tobacco Products from 2022: a key official during the separate FDA marketing-order proceedings.

## Main events and settlements

### 2018: Regulatory action and Altria investment

- On **April 24, 2018**, the FDA announced a nationwide enforcement initiative aimed at illegal sales of JUUL and other e-cigarettes to minors and demanded information from JUUL about youth use and product marketing.
- On **September 12, 2018**, the FDA called youth e-cigarette use an “epidemic” and required major manufacturers, including JUUL, to submit plans addressing underage use.
- In **November 2018**, JUUL announced that it would stop selling most flavored pods through ordinary retail outlets and shut down much of its U.S. social-media promotion.
- On **December 20, 2018**, Altria announced a **$12.8 billion investment for a 35% stake in JUUL**. The transaction later became central to antitrust proceedings and to plaintiffs’ theory that Altria assisted JUUL’s expansion.

### 2019–2020: Government suits and federal consolidation

- In **2019**, states including North Carolina, California, New York, and others began filing enforcement actions.
- On **October 2, 2019**, the federal Judicial Panel on Multidistrict Litigation created **MDL No. 2913** and assigned it to Judge Orrick in San Francisco.
- On **February 12, 2020**, Massachusetts filed a detailed complaint alleging that JUUL deliberately sought teenagers through youth-oriented websites, social-media campaigns, influencers, and imagery. The complaint became notable for quoting internal documents and identifying advertising placements and models allegedly selected to reach young audiences.
- The MDL grew to include thousands of personal-injury, consumer, school-district, local-government, and tribal claim
```
</details>

<details><summary><code>gpt-5.6-sol</code> — matter_recall bigthorium — 0/11; missed: John Maxwell (sales), Sarah Thompson (business development), Robert Williams (CFO), Emily Roberts (government relations), Laura Smith (procurement), Evelyn Archer (general counsel), Daniel Carter / Law Firm X, Howard Bass (city treasurer)</summary>

```
I do not know of any real, publicly documented bribery investigation involving “BigThorium” and the “City of Atlantis.” Those names appear fictional or anonymized, and Atlantis is not a real municipality.

Without a case name, jurisdiction, docket number, or source, I cannot reliably identify the parties, allegations, people, dates, or outcome without guessing.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id jebbush — hit</summary>

```
**Jeb Bush, Governor of Florida (1999–2007).**  

The description matches Bush’s two terms as Florida governor while his brother, George W. Bush, was President. His gubernatorial records became the publicly accessible “Jeb Bush Florida gubernatorial records” research collection. The listed controversies correspond to the 2000 Florida presidential-election recount; the Terri Schiavo litigation and “Terri’s Law”; the disappearance of foster child Rilya Wilson; Executive Order 04-08 ending affirmative-action preferences; and Florida’s Opportunity Scholarship voucher program, invalidated by the Florida Supreme Court in *Bush v. Holmes* (2006).
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id microsoft — hit</summary>

```
**United States v. Microsoft Corp. (the Microsoft antitrust case).**

It is modeled on the federal and state antitrust prosecution of Microsoft in the late 1990s. The government alleged Microsoft unlawfully maintained its Windows operating-system monopoly through practices involving Internet Explorer, including tying the browser to Windows and imposing restrictive licensing terms on PC manufacturers and software partners. Judge Thomas Penfield Jackson initially ordered Microsoft broken into separate operating-system and applications companies; the D.C. Circuit affirmed key monopoly-maintenance findings but vacated the breakup remedy in 2001. The matter was resolved by a consent decree later that year.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id veridian — no hit — template: Zimmer Biomet</summary>

```
**Zimmer Biomet Holdings, Inc. — the M2a Magnum Hip Implant Products Liability Litigation (MDL No. 2859, N.D. Indiana).**

The description matches Zimmer Biomet’s Warsaw, Indiana operations and its metal-on-metal **M2a Magnum** total hip system. The MDL alleged cobalt/chromium metallosis, adverse local tissue reactions, premature failures and revision surgeries, inadequate warnings, aggressive marketing to younger/more active patients, and surgeon-consultant payments. The system was FDA-cleared in March 2017 and reportedly discontinued/withdrawn in February 2024. The separate June 2022 recall involving acetabular-cup coating adhesion also aligns with Zimmer Biomet cup-component recalls.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id enron — hit</summary>

```
**Enron Corporation — the Enron securities-fraud litigation (e.g., *In re Enron Corp. Securities, Derivative & ERISA Litigation*).**

“Volteron” is plainly modeled on Enron: the 1999–December 2001 class period tracks Enron’s collapse; “prepay” commodity transactions and FAS 125/140 accounting refer to Enron’s off-balance-sheet financing/accounting practices; and the alleged document shredding at its headquarters mirrors Enron’s and Arthur Andersen’s destruction of records. The energy-market allegations describe Enron’s California electricity-market manipulation, including congestion-related scheduling strategies. The reference to an employee fantasy-football/NFL gambling ring also tracks allegations involving Enron employees. “New Searchland” appears to be a disguised stand-in for Houston, Texas.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id enron_k — hit</summary>

```
**The Deepwater Horizon oil-spill litigation (BP/Transocean/Halliburton), arising from the 2010 Macondo well blowout.**

The pleading is plainly modeled on lawsuits filed after the April 20, 2010 explosion, fire, and sinking of the *Deepwater Horizon* drilling rig in the Gulf of Mexico. The disguised defendants correspond to **BP p.l.c.** (well operator), **Transocean Ltd.** (rig owner/operator), **Halliburton** (cementing contractor), and likely **Cameron International** (blowout-preventer equipment). “New Searchland Resort & Spa” appears to stand in for a Gulf-coast hotel/resort business seeking classwide economic-loss damages from the spill. The altered date, rig name (“Bleak Horizon”), and Gulf name are anonymized substitutions for the Macondo/Deepwater Horizon disaster.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id mnk — hit</summary>

```
**Mallinckrodt plc (formerly Mallinckrodt Inc.)**, in the opioid litigation and bankruptcy proceedings, *In re Mallinckrodt plc*, Chapter 11 (D. Del.).

Mallinckrodt was headquartered in the St. Louis area before becoming an Irish-domiciled company. Its generics business was a major manufacturer of oxycodone, hydrocodone, and methadone tablets, while it marketed the branded extended-release hydromorphone drug **Exalgo**. It was sued in the federal opioid MDL and by numerous states over alleged failures in suspicious-order monitoring, use of chargeback data, opioid marketing, and DEA quota requests. In 2017 it entered a roughly **$35 million** DEA/DOJ settlement concerning suspicious-order reporting, and it later filed Chapter 11 in 2020, ultimately agreeing to a multibillion-dollar opioid settlement framework.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id worldcom — hit</summary>

```
**WorldCom, Inc. — the Bernard Ebbers fraud case.**

The description matches WorldCom’s 2002 accounting scandal, in which it improperly capitalized ordinary “line costs” to inflate earnings, ultimately restating approximately $11 billion. Internal auditor Cynthia Cooper helped uncover the fraud. CEO Bernard Ebbers, the Mississippi former basketball coach and motel operator, was convicted of securities fraud and related offenses and sentenced to 25 years. WorldCom filed the then-largest U.S. bankruptcy in July 2002, emerged as **MCI**, and was later acquired by **Verizon**.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id healthsouth — hit</summary>

```
**HealthSouth Corporation / Richard M. Scrushy — the HealthSouth accounting-fraud case.**

The description matches Birmingham, Alabama-based HealthSouth, then a major operator of outpatient surgery, rehabilitation, and diagnostic facilities. In 2003, following an FBI raid, the SEC alleged that HealthSouth had inflated earnings by roughly $1.4 billion, ultimately alleged at about $2.7 billion. Multiple CFOs participated in the scheme, calling themselves “the family,” and five pleaded guilty.

Founder and CEO Richard Scrushy was acquitted in 2005 of the HealthSouth securities-fraud charges, including prominent Sarbanes-Oxley certification-related allegations. He was later convicted in the separate Alabama governor bribery case involving former Gov. Don Siegelman.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id peregrine — hit</summary>

```
**Peregrine Systems, Inc. — the Peregrine accounting-fraud case involving former CEO Stephen R. Gardner.**

Peregrine Systems was a San Diego enterprise software company that disclosed in 2002 that it had improperly recognized roughly $500 million in revenue through contingent reseller transactions and undisclosed side agreements, while factoring related receivables. It restated results, replaced/dismissed auditors, entered Chapter 11, and sold its Remedy help-desk/software unit to BMC Software. Eight former executives were indicted in 2004; Gardner later pleaded guilty and was sentenced to eight years. Its chairman, John J. Moores, owned Major League Baseball’s San Diego Padres.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id mckesson_robbins — hit</summary>

```
**McKesson & Robbins, Inc. — the 1938 McKesson & Robbins fraud involving Philip Musica (alias F. Donald Coster).**

McKesson & Robbins’ president, Philip Musica, was a previously convicted fraudster operating as “F. Donald Coster.” He and associates, including brothers using assumed identities, fabricated approximately $19 million in inventory and accounts receivable through a nonexistent crude-drug operation. When the fraud was uncovered, Musica/Coster committed suicide. The scandal exposed the inadequacy of auditors’ reliance on management-provided records and led to the SEC’s landmark investigation and the auditing reforms associated with the McKesson & Robbins case—especially physical inventory observation and independent confirmation of receivables.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id equity_funding — hit</summary>

```
**Equity Funding Corporation of America; Raymond L. Dirks and *Dirks v. SEC*, 463 U.S. 646 (1983).**

The description tracks the 1973 collapse of Los Angeles-based Equity Funding, which fabricated large numbers of life-insurance policies, used computer-generated records and forged documentation, and sold purported reinsurance interests to other insurers. Its chairman, Stanley Goldblum, and numerous executives were prosecuted; the company entered bankruptcy, and its auditor, Haskins & Sells, faced litigation and regulatory scrutiny.

Former Equity Funding officer Ronald Secrist disclosed the fraud to securities analyst Raymond Dirks. Dirks investigated and alerted clients and the press, prompting trading before public disclosure. The SEC censured Dirks for aiding and abetting insider trading, but the Supreme Court reversed, holding that a tippee’s liability depends on whether the insider breached a fiduciary duty for personal benefit and whether the tippee knew or should have known of that breach.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id purdue — hit</summary>

```
**Purdue Pharma L.P. and the Sackler family — *Harrington v. Purdue Pharma L.P.* (2024).**

The description tracks Purdue Pharma, the Connecticut-based maker of OxyContin, launched in 1996 and promoted as less addictive because of its extended-release formulation. Purdue and three executives pleaded guilty in 2007 to felony misbranding and paid roughly $634.5 million. Purdue entered Chapter 11 in 2019 amid massive opioid litigation and pleaded guilty again in 2020. Its bankruptcy plan included releases shielding Sackler family members from opioid-related civil claims in exchange for a multibillion-dollar contribution; the U.S. Supreme Court invalidated those nonconsensual third-party releases in *Harrington v. Purdue Pharma L.P.*, 603 U.S. 204 (2024).
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id insys — hit</summary>

```
**Insys Therapeutics and its founder John Kapoor — the United States v. John Kapoor et al. prosecution.**

The drug was **Subsys**, a fentanyl sublingual spray approved for breakthrough cancer pain in opioid-tolerant cancer patients. Boston federal prosecutors alleged Insys used sham speaker programs and a reimbursement “reimbursement center” to induce and facilitate medically unnecessary prescriptions, including for non-cancer patients. In 2019, Kapoor and several executives were convicted of racketeering conspiracy; Kapoor, an Indian-born billionaire, was sentenced to **66 months (5½ years)**. The case also involved former sales executive **Alec Burlakoff**, associated with the notorious dose-titration rap video. Insys filed Chapter 11 shortly after reaching a major settlement with the U.S. government.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id rdc — hit</summary>

```
**Rochester Drug Cooperative (RDC), United States v. Rochester Drug Cooperative and former CEO Laurence Doud.**  

The description matches the April 2019 Southern District of New York prosecution of Rochester Drug Cooperative, a member-owned pharmaceutical wholesaler based in Rochester, New York. Prosecutors alleged RDC distributed massive quantities of oxycodone and fentanyl despite internal compliance warnings and failed to file required suspicious-order reports with the DEA. RDC entered a deferred-prosecution agreement and agreed to pay a $20 million penalty, then filed for bankruptcy in 2020. Former CEO **Laurence Doud** was charged and later convicted for narcotics-distribution conspiracy, while former compliance officer **Robert “Bob” K.** (commonly identified in reporting as RDC’s former compliance chief) pleaded guilty.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id clinton_email — hit</summary>

```
Hillary Clinton’s private email server controversy / FBI investigation into Clinton’s email practices.

It concerns Clinton’s use of a private server at her Chappaqua, New York home while serving as Secretary of State from 2009–2013. Roughly 30,000 work-related emails were provided to the State Department and released in FOIA batches, while another roughly 30,000 were characterized as personal and deleted. FBI Director James Comey announced on July 5, 2016 that the FBI would not recommend prosecution, though he described Clinton and her aides as “extremely careless.” On October 28, 2016, Comey notified Congress that the investigation was being revisited after emails were discovered on Anthony Weiner’s laptop, used by Clinton aide Huma Abedin; he announced on November 6 that the review had not changed the FBI’s conclusion.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id bridgegate — hit</summary>

```
**Kelly v. United States (2020), arising from the “Bridgegate” scandal involving New Jersey Governor Chris Christie’s administration and the Port Authority of New York and New Jersey.**

The borough was Fort Lee, New Jersey, whose access lanes to the George Washington Bridge were closed in September 2013. Christie deputy chief of staff Bridget Anne Kelly sent the email, “Time for some traffic problems in Fort Lee,” and Port Authority official David Wildstein carried out the purported traffic study; Port Authority executive Bill Baroni was also convicted. Wildstein pleaded guilty and testified. In *Kelly v. United States*, 590 U.S. 391 (2020), the Supreme Court unanimously held that the scheme was political retaliation rather than a scheme to obtain money or property, so it did not constitute federal wire fraud or program fraud.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id sony_hack — hit</summary>

```
**Sony Pictures Entertainment hack (2014), involving co-chair Amy Pascal and the film *The Interview*.**

The facts describe the November 2014 cyberattack on Sony Pictures Entertainment by the “Guardians of Peace,” which leaked internal emails, employee information, and unreleased films. U.S. authorities attributed it to North Korea in retaliation for *The Interview*, a comedy about assassinating Kim Jong-un. Sony initially withdrew the film’s theatrical release, prompting President Obama’s criticism. Amy Pascal resigned after leaked emails with producer Scott Rudin contained racially insensitive jokes about President Obama. Sony employees later brought data-breach litigation that was settled.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id depuy_asr — hit</summary>

```
**DePuy Orthopaedics, Inc. / the ASR Hip Implant litigation (In re DePuy Orthopaedics, Inc. ASR Hip Implant Products Liability Litigation).**

The matter concerns Johnson & Johnson subsidiary DePuy’s **ASR XL Acetabular System** and **ASR Hip Resurfacing System**, recalled worldwide in August 2010 after high failure and revision rates reported in the UK National Joint Registry. About 93,000 ASR devices had been implanted. Federal cases were centralized in the Northern District of Ohio, and the first bellwether, **Kransky v. DePuy Orthopaedics**, produced an approximately **$8.3 million** Los Angeles verdict in 2013. DePuy/J&J then announced a roughly **$2.5 billion** settlement program for thousands of patients requiring revision surgery.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id earplugs — hit</summary>

```
**3M Combat Arms Earplug Products Liability Litigation (MDL No. 2885), involving Aearo Technologies and 3M.**

The matter is modeled on 3M’s dual-ended Combat Arms Earplugs, Version 2 (CAEv2), supplied to U.S. military personnel from 2003–2015. The earplugs were alleged to be too short and prone to loosening, causing hearing loss and tinnitus. Competitor Moldex-Metric filed the False Claims Act whistleblower action; 3M/Aearo settled with the United States in 2018 for $9.1 million without admitting liability.

The ensuing veterans’ litigation became the massive Northern District of Florida MDL, *In re: 3M Combat Arms Earplug Products Liability Litigation*. After substantial bellwether verdicts, including a $77.5 million verdict, 3M attempted to use Aearo’s bankruptcy to channel claims, but that effort failed. In 2023, 3M announced a settlement valued at approximately $6 billion.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id bair_hugger — hit</summary>

```
**3M’s Bair Hugger multidistrict litigation (In re: Bair Hugger Forced Air Warming Devices Products Liability Litigation), involving inventor Dr. Scott Augustine.**

The description matches claims that 3M’s Bair Hugger forced-air warming blankets disrupted laminar airflow during orthopedic implant surgery and allegedly contributed to deep-joint/periprosthetic infections. Augustine invented Bair Hugger, sold the business that became part of 3M/Arizant, later promoted the competing HotDog conductive-fabric warming system, and was sued by 3M over allegedly false advertising. Roughly 6,000 cases were centralized in the District of Minnesota; the first bellwether, *McBroom v. 3M*, resulted in a 2018 defense verdict. Judge Joan Ericksen later excluded plaintiffs’ general-causation experts and entered summary judgment, but the Eighth Circuit reversed in 2021, and the Supreme Court denied certiorari.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id dalkon — hit</summary>

```
**A.H. Robins Company and the Dalkon Shield litigation** — especially *In re A.H. Robins Co.*, the Chapter 11 bankruptcy proceedings arising from Dalkon Shield claims.

The Dalkon Shield was a crab-shaped IUD marketed by A.H. Robins from 1971–1974. Its multifilament string was alleged to permit bacteria to ascend into the uterus, causing pelvic inflammatory disease, infertility, septic abortions, and deaths. The resulting litigation involved hundreds of thousands of claimants. A.H. Robins filed Chapter 11 in 1985; after its acquisition by American Home Products, it emerged through a plan establishing the Dalkon Shield Claimants Trust, funded at roughly $2.5 billion. The scandal was a major impetus for the Medical Device Amendments of 1976 and is commonly cited as a foundational mass-tort bankruptcy model.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id bhopal — hit</summary>

```
**Union Carbide Corporation / the Bhopal gas tragedy litigation (In re Union Carbide Corp. Gas Plant Disaster at Bhopal, India in December 1984), involving chairman Warren Anderson.**

The facts describe the 2–3 December 1984 methyl isocyanate gas leak at Union Carbide India Limited’s pesticide plant in Bhopal, Madhya Pradesh. Union Carbide was majority owner of UCIL; the New York federal case was dismissed on forum non conveniens grounds in 1986. India sued under the Bhopal Gas Leak Disaster (Processing of Claims) Act and reached the 1989 US$470 million settlement. Anderson was arrested, granted bail, left India, and died in 2014 while facing unresolved Indian criminal proceedings. In 2010, seven former UCIL officials were convicted of negligence.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id texaco_pennzoil — hit</summary>

```
**Pennzoil Co. v. Texaco Inc.** — the famous 1980s Getty Oil takeover litigation.

Pennzoil had reached an agreement in principle to acquire a controlling stake in Getty Oil from the Getty family interests, including the J. Paul Getty Museum. Texaco then made a higher offer and acquired Getty outright. Pennzoil sued Texaco in Texas for tortious interference with contract; the Houston jury awarded roughly $7.53 billion in actual damages and $3 billion punitive damages in 1985. Texaco’s inability to bond the judgment contributed to its 1987 Chapter 11 filing, after which it settled with Pennzoil for about $3 billion. Pennzoil’s lead lawyer was **Joe Jamail**, whose campaign contribution to Judge Anthony Farris became part of the controversy surrounding the judge’s replacement during trial.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id dieselgate — hit</summary>

```
**Volkswagen AG — the “Dieselgate” emissions-cheating scandal.**

In September 2015, the U.S. EPA and California regulators revealed that Volkswagen had used “defeat device” software in roughly 11 million diesel vehicles worldwide to recognize laboratory testing and reduce NOx emissions only during tests. CEO Martin Winterkorn resigned shortly afterward. Volkswagen later pleaded guilty in the United States and incurred more than $25 billion in U.S. penalties, settlements, and buybacks. The road-testing evidence originated with West Virginia University’s Center for Alternative Fuels, Engines and Emissions, funded by the International Council on Clean Transportation. Executive Oliver Schmidt was arrested at Miami International Airport in January 2017 and later sentenced to seven years in prison.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id theranos — hit</summary>

```
**Theranos, Elizabeth Holmes, and the Theranos fraud case.**

The description matches Theranos, the Silicon Valley blood-testing company founded by Stanford dropout Elizabeth Holmes. Theranos claimed its Edison device could perform many tests from a finger-prick sample, raised roughly $700 million, reached a reported $9 billion valuation, and partnered with Walgreens for in-store testing sites. John Carreyrou’s 2015 *Wall Street Journal* investigation relied on whistleblowers including former employee Tyler Shultz, grandson of director George Shultz, and revealed reliance on conventional machines and unreliable testing. Holmes was convicted in 2022 and sentenced to 11 years and 3 months; former president and partner Ramesh “Sunny” Balwani received a sentence of 12 years and 11 months.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id ftx — hit</summary>

```
**FTX Trading Ltd. and its founder, Sam Bankman-Fried — the United States v. Samuel Bankman-Fried case.**

The description tracks FTX’s November 2022 collapse after reporting on Alameda Research’s balance sheet triggered a liquidity crisis. Prosecutors alleged that billions in FTX customer funds were diverted to Alameda and used for investments, real estate, political contributions, and insider loans. Bankman-Fried, an MIT graduate associated with effective altruism, was extradited from the Bahamas, convicted in the Southern District of New York in 2023 on seven fraud/conspiracy counts after testimony from Caroline Ellison, Gary Wang, and Nishad Singh, and sentenced to 25 years in 2024. The FTX bankruptcy estate later proposed customer repayment at petition-date dollar values.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id near — hit</summary>

```
**Near Intelligence, Inc. — involving former CEO Anil Mathews and former CFO Ashish Parikh.**

The facts match Near Intelligence, the Pasadena-area location-data company with Singapore and India operations that went public through a March 2023 SPAC merger valued at roughly $1 billion. Near filed Chapter 11 in December 2023 after disclosing that prior financial statements were unreliable and terminating Mathews and Parikh for cause. SEC allegations described a purported round-trip revenue arrangement with Near’s major ad-tech customer, **MobileFuse**, involving payments from Near that returned as payments on sham invoices, overstating revenue by approximately 27%; the SEC also alleged Mathews charged rent for a luxury residence to Near as “professional services.”
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id meyer — no hit</summary>

```
**SEC v. Stable Road Capital LLC and Brian K. Lee** — a September 30, 2024 SEC enforcement action filed in the Southern District of New York.

The description tracks the SEC’s allegations against private-fund adviser Stable Road Capital and its CEO, Brian Lee: misuse of investor/fund assets, misleading account statements, coercive releases tied to reduced distributions, and failure to satisfy a capital call that caused loss of a roughly $3 million investment. The funds reportedly held interests in SpaceX and other late-stage private companies. The hypothetical’s “September 2026” date appears to be altered; the underlying matter was filed in 2024.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id endo — hit</summary>

```
**Endo International plc (including its subsidiary Endo Pharmaceuticals Inc.)**.

The description matches Endo’s reformulated extended-release oxymorphone product, **Opana ER**, which it marketed as abuse-deterrent/crush-resistant after a 2012 reformulation. The FDA requested Opana ER’s withdrawal in 2017 because of serious public-health harms associated with injection abuse, including HIV and thrombotic microangiopathy outbreaks. Endo became Irish-domiciled through its acquisition of Paladin Labs and owned generic-opioid businesses including **Par Pharmaceutical** and **Qualitest**. It was a defendant in the federal opioid MDL and state opioid litigation, entered Chapter 11 in 2022, and its subsidiary **Endo Health Solutions Inc.** pleaded guilty in 2024 to misbranding Opana ER.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id teva — hit</summary>

```
**Teva Pharmaceutical Industries Ltd.**  

The description matches Teva, the Israeli generic-drug giant that acquired Allergan’s generics business in 2016. Its branded fentanyl products included **Actiq** (the fentanyl “lollipop”) and **Fentora** (a buccal tablet), both alleged to have been promoted beyond breakthrough cancer pain. Teva was also a major generic supplier of oxycodone and hydrocodone, was a defendant in the federal opioid MDL bellwether litigation and California’s 2021 opioid bench trial, and reached a 2022 nationwide opioid settlement valued at up to roughly **$4.25 billion**, including cash payments and naloxone nasal-spray products.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id juul — hit</summary>

```
**Juul Labs, Inc. — the JUUL vaping litigation and settlements.**

The description matches Juul’s 2015 launch of its nicotine-salt pod vaporizer, flavored products, and youth-oriented social-media marketing. Juul rapidly captured roughly 75% of the U.S. e-cigarette market, and Altria bought a 35% stake in December 2018 at an approximately $38 billion valuation. Juul then faced extensive youth-vaping litigation, including federal MDL proceedings, school-district and state suits, and FDA marketing-denial action in 2022 that was later administratively stayed.

Juul agreed to major settlements, including a roughly $1.7 billion multistate/global resolution in 2022–23 and a separate $462 million settlement with six states and D.C. Altria substantially wrote down its Juul investment. Settlement terms also required Juul documents to be made publicly available through the University of California, San Francisco’s Industry Documents Library.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_id bigthorium — no hit — template: Johnson Controls / Milwaukee</summary>

```
**Johnson Controls / the City of Milwaukee energy-efficiency contract investigation** is the closest apparent model, though the description does not cleanly match a publicly reported case and may be a composite.

The clues resemble municipal “performance contracting” or energy-efficiency procurement controversies involving private energy-services companies, alleged gifts to local officials, consultants/intermediaries, and concerns that bid scoring was manipulated. However, I cannot identify a reported investigation matching all of the stated facts—particularly luxury watches for a city treasurer, an internal investigation led by the company’s general counsel, and no ensuing charges or litigation. It is therefore more likely a fictionalized or anonymized internal corporate investigation than a directly identifiable public case.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall veridian</summary>

```
I do not know of any real federal multidistrict litigation titled **In re Veridian Orthopedics ApexHip Products Liability Litigation, MDL No. 3102 (N.D. Ind.)**.

The caption appears likely to be fictional or mistaken. I cannot reliably identify:

- any manufacturer called **Veridian Orthopedics** associated with an **ApexHip** device;
- an MDL numbered **3102** in the Northern District of Indiana under that title;
- the plaintiffs, defendants, presiding judge, counsel, alleged device defects, bellwether proceedings, settlement, or final disposition.

Because I cannot verify that this matter exists, I should not invent parties, allegations, dates, or an outcome. If you have a docket citation, order, PACER link, or an alternate spelling/caption, I can help interpret it.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall microsoft — 15/16; missed: 'cut off Netscape's air supply' e-mails</summary>

```
**United States v. Microsoft Corp.** was the major federal antitrust case against Microsoft concerning its conduct in the market for personal-computer operating systems and web browsers. It was filed in 1998, tried before Judge Thomas Penfield Jackson, and ultimately resolved in 2001–2002 through a settlement imposing conduct restrictions rather than breaking up the company.

## Parties

- **Plaintiffs:**  
  - The **United States Department of Justice**, Antitrust Division.  
  - Initially **20 U.S. states and the District of Columbia** joined as plaintiffs; one state later withdrew, leaving 19 states and D.C. in the principal litigation.  
  - A group of “non-settling states” later continued to seek stronger remedies after the federal government and Microsoft reached a proposed settlement.

- **Defendant:**  
  - **Microsoft Corporation**, then the dominant supplier of PC operating systems through **Windows**.

## Core allegations and issues

The government alleged that Microsoft unlawfully maintained its monopoly in the market for Intel-compatible PC operating systems—principally Windows—under **Section 2 of the Sherman Act**.

The central theory was that Microsoft used its Windows monopoly to suppress the competitive threat posed by **Netscape Navigator** and **Sun Microsystems’ Java technologies**.

### Browser-related allegations

The government argued that Microsoft feared Netscape’s browser could become a cross-platform “middleware” layer: software that would allow developers to write applications less dependent on Windows. If applications could run through a browser or Java environment across multiple operating systems, Windows’ dominance could be weakened.

The complaint alleged that Microsoft responded through anticompetitive conduct, including:

- **Tying Internet Explorer to Windows:** Microsoft integrated or bundled its Internet Explorer browser with Windows and imposed restrictions that made it difficult for computer manufacturers to remove or hide it.
- **Restrictive OEM agreements:** Microsoft allegedly used licensing terms with PC manufacturers—known as OEMs—to discourage or limit promotion, installation, or prominent placement of Netscape Navigator and other competing software.
- **Exclusive or restrictive arrangements with Internet companies:** Microsoft made agreements with firms such as **America Online**, **Apple**, **Intuit**, and Internet access providers that allegedly reduced Netscape’s distribution opportunities.
- **Conduct directed at Java:** The government alleged Microsoft sought to undermine Sun’s cross-platform Java strategy by distributing a Microsoft-specific version of Java and encouraging developers to use Windows-dependent extensions.

The government also alleged attempted monopolization of the browser market, though the principal successful claim concerned unlawful maintenance of the Windows operating-system monopoly.

## Key people

- **Bill Gates** — Microsoft co-founder, chairman, and chief executive officer during much of the case. His videotaped deposition became a notable feature of the trial.
- **Steve Ballmer** — Microsoft president and later CEO; a senior Microsoft executive during the litigation.
- **David Boies** — Lead trial lawyer for the United States and the states. He conducted prominent examinations of Microsoft witnesses.
- **Joel I. Klein** — Assistant Attorney General heading the DOJ Antitrust Division when the case was filed.
- **Janet Reno** — U.S. Attorney General during the Clinton administration.
- **Judge Thomas Penfield Jackson** — U.S. District Judge for the District of Columbia who presided over the trial and initially ordered Microsoft’s breakup.
- **Richard A. Posner** — Judge of the U.S. Court of Appeals for the Seventh Circuit; he served as mediator during unsuccessful settlement discussions in 2000.
- **Judge Colleen Kollar-Kotelly** — District judge who handled the case on remand and approved the final consent decree.
- **Sun Microsystems** — Important nonparty industry participant whose Java technology was central to the middleware theory.
- **Netscape Communications Corp.** — Microsoft’s principal browser competitor; later acquired by AOL.

## Main events and dates

### 1990s background

- **1994:** The DOJ had already entered a consent decree with Microsoft concerning certain licensing practices. That earlier decree became relevant when the government later challenged Microsoft’s browser-related conduct.
- **1995:** Microsoft released Internet Explorer and began competing aggressively with Netscape Navigator.
- **1997:** The DOJ sought to enforce the 1994 decree against Microsoft over its requirement that PC makers distribute Internet Explorer with Windows 95. Judge Jackson initially issued a preliminary injunction, but the D.C. Circuit later ruled that the earlier decree did not prohibit Microsoft’s integration of Internet Explorer into Windows.

### Filing and trial

- **May 18, 1998:** The DOJ and 20 states plus the District of Columbia filed the principal antitrust complaint against Microsoft in the U.S. District Court for the District of Columbia.
- **October 19, 1998:** The bench trial began before Judge Jackson.
- **1998–1999:** The government presented evidence about Microsoft’s Windows licensing practices, browser distribution arrangements, dealings with Netscape and Java-related conduct, and internal Microsoft communications.

### District court findings and breakup order

- **November 5, 1999:** Judge Jackson issued **Findings of Fact**. He found that Microsoft possessed monopoly power in the market for Intel-compatible PC operating systems and had taken actions to protect that monopoly from middleware threats.
- **April 3, 2000:** Judge Jackson issued **Conclusions of Law**, holding that Microsoft had unlawfully maintained its operating-system monopoly in violation of Section 2 of the Sherman Act. He rejected some claims, including the government’s tying claim as framed under Section 1.
- **June 7, 
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall mnk — 9/21; missed: Exalgo (hydromorphone ER), suspicious order monitoring, chargeback data / downstream visibility, Florida pill mills, DEA production quota, Covidien spin-off (2013), Washington Post ARCOS data: ~28% of pills, Acthar Gel Medicaid-rebate matter (separate)</summary>

```
Mallinckrodt plc and certain affiliates were major defendants in the nationwide opioid litigation, principally in the federal multidistrict litigation, **In re National Prescription Opiate Litigation, MDL No. 2804**, pending before U.S. District Judge **Dan A. Polster** in the Northern District of Ohio. Mallinckrodt also faced numerous state-court suits, including actions by state attorneys general, counties, cities, tribes, hospitals, and other public entities.

## Parties and claims

### Defendants
The Mallinckrodt defendants generally included:

- **Mallinckrodt plc**, the parent company;
- **Mallinckrodt LLC** and related U.S. operating subsidiaries;
- **SpecGx LLC**, Mallinckrodt’s generic-drug business and a principal manufacturer/distributor of opioid products;
- In some pleadings, predecessor or affiliated entities connected with Mallinckrodt’s opioid business.

Mallinckrodt was primarily sued as a manufacturer and marketer of generic opioid pain medicines, including oxycodone, hydrocodone, morphine, fentanyl-related products, and other prescription opioids.

### Plaintiffs
The plaintiffs included:

- States and territories, through attorneys general;
- Counties, municipalities, and other local governments;
- Native American tribes;
- Hospitals and health systems in some related litigation;
- Other public entities seeking recovery for opioid-related public costs.

The MDL consolidated thousands of federal opioid cases. State actions proceeded separately in many jurisdictions, though Mallinckrodt’s bankruptcy ultimately centralized resolution of most governmental opioid claims through its restructuring plan.

### Core allegations
The governmental plaintiffs alleged that Mallinckrodt and other opioid manufacturers:

1. **Misrepresented the risks and benefits of prescription opioids**, including allegedly minimizing addiction risks and overstating long-term efficacy for chronic pain.
2. **Promoted or enabled excessive prescribing and distribution** of opioids.
3. **Failed to maintain effective controls against diversion**, despite allegedly suspicious ordering patterns and unusually large volumes of opioid shipments.
4. **Created or contributed to a public nuisance** and caused governments to incur substantial costs for addiction treatment, emergency response, law enforcement, child welfare, and other opioid-crisis consequences.
5. Violated state consumer-protection, false-advertising, controlled-substances, and related laws, depending on the jurisdiction.

Mallinckrodt disputed liability. Its position was generally that it sold FDA-approved medicines through regulated channels, that prescribing decisions were made by physicians, and that responsibility for the opioid crisis could not properly be assigned to it under the plaintiffs’ legal theories.

## Key people

- **Judge Dan A. Polster** — federal judge overseeing MDL 2804 in Cleveland. He pressed parties toward a nationwide settlement framework and supervised major opioid litigation proceedings.
- **Mark Trudeau** — Mallinckrodt’s president and chief executive officer during the 2020 bankruptcy and settlement period. He publicly described the restructuring as a means to resolve opioid-related liabilities while preserving the company’s operations.
- **Mark A. Goldsmith** — U.S. Bankruptcy Judge for the District of Delaware who confirmed Mallinckrodt’s Chapter 11 plan in 2022.
- **State attorneys general and local-government counsel** — led the governmental claims. The settlement structure gave substantial roles to state and local-government representatives in administering and allocating opioid-abatement funds.
- **The Official Committee of Unsecured Creditors and opioid claimants’ representatives** — played central roles in Mallinckrodt’s bankruptcy negotiations and plan confirmation process.

## Main events and timeline

### 2017–2018: Opioid suits begin and MDL is created
- In **2017**, state and local governments increasingly filed opioid suits against manufacturers, distributors, pharmacies, and others.
- On **December 5, 2017**, the Judicial Panel on Multidistrict Litigation created **MDL No. 2804**, *In re National Prescription Opiate Litigation*, in the Northern District of Ohio.
- Mallinckrodt became one of the manufacturer defendants in the MDL and faced parallel state-court litigation.

### 2018–2019: Government claims expand
- Thousands of governmental entities pursued claims against opioid-industry defendants.
- Mallinckrodt faced allegations tied both to its marketing/manufacturing conduct and to the volume of opioid products distributed through its business.
- The litigation proceeded amid broader settlement negotiations involving manufacturers, distributors, and pharmacies. Mallinckrodt’s financial condition became a major issue because of its opioid exposure and other liabilities.

### February 2020: Mallinckrodt announces proposed opioid settlement
- On **February 27, 2020**, Mallinckrodt announced an agreement in principle with a coalition of state attorneys general and plaintiffs’ lawyers.
- The proposed resolution contemplated approximately **$1.6 billion** in payments over time to resolve opioid claims, subject to bankruptcy-court approval and other conditions.
- The contemplated settlement also included a mechanism for opioid-abatement funding and releases for Mallinckrodt entities.

### October 2020: Chapter 11 filing
- On **October 12, 2020**, Mallinckrodt and numerous affiliates filed for Chapter 11 protection in the U.S. Bankruptcy Court for the District of Delaware.
- The bankruptcy filing was intended, in substantial part, to implement a global resolution of opioid litigation and other liabilities.
- The filing stayed many pending claims against the debtor entities and shifted the central fight from the MDL and state courts to the bankruptcy process.

### 2021: Settlement and plan negotiations
- Mallinckrodt negotiated with governmental opioid claimants, creditors, and other stakeholders over the term
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall enron — 16/20; missed: document shredding, prepay transactions with banks (Mahonia / JPMorgan / Citigroup), California energy-crisis trading schemes, Merrill Lynch Nigerian barge deal</summary>

```
## Overview

The Enron scandal was the collapse of Enron Corp., once one of the largest U.S. energy-trading companies, after revelations in 2001 that it had used complex off-balance-sheet partnerships and misleading accounting to conceal debt, inflate reported earnings, and mislead investors and employees. Enron filed for bankruptcy on December 2, 2001. Its collapse destroyed billions of dollars in shareholder value, wiped out many employees’ retirement savings, led to the dissolution of its auditor Arthur Andersen LLP, and produced major civil enforcement actions and criminal prosecutions.

The central criminal cases were brought by the U.S. Department of Justice, principally through the Enron Task Force, against Enron executives including Kenneth L. Lay, Jeffrey K. Skilling, Andrew S. Fastow, Richard A. Causey, and others.

---

## Principal parties and people

### Enron

- **Enron Corp.** — Houston-based energy company that evolved from a natural-gas pipeline business into an energy-trading and financial-services enterprise.
- **Kenneth L. Lay** — Enron founder and chairman; served as chief executive officer at various times, including again after Jeffrey Skilling resigned in August 2001.
- **Jeffrey K. Skilling** — Enron president and chief operating officer, later CEO from February 2001 until his resignation on August 14, 2001. He was associated with Enron’s aggressive trading and “asset-light” business model.
- **Andrew S. Fastow** — Enron chief financial officer from 1998 until October 2001. He created and managed many of the special-purpose entities central to the accounting scandal.
- **Richard A. Causey** — Enron chief accounting officer. He was involved in accounting decisions and financial disclosures.
- **Michael J. Kopper** — Senior Enron finance executive and Fastow lieutenant; participated in the partnership arrangements.
- **Ben F. Glisan Jr.** — Enron treasurer; involved in transactions involving Enron’s off-balance-sheet entities.
- **David B. Duncan** — Arthur Andersen’s lead audit partner on Enron.
- **Sherron Watkins** — Enron vice president who warned Lay in an August 2001 memorandum that Enron could “implode in a wave of accounting scandals.”
- **Clifford Baxter** — Former Enron vice chairman and senior executive. He resigned in May 2001 and died by suicide in January 2002.

### Arthur Andersen

- **Arthur Andersen LLP** — Enron’s outside auditor. Andersen audited Enron’s financial statements while also earning substantial consulting fees.
- Andersen personnel, including David Duncan, were accused of destroying Enron-related audit documents after the Securities and Exchange Commission began examining Enron’s accounting.

### Government and regulatory actors

- **U.S. Securities and Exchange Commission (SEC)** — Opened a formal investigation into Enron’s accounting in October 2001 and later brought civil enforcement actions.
- **U.S. Department of Justice (DOJ)** — Conducted criminal investigations and prosecutions through the Enron Task Force.
- **Federal Bureau of Investigation (FBI)** — Assisted in the criminal investigation.
- **Congress** — Held hearings in late 2001 and 2002, including Senate investigations into Enron’s accounting, corporate governance, and the role of banks and auditors.
- **U.S. Bankruptcy Court for the Southern District of New York** — Oversaw Enron’s Chapter 11 bankruptcy proceedings.

---

## Core allegations and issues

### 1. Off-balance-sheet partnerships and concealed debt

The central allegation was that Enron used special-purpose entities—often called SPEs—to move debt and poorly performing assets off Enron’s balance sheet while preserving the appearance of profitability and financial strength.

Important entities included:

- **LJM1 and LJM2** — Partnerships controlled by CFO Andrew Fastow. “LJM” referred to the initials of Fastow’s wife and children. Fastow managed these entities while serving as Enron’s CFO, creating an obvious conflict of interest.
- **Chewco Investments L.P.** — A partnership used in connection with Enron’s investment in a joint venture called **JEDI**. Chewco was structured so Enron could avoid consolidating JEDI’s debt and losses on Enron’s financial statements.
- **Raptors** — A series of SPEs used to hedge Enron’s investments in technology and other companies. The alleged problem was that the “hedges” were economically unsound because they were backed substantially by Enron stock or Enron-related assets. When Enron’s stock price fell, the hedges failed.

The government and SEC alleged that these structures were not independent enough to qualify for off-balance-sheet treatment and that Enron improperly avoided consolidating their losses and liabilities.

### 2. Misleading financial statements and earnings manipulation

Enron was accused of reporting misleading earnings, cash flow, debt levels, and shareholder equity. The company used aggressive accounting practices, including “mark-to-market” accounting, under which it booked estimated future profits from long-term contracts immediately rather than as cash was actually earned.

Mark-to-market accounting was not inherently illegal, but prosecutors and regulators alleged that Enron used unrealistic assumptions and manipulated valuations to create reported profits that did not reflect economic reality.

### 3. Misleading investors, employees, analysts, and lenders

Lay, Skilling, Causey, and others were accused of making materially false or misleading statements about Enron’s financial condition while insiders knew that the company faced serious problems.

A major issue was Enron executives’ public reassurance of investors while selling personal holdings of Enron stock. Employees, meanwhile, had substantial retirement-plan investments in Enron shares and faced restrictions on selling during a critical period in late 2001.

### 4. Auditor independence and document destruction

Arthur Andersen was accused of failing to act independently and of approving or toler
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall jebbush — 8/18; missed: One Florida (ending racial preferences), felon voter purge / disenfranchisement, James Crosby (corrections secretary) corruption, Elián González (2000), Lt. Governors Frank Brogan / Toni Jennings, class-size amendment (2002), Scripps Florida biotech deal, Stand Your Ground (2005)</summary>

```
Jeb Bush, a Republican and former Florida Commerce Secretary, served two terms as governor from January 5, 1999, to January 2, 2007. His administration was defined by conservative education reform, tax and spending restraint, aggressive child-welfare intervention after the death of a foster child, the 2000 presidential-election recount, hurricane disasters, and the Terri Schiavo right-to-die litigation.

## 1. The 2000 presidential-election recount

**Parties and people:**  
- Republican presidential nominee George W. Bush, Jeb Bush’s brother  
- Democratic nominee Vice President Al Gore  
- Florida Secretary of State Katherine Harris, a Republican  
- Florida Attorney General Bob Butterworth, a Democrat  
- Florida Supreme Court  
- U.S. Supreme Court  

**Issue:** Florida’s presidential vote was extraordinarily close. The outcome would decide the presidency.

**Main events:**  
- **November 7, 2000:** Election Day. Initial returns showed George W. Bush ahead in Florida by a tiny margin.  
- Florida law triggered an automatic machine recount. Gore sought manual recounts in several Democratic-leaning counties, especially Palm Beach, Broward, Miami-Dade, and Volusia.  
- Harris enforced statutory certification deadlines; Gore’s campaign challenged those decisions in court.  
- **December 8, 2000:** The Florida Supreme Court ordered a statewide manual recount of undervotes—ballots on which voting machines recorded no presidential vote.  
- **December 12, 2000:** In *Bush v. Gore*, the U.S. Supreme Court, by a 5–4 vote, halted the recount, holding that differing county standards for evaluating ballots violated equal-protection principles and that no constitutionally acceptable recount could be completed by the deadline.

**Bush’s role and controversy:**  
Jeb Bush was not a litigant and did not administer the recount; Harris and county election officials did. But because the disputed state was governed by the Republican brother of one candidate, Democrats and critics alleged an appearance of conflict or partisan influence. No court found that Jeb Bush had manipulated the vote count or recount process.

**Outcome:**  
George W. Bush was certified as Florida’s winner by **537 votes** and became president. The recount made Florida—and Jeb Bush’s governorship—central to one of the most consequential election disputes in U.S. history.

---

## 2. Education reform, vouchers, testing, and the “A+ Plan”

**Parties and people:**  
- Gov. Jeb Bush  
- Florida Legislature, generally Republican-controlled during his tenure  
- Florida Education Commissioner Charlie Crist, later governor  
- Teachers’ unions, especially the Florida Education Association  
- Public-school advocates and civil-liberties groups  
- Parents seeking vouchers or school-choice options  

**Issue:** Bush made education reform his signature domestic policy. His agenda emphasized statewide testing, school grades, accountability, charter schools, and vouchers for students assigned to failing public schools.

**Main events:**  
- **1999:** Bush and the Legislature enacted the **A+ Plan for Education**, creating an A–F grading system for public schools based heavily on Florida Comprehensive Assessment Test (FCAT) results.  
- Schools receiving repeated failing grades could trigger eligibility for the **Opportunity Scholarship Program**, allowing students to receive state-funded vouchers to attend private schools.  
- Bush also supported charter-school expansion and the **McKay Scholarship Program**, which gave vouchers to many students with disabilities to attend private schools.

**Controversies and allegations:**  
Critics argued that the system:
- Over-relied on standardized testing;
- Narrowed classroom instruction toward test preparation;
- Penalized schools serving poor, immigrant, and high-needs populations;
- Diverted public money to private and religious schools;
- Undermined public education and teachers’ unions.

Bush and supporters argued that the reforms created measurable accountability, exposed failing schools, gave parents leverage, and improved student performance over time.

**Court fight and outcome:**  
- In **2006**, the Florida Supreme Court struck down the Opportunity Scholarship Program in *Bush v. Holmes*. The court held that the voucher program violated the Florida Constitution’s requirement that the state provide a “uniform, efficient, safe, secure, and high quality system of free public schools.”  
- The ruling ended the statewide voucher program for students in failing schools.  
- Other school-choice programs, particularly the McKay scholarships for students with disabilities, remained in place.  
- Florida’s testing-and-accountability model remained influential and became a major part of Bush’s national political identity.

---

## 3. The Terri Schiavo case and “Terri’s Law”

**Parties and people:**  
- Terri Schiavo, a Florida woman in a persistent vegetative state after a 1990 cardiac arrest  
- Michael Schiavo, her husband and legal guardian  
- Robert and Mary Schindler, Terri’s parents  
- Gov. Jeb Bush  
- Florida Legislature  
- Florida courts, federal courts, and ultimately the U.S. Supreme Court  
- President George W. Bush and Congress, later involved in the federal phase  

**Issue:** Whether Terri Schiavo’s feeding tube should be removed. Michael Schiavo said Terri had expressed a wish not to be kept alive artificially under such circumstances. Her parents disputed that claim and sought continued treatment.

**Main events:**  
- Litigation over Terri Schiavo’s care had been ongoing since the 1990s. Courts repeatedly found that Michael Schiavo had authority as guardian and that evidence supported his claim about Terri’s wishes.  
- **October 15, 2003:** After a court-authorized removal of the feeding tube, the Republican-controlled Florida Legislature passed a special law commonly called **“Terri’s Law.”**  
- **October 21, 2003:** Gov. Bush signed the law, authorizing him to order the feedin
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall peregrine — 5/13; missed: John Moores (chairman, Padres owner), channel stuffing / side letters with resellers, ~$500 million revenue overstatement, factoring / selling receivables to banks, Remedy division sold to BMC, acquired by Hewlett-Packard (2005), 2004 indictments of eight executives, Gardner's eight-year sentence (2008)</summary>

```
Peregrine Systems, Inc. was a San Diego-based enterprise software company whose collapse became one of the major accounting-fraud cases of the early 2000s technology bust.

## Parties

- **Peregrine Systems, Inc.** — Publicly traded software company that sold asset-management, procurement, and enterprise-management software.
- **U.S. Securities and Exchange Commission (SEC)** — Brought civil securities-fraud and related accounting cases.
- **U.S. Department of Justice / U.S. Attorney’s Office for the Southern District of California** — Pursued criminal charges against former executives.
- **Former Peregrine executives**, principally:
  - **Stephen R. Gardner** — Peregrine’s founder, chairman, and chief executive officer.
  - **Gary J. Lauer** — Peregrine’s former president and chief operating officer.
  - **Matt G. Gless** — Peregrine’s former chief financial officer.
  - **Kevin J. O’Rourke** — Former executive vice president of worldwide sales.
  - **Other finance and sales personnel** were implicated in the company’s revenue-recognition practices.
- **Arthur Andersen LLP** — Peregrine’s outside auditor during the relevant period; Andersen’s audit work was scrutinized in the aftermath, though the central criminal cases focused on Peregrine personnel.

## Core allegations and accounting issues

The central allegation was that Peregrine materially **overstated revenue and earnings**, especially during roughly 1999 through 2002, by recording software-license revenue that did not qualify for recognition under applicable accounting rules.

The alleged practices included:

1. **Recognizing revenue before deals were complete**
   - Peregrine allegedly booked revenue before contracts were fully executed, before customers were obligated to pay, or before material contingencies had been resolved.

2. **“Side letters” and undisclosed concessions**
   - Sales personnel and executives allegedly used side agreements, oral promises, cancellation rights, payment extensions, return rights, or other concessions that undermined the apparent finality of reported sales.
   - These arrangements meant that purported sales often lacked the fixed, enforceable commitments needed for immediate revenue recognition.

3. **Round-trip or circular transactions**
   - The company was accused of using transactions involving customers, resellers, or business partners in ways that created the appearance of revenue without genuine economic substance or with undisclosed reciprocal arrangements.

4. **Improper quarter-end revenue**
   - The alleged fraud was particularly tied to pressure to meet quarterly revenue and earnings targets. Deals were reportedly pushed through near quarter-end and booked despite unresolved terms or inadequate documentation.

5. **Misleading public disclosures**
   - Peregrine’s financial statements and public statements allegedly portrayed the company as meeting growth and profitability expectations when its reported results were materially inflated.

The accounting problems became especially consequential because Peregrine had grown rapidly through acquisitions and was valued as a major enterprise-software company. When the revenue-recognition issues surfaced, the company’s reported financial performance could no longer be relied upon.

## Key people and roles

### Stephen R. Gardner
- Founder, chairman, and CEO.
- Prosecutors alleged that Gardner participated in or knew of improper revenue-recognition practices and made misleading statements to investors.
- He was one of the highest-profile defendants because he led the company during the period of aggressive growth and alleged accounting manipulation.

### Gary J. Lauer
- Former president and COO.
- Prosecutors alleged that Lauer was involved in the company’s improper revenue-recognition scheme and related misleading disclosures.
- He later became a central cooperating witness in the criminal proceedings.

### Matt G. Gless
- Former CFO.
- As finance chief, Gless was associated with the preparation and reporting of Peregrine’s financial results.
- He was charged in connection with the alleged accounting fraud and later resolved the criminal case through a guilty plea.

### Kevin J. O’Rourke
- Former executive vice president of worldwide sales.
- Prosecutors alleged that sales practices—including side agreements and improperly structured transactions—were integral to the false revenue reporting.
- He also entered a guilty plea.

## Main events and dates

### 1999–2002: Alleged fraud period
- Peregrine’s rapid expansion and acquisition strategy coincided with the alleged improper revenue-recognition practices.
- The government alleged that executives and employees caused the company to report revenue from transactions that were incomplete, contingent, or otherwise not properly recognizable.

### May 2002: Peregrine announces accounting problems
- On **May 6, 2002**, Peregrine announced that it expected to restate prior financial results because of accounting irregularities involving revenue recognition.
- The announcement triggered a severe market reaction and intensified regulatory and criminal scrutiny.

### June 2002: Bankruptcy filing
- On **June 10, 2002**, Peregrine filed for Chapter 11 bankruptcy protection.
- The filing followed the collapse in investor confidence, the inability to rely on prior financial statements, and the company’s liquidity and operational problems.

### 2003–2004: Criminal charges and guilty pleas
- Federal prosecutors brought criminal cases against former Peregrine executives.
- **Gary Lauer**, the former president and COO, pleaded guilty in **2004** to conspiracy and securities-fraud-related charges and agreed to cooperate with prosecutors.
- **Matt Gless**, the former CFO, and **Kevin O’Rourke**, the former worldwide sales executive, also pleaded guilty to charges arising from the scheme.

### 2005: Gardner trial and conviction
- In **2005**, Stephen Gardner was tried in federal court in San Diego.
- He was convi
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall mckesson_robbins — 7/13; missed: Price Waterhouse (auditor), crude drug department, fictitious Canadian warehouses (Montreal), Julian Thompson (treasurer) exposed it, auditing standards: observe inventory, confirm receivables, Bridgeport / Fairfield, Connecticut</summary>

```
The **McKesson & Robbins fraud** was a major American corporate-accounting scandal uncovered in late **1938**. It involved the pharmaceutical and chemical wholesaler **McKesson & Robbins, Inc.**, whose reported assets and profits had been massively inflated through fictitious subsidiaries, fake inventory, and forged accounts receivable.

## Parties

- **McKesson & Robbins, Inc.**  
  A large drug, chemical, and liquor wholesaler headquartered in New York. It was publicly traded and its securities were widely held.

- **Philip Musica**, operating under the name **F. Donald Coster**  
  The company’s president and controlling figure. “F. Donald Coster” was an assumed identity; Musica had a prior criminal history involving fraud and had used aliases.

- **The Musica family and associates**  
  Several relatives and associates participated in or benefited from the scheme, including **George Dietrich**, a Musica associate who was involved in the fictitious Canadian operation. Accounts of the scandal also identify Musica relatives as participants in the false-paper network and diversion of company funds.

- **Price, Waterhouse & Co.**  
  McKesson & Robbins’s outside auditors. The scandal became historically important because the auditors had confirmed receivables by correspondence but had not physically inspected purported inventories or independently verified the existence and operations of the supposed supplier.

- **Shareholders, creditors, and regulators**, including the **U.S. Securities and Exchange Commission (SEC)**  
  Investors and lenders relied on McKesson & Robbins’s financial statements. The SEC investigated after the fraud was exposed.

## Key allegations and issues

The central allegation was that Musica/Coster and his associates caused McKesson & Robbins to report assets and income that did not exist.

The fraud principally involved a purported Canadian supplier, commonly described as **W. W. Smith & Co.** The supposed company was used to create false transactions with McKesson & Robbins. Through it, the conspirators fabricated:

- **Inventory** that did not exist;
- **Accounts receivable** supposedly owed to McKesson & Robbins;
- **Sales and purchases** designed to make the company appear more profitable and financially sound than it was;
- Supporting documents, confirmations, and correspondence intended to deceive auditors and management.

The false assets were enormous for the period. The fraud is commonly described as involving roughly **$18 million to $19 million** in nonexistent inventory and receivables—an amount that materially distorted McKesson & Robbins’s balance sheet.

A major auditing issue was that Price, Waterhouse confirmed receivables through written communications sent to addresses controlled by the fraudsters. The auditors did not independently verify the purported supplier’s physical existence or inspect the alleged inventory. The scandal therefore became a landmark in the development of modern audit procedures, especially:

- direct confirmation of receivables with reliable third parties;
- physical observation or verification of inventory;
- greater professional skepticism;
- stronger auditor independence and responsibility for detecting material fraud.

## Key people

### Philip Musica / “F. Donald Coster”
- **Role:** President and dominant executive of McKesson & Robbins.
- **Conduct:** Used the Coster identity to conceal his past and gain control of the company. He orchestrated the false-vendor and false-asset scheme.
- **Background:** Musica had previously been associated with fraudulent business activity and had adopted aliases before becoming “F. Donald Coster.”

### George Dietrich
- **Role:** Associate of Musica and participant in the fictitious supplier operation.
- **Conduct:** Connected with the sham Canadian entity used to generate false confirmations and documentation.

### McKesson & Robbins directors and officers
- **Role:** Corporate management and board members responsible for the company’s governance.
- **Issue:** The scandal exposed failures of internal controls and board oversight. The company’s legitimate operations were substantial, but its leadership structure allowed Musica’s group to dominate key information and transactions.

### Price, Waterhouse & Co.
- **Role:** Independent public accountants/auditors.
- **Issue:** Their audit work became a focal point because they accepted documentary evidence and confirmations that were controlled by the perpetrators, without sufficient independent verification of inventory and counterparties.

## Main events and dates

- **1920s–early 1930s:**  
  Philip Musica, using aliases and eventually the name **F. Donald Coster**, built a business career despite a prior fraud-related background.

- **1930s:**  
  Musica/Coster gained control of McKesson & Robbins and became its president. During this period, the fictitious supplier arrangement and false accounting entries were used to inflate reported assets and earnings.

- **1938:**  
  The fraud began to unravel when questions arose about the company’s purported transactions and assets. Investigators and company personnel discovered that the alleged supplier and related assets were not genuine.

- **December 1938:**  
  The scandal became public. The company disclosed that large amounts of inventory and receivables shown on its books were fictitious.

- **December 16, 1938:**  
  **Philip Musica/F. Donald Coster died by suicide**, shooting himself as the fraud was being exposed and authorities closed in.

- **1939 and afterward:**  
  Investigations, litigation, and regulatory scrutiny followed. The SEC examined the affair, and the scandal became a leading example in accounting and auditing education.

## Outcome

Musica/Coster did not stand trial because he died by suicide in December 1938. Other participants and associates faced investigation and legal consequences, while McKesson & Robbins had to confront the financial damage, restate its pos
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall equity_funding — 9/14; missed: Fred Levin (executive VP), sold to reinsurers for cash, forged bonds / counterfeit securities, reorganised as Orion Capital, Goldblum and ~20 executives convicted</summary>

```
**Equity Funding Corporation of America (EFCA)** was the center of one of the largest U.S. corporate frauds of the early 1970s. The scandal became public in **March 1973** and involved the fabrication of thousands of life-insurance policies, false financial statements, and deception of auditors, reinsurers, investors, regulators, and lenders.

## Parties

- **Equity Funding Corporation of America**, a Los Angeles-based financial-services conglomerate.
  - Its principal insurance subsidiary was **Equity Funding Life Insurance Company**.
- **Company officers and employees** who participated in or concealed the fraud.
- **Independent auditors**, principally **Haskins & Sells** (later part of Deloitte), which audited Equity Funding’s financial statements.
- **Reinsurance companies**, which accepted purported portions of Equity Funding’s insurance risks and paid or became liable on claims tied to fictitious policies.
- **Investors, lenders, policyholders, and regulators**, including the **California Department of Insurance**, the **Securities and Exchange Commission (SEC)**, and federal prosecutors.

## Key allegations and issues

The central allegation was that Equity Funding’s management created a long-running scheme to make the company appear more profitable and financially sound than it was.

The fraud included:

1. **Fictitious life-insurance policies**
   - Employees created thousands of nonexistent policyholders and policies.
   - The company generated fake applications, policy records, premium notices, and other supporting documents.
   - These fake policies were used to report nonexistent premium income and insurance assets.

2. **Fraudulent reinsurance**
   - Equity Funding ceded portions of the purported insurance risks to reinsurers.
   - Because many underlying policies did not exist, reinsurers were induced to assume liabilities based on fabricated business.
   - In some instances, claims were made on fictitious insured persons, producing payments or obligations tied to nonexistent deaths and policies.

3. **False accounting and financial reporting**
   - The company overstated assets, income, policy reserves, and business volume.
   - It used fabricated records and manipulated data to support financial statements and deceive auditors and investors.
   - The fraud was aided by the company’s use of computerized records; employees reportedly generated false data and documents to make the fake insurance business appear legitimate.

4. **Securities fraud**
   - Equity Funding’s public disclosures and financial statements allegedly misrepresented the company’s condition.
   - Investors bought or held Equity Funding securities based on materially false information.

A major issue exposed by the case was the vulnerability of traditional auditing methods when management controls the underlying records and can manufacture convincing documentation, including computer-generated records.

## Key people

- **Stanley Goldblum** — Chairman and chief executive of Equity Funding. He was one of the principal figures associated with the fraud and was later criminally convicted.
- **Charles O. “Chuck” McCormick** — A senior Equity Funding executive, commonly identified as a central participant in the scheme. He became an important cooperating witness after the fraud began to unravel.
- **Raymond Dirks** — A securities analyst with the brokerage firm **Delafield Childs**. He was not an Equity Funding insider or participant in the fraud. He received information from a former Equity Funding officer and investigated the allegations, then told clients and other investors. His role later produced the landmark insider-trading case **Dirks v. SEC**.
- **Ronald Secrist** — A former Equity Funding officer who helped bring allegations to outside attention. He provided information concerning the fraud to Dirks.
- **Haskins & Sells** — Equity Funding’s outside auditor. The firm was criticized and sued over its failure to detect the fraud, though the scandal involved extensive falsification by company personnel.

## Main events and dates

### Before 1973: development of the scheme
During the late 1960s and early 1970s, Equity Funding grew rapidly through insurance and investment-related operations. According to later criminal cases and investigations, company management increasingly relied on fabricated insurance policies and false accounting entries to meet earnings expectations and conceal financial weakness.

### Early 1973: whistleblower disclosures and investigation
In **early 1973**, former executive **Ronald Secrist** gave analyst **Raymond Dirks** information alleging that Equity Funding had created fictitious insurance policies and falsified its books.

Dirks investigated by speaking with former employees and others connected to the company. He concluded that the allegations were credible and informed clients and other market participants. Some investors sold Equity Funding stock before the company’s collapse.

### March 1973: collapse becomes public
In **March 1973**, regulators and law-enforcement authorities moved against Equity Funding after the allegations gained traction. The company’s offices were searched and its records examined. The California insurance authorities took action against the insurance operation, and Equity Funding’s business effectively collapsed.

The revelation was that the company had allegedly created **tens of thousands of fictitious life-insurance policies**—often described in contemporary accounts as roughly **64,000** fake policies, though figures varied as investigators reconstructed the records.

### 1973 onward: criminal, civil, and regulatory proceedings
Federal criminal prosecutions followed against Goldblum and other executives and employees. Civil litigation also followed from investors, insurers, reinsurers, and others claiming losses caused by the fraud.

The scandal also led to litigation involving analyst Raymond Dirks. The SEC accused Dirks of aiding and abett
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall healthsouth — 10/13; missed: Sarbanes-Oxley certification charges, Ernst & Young (auditor), acquitted, June 2005</summary>

```
## HealthSouth accounting fraud (2003)

### Parties and core allegations

The central company was **HealthSouth Corporation**, a Birmingham, Alabama–based operator of rehabilitation hospitals, outpatient surgery centers, and other health-care facilities. Its founder, chairman, and chief executive was **Richard M. Scrushy**.

In March 2003, the **U.S. Securities and Exchange Commission (SEC)** and federal prosecutors alleged that HealthSouth had materially overstated its earnings and assets for years—ultimately by roughly **$2.7 billion**.

The alleged scheme was principally an accounting fraud designed to make HealthSouth appear to meet Wall Street earnings expectations. Prosecutors said senior finance personnel:

- Invented or inflated revenue and assets;
- Recorded false entries in HealthSouth’s books;
- Used relatively small false amounts spread across many accounts—often described as “**filling the gap**”—to avoid attracting attention;
- Used false asset entries sometimes referred to internally as “**AP summary**” accounts or “**dirt**”;
- Caused false financial statements and SEC filings to be issued.

The government alleged that Scrushy, as CEO, directed or knowingly participated in the fraud and benefited from it through compensation and stock sales. Scrushy denied knowing about the accounting manipulation and argued that subordinates had concealed it from him.

### Key people

- **Richard M. Scrushy** — HealthSouth founder, chairman, and CEO; the principal defendant in the criminal cases.
- **Aaron Beam** — HealthSouth’s first chief financial officer. He pleaded guilty and became a major prosecution witness against Scrushy.
- **William T. “Bill” Owens** — HealthSouth CFO after Beam; pleaded guilty and testified for the government.
- **Michael Vines** — HealthSouth CFO during part of the fraud period; pleaded guilty.
- **Weston Smith** — HealthSouth CFO from 1997 to 2002; pleaded guilty and testified against Scrushy.
- **Robert P. May** — appointed HealthSouth’s CEO after Scrushy was removed; led efforts to stabilize and restate the company.
- **U.S. Attorney’s Office / Department of Justice** — prosecuted the criminal cases.
- **SEC** — brought civil securities-fraud allegations and sought emergency relief against Scrushy and HealthSouth.

A striking feature of the case was that numerous former HealthSouth executives pleaded guilty—more than a dozen senior officers and finance employees in total—but Scrushy was acquitted in the principal accounting-fraud trial.

---

## Main events and dates

### Before 2003: alleged long-running fraud

Federal prosecutors alleged that the fraud began in the **mid-1990s** and continued into **2002**. HealthSouth grew rapidly through acquisitions and became one of the country’s largest health-care companies. Its reported profits and assets helped support its stock price and access to capital.

According to later guilty pleas and testimony, CFOs and other finance executives manipulated accounts when actual results fell short of projected earnings.

### March 2003: investigation becomes public

- **March 19, 2003:** The SEC filed a civil enforcement action against Scrushy and HealthSouth. The SEC accused Scrushy of orchestrating a massive accounting fraud and sought, among other relief, asset freezes and removal of Scrushy from control of the company.
- On the same day, federal authorities arrested Scrushy on criminal charges.
- HealthSouth’s board removed Scrushy as chairman and CEO.
- The company’s shares were delisted from the New York Stock Exchange shortly afterward.

The SEC’s initial complaint alleged that HealthSouth had overstated income by approximately **$1.4 billion**; the alleged total was later understood to be substantially larger, around **$2.7 billion**.

### 2003–2004: guilty pleas by former executives

A series of former HealthSouth finance executives pleaded guilty to charges including conspiracy, securities fraud, wire fraud, false statements, and related offenses. Several agreed to cooperate with prosecutors.

Their accounts generally described a fraud directed from the finance department and, according to the government, known to or encouraged by Scrushy. Scrushy maintained that the CFOs had acted without his knowledge and had falsely implicated him to obtain favorable plea agreements.

### 2005: Scrushy’s principal accounting-fraud trial and acquittal

Scrushy’s main criminal trial began in **January 2005** in federal court in **Birmingham, Alabama**, before U.S. District Judge **Karon O. Bowdre**.

The prosecution’s case relied heavily on testimony from former CFOs and other HealthSouth insiders, including Beam, Owens, and Smith. The government alleged that Scrushy pressured executives to meet earnings targets, participated in discussions about false numbers, and knew the company’s reported results were fabricated.

The defense emphasized that:

- Scrushy was not an accountant;
- HealthSouth was a large, decentralized company;
- The CFO witnesses were admitted criminals seeking reduced sentences;
- There was no decisive documentary evidence—such as a written instruction or recording—showing Scrushy ordered the accounting fraud.

- **June 28, 2005:** After a lengthy trial, a federal jury acquitted Scrushy on all **36 counts** in the principal HealthSouth accounting-fraud prosecution. The acquittal covered charges including conspiracy, securities fraud, wire fraud, mail fraud, and false-certification-related allegations.

The verdict did not mean the fraud had not occurred. Numerous HealthSouth executives had admitted it, and HealthSouth restated its financial results. Rather, the jury found the government had not proved beyond a reasonable doubt that Scrushy personally participated in or knew of the charged accounting fraud.

---

## The separate bribery case and conviction

Scrushy’s acquittal in the accounting case did not end his criminal exposure.

### Allegations

Federal prosecutors separately charged Scrushy and **Don 
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall worldcom — 13/14; missed: capitalised line costs</summary>

```
## Overview

The WorldCom accounting fraud was one of the largest corporate-accounting scandals in U.S. history. WorldCom, a telecommunications company based in Clinton, Mississippi, improperly recorded billions of dollars in ordinary operating expenses as capital investments. The manipulation made the company appear profitable when it was actually suffering major losses.

The scandal emerged publicly in June 2002, drove WorldCom into what was then the largest U.S. bankruptcy, led to criminal convictions of senior executives, civil enforcement actions by the Securities and Exchange Commission, and contributed to the climate that produced the Sarbanes-Oxley Act of 2002.

## Parties

- **WorldCom, Inc.** — The telecommunications company. It had grown rapidly through acquisitions, including MCI, and was one of the largest long-distance and data-network providers in the United States.
- **Bernard J. Ebbers** — WorldCom’s founder and chief executive officer. He was the central executive defendant in the criminal case.
- **Scott D. Sullivan** — WorldCom’s chief financial officer. He directed or participated in the accounting manipulations and later pleaded guilty and cooperated with prosecutors.
- **David F. Myers** — WorldCom’s controller. He pleaded guilty and cooperated with the government.
- **Buford Yates Jr.** — WorldCom’s director of general accounting. He pleaded guilty.
- **Arthur Andersen LLP** — WorldCom’s outside auditor during much of the relevant period. Andersen’s auditing work was heavily criticized; its broader collapse was already underway because of the Enron scandal.
- **U.S. Securities and Exchange Commission (SEC)** — Brought civil securities-fraud proceedings against WorldCom and later pursued settlements and remedies.
- **U.S. Department of Justice / federal prosecutors** — Prosecuted Ebbers and other executives criminally.
- **WorldCom shareholders, bondholders, employees, and customers** — Major victims of the collapse. Thousands of employees lost jobs, and investors suffered enormous losses.
- **MCI, Inc.** — The name adopted by the reorganized company after WorldCom emerged from bankruptcy.

## Core accounting fraud

### The principal scheme: “line costs” capitalized as assets

WorldCom paid other telecommunications carriers for access to their networks. These payments—often called **line costs**—were ordinary recurring operating expenses. Under proper accounting, they should have been recorded immediately as expenses, reducing reported income.

Instead, beginning principally in 2001 and continuing into 2002, WorldCom personnel improperly transferred billions of dollars of line costs from expense accounts to capital-asset accounts. This was commonly described as **capitalizing line costs**.

Capitalizing the costs had two immediate effects:

1. It reduced WorldCom’s reported expenses in the current period.
2. It inflated reported profits and assets.

The company then depreciated the falsely created “assets” over time, spreading the expense into future periods rather than recognizing it when incurred.

### Other manipulations

WorldCom also used improper accounting entries involving reserves—sometimes called “cookie jar” reserves—to boost earnings. The company released or adjusted reserves in ways that helped it meet Wall Street earnings expectations.

The central allegation was not merely that WorldCom made aggressive accounting judgments. Prosecutors and regulators alleged that senior executives knowingly caused false entries to be made to conceal declining revenue and profitability and to maintain the appearance that WorldCom was meeting analysts’ expectations.

## Key people and roles

### Bernard Ebbers — CEO

Ebbers founded WorldCom and served as its CEO. Prosecutors alleged that he pressured subordinates to meet earnings targets and participated in a broader scheme to mislead investors about WorldCom’s financial condition.

A significant issue at trial was whether Ebbers personally knew of and directed the specific accounting entries. The government’s case relied heavily on testimony from former executives, especially CFO Scott Sullivan, as well as evidence of Ebbers’s intense focus on meeting earnings expectations and his financial dependence on WorldCom’s stock price.

Ebbers had also received hundreds of millions of dollars in loans and guarantees from WorldCom. Those arrangements heightened concerns about conflicts of interest and his incentive to preserve the company’s market value.

### Scott Sullivan — CFO

Sullivan was WorldCom’s chief financial officer and the government’s principal insider witness against Ebbers. He admitted participating in the fraud, pleaded guilty, and testified that Ebbers knew about and supported efforts to meet earnings targets through improper accounting.

Sullivan’s cooperation was central to the prosecution’s case against Ebbers.

### David Myers — Controller

Myers, the controller, participated in the improper accounting and pleaded guilty. He cooperated with prosecutors and testified about the mechanics of the entries and the pressure within the company to achieve financial targets.

### Buford Yates Jr. — Director of General Accounting

Yates was involved in recording the improper entries. He pleaded guilty to conspiracy and securities-fraud-related charges.

### Cynthia Cooper — Vice President of Internal Audit

Cynthia Cooper led WorldCom’s internal-audit team. Her team discovered suspicious accounting entries and pursued the investigation despite resistance and pressure within the company.

Cooper and her colleagues found that billions of dollars in line costs had been improperly capitalized. Their work was crucial to exposing the fraud. Cooper later became widely recognized as a leading corporate whistleblower.

### Arthur Andersen — Outside auditor

Arthur Andersen audited WorldCom’s financial statements during relevant periods. Andersen faced scrutiny over whether it had adequately tested WorldCom’s accounting and d
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall rdc — 10/12; missed: suspicious orders: ~8,300 flagged, 4 reported, Judge George Daniels</summary>

```
The criminal case against Rochester Drug Co-operative, Inc. (“RDC”) and its longtime chief executive, Laurence F. Doud, was a major federal opioid-distribution prosecution in the Southern District of New York. It centered on allegations that RDC, one of the nation’s largest pharmaceutical distributors, knowingly failed to report suspicious opioid orders and thereby helped fuel unlawful diversion of prescription opioids.

## Parties

- **United States of America** — prosecuted the case through the U.S. Attorney’s Office for the Southern District of New York, working with the DEA and other federal investigators.
- **Rochester Drug Co-operative, Inc. (RDC)** — a Rochester, New York-based pharmaceutical wholesaler and drug distributor. RDC distributed controlled substances, including oxycodone and fentanyl products, to pharmacies.
- **Laurence F. Doud** — RDC’s president and chief executive officer. He had led the company for decades and was the principal individual defendant.
- **William Pietruszewski** — RDC’s former chief compliance officer. He was charged separately and became an important cooperating witness against Doud and RDC.

## Core allegations and legal issues

Federal prosecutors alleged that, from roughly **2012 through 2016**, RDC and Doud violated the Controlled Substances Act by failing to maintain an effective system for detecting and reporting suspicious orders of controlled substances.

The government’s central theory was that RDC:

- Distributed very large quantities of opioid pills, particularly **oxycodone**, to pharmacies whose ordering patterns were plainly suspicious.
- Failed to report suspicious orders to the DEA as required by federal law.
- Continued supplying pharmacies despite warning signs such as unusually large orders, sharp increases in purchases, orders disproportionate to a pharmacy’s legitimate business, and pharmacies located in areas with little apparent medical need for the volume of opioids ordered.
- Used compliance procedures that were ineffective or manipulated to avoid reporting suspicious orders.
- In some instances, allegedly shipped opioids after employees had identified concerns about the customer or order.

The indictment alleged that Doud personally participated in and directed aspects of the conduct. Prosecutors said he knew RDC’s compliance system was inadequate, resisted reporting suspicious orders because reporting could jeopardize sales, and helped conceal or minimize suspicious-order concerns.

The charges included conspiracy and substantive Controlled Substances Act offenses involving the failure to report suspicious orders. The case was notable because it treated a major drug distributor’s alleged compliance failures as criminal conduct, rather than solely as a civil or administrative regulatory matter.

## Key events and dates

### April 23, 2019 — Charges announced

Federal prosecutors announced criminal charges against RDC and Doud.

The government alleged that RDC had distributed millions of oxycodone tablets to pharmacies with suspicious ordering patterns and had failed to report those orders to the DEA. The announcement described RDC as one of the country’s largest pharmaceutical distributors and emphasized that its alleged failures contributed to opioid diversion.

Doud was arrested and charged in connection with the alleged scheme.

### April 2019 — RDC enters a deferred-prosecution agreement

At the same time the charges were announced, RDC entered into a **deferred-prosecution agreement (DPA)** with the U.S. Attorney’s Office.

Under the agreement, RDC:

- Admitted to a detailed statement of facts concerning its failures to report suspicious opioid orders.
- Agreed to pay a **$20 million criminal penalty**.
- Agreed to cooperate with the government and strengthen its controlled-substance compliance program.
- Agreed to oversight and compliance obligations, including an independent monitor.
- Faced dismissal of the criminal charges if it complied with the agreement’s terms during the deferral period.

The DPA did not resolve the case against Doud personally.

### 2019 — Pietruszewski pleads guilty and cooperates

**William Pietruszewski**, RDC’s former chief compliance officer, pleaded guilty to a federal charge arising from the suspicious-order reporting scheme. He agreed to cooperate with prosecutors.

His role was significant because he had been responsible for compliance functions at RDC and could testify about internal warnings, company practices, and Doud’s knowledge and involvement.

### 2020–2021 — Doud’s case proceeds toward trial

Doud contested the charges. The litigation involved disputes over the scope of the Controlled Substances Act’s suspicious-order reporting requirements, Doud’s knowledge and intent, and the admissibility and significance of RDC’s internal compliance evidence.

The government’s case depended heavily on evidence that Doud was not merely an executive detached from compliance operations, but was aware of suspicious-order problems and participated in decisions that allowed opioid shipments to continue.

### March 2022 — Doud pleads guilty

On **March 4, 2022**, Laurence Doud pleaded guilty in federal court in Manhattan.

He pleaded guilty to **conspiring to distribute controlled substances unlawfully**, based on RDC’s failure to report suspicious opioid orders to the DEA. In pleading guilty, Doud admitted that he participated in the company’s failure to report suspicious orders as required.

The plea avoided a trial.

### September 2022 — Doud is sentenced

On **September 9, 2022**, U.S. District Judge **Jed S. Rakoff** sentenced Doud to **27 months in federal prison**.

The sentence also included:

- **Three years of supervised release** after imprisonment; and
- A **$100,000 fine**.

Judge Rakoff rejected arguments for a noncustodial sentence and treated the offense as serious because of the role that unlawful opioid distribution and diversion played in the opioid crisis.

## Outcome

### R
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall insys — 14/15; missed: 'titration' rap video</summary>

```
The Insys Therapeutics/Subsys racketeering matter was a major federal criminal prosecution arising from the marketing of **Subsys**, a fentanyl spray approved only for breakthrough cancer pain in opioid-tolerant patients.

## Parties

- **United States Department of Justice / U.S. Attorney’s Office for the District of Massachusetts** prosecuted the case.
- **Insys Therapeutics, Inc.**, an Arizona-based pharmaceutical company, manufactured and sold Subsys.
- Key individual defendants included:
  - **John N. Kapoor** — Insys founder, former executive chairman, and controlling shareholder.
  - **Michael Babich** — Insys president and chief executive officer.
  - **Alec Burlakoff** — Insys vice president of sales.
  - **Richard Simon** — former national director of sales.
  - **Sunil Bhatt** — former vice president of sales.
  - **Joseph Rowan** — former regional sales director.
  - **Andrew Davenport** — former regional sales director.
  - **David Torres** — former sales representative.
- Other Insys employees and physicians were involved in related prosecutions, guilty pleas, or cooperation agreements, including former sales representatives and doctors accused of accepting speaker-program payments.

## Core allegations and issues

Federal prosecutors alleged that Insys executives and sales personnel operated a racketeering conspiracy to increase Subsys prescriptions and revenue through illegal means.

The central allegations were:

1. **Bribing and paying kickbacks to prescribers**
   - Insys allegedly used purported “speaker programs” as a vehicle to pay doctors to prescribe more Subsys.
   - Prosecutors said many programs were sham events: little or no educational content occurred, attendance was fabricated or minimal, and doctors were paid honoraria tied in practice to their prescribing volume.
   - The government alleged that physicians were rewarded for prescribing Subsys, including for patients who did not have cancer.

2. **Promoting Subsys for medically inappropriate and off-label use**
   - Subsys was FDA-approved for breakthrough pain in cancer patients already tolerant to opioids.
   - Prosecutors alleged Insys pushed it for non-cancer pain patients and encouraged prescribing beyond the approved indication.
   - Sales representatives were accused of targeting high-volume pain-management doctors and encouraging aggressive prescribing.

3. **Defrauding insurers and pharmacy-benefit managers**
   - Insys allegedly maintained a reimbursement-support operation, often called the “reimbursement center,” that contacted insurers and pharmacy-benefit managers to obtain prior authorization.
   - Prosecutors alleged employees misrepresented patients’ diagnoses, cancer status, opioid tolerance, or medical need in order to secure coverage.
   - The alleged fraud enabled prescriptions that insurers otherwise might have denied.

4. **Racketeering conspiracy**
   - The government charged that the bribery/kickback scheme and insurance-fraud scheme formed an enterprise-wide racketeering conspiracy under the federal RICO statute.
   - The prosecution portrayed the conduct as directed from senior management, not merely isolated misconduct by sales representatives.

## Key people and roles

### John Kapoor
Kapoor founded Insys and served as executive chairman. Prosecutors alleged he was a central leader of the scheme and that he pushed sales growth while approving or tolerating the speaker-program and reimbursement practices used to drive prescriptions.

### Michael Babich
Babich was Insys’s CEO and president. He pleaded guilty before trial and cooperated with the government. His testimony was important to the prosecution’s effort to show that senior executives knew of and participated in the unlawful sales strategy.

### Alec Burlakoff
Burlakoff was vice president of sales and one of the government’s principal witnesses after pleading guilty. He testified about the sales culture, the use of speaker fees to influence doctors, and management’s focus on prescription volume.

### Richard Simon
Simon, the former national director of sales, was among the executives convicted at trial. Prosecutors alleged he helped oversee and implement the sales practices at issue.

### Sunil Bhatt
Bhatt, a former vice president of sales, was convicted at trial. The government alleged he participated in the speaker-program kickback scheme and the broader effort to increase Subsys prescribing.

### Joseph Rowan and Andrew Davenport
Rowan and Davenport were former regional sales directors. Both were convicted at trial for their roles in the alleged racketeering conspiracy and related conduct.

### David Torres
Torres, a former sales representative, was convicted at trial. The government alleged he participated in the speaker-program scheme and efforts to induce prescriptions.

## Main events and timeline

### 2012–2015: Alleged scheme period
During the principal period described by prosecutors, Insys rapidly expanded Subsys sales. The government alleged that the company used paid speaker programs, sales pressure, and reimbursement-center practices to obtain prescriptions and insurance coverage.

### December 2016: Federal charges against Insys executives
On **December 8, 2016**, federal authorities announced charges against Kapoor and several Insys executives and sales personnel in Massachusetts. The charges included racketeering conspiracy, conspiracy to commit mail and wire fraud, and conspiracy to violate the Anti-Kickback Statute.

The case was notable because Kapoor was described as the first pharmaceutical-company CEO charged in connection with a nationwide opioid-marketing scheme of this kind.

### 2017–2018: Guilty pleas and cooperation
Several former Insys employees pleaded guilty, including Babich and Burlakoff. Their cooperation gave prosecutors insider testimony about company practices and executive decision-making.

### January–May 2019: Trial and convictions
The principal trial began in **January 2019** in fed
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall clinton_email — 13/15; missed: Platte River Networks / Datto, FOIA litigation (Judicial Watch) / monthly releases</summary>

```
The Hillary Clinton private e-mail server controversy concerned Hillary Rodham Clinton’s use of a privately maintained e-mail system while she was U.S. Secretary of State, rather than a State Department e-mail account. It became a major political and legal issue during her 2016 presidential campaign and led to an FBI investigation.

## Parties and institutions

- **Hillary Rodham Clinton** — U.S. Secretary of State from January 21, 2009, to February 1, 2013; Democratic presidential candidate in 2016.
- **U.S. Department of State** — The agency whose records-management and classified-information rules were implicated.
- **Federal Bureau of Investigation (FBI)** — Conducted the criminal investigation.
- **U.S. Department of Justice (DOJ)** — Had authority over any prosecution decision.
- **James B. Comey** — FBI Director from 2013 to 2017; publicly announced the FBI’s conclusions in July and October 2016.
- **Loretta E. Lynch** — U.S. Attorney General during the investigation; accepted the FBI/DOJ decision not to prosecute.
- **Patrick F. Kennedy** — State Department under secretary for management; a senior official involved in discussions later examined by the FBI concerning classification markings.
- **Cheryl Mills** — Clinton’s chief of staff at the State Department and later a lawyer/adviser; involved in handling Clinton-related records.
- **Huma Abedin** — Clinton aide and longtime adviser; her e-mails and devices became relevant to the late-2016 reopening announcement.
- **Anthony Weiner** — Then-separated husband of Abedin; his laptop was seized in an unrelated investigation, leading the FBI to discover e-mails potentially relevant to the Clinton matter.
- **David Petraeus** — Former CIA director whose separate mishandling-of-classified-information case was frequently cited by critics as a comparison.

## Core allegations and issues

The controversy involved several overlapping questions:

1. **Use of a private server and personal e-mail account**
   - Clinton used the address **hdr22@clintonemail.com** and a private server located at her residence in Chappaqua, New York, for official State Department communications.
   - Critics argued this avoided normal government recordkeeping, transparency, and archival procedures.
   - Clinton said the arrangement was permitted at the time and was adopted partly for convenience—using one device/account rather than separate personal and official systems.

2. **Federal records preservation**
   - Federal officials are required to preserve official records.
   - After leaving office, Clinton provided approximately **30,000 e-mails** that she and her lawyers identified as work-related to the State Department in December 2014.
   - About **31,000 additional e-mails** were characterized as personal and deleted. Critics questioned whether all official records had been properly retained and produced.

3. **Handling of classified information**
   - The central criminal-law issue was whether classified information had been improperly transmitted, stored, or handled through the private system.
   - The FBI found that some e-mails contained information that was classified at the time they were sent or received, including material later determined to contain highly classified information.
   - Clinton and her supporters emphasized that none of the e-mails was marked classified when sent in the manner ordinarily used to identify classified material. Critics argued that officials can still be responsible for recognizing sensitive information even without markings.

4. **Potential violations of statutes governing national-defense information**
   - The FBI examined whether Clinton or others had acted with the criminal intent or extreme negligence necessary for prosecution under statutes concerning mishandling of classified or national-defense information.
   - The FBI ultimately concluded that the evidence did not support a criminal case against Clinton or her aides.

## Main events and dates

### 2009–2013: Clinton’s tenure as Secretary of State

- **January 21, 2009:** Clinton became Secretary of State.
- During her tenure, she used a private e-mail server for official and personal communications.
- **February 1, 2013:** Clinton left office.

### 2014–early 2015: Records dispute becomes public

- **December 2014:** Clinton’s representatives delivered roughly 30,000 work-related e-mails to the State Department.
- **March 2, 2015:** The New York Times reported that Clinton had exclusively used a personal e-mail account on a private server for official business as Secretary of State.
- **March 10, 2015:** Clinton held a press conference at the United Nations, saying she had used one device for convenience and had turned over work-related e-mails. She said she had not sent or received classified material on her private account.
- **March 2015:** The House Select Committee on Benghazi, already investigating the September 11, 2012 Benghazi attacks, sought Clinton-related e-mails and helped intensify scrutiny of the server.
- **March 2015:** The State Department’s inspector general referred the matter to the FBI after reviewing e-mails that appeared potentially classified.

### July 2015: FBI investigation formally announced

- **July 7, 2015:** The FBI publicly confirmed that it was investigating the “potential mishandling of classified information” connected with Clinton’s private e-mail arrangement.
- The investigation examined the server, e-mails, devices, and the conduct of Clinton and her aides.

### 2016: Interviews and FBI conclusion

- **July 2, 2016:** Clinton was interviewed by the FBI for approximately three and a half hours.
- **July 5, 2016:** FBI Director James Comey made an unusual public statement describing the FBI’s findings.
  - Comey said the FBI had found **110 e-mails in 52 e-mail chains** containing information classified at the time they were sent or received.
  - He said **eight chains** contained “Top Secret” information at the time, **3
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall purdue — 13/16; missed: MDL 2804 / Judge Polster, McKinsey's role / settlement, Dopesick / Empire of Pain</summary>

```
## Overview

Purdue Pharma L.P., maker of the prescription opioid OxyContin, became one of the central defendants in U.S. opioid litigation. The company and members of the Sackler family, who owned and controlled Purdue, were accused of helping fuel the opioid epidemic through deceptive marketing, inadequate controls against diversion and abuse, and continued promotion of opioids despite evidence of widespread addiction and overdose deaths.

The litigation culminated in Purdue’s 2019 Chapter 11 bankruptcy and a proposed settlement under which the Sackler family would contribute billions of dollars in exchange for broad releases from civil opioid claims. In June 2024, the U.S. Supreme Court rejected the bankruptcy plan because it released nondebtor Sackler family members from opioid-related claims without the consent of affected claimants. Purdue’s bankruptcy remained pending afterward, with mediation and negotiations continuing.

---

## Principal parties

### Purdue Pharma

**Purdue Pharma L.P.** and affiliated entities were privately held pharmaceutical companies headquartered in Stamford, Connecticut. Their best-known product was **OxyContin**, an extended-release oxycodone painkiller introduced in 1996.

Purdue was controlled by branches of the **Sackler family**, descendants of brothers Arthur, Mortimer, and Raymond Sackler. Arthur Sackler died in 1987, before OxyContin was introduced; the principal family members associated with Purdue during the OxyContin era were descendants of **Mortimer Sackler** and **Raymond Sackler**.

### The Sackler family

The Sacklers were not generally debtors in Purdue’s bankruptcy. That distinction became legally decisive.

Key figures included:

- **Richard Sackler** — former Purdue president and board member; son of Raymond Sackler. He was a prominent figure in litigation allegations concerning Purdue’s opioid marketing strategy.
- **Raymond Sackler** — Purdue co-owner and longtime board member; died in 2017.
- **Mortimer Sackler** — Purdue co-owner; died in 2010.
- **David Sackler** — Purdue board member and descendant of Raymond Sackler.
- **Theresa Sackler** — widow of Raymond Sackler and Purdue board member.
- Other Sackler family members and trusts were included in proposed releases and settlement arrangements.

The family denied wrongdoing and maintained that Purdue’s medicines were approved by the Food and Drug Administration and prescribed by physicians.

### Government and private claimants

Major claimants included:

- The **United States Department of Justice**, including federal prosecutors.
- The **Drug Enforcement Administration** and other federal agencies.
- **State attorneys general**, including Massachusetts Attorney General Maura Healey, New York Attorney General Letitia James, Connecticut Attorney General William Tong, and others.
- Thousands of **cities, counties, tribes, hospitals, insurers, and individuals** alleging opioid-related harms.
- The **Official Committee of Unsecured Creditors** in Purdue’s bankruptcy.
- A committee representing **personal-injury claimants**, including people with opioid-use disorder and families of people who died from overdoses.
- The **U.S. Trustee**, a Justice Department component that challenged the Sackler releases in the bankruptcy plan.

---

## Core allegations and legal issues

### Alleged deceptive marketing of OxyContin

The central allegation was that Purdue marketed OxyContin in ways that understated its addiction risks and overstated its safety, efficacy, and resistance to abuse.

Claimants alleged that Purdue:

- Promoted OxyContin as less addictive, less prone to abuse, or safer than other opioids.
- Emphasized a “12-hour” dosing claim even when some patients experienced pain relief for shorter periods, potentially leading to withdrawal symptoms, escalating doses, or more frequent use.
- Encouraged physicians to prescribe opioids for chronic, non-cancer pain.
- Targeted high-volume prescribers and continued sales efforts despite warning signs that certain doctors or pharmacies were associated with inappropriate prescribing or diversion.
- Failed adequately to monitor suspicious orders and distribution patterns.
- Used sales representatives, educational programs, and promotional materials to influence prescribing practices.

The allegations were not limited to Purdue’s conduct. Plaintiffs also alleged that Sackler family members exercised substantial control over Purdue, received large distributions from the company, and should be held personally accountable for conduct connected to the opioid crisis.

### Fraudulent-transfer and asset-removal allegations

A major issue in the bankruptcy was whether the Sacklers had removed billions of dollars from Purdue before its bankruptcy filing.

States and other claimants alleged that the Sacklers extracted approximately **$10 billion or more** from Purdue over roughly a decade, leaving the company unable to satisfy opioid liabilities. The Sacklers disputed that characterization and argued that distributions were lawful and that they had not caused Purdue’s insolvency.

The proposed settlement required Sackler family members to contribute billions of dollars, but it also sought to protect them from present and future civil opioid claims.

### The nonconsensual third-party release issue

The most important legal issue by 2024 was whether a bankruptcy court could approve a plan that released the Sacklers—who had not themselves filed for bankruptcy—from opioid-related claims without every claimant’s consent.

The proposed plan would have:

- Dissolved Purdue as a privately owned company.
- Created a successor public-benefit entity, later called **Knoa Pharma**, to produce opioid-use-disorder treatments and other medicines.
- Directed billions of dollars to opioid-abatement efforts and claimant compensation.
- Required Sackler contributions.
- Granted Sackler family members broad releases from civil claims related to Purdue and opioids.

Opponents
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall bridgegate — 14/15; missed: Mastro / Gibson Dunn internal report</summary>

```
## Overview

The Fort Lee lane closure scandal—commonly called **“Bridgegate”**—arose from the September 2013 closure of local-access lanes leading from **Fort Lee, New Jersey**, onto the **George Washington Bridge**, which connects New Jersey to Manhattan. Prosecutors alleged that the closures were ordered as political retaliation against Fort Lee’s Democratic mayor, **Mark Sokolich**, because he had declined to endorse Republican Governor **Chris Christie** for reelection.

The scandal led to federal criminal convictions of two Christie allies, although the U.S. Supreme Court unanimously overturned those convictions in 2020. Christie was never charged.

## Principal parties and people

- **Chris Christie** — Republican Governor of New Jersey from 2010 to 2018. His administration and political circle were central to the controversy. He denied knowing about the lane closures in advance and was not criminally charged.

- **Mark Sokolich** — Democratic mayor of Fort Lee. Prosecutors said he was the intended political target because he did not endorse Christie’s 2013 reelection campaign.

- **Bridget Anne Kelly** — Christie’s deputy chief of staff. She sent the now-famous August 13, 2013 email: **“Time for some traffic problems in Fort Lee.”** She was convicted in 2016, but her convictions were later overturned by the Supreme Court.

- **Bill Baroni** — Deputy executive director of the **Port Authority of New York and New Jersey**, the bi-state agency that operates the George Washington Bridge. A Christie appointee. He was convicted in 2016; the Supreme Court later overturned his convictions.

- **David Wildstein** — A Christie political ally and Port Authority official, serving as director of interstate capital projects. He pleaded guilty in 2015 and testified for the government against Kelly and Baroni.

- **David Samson** — Chairman of the Port Authority and a Christie ally. He was not charged in the Bridgegate case itself, though he later pleaded guilty in a separate federal bribery-related matter involving United Airlines.

- **Jamie Fox** — Executive director of the Port Authority during the closures. He resigned in December 2013 amid the scandal.

- **Patrick Foye** — Executive director of the Port Authority’s New York side. He ordered the lanes reopened after concluding that the purported traffic study was improper and dangerous.

- **United States v. Kelly and Baroni** — The federal criminal case that ultimately reached the U.S. Supreme Court as **Kelly v. United States**, 590 U.S. ___ (2020).

## The alleged scheme

Fort Lee had three dedicated local-access toll lanes feeding traffic onto the upper level of the George Washington Bridge. Normally, those lanes were reserved for Fort Lee commuters.

Federal prosecutors alleged that Kelly, Wildstein, and Baroni arranged to reduce Fort Lee’s dedicated access from three lanes to one, falsely presenting the action as a traffic study. The alleged real purpose was to punish Mayor Sokolich for failing to support Christie politically.

The closures caused severe gridlock in Fort Lee. Residents, school buses, commuters, and emergency responders were delayed. The disruption became a major public scandal once internal emails and texts emerged.

## Main events and dates

### 2013

- **August 13, 2013** — Bridget Kelly emailed David Wildstein:  
  **“Time for some traffic problems in Fort Lee.”**  
  Wildstein replied: **“Got it.”**

- **September 9, 2013** — The lane reconfiguration began. Two of Fort Lee’s three dedicated local-access lanes were closed, leaving one lane. Port Authority personnel publicly described the change as part of a traffic study.

- **September 9–13, 2013** — Fort Lee experienced extraordinary congestion. The closures disrupted local traffic, school transportation, and emergency services.

- **September 13, 2013** — Patrick Foye ordered the lanes restored, ending the closures after four days.

- **December 2013** — The controversy intensified after reports and documents suggested the “traffic study” explanation was pretextual. Jamie Fox resigned as Port Authority executive director.

### 2014

- **January 8, 2014** — Christie held a lengthy press conference, saying he had been misled by members of his staff and declaring that he had no prior knowledge of the closures. He announced Kelly’s firing and said he was “embarrassed and humiliated” by the conduct.

- **January 9, 2014** — David Wildstein resigned from the Port Authority.

- **January 2014 onward** — New Jersey legislative investigations and federal investigations examined the closures, the Christie administration, and Port Authority conduct.

### 2015

- **January 2015** — David Wildstein pleaded guilty in federal court to conspiracy charges. He admitted participating in the retaliatory lane-closure scheme and agreed to cooperate with prosecutors.

- **May 2015** — A federal grand jury indicted Bridget Kelly and Bill Baroni. The indictment alleged wire fraud, federal-program fraud, conspiracy, and related offenses. The theory was that they used Port Authority resources—including bridge lanes, employee labor, and toll-related operations—for a political punishment scheme.

### 2016

- **November 4, 2016** — After a federal trial in Newark, New Jersey, a jury convicted Kelly and Baroni on multiple counts, including conspiracy, wire fraud, and federal-program fraud.

  Wildstein was the government’s principal cooperating witness. He testified that the closures were political retaliation directed at Mayor Sokolich and that Kelly and Baroni knew the traffic-study explanation was false.

### 2017–2019

- **March 2017** — Baroni was sentenced to two years in prison; Kelly was sentenced to 18 months. Their prison terms were delayed while they appealed.

- **November 2018** — The U.S. Court of Appeals for the Third Circuit largely upheld their convictions, though it vacated certain counts and ordered resentencing.

- **June 2019** — The U.S. Supreme Court agreed to hear the
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall sony_hack — 10/15; missed: January 2015 sanctions on North Korea, WikiLeaks published the archive (April 2015), employee class action settled (~$8m), Park Jin Hyok indicted (2018), Spider-Man / Marvel, Jolie e-mails</summary>

```
## Overview

The 2014 Sony Pictures Entertainment hack was a major cyberattack against Sony Pictures Entertainment (SPE), the Hollywood film and television subsidiary of Sony Corporation. Attackers calling themselves the **“Guardians of Peace” (GOP)** infiltrated Sony’s computer systems, stole and publicly released large quantities of confidential data, destroyed or disabled internal systems, and threatened violence against theaters showing Sony’s comedy film **_The Interview_**.

The U.S. government publicly attributed the attack to **North Korea**, concluding that the operation was retaliation for _The Interview_, a film depicting a fictional assassination of North Korean leader **Kim Jong Un**. North Korea denied responsibility, though it praised the attack and described it as a “righteous deed.”

The incident led Sony to cancel the film’s planned wide theatrical release temporarily, then release it through selected theaters and online platforms. It also became a major U.S. cybersecurity and foreign-policy event, prompting sanctions against North Korean entities and individuals.

---

## Parties

### Sony Pictures Entertainment
- **Sony Pictures Entertainment (SPE)** was the direct victim.
- SPE was led at the time by **Michael Lynton**, chairman and chief executive officer.
- **Amy Pascal** was co-chair of SPE and a prominent figure in the leaked emails.
- SPE’s parent company was **Sony Corporation**, then led by **Kazuo Hirai**.

### The attackers: “Guardians of Peace”
- The attackers identified themselves as the **Guardians of Peace**, or GOP.
- They claimed responsibility for the intrusion, theft, destruction of data, and later threats directed at theaters.
- The group demanded that Sony stop releasing _The Interview_ and made broader claims about Sony’s business practices, though its public messaging shifted over time.

### North Korea
- The U.S. government concluded that the **Government of North Korea** was responsible.
- The FBI said the attack involved North Korean government-linked actors and cited technical evidence, including malware similarities, infrastructure links, and operational connections to earlier North Korean cyber activity.
- North Korea’s government denied conducting the hack but condemned _The Interview_ and praised the attackers.

### The United States government
- The **Federal Bureau of Investigation (FBI)** led the public U.S. attribution.
- The **White House**, under President **Barack Obama**, condemned the attack and criticized Sony’s initial decision to cancel the film’s release.
- The **U.S. Treasury Department** imposed sanctions on North Korean entities and officials in January 2015.

### Theaters and distributors
- Major theater chains—including **AMC Theatres**, **Cinemark**, **Regal Entertainment Group**, and **Carmike Cinemas**—declined to show _The Interview_ after the GOP’s threats.
- Sony ultimately arranged a limited theatrical release through independent theaters and a digital release through platforms including **Google Play, YouTube Movies, Xbox Video, and Sony’s own online channels**.

---

## Key allegations and issues

### 1. Destructive cyberattack and theft of confidential information
The attackers penetrated Sony Pictures’ network and stole a vast amount of internal material. The leaked data included:

- Employee personal information, including Social Security numbers, salaries, and medical-related information;
- Internal emails;
- Unreleased films and screeners;
- Contracts and business plans;
- Financial records;
- Information about actors, executives, and employees;
- Passwords and other internal network material.

The attack was not merely a data theft. Sony computers displayed a threatening image from the GOP, and the company’s internal systems were severely disrupted. Employees reportedly had to use paper, whiteboards, and personal devices while Sony rebuilt systems.

### 2. Retaliation over _The Interview_
The central political allegation was that the attack was intended to stop the release of _The Interview_, directed by **Seth Rogen** and **Evan Goldberg** and starring **James Franco** and Rogen.

The film portrayed a fictional plot in which two American journalists are recruited to assassinate Kim Jong Un. North Korea had objected publicly to the film before the hack, calling it an act of “war” and urging the United States to prevent its release.

The GOP eventually demanded that Sony withdraw the film and threatened theaters that showed it.

### 3. Threats of violence against theaters
On **December 16, 2014**, the GOP issued a message invoking the September 11 attacks and warning theaters against showing _The Interview_. The threat stated, in substance, that theaters showing the film should expect danger and advised people to stay away.

No attack occurred. U.S. authorities later said they had no credible intelligence of a specific plot against theaters, but the threats caused major exhibitors to pull out.

### 4. Privacy, employment, and corporate-governance fallout
The leaks exposed private communications and compensation information, causing reputational damage to Sony and individuals mentioned in the emails. They also triggered lawsuits by current and former Sony employees alleging that Sony failed to adequately protect their personal information.

The incident became a prominent example of the risks posed by inadequate cybersecurity controls, destructive malware, employee-data exposure, and the use of cyberattacks to influence speech and commercial distribution.

---

## Key people

### Sony executives

- **Michael Lynton** — Chairman and CEO of Sony Pictures Entertainment. He was one of the principal executives managing Sony’s response.
- **Amy Pascal** — Co-chair of Sony Pictures Entertainment. Leaked emails between Pascal and producer **Scott Rudin** included racially insensitive jokes about President Obama. The controversy contributed to Pascal’s departure from her leadership role in 2015.
- **Kazuo Hirai** — P
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall depuy_asr — 10/14; missed: ~93,000 implanted, Pinnacle sibling litigation (Dallas), Australian registry / 2009 withdrawal there, Warsaw, Indiana</summary>

```
## Overview

The DePuy ASR litigation arose from the worldwide recall of two metal-on-metal hip replacement systems made by DePuy Orthopaedics, Inc., a Johnson & Johnson subsidiary:

- **ASR XL Acetabular System** — a total hip replacement component.
- **ASR Hip Resurfacing System** — a resurfacing implant, generally used in younger and more active patients.

On **August 24, 2010**, DePuy announced a global recall of both systems after unusually high early failure and revision-surgery rates. The litigation alleged that the implants’ design caused excessive wear, release of cobalt and chromium metal debris, tissue damage, pain, loosening, dislocation, and premature failure.

## Parties

### Defendants

The principal defendants were:

- **DePuy Orthopaedics, Inc.**
- **Johnson & Johnson**, DePuy’s parent company.
- In some cases, related Johnson & Johnson entities and distributors were also named.

### Plaintiffs

Plaintiffs were patients who received ASR implants, and in some cases their spouses asserting loss-of-consortium claims. They brought individual suits and class or consolidated actions in U.S. federal and state courts, as well as litigation abroad.

The federal cases were centralized in multidistrict litigation:

- **In re DePuy Orthopaedics, Inc. ASR Hip Implant Products Liability Litigation**
- **MDL No. 2197**
- U.S. District Court for the **Northern District of Ohio**
- Presiding judge: **Judge David A. Katz**

## Key allegations and issues

Plaintiffs generally alleged that the ASR devices were defectively designed and that DePuy and Johnson & Johnson failed to adequately warn doctors and patients about known risks.

Major allegations included:

1. **Defective design**
   - The ASR cup was alleged to have a shallow design and inadequate coverage angle, making it prone to instability, edge loading, excessive wear, loosening, and dislocation.
   - Plaintiffs contended that the metal-on-metal articulation generated excessive cobalt and chromium debris.

2. **Metallosis and tissue injury**
   - Wear debris could enter surrounding tissue and the bloodstream.
   - Plaintiffs alleged injuries including metallosis, inflammation, pseudotumors, tissue necrosis, bone loss, pain, impaired mobility, and systemic metal-ion concerns.

3. **Premature failure and revision surgery**
   - The implants allegedly failed far earlier than patients were led to expect, requiring painful and expensive revision surgeries.
   - DePuy’s recall notice stated that approximately **12 percent** of ASR hip recipients required revision surgery within five years, though plaintiffs argued the true failure rate was higher in some populations and registries.

4. **Failure to warn and concealment**
   - Plaintiffs alleged DePuy knew or should have known from internal data, complaints, registry information, and surgeon reports that the ASR system had an unacceptable failure rate.
   - Claims commonly included failure to warn, negligence, strict products liability, breach of warranty, fraud or misrepresentation, and consumer-protection violations.

5. **Regulatory issues**
   - The ASR XL system entered the U.S. market through the FDA’s **510(k)** clearance process, which permits marketing based on substantial equivalence to an existing device rather than requiring the full premarket-approval process.
   - The ASR resurfacing device had a more complicated regulatory history and was not broadly approved for U.S. sale in the same manner as the XL total-hip component. Litigation nevertheless focused heavily on the alleged safety problems common to the ASR design.

## Key people

- **Judge David A. Katz** — federal judge overseeing the ASR multidistrict litigation in the Northern District of Ohio.
- **Andrew D. Ekdahl** — then president of DePuy Orthopaedics; he was associated with DePuy’s public response to the recall.
- **Johnson & Johnson and DePuy executives, engineers, and medical personnel** — their internal communications, complaint data, design decisions, and knowledge of failure rates became central subjects in discovery and trials.
- **Individual plaintiffs in bellwether trials**, including:
  - **Loren Kransky**, whose 2013 California trial produced a major plaintiff verdict.
  - **Helen Strum**, whose 2014 federal MDL bellwether trial produced a defense verdict.
  - **Ann McCracken**, whose 2014 federal MDL bellwether trial produced a major plaintiff verdict.

## Main events and timeline

### Before the recall

- **2003–2005:** DePuy introduced ASR hip products in various markets. The ASR XL acetabular component was marketed in the United States after FDA 510(k) clearance.
- **2008–2010:** Reports accumulated of early failures, elevated metal-ion levels, pain, loosening, and revision surgeries. National joint registries outside the United States, particularly in the United Kingdom and Australia, reported concerning revision rates for metal-on-metal hips, including ASR devices.

### 2010 recall

- **August 24, 2010:** DePuy announced a **worldwide recall** of the ASR XL Acetabular System and ASR Hip Resurfacing System.
  - DePuy advised surgeons and patients that the devices had a higher-than-expected revision rate.
  - The company offered to cover certain medical costs associated with monitoring and revision surgery, but that program did not resolve all claims for pain, lost wages, future medical care, or other damages.

### Federal consolidation

- **December 2010:** The U.S. Judicial Panel on Multidistrict Litigation centralized federal ASR cases in the Northern District of Ohio as **MDL No. 2197**, before Judge Katz.
- Thousands of lawsuits were filed in federal court, state courts, and foreign jurisdictions.

### Early major trial result

- **March 2013:** In **Kransky v. DePuy Orthopaedics, Inc.**, a California state-court jury awarded **Loren Kransky** approximately **$8.3 million** in compensatory damages.
  - Kransky had received an ASR XL implant and later underwent revision surgery.
  - The jury fo
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall bair_hugger — 10/14; missed: Gareis bellwether defence verdict (May 2018), certiorari denied (2022), 3M v. Augustine false-advertising suit (Lanham Act), ~5,000-6,000 cases</summary>

```
## Bair Hugger Forced-Air Warming MDL (MDL No. 2666)

**In re: Bair Hugger Forced Air Warming Products Liability Litigation**, MDL No. 2666, was centralized in the **U.S. District Court for the District of Minnesota** in 2015. It concerned claims that 3M’s Bair Hugger forced-air surgical warming system caused deep-joint infections in patients undergoing hip or knee replacement surgery.

### Parties

- **Plaintiffs:** Thousands of patients, generally recipients of hip or knee arthroplasty procedures, who alleged they developed serious infections after surgery in which a Bair Hugger warming device was used.
- **Defendants:** Primarily:
  - **3M Company**
  - **Arizant Healthcare Inc.**, the original manufacturer of Bair Hugger products, acquired by 3M in 2010.
  - Related 3M entities were also named in various cases.

The Bair Hugger system uses a heater/blower unit and disposable blanket to circulate warmed air around a surgical patient to prevent hypothermia.

### Core allegations and issues

Plaintiffs alleged that the forced-air warming system could draw contaminated air from the operating-room floor or other areas into the device, then release warmed air that disrupted the operating room’s ultraclean downward airflow. According to the plaintiffs’ theory, this could carry bacteria into the surgical field and cause **periprosthetic joint infections**—deep infections involving an artificial hip or knee implant.

The principal claims included:

- **Design defect:** The forced-air design allegedly created a risk of contamination and surgical-site infection.
- **Failure to warn:** Plaintiffs alleged that 3M and Arizant failed to adequately warn surgeons, hospitals, and patients of the asserted infection risk.
- **Negligence and strict products liability**
- **Breach of warranty**
- In some cases, claims involving alleged concealment or misrepresentation of safety information.

3M denied that Bair Hugger caused the infections. Its central position was that the devices were safe, effective, FDA-cleared, widely used, and supported by clinical evidence. 3M also argued that plaintiffs could not reliably establish general causation—that Bair Hugger devices are capable of causing the infections alleged—or specific causation in individual patients.

A major scientific dispute involved whether laboratory airflow studies and certain clinical literature supported the plaintiffs’ theory that forced-air warming disrupted laminar airflow enough to increase infection risk. The defense emphasized that infection after joint replacement has many potential causes and that epidemiological evidence did not establish a causal association between Bair Hugger use and deep-joint infection.

### Key people

- **Judge Joan N. Ericksen**, U.S. District Judge for the District of Minnesota, presided over the MDL for much of its central litigation and issued important expert-evidence rulings.
- **Dr. Scott D. Augustine**, an anesthesiologist and former Arizant executive, was a prominent figure in the controversy. He helped develop the Bair Hugger system but later became associated with a competing warming technology, the **HotDog** conductive warming system. Plaintiffs relied in part on his criticisms of forced-air warming.
- **Dr. Robert McMurray**, an orthopedic surgeon and one of the plaintiffs’ principal causation experts, offered opinions linking Bair Hugger use to surgical-site and periprosthetic joint infections. His testimony became central to the Daubert litigation.
- **3M and Arizant personnel** were involved in discovery concerning product design, testing, marketing, adverse-event information, and communications about infection-risk concerns.

### Major events and timeline

- **2010:** 3M acquired Arizant Healthcare, the Bair Hugger manufacturer.
- **December 2015:** The Judicial Panel on Multidistrict Litigation centralized federal Bair Hugger cases in the District of Minnesota as **MDL No. 2666**.
- **2016–2018:** The parties conducted extensive discovery, including discovery concerning device design, airflow testing, infection literature, regulatory history, internal company documents, and expert testimony.
- **2019:** Judge Ericksen issued significant **Daubert** rulings excluding or limiting key plaintiff expert opinions on general causation. The court concluded that the plaintiffs’ proposed expert testimony did not meet the required reliability standards under Federal Rule of Evidence 702 and *Daubert*.
- **2019:** Following the exclusion of critical causation evidence, the court granted summary judgment for 3M in a group of bellwether cases. Without admissible expert evidence establishing that Bair Hugger could cause the alleged infections, plaintiffs could not prove causation.
- **2020:** The U.S. Court of Appeals for the Eighth Circuit affirmed important rulings favoring 3M, including the exclusion of plaintiffs’ causation experts and resulting summary judgments. The appellate decision is commonly associated with **In re Bair Hugger Forced Air Warming Products Liability Litigation**, 9xx F.3d (8th Cir. 2020), though the MDL generated multiple related decisions.
- **2021–2022:** Additional cases were resolved through dismissals, summary judgments, settlements, remands, or other case-specific dispositions. The MDL’s central mass-tort theory had been substantially undermined by the expert-evidence rulings.
- **2023:** The MDL was formally closed after the coordinated proceedings had largely concluded and remaining matters had been resolved, remanded, or otherwise disposed of.

### Outcome

The litigation did **not** produce a plaintiff verdict establishing that Bair Hugger caused deep-joint infections. The decisive development was the exclusion of plaintiffs’ principal general-causation expert evidence. That exclusion prevented plaintiffs in the bellwether cases from proving that Bair Hugger forced-air warming systems were capable of causing the infections at issue.

As a result:

- **3M won summary judg
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall dalkon — 12/15; missed: Judge Miles Lord's 1984 rebuke, Medical Device Amendments of 1976, 18 deaths; ~200,000-300,000 claims</summary>

```
The **Dalkon Shield litigation** arose from injuries allegedly caused by the **Dalkon Shield intrauterine device (IUD)**, a contraceptive marketed in the United States in the early 1970s by **A.H. Robins Company, Inc.**, a Richmond, Virginia pharmaceutical company. The litigation ultimately drove A.H. Robins into Chapter 11 bankruptcy and produced one of the most important mass-tort bankruptcy reorganizations of the era.

## Parties

- **Plaintiffs/claimants:** Hundreds of thousands of women who used the Dalkon Shield, along with some spouses and estates. Claimants alleged pelvic inflammatory disease, infertility, ectopic pregnancy, miscarriage, hysterectomy, sepsis, and death.
- **Defendant/debtor:** **A.H. Robins Company, Inc.**
- **Key corporate figures:**
  - **E. Claiborne Robins Jr.**, chairman and chief executive of A.H. Robins during much of the crisis.
  - **A.H. Robins III**, a senior company executive and member of the controlling Robins family.
- **Inventor/promoter:** **Dr. Hugh J. Davis**, a Johns Hopkins-affiliated physician who helped develop the device and promoted it. He had a financial interest in the product through royalty arrangements.
- **Manufacturer/marketer:** The device was initially developed through the **Dalkon Corporation** and then marketed by A.H. Robins.
- **Bankruptcy participants:** The debtor, Dalkon Shield claimants, creditors, insurers, shareholders, the bankruptcy court, and later **American Home Products Corporation**, which acquired Robins under the confirmed plan.
- **Trust:** The eventual **Dalkon Shield Claimants Trust**, created to process and pay personal-injury claims.

## The product and central allegations

The Dalkon Shield was introduced in **1970**. It was an IUD with a distinctive multifilament string intended to aid removal. The central allegation was that the string could act as a wick, allowing bacteria to travel from the vagina into the uterus and upper reproductive tract, causing serious infection.

Claimants alleged that A.H. Robins and others:

1. **Designed and marketed an unreasonably dangerous product.**
2. **Failed to adequately test the device** before widespread marketing.
3. **Failed to warn physicians and users** about infection risks and other dangers.
4. **Misrepresented the device’s safety and effectiveness** in promotional materials.
5. **Ignored, minimized, or concealed adverse-event information** after reports of infections, pregnancies, miscarriages, infertility, and deaths emerged.
6. In some cases, engaged in conduct supporting claims for **punitive damages**, not merely compensatory damages.

The litigation was especially damaging because plaintiffs’ lawyers obtained internal company documents and testimony suggesting that Robins had received warning signs yet continued to defend the product aggressively.

## Main events and dates

### 1970–1974: Marketing and withdrawal

- **1970:** The Dalkon Shield entered the U.S. market. It was promoted as an effective, convenient contraceptive.
- **Early 1970s:** Reports accumulated of pelvic infections, septic abortions, pregnancies with the device in place, miscarriages, infertility, and other complications.
- **June 1974:** A widely publicized death of a Dalkon Shield user, **Diana O’Donnell**, from septic abortion complications became emblematic of the product’s risks.
- **June 1974:** A.H. Robins suspended U.S. sales of the Dalkon Shield.
- **1974:** The company effectively withdrew the device from the market, though litigation continued for years because many women had already used it and injuries could emerge later.

### 1974–1985: Expanding mass-tort litigation

- After withdrawal, lawsuits multiplied across the country. By the mid-1980s, Robins faced an enormous and uncertain volume of claims.
- The company initially attempted to defend cases individually and settle others, but the number of claims and the possibility of large punitive-damages verdicts created a threat that exceeded its ability to predict or manage liability.
- The litigation became a classic mass-tort problem: thousands of individual injuries, differing medical histories, disputed causation, and potentially catastrophic aggregate exposure.
- A.H. Robins had substantial assets and insurance, but the scale of claims made ordinary litigation and settlement management increasingly untenable.

### August 21, 1985: A.H. Robins files Chapter 11

- On **August 21, 1985**, **A.H. Robins Company filed for Chapter 11 bankruptcy protection** in the U.S. Bankruptcy Court for the Eastern District of Virginia.
- The filing was intended to halt the fragmented litigation through the automatic stay and create a centralized process for resolving Dalkon Shield claims.
- The bankruptcy was controversial because Robins was not simply a failed operating company; it was a profitable enterprise overwhelmed by contingent mass-tort liabilities.

### 1985–1988: Bankruptcy litigation and plan negotiations

- The bankruptcy court had to address how to deal with both:
  - women who had already filed lawsuits or had known injuries; and
  - women who might later discover injuries or assert claims.
- A major issue was whether the reorganization could channel Dalkon Shield claims away from the reorganized company and related parties into a dedicated compensation mechanism.
- The case generated extensive disputes over valuation of claims, adequacy of notice, representation of future claimants, insurance proceeds, punitive damages, and the fairness of any settlement structure.
- **Judge Robert R. Merhige Jr.** of the U.S. District Court for the Eastern District of Virginia played a prominent role in the broader Dalkon Shield proceedings and settlement process. The bankruptcy case itself was administered in the federal bankruptcy system in Richmond.

### 1988: Plan confirmation framework

- In **1988**, the bankruptcy court confirmed a reorganization plan that established the **Dalkon Shield Claimants Trust**.
- The plan was design
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall earplugs — 14/14; missed: </summary>

```
The 3M Combat Arms Earplugs litigation was a massive federal multidistrict litigation involving claims by U.S. military service members and veterans that defective dual-ended earplugs made by 3M and its predecessor, Aearo Technologies, caused hearing loss and tinnitus.

## Case and parties

The MDL was:

**In re: 3M Combat Arms Earplug Products Liability Litigation, MDL No. 2885**  
U.S. District Court for the Northern District of Florida, Pensacola Division  
Presiding judge: **Chief U.S. District Judge M. Casey Rodgers**

The litigation was centralized in **April 2019** by the Judicial Panel on Multidistrict Litigation.

### Plaintiffs

The plaintiffs were primarily current and former U.S. military personnel—Army, Navy, Air Force, Marine Corps, Coast Guard, and National Guard members—who used the earplugs during training, combat deployments, weapons qualification, aviation, artillery operations, or other noisy military activities.

They alleged injuries including:

- Noise-induced hearing loss;
- Tinnitus, or persistent ringing in the ears;
- Related communication, sleep, concentration, and quality-of-life problems.

At its height, the MDL involved roughly **300,000 claimants**, making it one of the largest mass-tort proceedings in U.S. history.

### Defendants

The principal defendants were:

- **3M Company**, the Minnesota-based conglomerate;
- **Aearo Technologies LLC**, the company that developed and manufactured the earplugs before 3M acquired it in **2008**.

The product at issue was the **Combat Arms Earplug, Version 2 (CAEv2)**, a yellow-and-olive-green dual-ended earplug supplied to the U.S. military, generally from about **2003 to 2015**.

## Key allegations and issues

The central allegation was that the CAEv2 earplugs were defectively designed because they could loosen or imperceptibly back out of a user’s ear canal. Plaintiffs contended that this prevented the plugs from providing the advertised level of hearing protection.

The earplugs had two ends:

- One end was intended to block sound;
- The other was intended to reduce harmful noise while allowing users to hear commands or other lower-level sounds.

Plaintiffs alleged that the earplugs were too short and could fail to maintain a proper seal unless users folded back the earplug flanges or used another technique not adequately disclosed in the instructions. They argued that 3M and Aearo knew or should have known of the fit and sealing problem but failed to warn the military or users adequately.

The claims varied by state and plaintiff but commonly included:

- Design defect;
- Failure to warn;
- Negligence;
- Breach of warranty;
- Fraudulent concealment or misrepresentation in some cases;
- Claims that 3M failed to provide adequate instructions concerning proper fitting and use.

3M denied that the earplugs were defective or that they caused the claimed injuries. It argued, among other things, that hearing loss and tinnitus can result from many military and non-military noise exposures, that individual causation had to be proven case by case, and that the military had extensive knowledge and control over the product’s use.

A major legal issue was whether 3M could invoke the federal **government-contractor defense**, derived from *Boyle v. United Technologies Corp.* Under that doctrine, a contractor may avoid certain state-law liability where the federal government approved reasonably precise specifications, the product conformed to them, and the contractor warned the government of dangers known to the contractor but not the government.

Judge Rodgers rejected 3M’s broad effort to obtain summary judgment under that defense in **2021**, concluding that disputed factual issues remained, including whether the military had approved the relevant design specifications and whether 3M/Aearo had adequately disclosed information about the earplugs’ performance and fitting issues.

## Important background: the 2018 False Claims Act settlement

Before the MDL was created, 3M had resolved a separate federal False Claims Act matter involving the earplugs.

In **July 2018**, 3M agreed to pay **$9.1 million** to settle allegations brought by the United States that Aearo had knowingly supplied defective CAEv2 earplugs to the military and failed to disclose testing information. The government alleged that Aearo had altered testing procedures in a way that produced a higher noise-reduction rating than the earplugs would otherwise have received.

3M did not admit liability in that settlement. The settlement did not compensate individual service members for personal injuries, but it helped spur the later wave of private lawsuits.

## Key people

### Judge M. Casey Rodgers

**Chief Judge M. Casey Rodgers** of the Northern District of Florida oversaw the MDL. She managed the consolidated pretrial proceedings, ruled on major legal issues, selected bellwether cases for trial, and later supervised the settlement process.

### Mike Roman

**Mike Roman** was 3M’s chief executive officer during much of the litigation and during the 2023 settlement negotiations. He publicly defended the company’s position while also leading 3M through the eventual global resolution.

### Aearo Technologies

Aearo was not merely a nominal defendant; it was central because it designed and originally manufactured the CAEv2 earplugs before 3M acquired it in 2008.

### Plaintiffs’ leadership counsel

The plaintiffs were represented by a court-appointed Plaintiffs’ Leadership Committee and numerous individual law firms. The litigation involved thousands of lawyers and a large coordinated claimant structure rather than one single named plaintiff.

## Main events and timeline

### 2003–2015: Earplugs supplied to the military

Aearo, and later 3M after its 2008 acquisition of Aearo, supplied CAEv2 earplugs to the U.S. military. The earplugs were widely used by service members in high-noise environments.

### July 2018: Federal False Claims Act settlement

3M paid **$9.1 mi
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall near — 3/12; missed: MobileFuse / Kenneth Harlan, round-trip revenue scheme, ~27% revenue overstatement; $37.3m of $138.3m, KludeIn I SPAC merger, March 2023, Nasdaq ticker NIR, Pasadena, California, Chapter 11, 8 December 2023, luxury residence billed as professional services</summary>

```
I don’t know of an SEC accounting-fraud case filed in 2026 against former Near Intelligence, Inc. CEO Anil Mathews and CFO Rahul Agarwal. As of my knowledge cutoff, 2026 is also in the future relative to the information I can reliably verify.

I therefore can’t accurately provide the complaint’s allegations, dates, or outcome without risking fabrication. If you provide an SEC litigation release number, complaint, administrative-order number, or link, I can summarize the parties, allegations, chronology, and disposition precisely.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall meyer — 3/10; missed: SpaceX pre-IPO interests, misappropriation for personal expenses, inflated account statements, releases for reduced distributions, forfeited ~$3m capital call, Investment Advisers Act antifraud, conduct since December 2021</summary>

```
I can’t describe that matter because September 2026 is in the future relative to my knowledge context, and I do not have reliable information confirming an SEC case against Meyer Global Management LLC or its CEO, Owen Meyer. I should not guess about the allegations, dates, parties, or outcome.
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall texaco_pennzoil — 12/16; missed: Joe Jamail (plaintiff's counsel), Judges Anthony Farris / Solomon Casseb, bond requirement; Pennzoil v. Texaco (U.S. 1987) abstention, Carl Icahn's role</summary>

```
**Pennzoil Co. v. Texaco Inc.** was the landmark New York contract case arising from Texaco’s 1984 acquisition of Getty Oil. It is best known for holding that parties can form a binding agreement in principle—even before signing a formal merger contract—if their words and conduct show an intent to be bound.

## Parties

- **Pennzoil Company** — an oil company seeking to acquire Getty Oil.
- **Texaco Inc.** — the oil company that ultimately acquired Getty Oil.
- **Getty Oil Company** — the takeover target.
- **The J. Paul Getty Museum / Sarah C. Getty Trust interests** — major Getty shareholders whose support was crucial.
- **Gordon P. Getty** — son of J. Paul Getty and a major Getty shareholder; his position was central to the negotiations.
- **Hugh Liedtke** — Pennzoil’s chairman and chief executive, who led Pennzoil’s bid.
- **C. J. “Chuck” P. McKinney / Getty management and directors** — Getty’s board and executives participated in the negotiations and approval process.
- **John K. McKinley / Texaco leadership** — Texaco’s executives and board led Texaco’s competing bid.  
  More prominently, **Alfred C. DeCrane Jr.** was Texaco’s chairman and CEO during the transaction.

## Core dispute

Pennzoil alleged that Getty Oil had entered into a binding agreement with Pennzoil on **January 3, 1984**, under which Pennzoil would acquire Getty through a negotiated transaction.

Pennzoil’s proposed deal involved:

- Pennzoil acquiring a substantial Getty stake at **$110 per share**;
- a merger or restructuring involving the remaining Getty shares;
- participation by the Getty Trust interests;
- a planned public announcement and later execution of definitive documents.

Before formal merger documents were signed, Texaco made a higher offer—ultimately **$128 per share**—and Getty accepted Texaco’s proposal.

Pennzoil sued Texaco, claiming Texaco knowingly interfered with Pennzoil’s binding contract with Getty. Texaco argued that there was no enforceable contract because the parties expected to execute formal definitive agreements and had not yet done so.

The central legal issue was therefore:

> Did Pennzoil and Getty intend to be bound by their January 3 agreement in principle, notwithstanding the absence of signed final transaction documents?

## Main events and dates

### Late December 1983–early January 1984: Pennzoil negotiates with Getty

Getty Oil had become a takeover target after dissatisfaction among shareholders and pressure surrounding the company’s value and management. Pennzoil, led by Hugh Liedtke, negotiated with Getty’s board and with Gordon Getty and other Getty-affiliated holders.

### January 3, 1984: Getty board approves Pennzoil transaction terms

On the evening of **January 3, 1984**, Getty’s board approved the essential economic terms of a transaction with Pennzoil. The parties issued a press release describing an “agreement in principle” or transaction arrangement.

The announcement stated key terms, including the **$110-per-share** price and the contemplated structure of the deal. Pennzoil treated this as a binding agreement, subject only to preparation of formal documentation and completion of customary closing steps.

Getty’s representatives and Pennzoil continued working on definitive merger documents after the announcement.

### January 4–6, 1984: Texaco enters with a higher bid

Texaco made a competing proposal. Its offer exceeded Pennzoil’s price and ultimately reached **$128 per Getty share**.

Getty accepted Texaco’s offer rather than proceeding with Pennzoil. Texaco completed its acquisition of Getty in 1984, in what was then one of the largest corporate takeovers in U.S. history.

### 1984: Pennzoil sues Texaco in Texas

Pennzoil filed suit in Texas state court against Texaco for **tortious interference with contract**. Pennzoil did not principally seek to force Getty to merge with it; instead, it sought damages from Texaco for inducing Getty to abandon what Pennzoil said was an enforceable agreement.

Pennzoil alleged that Texaco knew of the Pennzoil-Getty agreement and deliberately induced Getty to breach it by offering more money.

### 1985: Jury verdict for Pennzoil

A Texas jury found that:

1. Pennzoil and Getty had formed a binding contract;
2. Texaco knowingly interfered with that contract; and
3. Pennzoil suffered damages.

The trial court entered a judgment of approximately:

- **$7.53 billion in compensatory damages**, plus
- **$3 billion in punitive damages**,

for a total exceeding **$10 billion** before later appellate changes.

The compensatory award was based largely on the value Pennzoil allegedly lost by being deprived of the Getty transaction.

### 1987: Texas appellate court upholds liability, reduces punitive damages

In **Texaco Inc. v. Pennzoil Co., 729 S.W.2d 768 (Tex. App.—Houston [1st Dist.] 1987, writ ref’d n.r.e.)**, the Texas Court of Appeals upheld the finding that a binding Pennzoil-Getty agreement existed.

The court emphasized objective manifestations of intent, including:

- the detailed terms agreed upon;
- Getty board approval;
- the public announcement;
- the parties’ conduct after January 3;
- the fact that the remaining matters were viewed as details to be documented rather than unresolved essential terms.

The court rejected Texaco’s argument that use of phrases such as “agreement in principle” necessarily meant no contract existed.

However, the appellate court substantially reduced the punitive-damages award, from **$3 billion** to **$1 billion**. The compensatory award remained roughly **$7.53 billion**, producing a judgment of about **$8.5 billion** plus interest.

### 1987–1988: Texaco bankruptcy and settlement

The enormous judgment threatened Texaco’s financial survival. Texaco sought bankruptcy protection under **Chapter 11 on April 12, 1987**, in part to manage the judgment and prevent Pennzoil from enforcing it while appeals and negotiations continued.

The litigation ended in a negotiated settlement in **Decemb
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall bhopal — 15/15; missed: </summary>

```
## The Bhopal Gas Disaster

### What happened

On the night of **2–3 December 1984**, a catastrophic release of toxic gas occurred at the **Union Carbide India Limited (UCIL)** pesticide plant in **Bhopal, Madhya Pradesh, India**.

The plant manufactured the pesticide **Sevin** and used **methyl isocyanate (MIC)**, an extremely toxic chemical, in the process. Water entered—or was alleged to have entered—a storage tank, **Tank 610**, containing MIC. A runaway chemical reaction caused pressure and temperature to rise, releasing a large cloud of MIC and other toxic substances over densely populated neighborhoods surrounding the plant.

The disaster killed thousands of people immediately and injured hundreds of thousands. Death estimates vary substantially:

- Indian government figures commonly cited about **3,787 immediate deaths**;
- Other estimates place the eventual death toll at **15,000 to 25,000 or more**;
- Roughly **500,000 people** were exposed, according to widely cited estimates.

Survivors suffered respiratory disease, eye injuries, neurological problems, reproductive and birth-related harms, and other chronic illnesses. Contamination of soil and groundwater around the abandoned plant also became a long-running issue.

---

## Parties

### Corporate defendants

- **Union Carbide Corporation (UCC)**  
  A U.S. corporation headquartered in Danbury, Connecticut. UCC owned a majority interest—about **50.9%**—in UCIL at the time of the disaster.

- **Union Carbide India Limited (UCIL)**  
  The Indian company that owned and operated the Bhopal plant. It was majority-owned by UCC, with the remainder held by Indian public and institutional investors.

- **Warren M. Anderson**  
  Chairman and chief executive officer of UCC at the time of the disaster. He became the most prominent individual defendant in Indian criminal proceedings.

- Other UCIL officials, including:
  - **Keshub Mahindra**, UCIL’s non-executive chairman;
  - **Vijay Gokhale**, UCIL managing director;
  - **J. Mukund**, works manager;
  - **S. P. Choudhury**, production manager;
  - **K. M. Chowdhury**, assistant works manager;
  - **J. S. Mukund**, among those charged in the Indian criminal case.

### Claimants and government parties

- **Bhopal victims and survivors**, including injured residents and families of those killed.
- **Government of India**, which assumed exclusive authority to represent victims in civil litigation under the **Bhopal Gas Leak Disaster (Processing of Claims) Act 1985**.
- **State of Madhya Pradesh**, involved in criminal prosecution and related proceedings.
- Numerous survivor organizations and public-interest groups later challenged the adequacy of the settlement and sought additional compensation and environmental remediation.

---

## Key allegations and issues

### 1. Corporate responsibility and plant safety

Victims and the Indian government alleged that Union Carbide and UCIL were responsible for unsafe design, inadequate maintenance, poor training, cost-cutting, and deficient emergency systems at the Bhopal plant.

Major allegations included:

- inadequate maintenance of MIC storage and safety equipment;
- failure or non-operation of safety systems, including refrigeration, a vent-gas scrubber, and flare tower;
- understaffing and inadequate worker training;
- storing unusually large quantities of MIC;
- inadequate warning systems and emergency planning for nearby residents;
- use of a plant design and operating practices alleged to be less safe than those used in the United States;
- failure by UCC, as majority shareholder and technical adviser, to ensure adequate safety standards at UCIL.

Union Carbide disputed that it controlled day-to-day operations at UCIL and argued that the disaster resulted from sabotage—specifically, intentional introduction of water into the MIC tank. Critics and survivor groups rejected that explanation and emphasized systemic safety failures.

### 2. Whether U.S. courts or Indian courts should hear the civil case

A central early legal issue was forum: whether litigation should proceed in the United States, where UCC was based, or in India, where the disaster occurred.

The Indian government filed suit in U.S. federal court, seeking damages from UCC. UCC sought dismissal on **forum non conveniens** grounds, arguing that India was the more appropriate forum.

### 3. Adequacy of compensation

The eventual settlement—**US$470 million**—became one of the most controversial aspects of the litigation. Survivors argued that it was grossly inadequate given the scale of deaths, injuries, long-term disease, and environmental contamination.

### 4. Criminal accountability

Indian prosecutors pursued criminal charges against UCC, Warren Anderson, and UCIL officials. The proceedings were prolonged by jurisdictional disputes, UCC’s refusal to appear in India, Anderson’s absence from India, and appeals over the proper level of criminal charges.

### 5. Environmental contamination

Separate from the immediate gas release, survivors alleged that hazardous wastes left at or near the plant contaminated groundwater and caused continuing illness. Union Carbide and later its purchaser, **Dow Chemical Company**, disputed responsibility for remediation beyond obligations imposed by Indian authorities and courts.

---

## Main events and litigation timeline

### 3 December 1984: Gas leak

The MIC release occurred shortly after midnight. Residents in nearby settlements awoke to burning eyes, choking, vomiting, and respiratory distress as the gas cloud spread through Bhopal.

### 7 December 1984: Warren Anderson arrested and released

Warren Anderson traveled to India shortly after the disaster. He was arrested in Bhopal on criminal charges, released on bail, and allowed to leave India. He did not return to face trial.

His departure became a major source of anger and controversy. Indian authorities later sought his extradition from the United States, but the United States did no
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall dieselgate — 14/17; missed: Judge Charles Breyer, N.D. Cal. MDL, $14.7bn consumer settlement / buybacks (2016), Bosch supplied the engine software</summary>

```
## Overview

“Dieselgate” refers to Volkswagen Group’s use of illegal engine-control software in diesel vehicles to detect laboratory emissions testing and reduce nitrogen-oxide (“NOx”) emissions during the test, while allowing much higher emissions during ordinary driving.

The scandal became public in September 2015 and led to recalls, criminal prosecutions, executive departures, civil settlements, regulatory penalties, and major changes in Volkswagen’s corporate strategy. It involved Volkswagen AG and several affiliates, including Volkswagen Group of America, Audi, Porsche, and Volkswagen Financial Services.

## Main parties

- **Volkswagen AG** — German parent company headquartered in Wolfsburg.
- **Volkswagen Group of America, Inc.** — Volkswagen’s U.S. subsidiary.
- **Audi AG** — Volkswagen subsidiary; Audi diesel vehicles were also implicated.
- **Porsche AG / Porsche Cars North America** — Porsche diesel models using Volkswagen/Audi diesel technology were implicated in later proceedings.
- **U.S. Environmental Protection Agency (EPA)** — issued the initial public notice of violation.
- **California Air Resources Board (CARB)** — California regulator that investigated and worked with EPA.
- **U.S. Department of Justice (DOJ)** — brought criminal and civil enforcement actions.
- **U.S. Federal Trade Commission (FTC)** — sued Volkswagen over allegedly deceptive “clean diesel” advertising.
- **Vehicle owners, dealers, shareholders, and governments** — brought consumer, dealer, securities, and regulatory claims in the United States and elsewhere.

## Core allegations and issues

The central allegation was that Volkswagen installed software—commonly called a **“defeat device”**—in certain diesel engines.

Under U.S. law, manufacturers may not use defeat devices that reduce emissions controls outside testing conditions unless a narrow exception applies. Volkswagen’s software allegedly recognized conditions associated with official laboratory testing—such as steering-wheel position, vehicle speed, duration, and barometric conditions—and activated a low-emissions calibration during the test.

In normal driving, the vehicles emitted NOx at levels far above legal limits. EPA said some affected vehicles emitted NOx at up to roughly **40 times** the applicable U.S. standard.

The affected U.S. vehicles initially included approximately **482,000** model-year 2009–2015 Volkswagen and Audi 2.0-liter diesel vehicles. Volkswagen later acknowledged that roughly **11 million vehicles worldwide** had been equipped with relevant software or affected diesel-engine technology, though the legal and technical scope varied by jurisdiction and engine type.

The scandal also concerned:

- misleading “clean diesel” marketing;
- false or incomplete regulatory submissions;
- obstruction and concealment allegations;
- consumer losses and diminished vehicle value;
- investor disclosures and securities-law issues;
- responsibility of senior management and engineers.

## Key people

### Martin Winterkorn
- **Role:** Chief Executive Officer of Volkswagen AG until September 2015.
- **Importance:** Resigned shortly after the scandal became public, saying he was shocked by the events and accepting responsibility for the crisis, while denying personal knowledge of wrongdoing.
- **Later proceedings:** German prosecutors charged him in 2019 in connection with the scandal, including allegations relating to fraud and market manipulation. In the United States, he was indicted in 2018 on conspiracy and fraud-related charges. He has not been extradited from Germany.

### Oliver Schmidt
- **Role:** Former general manager of Volkswagen’s Engineering and Environmental Office in Auburn Hills, Michigan.
- **Importance:** A senior U.S.-based Volkswagen executive involved in regulatory matters.
- **Outcome:** Arrested in the United States in January 2017. He pleaded guilty in August 2017 to conspiracy to defraud the United States and violate the Clean Air Act. In December 2017, he was sentenced to **seven years in prison** and a **$400,000 fine**.

### James Robert Liang
- **Role:** Volkswagen engineer.
- **Importance:** One of the first Volkswagen employees charged in the United States.
- **Outcome:** Pleaded guilty in September 2016 to conspiracy to defraud the United States, commit wire fraud, and violate the Clean Air Act. He cooperated with investigators and was sentenced in August 2017 to **40 months in prison** and a **$200,000 fine**.

### Rupert Stadler
- **Role:** Former Chief Executive Officer of Audi AG and member of Volkswagen AG’s management board.
- **Importance:** Audi was deeply involved in Volkswagen Group diesel-engine development and sales.
- **Outcome:** In 2023, Stadler received a suspended sentence and fine in Germany after admitting responsibility in a Munich criminal case involving diesel-emissions fraud.

### Herbert Diess
- **Role:** Volkswagen brand chief during the early scandal period; later Volkswagen Group CEO from 2018 to 2022.
- **Importance:** Helped lead Volkswagen’s post-scandal restructuring and shift toward electric vehicles. He was not the central figure in the original U.S. criminal allegations.

### Matthias Müller
- **Role:** Porsche executive who succeeded Winterkorn as Volkswagen Group CEO in September 2015.
- **Importance:** Led Volkswagen through the immediate crisis, settlements, recalls, and restructuring until 2018.

## Main events and dates

### 2014: Independent testing raises concerns
- Researchers working with the **International Council on Clean Transportation (ICCT)** and West Virginia University’s Center for Alternative Fuels, Engines and Emissions conducted real-world road testing of certain Volkswagen diesel vehicles.
- Their testing found unexpectedly high NOx emissions from Volkswagen Jetta and Passat diesel vehicles during normal driving.
- CARB and EPA began pressing Volkswagen for explanations.

### 2014–2015: Volkswagen gives explanations regulators found inadequate
- V
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall theranos — 15/17; missed: Safeway, Bad Blood (2018)</summary>

```
## Overview

Theranos was a Silicon Valley blood-testing company founded in 2003 by **Elizabeth Holmes**, who claimed it had developed technology capable of running dozens or hundreds of laboratory tests from a tiny finger-prick blood sample. The company’s central device was called the **Edison**.

The fraud case concerned allegations that Theranos’s technology did not work as advertised, that the company secretly relied heavily on conventional blood-testing machines made by other manufacturers, and that Holmes and Theranos executive **Ramesh “Sunny” Balwani** misled investors, business partners, doctors, and patients about the company’s capabilities, finances, and operations.

Holmes and Balwani were tried separately in federal court in San Jose, California. Both were convicted of fraud-related offenses.

---

## Principal parties and people

- **Elizabeth A. Holmes**
  - Founder and chief executive officer of Theranos.
  - Public face of the company and its claims about revolutionary blood testing.
  - Indicted in 2018; tried in late 2021; convicted in January 2022.

- **Ramesh “Sunny” Balwani**
  - Theranos’s former president and chief operating officer.
  - Holmes’s former romantic partner; he joined Theranos in 2009 and became a major operational executive.
  - Indicted alongside Holmes in 2018, but tried separately in 2022.
  - Convicted in July 2022.

- **Theranos, Inc.**
  - Palo Alto, California-based blood-testing company.
  - At its height, it was valued by private investors at roughly $9 billion.
  - Dissolved in 2018.

- **U.S. Department of Justice / U.S. Attorney’s Office for the Northern District of California**
  - Prosecuted Holmes and Balwani for wire fraud and conspiracy to commit wire fraud.

- **Judge Edward J. Davila**
  - U.S. District Judge in the Northern District of California.
  - Presided over both trials.

- **John Carreyrou**
  - Wall Street Journal investigative reporter.
  - His reporting beginning in October 2015 exposed major questions about Theranos’s technology and business practices.

- **Tyler Shultz and Erika Cheung**
  - Former Theranos employees and whistleblowers.
  - Shultz, the grandson of former U.S. Secretary of State George Shultz, raised concerns about the reliability of Theranos testing.
  - Cheung, a former Theranos laboratory employee, also raised concerns about inaccurate testing and laboratory practices.

- **David Boies**
  - Prominent lawyer retained by Theranos.
  - Theranos used aggressive legal tactics against critics and whistleblowers, including Tyler Shultz.

- **Key investors and partners**
  - Investors included figures such as **Rupert Murdoch**, the **Walton family**, **Betsy DeVos**, and others.
  - Theranos partnered with **Walgreens**, which planned to offer Theranos blood tests in retail stores.
  - The prosecution alleged investors and partners were misled about the technology’s performance and commercial readiness.

---

## The alleged fraud

### Claims about the Edison technology

Holmes promoted Theranos as having invented a device that could perform a broad menu of blood tests using only a few drops of blood from a finger stick. Theranos represented that its technology was faster, cheaper, less painful, and more convenient than conventional laboratory testing.

The government alleged that these claims were materially false or misleading. Among the central allegations:

1. **The Edison could not reliably perform many of the tests Theranos claimed it could perform.**
   - The company’s devices had accuracy, reliability, and quality-control problems.
   - Theranos often could not run tests from finger-prick samples as advertised.

2. **Theranos used conventional machines while implying that tests were being run on Theranos technology.**
   - The company used commercially available analyzers from companies such as Siemens.
   - Prosecutors argued that Theranos concealed this reliance on conventional equipment from investors, partners, and patients.

3. **Theranos manipulated or diluted samples.**
   - To make small finger-prick samples usable on conventional machines, Theranos sometimes diluted samples, which could affect accuracy.

4. **Holmes and Balwani made misleading statements about business performance.**
   - The government alleged they falsely represented Theranos’s revenue, projected revenue, relationships with pharmaceutical companies, and the extent of validation of its technology.
   - One recurring allegation was that Theranos represented or implied that major pharmaceutical companies had validated or used its technology when that was not true in the manner claimed.

5. **Patients received unreliable results.**
   - Theranos’s testing problems could produce inaccurate results that affected medical decisions.
   - The criminal cases included a patient-fraud theory, though the jury’s verdicts differed between Holmes and Balwani on patient-related counts.

---

## Major events and timeline

### 2003–2014: Theranos’s rise

- **2003:** Elizabeth Holmes founded Theranos after leaving Stanford University.
- **2009:** Ramesh Balwani joined Theranos and later became president and COO.
- **2013–2014:** Theranos expanded its public profile and entered a major relationship with Walgreens to offer blood testing in retail locations.
- **2014:** Holmes became a prominent Silicon Valley figure, appearing on magazine covers and presenting Theranos as a breakthrough health-care company.

### 2015: Public exposure begins

- **October 15, 2015:** The Wall Street Journal published John Carreyrou’s first major Theranos investigation. It reported that Theranos was using conventional machines for many tests rather than relying solely on its proprietary Edison device, and that the technology had serious limitations.
- Theranos denied the reporting and attacked critics, but the reporting triggered regulatory scrutiny and further investigations.

### 2016: Regulatory collapse

- **January 2016:** The Centers for Medicare & Medicai
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall ftx — 15/18; missed: ~$8 billion customer funds, effective altruism, Michael Lewis, Going Infinite</summary>

```
## Overview

FTX was a major cryptocurrency exchange founded by Sam Bankman-Fried. Its collapse in November 2022 exposed that customer funds deposited with FTX had been diverted to support Alameda Research, a crypto trading firm also controlled by Bankman-Fried. The failure led to bankruptcy proceedings, criminal charges against Bankman-Fried, civil enforcement actions, and prosecutions of several senior associates.

Bankman-Fried was convicted in federal court in New York in November 2023 and sentenced in March 2024 to 25 years in prison.

## Main parties

- **FTX Trading Ltd. and affiliated companies**: The cryptocurrency exchange group. FTX.com primarily served non-U.S. customers; FTX.US was marketed as a separate U.S. platform.
- **Alameda Research**: A cryptocurrency trading firm founded by Bankman-Fried. It was closely intertwined with FTX and received special access to FTX customer assets.
- **Sam Bankman-Fried (“SBF”)**: Founder and chief executive of FTX; founder and former CEO of Alameda Research. He was the central defendant in the criminal case.
- **Caroline Ellison**: CEO of Alameda Research during the collapse. She pleaded guilty, cooperated with prosecutors, and testified against Bankman-Fried.
- **Gary Wang**: FTX co-founder and former chief technology officer. He pleaded guilty and testified that he helped create software features giving Alameda special privileges.
- **Nishad Singh**: Former FTX engineering director. He pleaded guilty and testified against Bankman-Fried.
- **Ryan Salame**: Former co-CEO of FTX Digital Markets, FTX’s Bahamas affiliate. He pleaded guilty in 2023 to campaign-finance and money-transmission-related offenses; he did not testify at Bankman-Fried’s trial.
- **John J. Ray III**: Restructuring executive appointed CEO after the bankruptcy. He had previously overseen Enron’s restructuring and described FTX’s records and controls as extraordinarily deficient.
- **U.S. Department of Justice / U.S. Attorney’s Office for the Southern District of New York**: Prosecuted Bankman-Fried.
- **Judge Lewis A. Kaplan**: Federal district judge who presided over Bankman-Fried’s criminal case and imposed sentence.
- **Judge John Dorsey**: Bankruptcy judge overseeing the FTX Chapter 11 case in Delaware.
- **SEC and CFTC**: U.S. regulators that brought parallel civil enforcement actions alleging fraud and related violations.

## Core allegations and issues

The central allegation was that Bankman-Fried orchestrated a years-long fraud by allowing Alameda Research to use billions of dollars in money belonging to FTX customers.

According to prosecutors and cooperating witnesses:

1. **Customer funds were diverted to Alameda.**  
   FTX customers believed their deposits were held for trading or withdrawal. Instead, Alameda was permitted to draw on those funds, including through accounts and payment channels connected to FTX.

2. **Alameda received secret special privileges.**  
   Gary Wang testified that he created features allowing Alameda to maintain a negative balance on FTX—effectively an enormous line of credit funded by customers—and to avoid ordinary liquidation protections that applied to other users.

3. **The money was used for Alameda’s losses and other spending.**  
   Prosecutors said customer money was used to cover Alameda trading losses, repay lenders, make venture investments, purchase real estate in the Bahamas, and finance political contributions and other expenditures.

4. **Bankman-Fried made misleading public statements.**  
   The government argued that he falsely represented that FTX safeguarded customer assets, that Alameda was separate from FTX, and that FTX did not use customer deposits for risky trading or lending.

5. **The collapse was triggered by a liquidity crisis, not merely a market downturn.**  
   When customers sought to withdraw funds in November 2022, FTX could not meet the requests because much of the money had already been transferred or committed elsewhere.

Bankman-Fried’s defense argued that he did not intend to steal customer money, that he believed Alameda could repay its borrowing, and that he made serious business mistakes rather than knowingly committing fraud. The jury rejected that defense.

## Main events and dates

### Before the collapse

- **2017**: Bankman-Fried founded Alameda Research.
- **2019**: FTX was launched. It grew rapidly into one of the world’s largest crypto exchanges.
- **2021–2022**: FTX and Bankman-Fried became prominent in crypto, venture investing, political giving, and public policy discussions. Bankman-Fried cultivated an image as a comparatively responsible industry leader.

### November 2022: FTX collapses

- **November 2, 2022**: CoinDesk published a report based on a leaked Alameda balance sheet. The report raised concerns that Alameda’s finances depended heavily on **FTT**, a token issued by FTX, and on illiquid affiliated assets.

- **November 6, 2022**: Binance CEO Changpeng Zhao announced that Binance would sell its holdings of FTT. The announcement intensified market concern and helped trigger a run on FTX.

- **November 6–8, 2022**: Customers attempted to withdraw billions of dollars from FTX. FTX could not satisfy the withdrawal demand.

- **November 8, 2022**: Binance announced a nonbinding letter of intent to acquire FTX.com, subject to due diligence.

- **November 9, 2022**: Binance withdrew from the proposed transaction, saying its due diligence and reports concerning mishandled customer funds and possible U.S. investigations made it unwilling to proceed.

- **November 11, 2022**: FTX, Alameda Research, and more than 100 affiliated entities filed for Chapter 11 bankruptcy protection in Delaware. Bankman-Fried resigned as CEO. John J. Ray III became chief executive and restructuring officer.

- **November 12, 2022**: Unauthorized transfers from FTX wallets were reported amid the chaotic aftermath of the bankruptcy filing.

### Criminal case begins

- **December 12, 2022**: Bankma
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall endo — 11/20; missed: 'pseudoaddiction' and 'usually do not become addicted' in training / marketing, American Pain Foundation / NIPC / painknowledge.com, Par Pharmaceutical (2015) and Qualitest (2010) generic subsidiaries, Malvern / Chadds Ford, Pennsylvania; Dublin domicile via Paladin Labs (2014), Opana ER launched 2006 (with Penwest), generic Opana ER / Impax & Actavis; FTC pay-for-delay case (2016-17), Opioid Industry Documents Archive (UCSF / Johns Hopkins) document release, CEOs Rajiv De Silva (2013-16), Paul Campanelli (2016-20), Blaise Coleman (2020-)</summary>

```
## Overview

Endo International plc and its U.S. subsidiary Endo Pharmaceuticals Inc. were major defendants in the nationwide opioid litigation. The claims centered on Endo’s marketing of opioid pain medicines—especially **Opana ER** (extended-release oxymorphone)—and allegations that it deceptively promoted opioids, minimized addiction and overdose risks, and helped create or worsen the opioid epidemic.

The litigation proceeded on several tracks:

1. the federal opioid multidistrict litigation, **In re National Prescription Opiate Litigation, MDL No. 2804**;
2. lawsuits by state attorneys general and local governments;
3. criminal and civil investigations involving Opana ER;
4. Endo’s 2022 Chapter 11 bankruptcy, which became the principal mechanism for resolving opioid claims; and
5. a 2024 federal criminal plea by Endo Pharmaceuticals.

---

## 1. The MDL: *In re National Prescription Opiate Litigation*, MDL No. 2804

### Court and parties

The federal opioid MDL was centralized in the **U.S. District Court for the Northern District of Ohio**, before **Judge Dan Aaron Polster**.

The MDL included thousands of claims brought by:

- counties, cities, municipalities, hospital systems, tribes, and other public entities;
- state attorneys general in related or coordinated proceedings; and
- other plaintiffs seeking recovery for public costs associated with opioid addiction, overdose, treatment, law enforcement, child-welfare services, and related harms.

**Endo Pharmaceuticals Inc.** and related Endo entities were among the manufacturer defendants, along with companies such as Purdue Pharma, Johnson & Johnson/Janssen, Teva, Allergan, Mallinckrodt, and others.

### Core allegations against Endo

The governmental plaintiffs generally alleged that Endo:

- marketed prescription opioids in a misleading and aggressive manner;
- overstated or misrepresented the benefits of opioids for chronic, non-cancer pain;
- downplayed the risks of addiction, dependence, abuse, diversion, overdose, and death;
- promoted opioid prescribing at doses and durations alleged to be unsafe;
- used sales representatives, educational programs, paid speakers, and purportedly independent medical materials to influence prescribers;
- failed to maintain adequate controls against suspicious prescribing and diversion; and
- created or contributed to a public nuisance and imposed substantial public costs on governments.

The principal Endo product at issue was **Opana ER**, an extended-release oxymorphone opioid. Plaintiffs also focused on Endo’s broader opioid-marketing practices.

Endo denied wrongdoing in civil litigation and disputed that its conduct legally caused the governments’ claimed injuries.

---

## 2. Opana ER and the FDA’s 2017 action

A central factual issue in the litigation was Endo’s reformulated Opana ER.

### Reformulation and abuse concerns

Endo introduced a reformulated version of Opana ER that it promoted as having abuse-deterrent properties. Critics and regulators concluded that the reformulation did not adequately prevent abuse and, in some settings, may have shifted abuse toward injection. Public-health authorities reported outbreaks of HIV and hepatitis C associated with injection of crushed or dissolved Opana ER in Indiana and elsewhere.

### FDA request to withdraw Opana ER

On **June 8, 2017**, the **Food and Drug Administration** asked Endo to voluntarily remove reformulated Opana ER from the market. The FDA stated that it had concluded that the drug’s benefits no longer outweighed its risks.

The FDA described this as the first time it had sought removal of a currently marketed opioid pain medicine because of the public-health consequences of abuse.

Endo announced on **July 6, 2017**, that it would voluntarily discontinue Opana ER. The company said it disagreed with the FDA’s assessment but would comply with the request.

The withdrawal became an important part of the factual backdrop for later governmental claims and criminal proceedings.

---

## 3. State attorney-general litigation and settlements

### State AG claims

Numerous state attorneys general sued Endo or asserted claims against it in broader opioid litigation. Their allegations substantially overlapped with those in the MDL: deceptive opioid marketing, failure to disclose addiction and overdose risks adequately, and contribution to statewide public-health and governmental costs.

States pursued claims under combinations of:

- consumer-protection statutes;
- false-advertising laws;
- public-nuisance theories;
- Medicaid and other public-expenditure recovery statutes; and
- common-law fraud, negligence, unjust-enrichment, or related theories.

### Major pre-bankruptcy state settlement: Oklahoma

One prominent early settlement was with **Oklahoma**.

On **May 28, 2019**, Oklahoma Attorney General **Mike Hunter** announced that Endo had agreed to pay **$8.75 million** to resolve Oklahoma’s opioid claims. The settlement was part of Oklahoma’s broader litigation against opioid manufacturers and distributors. Endo did not admit liability.

### Other state resolutions

Endo also reached opioid-related settlements or agreements with other states before bankruptcy, including a **$65 million settlement with New York**, announced in **2021**, resolving claims by New York Attorney General **Letitia James** concerning Endo’s opioid marketing. That settlement included monetary relief and restrictions on opioid marketing practices.

But Endo’s remaining nationwide opioid exposure was not resolved through a single ordinary MDL settlement before its bankruptcy filing. Instead, the bankruptcy process became the vehicle for a global resolution.

---

## 4. The 2022 bankruptcy

### Filing

On **August 16, 2022**, **Endo International plc** and many affiliated entities, including **Endo Pharmaceuticals Inc.**, filed for Chapter 11 protection in the **U.S. Bankruptcy Court for the Southern District of New York**.

The cases were assigned to **Judge 
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall juul — 9/15; missed: 'Vaporized' launch campaign (2015) with young models, nicotine-salt formulation; 5% pods, San Francisco Unified bellwether; school districts, $462m settlement with six states incl. NY & CA (Apr 2023), Altria write-down / exit; later NJOY purchase, JUUL documents in the UCSF Industry Documents Library</summary>

```
## Overview

The JUUL Labs youth-vaping litigation was a broad set of lawsuits and government enforcement actions alleging that JUUL Labs, Inc. marketed highly addictive nicotine e-cigarettes to minors and young adults, understated addiction risks, and helped create a youth-vaping epidemic. The matters ran from private consumer and personal-injury suits to state attorney-general actions, school-district claims, FDA proceedings, and criminal investigations.

The central defendants were:

- **JUUL Labs, Inc.**, maker of JUUL e-cigarettes and nicotine pods.
- **Altria Group, Inc.**, the tobacco company that bought a **35% stake in JUUL in December 2018** for about **$12.8 billion**. Altria was named in many suits as an alleged participant in or beneficiary of JUUL’s conduct.
- In some cases, individual JUUL executives were named, particularly:
  - **James Monsees**, JUUL co-founder and former chief product officer.
  - **Adam Bowen**, JUUL co-founder and former chief technology officer.
  - **Kevin Burns**, JUUL’s chief executive officer until September 2019.
  - **K.C. Crosthwaite**, former Altria executive who became JUUL CEO in September 2019.
  - **Nicholas Pritzker**, a JUUL board member and investor, named in some litigation.

## Core allegations

Although the claims varied by plaintiff and jurisdiction, the recurring allegations were that JUUL:

1. **Targeted or appealed to youth.**  
   Plaintiffs alleged JUUL used youthful-looking models, social-media marketing, launch parties, influencer-style promotion, colorful imagery, and flavors such as mango, crème, cucumber, and mint to attract teenagers.

2. **Misrepresented nicotine strength and addiction risk.**  
   JUUL’s pods used nicotine salts, allowing high nicotine concentrations to be inhaled more easily than traditional cigarettes. Plaintiffs alleged JUUL initially promoted its product as a satisfying alternative to cigarettes while failing adequately to disclose how addictive its nicotine delivery could be.

3. **Failed to prevent underage sales.**  
   Lawsuits alleged JUUL’s age-verification and retail controls were inadequate and that the company knew minors were obtaining JUUL products through retailers, online sales, and social networks.

4. **Created public-health and educational costs.**  
   School districts and local governments alleged they had to spend money on vaping detection, discipline, counseling, prevention programs, staff time, and student-health interventions.

5. **Caused personal injuries and addiction.**  
   Individual plaintiffs alleged nicotine addiction, withdrawal, anxiety, impaired concentration, respiratory symptoms, and other harms. Some suits also alleged that JUUL use led young people to begin or increase nicotine use.

Claims commonly included consumer-protection violations, fraud or misrepresentation, failure to warn, negligence, public nuisance, unjust enrichment, and—in certain cases—racketeering-related theories.

---

## Major events and timeline

### 2018: JUUL’s rapid growth and Altria investment

- **December 20, 2018:** Altria announced it would acquire a **35% stake in JUUL Labs for $12.8 billion**. The deal valued JUUL at roughly $38 billion.
- By this period, JUUL had become the dominant U.S. e-cigarette brand and was under intense scrutiny over teen use.

### 2019: Investigations, lawsuits, and leadership changes

- **2019:** State attorneys general, the FDA, Congress, school districts, parents, and individual users increasingly brought claims or investigations concerning JUUL’s youth marketing and nicotine practices.
- **September 25, 2019:** JUUL announced that CEO **Kevin Burns** would step down. **K.C. Crosthwaite**, formerly an Altria executive, became CEO.
- **October 2019:** JUUL stopped selling certain flavored pods in retail stores, including mango, crème, fruit, and cucumber, while continuing tobacco and menthol products at that time.
- **November 2019:** JUUL announced it would stop U.S. sales of mint-flavored pods, leaving tobacco and menthol as its principal U.S. flavors.
- **2019:** The federal multidistrict litigation process began. Federal JUUL cases were centralized in the **U.S. District Court for the Northern District of California** before **Judge William H. Orrick III**.

### 2020: Federal multidistrict litigation and regulatory pressure

- The consolidated federal proceeding became known as **In re: JUUL Labs, Inc., Marketing, Sales Practices, and Products Liability Litigation**, MDL No. 2913.
- The MDL included:
  - Personal-injury and consumer claims by users and parents;
  - Claims by school districts and local governments;
  - Claims by state and local governmental entities;
  - Claims involving Altria as well as JUUL.
- **January 2020:** The FDA issued enforcement guidance prioritizing action against unauthorized flavored cartridge-based e-cigarettes other than tobacco and menthol. JUUL had already withdrawn many flavors.
- **April 2020:** The FDA ordered JUUL to submit premarket tobacco product applications for continued sale of its products. JUUL submitted applications later that year.

### 2021: State settlements begin

- **June 28, 2021:** **North Carolina Attorney General Josh Stein** announced a **$40 million settlement** with JUUL. North Carolina alleged JUUL’s marketing and sales practices fueled youth vaping. The settlement imposed marketing restrictions and funded prevention, cessation, and enforcement efforts.
- Other states continued litigation or investigations, while the federal MDL proceeded through discovery and pretrial rulings.

### 2022: Large multistate and class settlements

#### $438.5 million multistate attorney-general settlement

- **September 6, 2022:** A coalition of **34 states and territories**, led in the investigation by **Connecticut Attorney General William Tong**, announced a **$438.5 million settlement** with JUUL.
- The agreement resolved investigations into JUUL’s marketing and sales practices, though individual states 
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall teva — 13/14; missed: Petah Tikva / Tel Aviv, Israel</summary>

```
The opioid litigation involving **Teva Pharmaceuticals USA, Inc.**, **Cephalon, Inc.**, and **Actavis Pharma, Inc.** was part of the broader U.S. opioid crisis litigation. It included thousands of lawsuits by states, local governments, tribes, hospitals, and others, much of it centralized in federal multidistrict litigation in Ohio. The central accusation was that the companies helped create or worsen the opioid epidemic through deceptive marketing and inadequate controls over opioid distribution.

## Parties

### Defendants
- **Teva Pharmaceutical Industries Ltd.** — Israeli parent company.
- **Teva Pharmaceuticals USA, Inc.** — U.S. operating subsidiary.
- **Cephalon, Inc.** — acquired by Teva in 2011.
- **Actavis Pharma, Inc.** — acquired by Teva in 2016; Actavis had itself acquired parts of Watson Pharmaceuticals and other opioid-related businesses.

The litigation often treated Teva, Cephalon, and Actavis as related corporate defendants because Teva acquired Cephalon and Actavis and allegedly assumed or became responsible for relevant opioid-related liabilities.

### Plaintiffs
Plaintiffs included:
- States and territories, including **New York**, **California**, **Oklahoma**, **West Virginia**, and others;
- Counties, cities, and other local governments;
- Native American tribes;
- Hospitals and health systems;
- Individual consumers and third-party payors in certain cases.

A major federal proceeding was **In re: National Prescription Opiate Litigation**, MDL No. 2804, before **U.S. District Judge Dan Aaron Polster** in the Northern District of Ohio.

## Drugs at issue

The companies’ opioid products included, among others:

- **Actiq** — fentanyl citrate lozenges, originally marketed by Cephalon for breakthrough cancer pain.
- **Fentora** — fentanyl buccal tablets, also associated with Cephalon.
- **Nuvigil/Provigil** were not opioids and were involved in other Cephalon litigation, but not the core opioid claims.
- **Opana ER** — oxymorphone extended-release, associated with Actavis/Endo-related litigation more broadly; Actavis’s role varied by product and jurisdiction.
- **Hydrocodone, oxycodone, fentanyl, morphine, and other generic opioid products** manufactured or distributed by Actavis/Watson/Teva entities.

The most prominent Cephalon-related allegations concerned **Actiq** and **Fentora**, potent fentanyl products approved for breakthrough pain in opioid-tolerant cancer patients.

## Key allegations and issues

The plaintiffs generally alleged that Teva, Cephalon, and Actavis:

1. **Misrepresented the risks of prescription opioids**
   - Plaintiffs alleged the companies minimized or obscured addiction, dependence, overdose, and withdrawal risks.
   - They alleged the companies promoted the proposition that addiction was uncommon when opioids were prescribed for pain, including chronic non-cancer pain.

2. **Promoted opioids beyond appropriate patient populations**
   - Cephalon was accused of promoting Actiq and Fentora for non-cancer pain and other uses outside their FDA-approved indications.
   - Actiq was approved for breakthrough cancer pain in opioid-tolerant patients, but plaintiffs alleged it was marketed to physicians who treated migraines, back pain, and other non-cancer conditions.

3. **Used misleading marketing materials and paid speakers**
   - The lawsuits alleged use of sales representatives, paid physician speakers, educational programs, and purportedly independent medical materials to encourage broader opioid prescribing.
   - Plaintiffs contended that the companies promoted higher doses, longer duration of treatment, and use in chronic pain patients without adequately disclosing risks.

4. **Failed to maintain effective anti-diversion controls**
   - In claims involving distribution, plaintiffs alleged that defendants failed to identify, investigate, and report suspicious orders or diversion patterns adequately.
   - Manufacturer claims and distributor claims were legally distinct, but many public-entity complaints alleged that both marketing and supply-chain conduct contributed to the crisis.

5. **Created a public nuisance and caused public costs**
   - State and local plaintiffs sought to recover costs associated with addiction treatment, emergency medical care, law enforcement, child welfare, incarceration, and other opioid-crisis consequences.
   - Claims varied by jurisdiction and included public nuisance, consumer-protection violations, false advertising, negligence, unjust enrichment, and statutory claims.

## Important people

### Judge Dan Aaron Polster
- Federal judge in the Northern District of Ohio.
- Presided over the federal opioid MDL, **In re: National Prescription Opiate Litigation**.
- He pushed parties toward a nationwide resolution and oversaw extensive discovery, bellwether preparation, and settlement negotiations.

### Teva leadership
- **Kåre Schultz**, Teva’s president and CEO from late 2017, was a principal corporate leader during major settlement negotiations.
- **Erez Vigodman**, Teva CEO from 2014 until 2017, led the company during part of the period when opioid litigation expanded.
- **Sol J. Barer**, Teva’s chairman for part of the relevant period, was among senior corporate figures during Teva’s acquisition-driven expansion.

### Cephalon leadership
- **Frank Baldino Jr.**, Cephalon’s founder, chairman, and CEO until his death in 2010, was the company’s most prominent historical executive during the period when Actiq and Fentora marketing practices drew federal scrutiny.
- Cephalon was acquired by Teva in **October 2011**, before the principal wave of public opioid litigation filed from 2014 onward.

### Government officials and litigators
- Numerous state attorneys general led separate state cases and settlement negotiations.
- **Letitia James**, New York Attorney General, was a leading figure in New York’s opioid litigation and announced New York’s settlement with Teva in 2022.
- **Rob Bonta**, California Attorney General
```
</details>

<details><summary><code>gpt-5.6-terra</code> — matter_recall bigthorium — 0/11; missed: John Maxwell (sales), Sarah Thompson (business development), Robert Williams (CFO), Emily Roberts (government relations), Laura Smith (procurement), Evelyn Archer (general counsel), Daniel Carter / Law Firm X, Howard Bass (city treasurer)</summary>

```
I don’t know of a real bribery investigation called “BigThorium” involving a “City of Atlantis.” Those names appear fictional or anonymized, and I should not invent parties, allegations, dates, or an outcome.

If you mean a particular real investigation under different names, provide the jurisdiction, approximate dates, or a news/court reference and I can help identify and summarize it.
```
</details>

