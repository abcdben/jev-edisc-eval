# Generalisation checks for the contamination study — 2026-10-06

Claim under test: *on the matters tested, knowing the case did not detectably change review accuracy.* Four checks that would strengthen or undermine it; each is read in claim language below. Jev is a system under test throughout. New OpenAI spend (paid, flex tier): A $0.30 · C $1.67 (list $3.34) · D $8.98 (list $21.24) · **total $10.95 of the $15 cap**. Jev spend: C $0.01, D $0.11.

| Check | Verdict for the claim | One line |
|---|---|---|
| A — knowledge-dependence error analysis | **strengthens** | Only 7% of Enron J documents are knowledge-dependent. On them every system is *less* accurate in the named condition (GPT-5.6 Luna 61%, GPT-5.6 Terra 61%, GPT-5.6 Sol 64%, Jev 66%) than on self-contained documents (GPT-5.6 Luna 83%, GPT-5.6 Terra 81%, GPT-5.6 Sol 83%, Jev 78%); the most accurate system on knowledge-dependent documents is Jev. The renaming drop is larger on knowledge-dependent documents for 1/4 systems, none with a CI excluding zero (n ≈ 59); the one system whose drop concentrates on knowledge-dependent documents is Jev (ΔF1 KD − SC -14.5 [-31.7, +0.5], seven flips), and Jev is not more accurate on those documents when named, so at most half the signature. The signature contamination predicts (better on KD and a KD-concentrated drop) is absent; the LLMs' Enron J edge over Jev sits on self-contained documents. |
| B — ranking stability | **ambiguous — leans weakens** | Rank order is not stable: Kendall W = 0.14 across 5 corpora × 4 systems (p≈0.56; four systems give W almost no power). Top system: enron_j → GPT-5.6 Sol, enron_k → GPT-5.6 Sol, mnk → GPT-5.6 Terra, veridian → Jev, endo → GPT-5.6 Terra. Within each LLM, F1 does not trend with its own case knowledge (Spearman ρ GPT-5.6 Luna +0.0, GPT-5.6 Terra -0.2, GPT-5.6 Sol -0.2). The mean-LLM − Jev F1 gap widens monotonically with the LLMs' case knowledge: enron_j (case 84) +6.3 pp, mnk (case 53) -2.0 pp, veridian (case 0) -4.1 pp (Endo excluded: its gold is the LLMs' own panel). The gap pattern is what contamination would predict, but it is equally what corpus type predicts (real human-judged email vs LLM-panel and synthetic gold), and Checks A and D test the mechanism directly and find none. |
| C — counterfactual conflict documents | **mixed — neutral for the claim as stated** | Knowledge-following rate on counterfactual documents, pooled over the four real matters: GPT-5.6 Luna 17% (knowledge-made-relevant tokens 27%, knowledge-made-irrelevant 4%; vs Veridian +0.0 pp [-14.2, +15.0]); GPT-5.6 Terra 14% (knowledge-made-relevant tokens 24%, knowledge-made-irrelevant 2%; vs Veridian -4.2 pp [-15.8, +8.3]); GPT-5.6 Sol 12% (knowledge-made-relevant tokens 18%, knowledge-made-irrelevant 4%; vs Veridian -8.3 pp [-16.7, +0.8]); Jev 8% (knowledge-made-relevant tokens 15%, knowledge-made-irrelevant 0%; vs Veridian +1.7 pp [-9.2, +14.2]). Every system reads the factual versions at ≥97%, so the overrides are real, almost entirely in one direction (a well-known 'hot' token keeps a document responsive even when the text says it is about something else), and concentrated on Jeb Bush, Mallinckrodt and Endo — Enron overrides are near zero. The rates are within noise of each system's Veridian baseline, where the only facts that can be overridden sit in the prompt itself; so the systems do let prior facts outweigh text on engineered conflicts, but no more for pre-trained facts than for in-context ones. On real corpora such conflicts are rare (Check A: ~7% of Enron J documents are even knowledge-dependent), which is why this does not show up as accuracy. |
| D — knowledge injection on Veridian | **strengthens** | ΔF1 with brief: GPT-5.6 Luna -0.3 [-1.7, +1.1], GPT-5.6 Terra -0.6 [-2.1, +0.8], GPT-5.6 Sol -1.0 [-2.6, +0.5], Jev +0.5 [-1.1, +2.2]. No system's F1 moves beyond noise when the only possible source of case knowledge is supplied. |

## Check A — knowledge-dependence error analysis (Enron J)

Prediction if contamination helps: higher named accuracy on knowledge-dependent documents AND a larger named→renamed drop on them. Tagging is by Luna (one of the systems under test) — a tagger-is-a-subject caveat, mitigated by the tag being about the document, not the call.

Tagger: GPT-5.6 Luna at temperature 0, prompt `a1`; 991 of 991 unique Enron J documents tagged. Knowledge-dependent share on the six knowledge requests: 6.9% [5.4, 8.9].

| Request | n | knowledge-dependent share |
|---|---:|---:|
| document_destruction | 141 | 0.0% [0.0, 2.7] |
| energy_schedules | 142 | 7.7% [4.4, 13.3] |
| fantasy_football | 142 | 2.8% [1.1, 7.0] |
| fas140 | 142 | 25.4% [18.9, 33.1] |
| financial_analysts | 141 | 0.7% [0.1, 3.9] |
| financial_forecasts | 142 | 4.9% [2.4, 9.8] |
| prepay_transactions | 141 | 2.8% [1.1, 7.1] |

Share tagged knowledge-dependent by gold label: not_responsive 6.8% (n=502), responsive 5.9% (n=489).

| System | subset | n (pos) | named acc | named P / R / F1 | renamed F1 | ΔF1 renamed−named [95% CI] | right→wrong / wrong→right |
|---|---|---:|---:|---|---:|---|---:|
| GPT-5.6 Luna | knowledge-dependent | 59 (27) | 61.0 [48.3, 72.4] | 59.1 / 48.1 / 53.1 | 57.1 | +4.1 [-6.7, +14.9] | 2 / 4 |
| GPT-5.6 Luna | self-contained | 791 (391) | 82.7 [79.9, 85.2] | 88.3 / 74.9 / 81.1 | 80.6 | -0.5 [-2.2, +1.3] | 19 / 15 |
| GPT-5.6 Luna | all | 850 (418) | 81.2 [78.4, 83.7] | 86.4 / 73.2 / 79.3 | 79.1 | -0.2 [-2.0, +1.5] | 21 / 19 |
| GPT-5.6 Terra | knowledge-dependent | 59 (27) | 61.0 [48.3, 72.4] | 83.3 / 18.5 / 30.3 | 34.3 | +4.0 [-17.6, +26.2] | 3 / 3 |
| GPT-5.6 Terra | self-contained | 792 (391) | 80.7 [77.8, 83.3] | 91.3 / 67.3 / 77.5 | 75.2 | -2.3 [-4.3, -0.2] | 26 / 12 |
| GPT-5.6 Terra | all | 851 (418) | 79.3 [76.5, 81.9] | 91.2 / 64.1 / 75.3 | 73.2 | -2.1 [-4.3, +0.0] | 29 / 15 |
| GPT-5.6 Sol | knowledge-dependent | 59 (27) | 64.4 [51.7, 75.4] | 66.7 / 44.4 / 53.3 | 70.6 | +17.3 [+4.8, +32.1] | 1 / 7 |
| GPT-5.6 Sol | self-contained | 791 (391) | 83.1 [80.3, 85.5] | 89.3 / 74.7 / 81.3 | 81.4 | +0.1 [-1.7, +1.9] | 18 / 18 |
| GPT-5.6 Sol | all | 850 (418) | 81.8 [79.0, 84.2] | 88.1 / 72.7 / 79.7 | 80.7 | +1.0 [-0.9, +2.9] | 19 / 25 |
| Jev | knowledge-dependent | 59 (27) | 66.1 [53.4, 76.9] | 76.9 / 37.0 / 50.0 | 34.3 | -15.7 [-33.3, -0.7] | 5 / 2 |
| Jev | self-contained | 791 (391) | 77.9 [74.9, 80.6] | 91.5 / 60.9 / 73.1 | 71.9 | -1.2 [-3.0, +0.5] | 15 / 8 |
| Jev | all | 850 (418) | 77.1 [74.1, 79.8] | 90.8 / 59.3 / 71.8 | 70.0 | -1.8 [-3.7, -0.1] | 20 / 10 |

Contrasts (knowledge-dependent − self-contained):

| System | named accuracy KD − SC | named F1 KD − SC | ΔF1(KD) − ΔF1(SC) | Δacc(KD) − Δacc(SC) |
|---|---|---|---|---|
| GPT-5.6 Luna | -21.7 [-35.2, -8.7] | -28.0 [-47.6, -11.5] | +4.6 [-6.4, +15.3] | +3.9 [-4.1, +12.5] |
| GPT-5.6 Terra | -19.7 [-32.2, -7.8] | -47.2 [-68.9, -27.8] | +6.3 [-15.2, +28.9] | +1.8 [-6.7, +10.2] |
| GPT-5.6 Sol | -18.7 [-31.3, -7.1] | -28.0 [-47.5, -11.7] | +17.2 [+4.7, +32.1] | +10.2 [+1.4, +19.7] |
| Jev | -11.8 [-24.7, +0.5] | -23.1 [-44.0, -5.6] | -14.5 [-31.7, +0.5] | -4.2 [-13.2, +4.9] |

Most common tagger reasons for 'knowledge-dependent': “identifying the transaction's fas 140 characterization requires outside context” (2); “attachment contents are unavailable; subject alone does not establish forecast relevance” (2); “recognizing raptor i's relevance requires outside enron matter knowledge” (1); “coral transaction agreements may require outside knowledge to identify prepay transactions” (1); “the attachment's contents are unavailable, so wfa and palmer require context” (1); “identifying delta iii as a prepay transaction requires outside enron knowledge” (1).

![Check A](fig_a_knowledge_dependence.png)

## Check B — ranking stability across known and unknown matters

Existing results only. Rank order of the systems per corpus and its agreement across corpora; F1 against the case-knowledge composite. n = 4 systems (5 in the roster table): Kendall W over four objects has almost no power, so the rank orders themselves and the magnitude of the F1 gaps carry the reading, not p-values.

**Four systems (Sol included): ablation named arms + Endo — all gold**

| Corpus (exposure) | gold | n pairs | prev. | mean κ | GPT-5.6 Luna P/R/F1 | GPT-5.6 Terra P/R/F1 | GPT-5.6 Sol P/R/F1 | Jev P/R/F1 | F1 rank order |
|---|---|---:|---:|---:|---|---|---|---|---|
| Enron — Complaint J (known) | human | 852 | 49% | 0.80 | 86/73/**79.3** | 91/64/**75.3** | 88/73/**79.7** | 91/59/**71.8** | Sol > Luna > Terra > Jev |
| Enron — Complaint K (known mailbox, knowledge-poor requests) | human | 999 | 50% | 0.76 | 93/46/**61.8** | 95/35/**51.5** | 93/47/**62.1** | 94/41/**57.3** | Sol > Luna > Jev > Terra |
| Mallinckrodt (less known) | LLM panel | 14720 | 11% | 0.78 | 64/97/**76.8** | 80/91/**85.0** † | 72/97/**82.7** | 85/82/**83.5** | Terra > Jev > Sol > Luna |
| Veridian (synthetic) (unknown) | synthetic planner gold | 10000 | 10% | 0.83 | 69/98/**81.0** | 73/98/**83.8** | 72/97/**82.6** | 84/89/**86.5** | Jev > Terra > Sol > Luna |
| Endo (post-cutoff documents) (less known) | LLM panel | 16000 | 16% | 0.76 | 85/94/**89.1** † | 96/93/**94.6** † | 92/92/**91.6** † | 87/68/**76.7** | Terra > Sol > Luna > Jev |
- Kendall W (f1): **0.14** over 5 corpora (enron_j, enron_k, mnk, veridian, endo), p≈0.56; mean ranks GPT-5.6 Luna 15.0, GPT-5.6 Terra 11.0, GPT-5.6 Sol 10.0, Jev 14.0
- Kendall W (recall): **0.65** over 5 corpora (enron_j, enron_k, mnk, veridian, endo), p≈0.02; mean ranks GPT-5.6 Luna 7.0, GPT-5.6 Terra 14.0, GPT-5.6 Sol 10.0, Jev 19.0
- Kendall W (precision): **0.73** over 5 corpora (enron_j, enron_k, mnk, veridian, endo), p≈0.01; mean ranks GPT-5.6 Luna 19.0, GPT-5.6 Terra 7.0, GPT-5.6 Sol 15.0, Jev 9.0
- Kendall W (f1 without endo): **0.10** over 4 corpora (enron_j, enron_k, mnk, veridian), p≈0.75; mean ranks GPT-5.6 Luna 12.0, GPT-5.6 Terra 10.0, GPT-5.6 Sol 8.0, Jev 10.0
- Kendall W (f1 without endo enron k): **0.20** over 3 corpora (enron_j, mnk, veridian), p≈0.61; mean ranks GPT-5.6 Luna 10.0, GPT-5.6 Terra 6.0, GPT-5.6 Sol 7.0, Jev 7.0
- GPT-5.6 Luna: F1 vs case score Spearman ρ = +0.00 (perm. p 1.00); difficulty-adjusted ρ = +0.80 (p 0.33) over 4 corpora
- GPT-5.6 Terra: F1 vs case score Spearman ρ = -0.20 (perm. p 0.92); difficulty-adjusted ρ = -0.20 (p 0.92) over 4 corpora
- GPT-5.6 Sol: F1 vs case score Spearman ρ = -0.20 (perm. p 0.92); difficulty-adjusted ρ = +0.80 (p 0.34) over 4 corpora
- Mean-LLM − Jev F1 gap vs mean LLM case score: ρ = +0.80 over enron_j, mnk, veridian, endo; gaps enron_j +6.3, mnk -2.0, veridian -4.1, endo +15.1

**Four systems (Sol included): ablation named arms + Endo — gray excluded**

| Corpus (exposure) | gold | n pairs | prev. | mean κ | GPT-5.6 Luna P/R/F1 | GPT-5.6 Terra P/R/F1 | GPT-5.6 Sol P/R/F1 | Jev P/R/F1 | F1 rank order |
|---|---|---:|---:|---:|---|---|---|---|---|
| Enron — Complaint J (known) | human | 852 | 49% | 0.80 | 86/73/**79.3** | 91/64/**75.3** | 88/73/**79.7** | 91/59/**71.8** | Sol > Luna > Terra > Jev |
| Enron — Complaint K (known mailbox, knowledge-poor requests) | human | 999 | 50% | 0.76 | 93/46/**61.8** | 95/35/**51.5** | 93/47/**62.1** | 94/41/**57.3** | Sol > Luna > Jev > Terra |
| Mallinckrodt (less known) | LLM panel | 13730 | 10% | 0.83 | 71/99/**82.9** | 92/97/**94.2** † | 85/99/**91.3** | 94/90/**91.8** | Terra > Jev > Sol > Luna |
| Veridian (synthetic) (unknown) | synthetic planner gold | 9322 | 8% | 0.86 | 74/100/**85.0** | 80/100/**88.9** | 78/99/**87.7** | 89/95/**92.1** | Jev > Terra > Sol > Luna |
| Endo (post-cutoff documents) (less known) | LLM panel | 14720 | 13% | 0.91 | 100/100/**100.0** † | 100/100/**100.0** † | 100/100/**100.0** † | 93/78/**84.9** | Luna > Terra > Sol > Jev |
- Kendall W (f1): **0.10** over 5 corpora (enron_j, enron_k, mnk, veridian, endo), p≈0.70; mean ranks GPT-5.6 Luna 14.0, GPT-5.6 Terra 12.0, GPT-5.6 Sol 10.0, Jev 14.0
- Kendall W (recall): **0.64** over 5 corpora (enron_j, enron_k, mnk, veridian, endo), p≈0.02; mean ranks GPT-5.6 Luna 8.5, GPT-5.6 Terra 13.5, GPT-5.6 Sol 9.0, Jev 19.0
- Kendall W (precision): **0.46** over 5 corpora (enron_j, enron_k, mnk, veridian, endo), p≈0.07; mean ranks GPT-5.6 Luna 17.0, GPT-5.6 Terra 8.0, GPT-5.6 Sol 15.0, Jev 10.0
- Kendall W (f1 without endo): **0.10** over 4 corpora (enron_j, enron_k, mnk, veridian), p≈0.75; mean ranks GPT-5.6 Luna 12.0, GPT-5.6 Terra 10.0, GPT-5.6 Sol 8.0, Jev 10.0
- Kendall W (f1 without endo enron k): **0.20** over 3 corpora (enron_j, mnk, veridian), p≈0.61; mean ranks GPT-5.6 Luna 10.0, GPT-5.6 Terra 6.0, GPT-5.6 Sol 7.0, Jev 7.0
- GPT-5.6 Luna: F1 vs case score Spearman ρ = -0.40 (perm. p 0.76); difficulty-adjusted ρ = +0.60 (p 0.40) over 4 corpora
- GPT-5.6 Terra: F1 vs case score Spearman ρ = -0.20 (perm. p 0.92); difficulty-adjusted ρ = -0.40 (p 0.75) over 4 corpora
- GPT-5.6 Sol: F1 vs case score Spearman ρ = -0.20 (perm. p 0.92); difficulty-adjusted ρ = +0.80 (p 0.34) over 4 corpora
- Mean-LLM − Jev F1 gap vs mean LLM case score: ρ = +0.80 over enron_j, mnk, veridian, endo; gaps enron_j +6.3, mnk -2.4, veridian -4.9, endo +15.1

**Main-study roster (adds Jeb Bush and CUAD; Sol absent) — all gold**

| Corpus (exposure) | gold | n pairs | prev. | mean κ | GPT-5.6 Luna P/R/F1 | GPT-5.6 Terra P/R/F1 | Jev P/R/F1 | Claude Sonnet 5 P/R/F1 | Gemini 3.8 Flash P/R/F1 | F1 rank order |
|---|---|---:|---:|---:|---|---|---|---|---|---|
| Jeb Bush (TREC 2016) (known) | human | 34276 | 3% | 0.85 | 61/93/**73.3** | 65/94/**76.4** | 75/76/**75.6** | 74/88/**80.5** | 68/92/**78.0** | Claude Sonnet 5 > Gemini 3.8 Flash > Terra > Jev > Luna |
| Mallinckrodt (less known) | LLM panel | 14720 | 11% | 0.76 | 64/97/**76.8** | 80/92/**85.3** † | 86/82/**83.8** | 74/91/**81.3** † | 86/96/**90.4** † | Gemini 3.8 Flash > Terra > Jev > Claude Sonnet 5 > Luna |
| CUAD contracts (benchmark (no case channels)) | human | 77928 | 1% | 0.77 | 52/79/**62.9** | 59/76/**66.5** | 52/83/**63.6** | 47/85/**60.5** | 62/80/**69.8** | Gemini 3.8 Flash > Terra > Jev > Luna > Claude Sonnet 5 |
| Veridian (synthetic) (unknown) | synthetic planner gold | 19540 | 11% | 0.81 | 70/99/**81.8** | 74/98/**84.2** | 84/90/**86.6** | 77/97/**86.0** | 86/95/**90.6** | Gemini 3.8 Flash > Jev > Claude Sonnet 5 > Terra > Luna |
| Endo (post-cutoff documents) (less known) | LLM panel | 16000 | 16% | 0.74 | 85/94/**89.1** † | 96/93/**94.6** † | 87/68/**76.7** | — | — | — |
- Kendall W (f1): **0.62** over 4 corpora (jebbush, mnk, cuad, veridian), p≈0.04; mean ranks GPT-5.6 Luna 19.0, GPT-5.6 Terra 11.0, Jev 12.0, Claude Sonnet 5 13.0, Gemini 3.8 Flash 5.0
- Kendall W (recall): **0.26** over 4 corpora (jebbush, mnk, cuad, veridian), p≈0.38; mean ranks GPT-5.6 Luna 8.0, GPT-5.6 Terra 11.0, Jev 17.0, Claude Sonnet 5 12.0, Gemini 3.8 Flash 12.0
- Kendall W (precision): **0.54** over 4 corpora (jebbush, mnk, cuad, veridian), p≈0.07; mean ranks GPT-5.6 Luna 18.0, GPT-5.6 Terra 13.0, Jev 9.0, Claude Sonnet 5 14.0, Gemini 3.8 Flash 6.0
- GPT-5.6 Luna: F1 vs case score Spearman ρ = -0.40 (perm. p 0.76); difficulty-adjusted ρ = +0.60 (p 0.40) over 4 corpora
- GPT-5.6 Terra: F1 vs case score Spearman ρ = -0.20 (perm. p 0.92); difficulty-adjusted ρ = +0.40 (p 0.76) over 4 corpora
- Mean-LLM − Jev F1 gap vs mean LLM case score: ρ = +0.80 over jebbush, mnk, veridian, endo; gaps jebbush -0.7, mnk -2.8, veridian -3.6, endo +15.2

**Main-study roster (adds Jeb Bush and CUAD; Sol absent) — gray excluded**

| Corpus (exposure) | gold | n pairs | prev. | mean κ | GPT-5.6 Luna P/R/F1 | GPT-5.6 Terra P/R/F1 | Jev P/R/F1 | Claude Sonnet 5 P/R/F1 | Gemini 3.8 Flash P/R/F1 | F1 rank order |
|---|---|---:|---:|---:|---|---|---|---|---|---|
| Jeb Bush (TREC 2016) (known) | human | 34263 | 3% | 0.85 | 60/93/**73.2** | 64/94/**76.4** | 75/76/**75.5** | 74/88/**80.4** | 68/92/**77.9** | Claude Sonnet 5 > Gemini 3.8 Flash > Terra > Jev > Luna |
| Mallinckrodt (less known) | LLM panel | 13730 | 10% | 0.84 | 71/99/**82.9** | 91/98/**94.3** † | 94/90/**92.0** | 83/98/**89.6** † | 96/100/**97.5** † | Gemini 3.8 Flash > Terra > Jev > Claude Sonnet 5 > Luna |
| CUAD contracts (benchmark (no case channels)) | human | 77907 | 1% | 0.77 | 52/79/**63.2** | 59/76/**66.8** | 52/83/**63.8** | 47/85/**60.8** | 62/80/**70.2** | Gemini 3.8 Flash > Terra > Jev > Luna > Claude Sonnet 5 |
| Veridian (synthetic) (unknown) | synthetic planner gold | 18193 | 8% | 0.85 | 77/100/**86.7** | 82/100/**90.2** | 90/96/**92.8** | 87/99/**92.6** | 94/100/**96.9** | Gemini 3.8 Flash > Jev > Claude Sonnet 5 > Terra > Luna |
| Endo (post-cutoff documents) (less known) | LLM panel | 14720 | 13% | 0.89 | 100/100/**100.0** † | 100/100/**100.0** † | 93/78/**84.9** | — | — | — |
- Kendall W (f1): **0.62** over 4 corpora (jebbush, mnk, cuad, veridian), p≈0.04; mean ranks GPT-5.6 Luna 19.0, GPT-5.6 Terra 11.0, Jev 12.0, Claude Sonnet 5 13.0, Gemini 3.8 Flash 5.0
- Kendall W (recall): **0.23** over 4 corpora (jebbush, mnk, cuad, veridian), p≈0.45; mean ranks GPT-5.6 Luna 10.5, GPT-5.6 Terra 10.5, Jev 17.0, Claude Sonnet 5 12.5, Gemini 3.8 Flash 9.5
- Kendall W (precision): **0.54** over 4 corpora (jebbush, mnk, cuad, veridian), p≈0.07; mean ranks GPT-5.6 Luna 18.0, GPT-5.6 Terra 13.0, Jev 9.0, Claude Sonnet 5 14.0, Gemini 3.8 Flash 6.0
- GPT-5.6 Luna: F1 vs case score Spearman ρ = -0.40 (perm. p 0.76); difficulty-adjusted ρ = +0.60 (p 0.40) over 4 corpora
- GPT-5.6 Terra: F1 vs case score Spearman ρ = -0.20 (perm. p 0.92); difficulty-adjusted ρ = +0.40 (p 0.76) over 4 corpora
- Mean-LLM − Jev F1 gap vs mean LLM case score: ρ = +0.80 over jebbush, mnk, veridian, endo; gaps jebbush -0.7, mnk -3.4, veridian -4.4, endo +15.1

† system is a member of that corpus's gold panel (its score is partly circular). Case-knowledge composite (0–100) per corpus: GPT-5.6 Luna: enron_j 91, enron_k 91, jebbush 86, mnk 56, endo 64, veridian 0; GPT-5.6 Sol: enron_j 67, enron_k 67, jebbush 71, mnk 54, endo 62, veridian 0; GPT-5.6 Terra: enron_j 95, enron_k 95, jebbush 73, mnk 49, endo 59, veridian 0.
Human-disagreement proxies (explore index, contested / n): enron_j 0.0%, enron_k 3.0%, jebbush 0.0%, mnk 0.0%, endo 0.0%, cuad 0.0%, veridian 0.0%.

![Check B](fig_b_ranking_stability.png)

## Check C — counterfactual conflict documents

Each pair is one short document in two versions: FACTUAL (consistent with the well-known fact) and COUNTERFACTUAL (the text contradicts it, flipping true relevance to a nameless request). The correct call follows the text. 'text-follow' = share of documents called as their text implies; on counterfactual documents 1 − text-follow is the knowledge-following rate. Veridian pairs assert and then contradict facts that exist only in the task context, so they measure 'fails to read the edit' with no world knowledge possible.

| Matter | System | pairs | text-follow FACTUAL | text-follow COUNTERFACTUAL [95% Wilson] | CF − factual text-follow, pp [paired 95% CI] | McNemar p | fact-relevant→irrelevant CF text-follow | fact-irrelevant→relevant CF text-follow | vs Veridian baseline |
|---|---|---:|---:|---|---|---:|---:|---:|---|
| enron | GPT-5.6 Luna | 30 | 100% | 97% [83, 99] | -3.3 [-10.0, -0.0] | 1 | 94% | 100% | +13.3 pp [+0.0, +26.7] |
| enron | GPT-5.6 Terra | 30 | 100% | 100% [89, 100] | -0.0 [-0.0, -0.0] | 1 | 100% | 100% | +10.0 pp [+0.0, +20.0] |
| enron | GPT-5.6 Sol | 30 | 100% | 100% [89, 100] | -0.0 [-0.0, -0.0] | 1 | 100% | 100% | +3.3 pp [+0.0, +10.0] |
| enron | Jev | 30 | 100% | 100% [89, 100] | -0.0 [-0.0, -0.0] | 1 | 100% | 100% | +10.0 pp [+0.0, +20.0] |
| jebbush | GPT-5.6 Luna | 30 | 97% | 80% [63, 90] | -16.7 [-33.3, -0.0] | 0.125 | 68% | 100% | -3.3 pp [-23.3, +16.7] |
| jebbush | GPT-5.6 Terra | 30 | 100% | 73% [56, 86] | -26.7 [-43.3, -13.3] | 0.00781 | 58% | 100% | -16.7 pp [-36.7, +3.3] |
| jebbush | GPT-5.6 Sol | 30 | 100% | 90% [74, 97] | -10.0 [-23.3, -0.0] | 0.25 | 84% | 100% | -6.7 pp [-20.0, +3.3] |
| jebbush | Jev | 30 | 100% | 83% [66, 93] | -16.7 [-30.0, -3.3] | 0.0625 | 74% | 100% | -6.7 pp [-23.3, +10.0] |
| mnk | GPT-5.6 Luna | 30 | 100% | 73% [56, 86] | -26.7 [-43.3, -10.0] | 0.00781 | 56% | 93% | -10.0 pp [-30.0, +10.0] |
| mnk | GPT-5.6 Terra | 30 | 100% | 87% [70, 95] | -13.3 [-26.7, -3.3] | 0.125 | 75% | 100% | -3.3 pp [-20.0, +10.0] |
| mnk | GPT-5.6 Sol | 30 | 100% | 80% [63, 90] | -20.0 [-33.3, -6.7] | 0.0312 | 69% | 93% | -16.7 pp [-33.3, -3.3] |
| mnk | Jev | 30 | 97% | 93% [79, 98] | -3.3 [-13.3, +6.7] | 1 | 88% | 100% | +3.3 pp [-10.0, +16.7] |
| endo | GPT-5.6 Luna | 30 | 100% | 83% [66, 93] | -16.7 [-30.0, -3.3] | 0.0625 | 73% | 93% | +0.0 pp [-20.0, +20.0] |
| endo | GPT-5.6 Terra | 30 | 100% | 83% [66, 93] | -16.7 [-30.0, -3.3] | 0.0625 | 73% | 93% | -6.7 pp [-23.3, +10.0] |
| endo | GPT-5.6 Sol | 30 | 100% | 83% [66, 93] | -16.7 [-30.0, -3.3] | 0.0625 | 73% | 93% | -13.3 pp [-30.0, +0.0] |
| endo | Jev | 30 | 100% | 90% [74, 97] | -10.0 [-20.0, -0.0] | 0.25 | 80% | 100% | +0.0 pp [-16.7, +13.3] |
| veridian | GPT-5.6 Luna | 30 | 100% | 83% [66, 93] | -16.7 [-30.0, -3.3] | 0.0625 | 75% | 100% |  |
| veridian | GPT-5.6 Terra | 30 | 100% | 90% [74, 97] | -10.0 [-20.0, -0.0] | 0.25 | 85% | 100% |  |
| veridian | GPT-5.6 Sol | 30 | 100% | 97% [83, 99] | -3.3 [-10.0, -0.0] | 1 | 95% | 100% |  |
| veridian | Jev | 30 | 100% | 90% [74, 97] | -10.0 [-20.0, -0.0] | 0.25 | 85% | 100% |  |

Pooled over the four real matters (120 pairs per system):

| System | factual text-follow (reading ceiling) | counterfactual text-follow | knowledge-following | on fact-relevant tokens made irrelevant | on fact-irrelevant tokens made relevant | vs Veridian baseline |
|---|---:|---|---:|---:|---:|---|
| GPT-5.6 Luna | 99% | 83.3% [75.7, 88.9] | **16.7%** | 27% (n=66) | 4% (n=54) | +0.0 [-14.2, +15.0] |
| GPT-5.6 Terra | 100% | 85.8% [78.5, 91.0] | **14.2%** | 24% (n=66) | 2% (n=54) | -4.2 [-15.8, +8.3] |
| GPT-5.6 Sol | 100% | 88.3% [81.4, 92.9] | **11.7%** | 18% (n=66) | 4% (n=54) | -8.3 [-16.7, +0.8] |
| Jev | 99% | 91.7% [85.3, 95.4] | **8.3%** | 15% (n=66) | 0% (n=54) | +1.7 [-9.2, +14.2] |

Note on the Veridian baseline: its overrides sit almost entirely on the surgeon-payments request, where a document *denying* any payment to a named surgeon is arguably still 'concerning' surgeon payments — part of that baseline is request-scope ambiguity rather than a failure to read the edit, so the baseline is lenient and the vs-Veridian comparison should be read with that in mind. The real-matter overrides (Roxicodone 'antacid' still called opioid marketing at p = 0.99; a Schiavo road-renaming file called an end-of-life dispute) have no such ambiguity.

Counterfactual documents where the call followed world knowledge rather than the text (per system; token → request):

- enron / GPT-5.6 Luna (1): Chewco → related_party (p=0.98)
- jebbush / GPT-5.6 Luna (6): Schiavo → family_dispute (p=0.99); Schiavo → family_dispute (p=0.99); Elián → family_dispute (p=0.98); One Florida → preferences (p=0.97); One Florida → preferences (p=0.98); One Florida → preferences (p=0.98)
- jebbush / GPT-5.6 Terra (8): Schiavo → family_dispute (p=0.99); Schiavo → family_dispute (p=0.99); Schiavo → family_dispute (p=0.98); Elián → family_dispute (p=0.78); One Florida → preferences (p=0.68); One Florida → preferences (p=0.97); One Florida → preferences (p=0.90); One Florida → preferences (p=0.95)
- jebbush / GPT-5.6 Sol (3): Schiavo → family_dispute (p=0.98); One Florida → preferences (p=0.80); One Florida → preferences (p=0.97)
- jebbush / Jev (5): Schiavo → family_dispute (p=0.52); Schiavo → family_dispute (p=0.79); Schiavo → family_dispute (p=0.73); Schiavo → family_dispute (p=0.78); One Florida → preferences (p=0.53)
- mnk / GPT-5.6 Luna (8): Exalgo → opioid_marketing (p=0.99); Exalgo → opioid_marketing (p=0.98); Exalgo → opioid_marketing (p=0.99); Methadose → opioid_marketing (p=0.98); Roxicodone → opioid_marketing (p=0.99); Roxicodone → opioid_marketing (p=0.99); Roxicodone → opioid_marketing (p=0.99); Covidien Imaging → subsidiary_dea (p=0.12)
- mnk / GPT-5.6 Terra (4): Exalgo → opioid_marketing (p=0.97); Exalgo → opioid_marketing (p=0.98); Methadose → opioid_marketing (p=0.98); Roxicodone → opioid_marketing (p=0.99)
- mnk / GPT-5.6 Sol (6): Exalgo → opioid_marketing (p=0.76); Exalgo → opioid_marketing (p=0.97); Exalgo → opioid_marketing (p=0.99); Methadose → opioid_marketing (p=0.96); Roxicodone → opioid_marketing (p=0.98); Covidien Imaging → subsidiary_dea (p=0.08)
- mnk / Jev (2): Roxicodone → opioid_marketing (p=0.54); Roxicodone → opioid_marketing (p=0.67)
- endo / GPT-5.6 Luna (5): Opana ER → opioid_marketing (p=0.99); Opana ER → opioid_marketing (p=0.98); Opana ER → opioid_marketing (p=0.98); Opana ER → opioid_marketing (p=0.99); Voltaren Gel → opioid_marketing (p=0.02)
- endo / GPT-5.6 Terra (5): Opana ER → opioid_marketing (p=0.98); Opana ER → opioid_marketing (p=0.93); Opana ER → opioid_marketing (p=0.93); Percocet → opioid_marketing (p=0.97); Fortesta → abuse_deterrence (p=0.08)
- endo / GPT-5.6 Sol (5): Opana ER → opioid_marketing (p=0.97); Opana ER → opioid_marketing (p=0.97); Opana ER → opioid_marketing (p=0.99); Percocet → opioid_marketing (p=0.98); Aveed → abuse_deterrence (p=0.03)
- endo / Jev (3): Opana ER → opioid_marketing (p=0.69); Opana ER → opioid_marketing (p=0.75); Opana ER → opioid_marketing (p=0.73)

![Check C](fig_c_counterfactual_conflict.png)

## Check D — knowledge injection on Veridian

If matter knowledge helps relevance review, supplying it for the one matter no system can know should raise F1. The brief is fictional (bible-consistent) and names the parties, products, people, deals and code names, timeline and outcome.

Brief: `data/ablation/veridian_brief.md` (5,726 characters, ≈1,431 tokens), appended to the Veridian task context exactly as the Mallinckrodt brief arm did. Run on a stratified subset of 491 of the 1000 ablation documents (stratum = the document's positive-label set; every request keeps its positive share) because the full arm's token volume would have exceeded the $15 cap; the without-brief side is the ablation's existing named run restricted to the same documents.

| System | pairs (docs) | without brief P/R/F1 | with brief P/R/F1 | ΔP [95% CI] | ΔR [95% CI] | ΔF1 [95% CI] | labels changed | right→wrong / wrong→right (McNemar p) | Mallinckrodt brief ΔF1 (ablation) | Big Thorium brief ΔF1 (ablation) | paid |
|---|---:|---|---|---|---|---|---:|---|---|---|---:|
| GPT-5.6 Luna | 4910 (491) | 67.7/99.0/**80.4** | 67.1/99.2/**80.1** | -0.5 [-2.3, +1.3] | +0.2 [-0.6, +1.2] | -0.3 [-1.7, +1.1] | 1.8% | 47 / 42 (0.672) | -1.0 [-1.8, -0.2] | -0.8 [-4.3, +2.7] | $0.30 |
| GPT-5.6 Terra | 4910 (491) | 71.3/97.9/**82.5** | 70.1/98.3/**81.9** | -1.2 [-3.2, +0.8] | +0.4 [-0.6, +1.5] | -0.6 [-2.1, +0.8] | 1.7% | 46 / 36 (0.32) | -0.7 [-1.5, +0.1] | -1.8 [-3.9, +0.2] | $2.96 |
| GPT-5.6 Sol | 4910 (491) | 70.8/98.1/**82.3** | 69.1/98.6/**81.3** | -1.7 [-3.8, +0.3] | +0.4 [-0.6, +1.7] | -1.0 [-2.6, +0.5] | 2.0% | 57 / 42 (0.159) | +0.6 [-0.1, +1.3] | +0.6 [-1.1, +2.5] | $5.72 |
| Jev | 4910 (491) | 83.7/89.0/**86.3** | 81.8/92.6/**86.8** | -1.9 [-4.1, +0.2] | +3.5 [+1.5, +5.6] | +0.5 [-1.1, +2.2] | 1.2% | 30 / 31 (1) | +1.3 [+0.5, +2.3] | -1.1 [-4.0, +1.7] | $0.11 |

Per request ΔF1 (with − without, pp; 500-draw cluster bootstrap):

| Request | GPT-5.6 Luna | GPT-5.6 Terra | GPT-5.6 Sol | Jev |
|---|---|---|---|---|
| rfp01_recall | -0.7 [-4.2, +2.6] | -0.9 [-3.1, +0.0] | -1.8 [-4.6, +0.0] | +1.1 [+0.0, +3.9] |
| rfp02_design_history | +4.8 [-1.4, +11.1] | -2.2 [-5.9, +1.5] | +4.9 [+0.0, +9.8] | +7.4 [+1.6, +16.0] |
| rfp03_complaints | +1.1 [-1.7, +3.9] | +0.0 [-2.1, +2.6] | -5.3 [-9.2, -1.2] | -0.9 [-3.7, +1.9] |
| rfp04_fda | -0.8 [-4.7, +3.2] | -2.6 [-5.7, +0.6] | +0.3 [-3.7, +5.0] | +1.3 [-2.1, +5.4] |
| rfp06_marketing | -1.5 [-5.2, +2.4] | +0.6 [-5.3, +6.3] | +1.7 [-2.0, +5.9] | -0.5 [-5.4, +3.8] |
| rfp07_surgeon_payments | -1.9 [-6.8, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | -3.8 [-11.1, +0.0] |
| rfp08_sales_scripts | -0.9 [-4.0, +2.3] | +0.4 [-6.6, +7.1] | +1.3 [-5.0, +8.1] | +0.4 [-6.1, +6.9] |
| rfp09_registry_decision | -1.1 [-4.7, +2.3] | +0.3 [-2.4, +3.3] | -5.2 [-9.0, -2.2] | +1.4 [-3.2, +6.2] |
| rfp13_financials | -4.1 [-8.4, +0.0] | -3.9 [-8.9, +1.0] | -0.9 [-4.3, +2.1] | -2.5 [-6.7, +0.0] |
| rfp17_personnel | +2.6 [-3.8, +10.0] | +3.9 [-6.4, +13.5] | +5.7 [-0.6, +12.8] | +2.5 [-7.1, +12.4] |

Gray-excluded ΔF1: GPT-5.6 Luna +0.0 [-1.6, +1.7] (n=4584), GPT-5.6 Terra -1.2 [-3.0, +0.7] (n=4584), GPT-5.6 Sol -0.6 [-2.4, +1.3] (n=4584), Jev -0.0 [-1.4, +1.4] (n=4584).

![Check D](fig_d_knowledge_injection.png)

## Caveats

- Check A's tagger is Luna, a system under test; tags describe documents, not calls, and the same tags are applied to all four systems, so a tagger bias would shift the KD share, not a system's contrast.
- Check B has four (five) systems and five to seven corpora; Endo's gold is a Luna+Terra+Sol panel and Mallinckrodt's a Sonnet 5+Terra+Gemini panel, so those cells are partly circular and are marked. Veridian's gold is the synthetic planner's.
- Check C documents are short and synthetic (templated like the classifier-native T1 items); the factual versions give each system's reading ceiling on the same material.
- Check D ran on a stratified half of the Veridian ablation documents for cost; the brief is one author's fictional background and ~1k tokens, comparable to the Mallinckrodt brief.
- All deltas are paired by document (cluster bootstrap over documents, 2,000 draws); C and D CIs are 95%.
- Check D was repeated on Big Thorium (the Relativity aiR for Review demo workspace: public documents, invented case) with Relativity's own aiR case summary as the brief, against a leave-one-out panel gold: ΔF1 gpt-5.6-luna -0.8 [-4.3, +2.7]; gpt-5.6-terra -1.8 [-3.9, +0.2]; gpt-5.6-sol +0.6 [-1.1, +2.5]; jev@base -1.1 [-4.0, +1.7] (`results/ablation/bigthorium/REPORT.md`).
