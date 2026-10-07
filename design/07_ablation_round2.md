# Pseudonymisation ablation, round 2 — CUAD (rename + paraphrase) and the Jeb Bush e-mails

Companion to `design/06_contamination_probe.md` (contamination probes) and `results/ablation/REPORT.md` (round 1: Enron J vs K, Veridian,
Mallinckrodt). Round 1 answered "does *knowing the matter* change review results?" for e-mail: the knowledge effect Δ(J) − Δ(K) was within
±2.6 F1 points for every system, intervals through zero. Round 2 extends the question to the two corpora round 1 could not cover:

* **CUAD**, the one corpus with document-level memorisation (finish-the-document LCS-F1 0.25–0.31 against a 0.15 floor; 5–10 % of windows
  with a ≥15-word verbatim run) and benchmark knowledge (40–41 of 41 clause categories recited). Renaming is not enough here: what the
  models hold is the *text*, so a second perturbation (paraphrase) is needed to remove the surface the memory is keyed on.
* **Jeb Bush**, where the models hold no trace of the collection but recite the governorship (recount, Schiavo, Rilya Wilson, Medicaid
  reform) — the "familiar matter, unfamiliar documents" case.

Code: `ediscovery_bench/ablation/{round2.py, round2_score.py, paraphrase.py, cuad_names.py, jeb_names.py}`; CLI `bench ablation2-*`.
Results: `results/ablation/round2/{REPORT.md, summary.json, fig_cuad.png, fig_jeb.png}`. Spend ledger: `data/ablation/round2_spend.json`.

Section C (2026-10-06) adds a sixth collection, **Big Thorium** — the Relativity aiR for Review demo workspace, distributed by Relativity:
public documents, invented case — as a second floor beside Veridian
(`ediscovery_bench/ablation/bigthorium.py`, `results/ablation/bigthorium/`).

---

## A. CUAD

### Unit of review and a structural point that shaped the design

The CUAD task unit is a **contract excerpt** (paragraph), headed `Contract: <title> (<company>, <year>)` / `Excerpt k of n`; 6,494 excerpts
from 102 contracts, 12 clause requests per excerpt (multi arm), gold from expert span overlap. Positives are rare: 718 excerpts carry at
least one positive label (867 labels). So:

* the sample is **every positive-bearing excerpt (718) plus 482 negatives spread over all 102 contracts** = 1,200 excerpts × 12 requests =
  14,400 paired decisions per condition; the bootstrap clusters by **contract** (102 clusters), because renaming is a per-contract
  treatment and memorisation is a per-contract property;
* renaming is **per contract** (one consistent mapping across all its excerpts), paraphrase is **per excerpt** (the header line is kept verbatim
  so the model still sees title and position);
* the memorisation dose is **per contract** (windows from the contract's own text), so the dose–response analysis has 89–102 points, not 1,200.

### Conditions

| condition | what changes | how |
|---|---|---|
| `named` | nothing (fresh run; the study's rows were not reused so that all three conditions share one prompt cache and one day) | — |
| `renamed` | party names and their defined-term aliases, product names, signature-block people, US-state jurisdictions, every date (year shifted by a per-contract −3..+3), every numeric dollar amount (per-contract factor 0.6–1.5, re-rounded to the original roundness), the header company token | `cuad_names.ContractRenamer`: organisation names found by suffix (Inc., LLC, Ltd, GmbH …), short names by frequency (an English word is treated as a party short name only if it recurs standalone ≥3×), defined-term aliases from `("X")` constructs, acronyms kept unless they are party aliases. Mapping per contract in `data/ablation/cuad_mapping.json` (873 phrases; 59 contracts with people) |
| `paraphrased` | wording and sentence structure, by GPT-5.6 Luna (temperature 0, flex) | `paraphrase.py`: a strict preservation prompt (every party, capitalised defined term and quoted definition, number, date, period and cross-reference verbatim and in order; every clause boundary; same obligations with the same modality). Deterministic checks after each rewrite — number multiset equality, quoted-term recall, capitalised-term recall ≥ 0.8, length ratio 0.55–1.7 — with one retry carrying the discrepancies; a second model (Terra) then judges legal equivalence on a sample |

Example mapping (contract 18, Harpoon/AbbVie development agreement): `AbbVie Biotechnology → Lorimar Ventures`, `AbbVie → Tremont`,
`Harpoon Therapeutics → Ellsworth Capital`, `Harpoon → Ellsworth`, `Delaware → Georgia`, `Illinois → Ohio`, year −3, amounts × 0.6.

### Controls (recommendation and what was run)

| control | what it isolates | status |
|---|---|---|
| **(i) within-CUAD dose–response** (primary) | if memorisation drives results, Δ should grow with the contract's memorisation score. Score = finish-the-document LCS-F1 on two windows of each contract's *original* text, pooled over Luna/Terra/Sol (`bench ablation2-memo`, 157 windows, 89 contracts; tercile cuts 0.24 / 0.32) | run |
| **(ii) Veridian paraphrase** (secondary) | the *cost of paraphrase itself* on a corpus no model can have seen: the identical pipeline (e-mail variant of the prompt) on 500 of the round-1 Veridian documents, paired against the round-1 `named` rows. Different genre (e-mail vs contract) — stated, and the reason it is secondary | run |
| (iii) post-cutoff EDGAR contracts | the clean control: same genre, unseen. Needs expert clause labels on ~100 contracts (CUAD's labelling cost was ~$2M for 510 contracts); a 20-contract version with a single lawyer-reviewer is ~2 weeks of labelling. No API cost beyond a repeat of this arm (~$14 paid per 1,200 excerpts) | optional, not run |

Alongside: the round-1 Veridian **rename** Δ (1,000 docs) is re-scored here as the renaming floor; and the finish-the-document probe is run
on the renamed and paraphrased versions of the same windows, so one can see directly how much of the memorised surface each perturbation
removes.

### Hypotheses

* H-A1 (rename). If CUAD results depend on recognising *which* contract or party this is, Δ(renamed) will be negative and larger than the
  Veridian renaming floor. If the models' CUAD knowledge is clause-type knowledge and memorised *text*, renaming parties will do nothing.
* H-A2 (paraphrase). If memorised text is what the models match on, Δ(paraphrased) will be negative beyond the paraphrase cost measured on
  Veridian, and larger in the high-memorisation tercile. A Δ within the Veridian cost, flat across terciles, means the review results do not
  rest on the memorised surface.
* Jev is a system under test under the same hypotheses; its vendor's no-pre-training statement is a claim, not an assumption.

### Metrics

ΔF1 / ΔRecall / ΔPrecision (perturbed − named) with cluster-bootstrap 95 % CIs (B = 2000); exact McNemar on discordant decisions; flips
(right→wrong / wrong→right, positives lost, false positives added); knowledge effects as differences of bootstrap delta distributions:
rename effect = Δ(CUAD renamed) − Δ(Veridian renamed), paraphrase effect = Δ(CUAD paraphrased) − Δ(Veridian paraphrased); dose–response by
tercile of contract memorisation plus Spearman ρ of per-contract Δaccuracy against dose. Leakage check: one renamed excerpt per contract
shown to each LLM, asked which real companies signed (run 2026-10-06: Luna 11/102, Terra 23/102, Sol 33/102 named a real party).

---

## B. Jeb Bush

### Data — and the problem that changed the design, then unchanged it

The TREC 2016 Total Recall (athome4) collection is not redistributed with the repo. At the time of design only a 600-e-mail local subset
with text existed, which forced a 600-doc / 11-request design. The user then supplied the collection as `data/TREC 2016 - Jeb Bush.zip`
(464 MB; `Jeb Bush TXT/<docno>.txt` × 290,101 plus the 2015 athome1 per-topic responsive lists under `Responsive Docs/`). `bench
ablation2-build` extracts **only the 3,116 e-mails of the study's eval sample** (`data/trec/eval_ids.jsonl`) into
`data/trec/raw/jeb_bush_txt/` (gitignored, as is the zip) and writes `data/trec/eval.jsonl` with the same normalisation as `bench
trec-build`, so the ids match the study's eval file exactly. Nothing else is extracted; the 2015 responsive lists in the zip duplicate the
athome1 judgments already tracked under `data/trec/raw/athome1/`, which are the gold used.

Sample: **1,000 e-mails from the eval sample** — up to 60 gold positives per request (matter and control alike), the rest hard-negative and
random-stratum e-mails (558 / 207 / 235). The same documents serve both conditions; every request is asked of every document in one call.

### Topic split (from what the knowledge probes showed the models recite, and what is present with gold)

| role | requests (gold) | why |
|---|---|---|
| matter-specific | `recount_2000`, `rilya_wilson`, `medicaid_reform`, `gw_bush` (athome4); `a1_terri_schiavo` (athome1, complete judgments; request text written for round 2 in the style of `tasks/trec.yaml`) | the governorship events the M1/M2 probes produced unprompted (recount / Bush v. Gore, Schiavo and Terri's Law, Rilya Wilson and DCF, Medicaid reform, the President's brother) |
| control | `movie_gallery`, `condominiums`, `bottled_water`, `marketing`, `faith_based`, `nra_rifle`, `nra_aliens` | Florida-government topics no model recited; names in the documents carry no case knowledge for them |

Other athome1 topics present in the zip (Affirmative Action / One Florida, Judicial Selection, Tort Reform, Capital Punishment, Scarlet
Letter, Manatee ×2, School Funding, Medical Schools) have too few positives in the eval sample (7–35) or are not matter-specific; they were
not added. Elián González and the felon purge are not TREC topics.

### Renaming — the minimal mapping

Renaming Florida would break the topical relevance of most requests (Tallahassee, Everglades, Florida statutes, DCF, AHCA), so the mapping
removes **identification of the people**, not the state: the Governor and his family (`Jeb Bush → Cal Weston`, `jeb@jeb.org →
cal@calweston.org`, Columba, Noelle, "Governor bush" in lower case), the 2000 tickets and litigation (`Bush v. Gore → Weston v. Hartwell`,
Cheney, Lieberman, Nader), the people named in the requests (Katherine Harris, Rilya Wilson, Terri Schiavo and the Schindlers, Miriam
Oliphant), the senior staff and Florida public figures the probes produced (Shanahan, Stutler, Yablonski, Oviedo, Regier, Levine, Arduin,
Struhs, Castille, Fasano, Brogan, Jennings, Crist, Nelson, Graham, Butterworth …), and every surname that appears in a header field
(715 people, 19 phrases; `data/ablation/jeb_mapping.json`); e-mail local parts of the form `oviedon@`, `kshanahan@` follow. State domains
(`myflorida.com`, `eog.state.fl.us`), agencies, cities and statutes are kept. The request texts and context pass through the same renamer
(`data/ablation/jeb__renamed.yaml`); the context's "(1999–2007)" is dropped. Residual `Jeb`/`Bush` in the renamed documents: 0 of 1,000.

The **leakage check** (`bench ablation2-leak`) measures what is left: renamed e-mails are shown to each LLM, which is asked whose e-mail
collection they come from. The dose for dose–response is the number of mentions of public figures *other than the Governor* (0 / 1–2 / 3+:
536 / 274 / 190 documents).

### Hypotheses and metrics

Knowledge effect = **Δ(matter topics) − Δ(control topics) on the same documents, paired within each bootstrap draw** (cluster by document,
B = 2000). If knowing who these people are helps review, Δ(matter) < Δ(control). ΔF1 / R / P with CIs, McNemar, flips, per-request Δ,
dose bands on the matter topics, and Δ(matter) − Δ(Veridian renamed) as the cross-corpus comparison.

---

## Cost table (exact: prompt tokens from the study's observed calls, document tokens from the built files, output as observed; paid = flex tier with prompt caching)

| arm / condition | calls | Luna | Terra | Sol | Jev | row total |
|---|---|---|---|---|---|---|
| CUAD named | 1,200 | $0.47 | $4.71 | $8.89 | $0.14 | $14.20 |
| CUAD renamed | 1,200 | $0.47 | $4.70 | $8.88 | $0.14 | $14.19 |
| CUAD paraphrased | 1,200 | $0.47 | $4.71 | $8.90 | $0.14 | $14.21 |
| Veridian paraphrased (control) | 500 | $0.23 | $2.31 | $4.41 | $0.07 | $7.02 |
| Jeb named | 1,000 | $0.50 | $4.99 | $9.52 | $0.16 | $15.16 |
| Jeb renamed | 1,000 | $0.50 | $4.99 | $9.53 | $0.16 | $15.17 |
| **classification runs** | | **$2.64** | **$26.40** | **$50.12** | **$0.79** | **$79.95** |
| paraphrase generation (Luna; CUAD 1,200 + Veridian 500) | | $0.50 | | | | $0.50 |
| fidelity judge (Terra; 100 + 50) | | | $0.24 | | | $0.24 |
| memorisation probe (102 × 2 windows × 3 variants × 3 models) | | | | | | $1.81 |
| leakage checks (Jeb 150 + CUAD 102, 3 LLMs) | | | | | | $1.33 |
| **full version** | | | | | | **$83.83** ($83.04 on the OpenAI key) |
| **cheap version** = full without Terra | | | | | | **$57.44** |

Per-call paid rates (12 requests, flex, cached prefix): CUAD Luna $0.00039, Terra $0.0039, Sol $0.0074, Jev $0.00011; Jeb Luna $0.0005,
Terra $0.0050, Sol $0.0095, Jev $0.00016. List prices are ~2.6× the paid figures.

Budget rule applied on 2026-10-04: full > $75 → the cheap version was run first (Terra dropped everywhere; Luna and Sol span the price/quality
range and Sol carries the strongest CUAD memorisation signal). **Terra was added on 2026-10-06** once the OpenAI key was topped up (six runs,
$26.62 realised against $26.40 estimated, each within 2 %), together with the leak checks that the exhausted key had cut short ($0.78), so the
full version is what the tables, figures and the contamination pages now report.

### Pilot validation (before the main runs)

* Paraphrase, 60 excerpts: 59/60 passed the deterministic checks, 60/60 numbers preserved, 3 retries; mean word-sequence similarity to the
  original 0.66 (max 0.87) — the rewrites are real rewrites. $0.011.
* Memorisation probe, 4 contracts (51 responses): mean LCS-F1 vs the original continuation fell from 0.29 (original) to 0.26 (paraphrased)
  for Luna, 0.25 → 0.18 for Terra. $0.036.
* Jev smoke test, 5 documents on CUAD and Jeb: 115 rows, 0 errors, $0.001. Luna smoke test on renamed Jeb, 5 documents.

---

## Results

Full tables: `results/ablation/round2/REPORT.md`. Figures: `results/ablation/round2/fig_cuad.png`, `fig_jeb.png`. † = 95 % CI excludes zero.

### A. CUAD

| system | ΔF1 renamed | ΔF1 paraphrased | Veridian renamed (floor, r1, renamer v2) | Veridian paraphrased (control) | rename effect | paraphrase effect |
|---|---|---|---|---|---|---|
| GPT-5.6 Luna | −0.6 [−1.6, +0.4] | −1.3 [−2.7, −0.0] † | −0.1 [−0.9, +0.6] | −0.5 [−1.8, +0.7] | −0.4 [−1.7, +0.7] | −0.8 [−2.6, +1.0] |
| GPT-5.6 Terra | −0.7 [−1.7, +0.3] | −0.3 [−1.5, +0.9] | −0.4 [−1.2, +0.4] | −0.3 [−1.6, +0.9] | −0.3 [−1.6, +1.0] | +0.1 [−1.6, +1.7] |
| GPT-5.6 Sol | +0.2 [−0.8, +1.2] | −0.4 [−1.4, +0.5] | −1.0 [−1.9, −0.2] † | +1.0 [−0.1, +2.2] | +1.2 [−0.1, +2.5] | −1.4 [−2.9, +0.0] |
| Jev | +0.0 [−0.6, +0.7] | −0.3 [−1.2, +0.6] | −0.3 [−0.9, +0.3] | −0.3 [−1.4, +0.8] | +0.3 [−0.5, +1.3] | −0.0 [−1.4, +1.5] |

* **Renaming parties, dates, amounts and jurisdictions does nothing** for any system (|Δ| ≤ 0.7 points, CIs through zero; 24–52 decisions
  flip each way out of 14,400). Net of the Veridian rename floor (re-run 2026-10-06 with renamer v2, see the audit below) the rename effects
  are −0.4 / −0.3 / +1.2 / +0.3, every interval through zero. *Before the fix* the Veridian floor read +0.2 / −2.9 / −2.3 / −1.9 and the
  rename effects for Terra, Sol and Jev were +2.2 †, +2.5 †, +1.9 †; those were an artefact of the leaky v1 renamer, not knowledge, and
  are withdrawn. The two renamers remain different treatments (people in every header and company and product names across an e-mail
  corpus, against parties, terms, dates and amounts in contract excerpts), so the column is still a loose control.
* **Paraphrase costs ≤ 1.3 points.** Luna −1.3 (McNemar p = 0.045; 72 right→wrong vs 49 wrong→right); Terra −0.3; Sol −0.4; Jev −0.3. Net of
  the paraphrase cost on Veridian the effects are −0.8, +0.1, −1.4 and 0.0 with intervals through zero (Sol's upper bound +0.0002). The probe shows
  the paraphrase did remove memorised surface: Sol's LCS-F1 against the original continuation fell 0.315 → 0.279 and the share of windows
  with a ≥15-word verbatim run 10 % → 6 % (Terra 0.301 → 0.255, 8 % → 4 %), while renaming left it almost unchanged (0.302, 9 %).
* **No dose–response.** Δ does not grow with the contract's memorisation score for any system or perturbation (Spearman ρ between −0.02 and
  +0.20, Terra 0.00 / 0.02, none significant; the only tercile cells with CIs off zero are in the *low* and *mid* terciles).

Reading: CUAD results rest on clause-type competence, not on recognising the contract or its text. Perturbing the memorised surface moves
review F1 by about a point, within the cost the same perturbation has on an unseen corpus. For the article: "the models' document-level
memorisation of CUAD does not translate into review accuracy: paraphrasing the excerpts — which measurably reduces verbatim
retrievability — changes F1 by ≤ 1.3 points, no more than on the fictional control, and no more on the contracts the models remember best."

### B. Jeb Bush

| system | ΔF1 all | ΔF1 matter | ΔF1 control | knowledge effect (matter − control) | ΔRecall matter | ΔPrecision matter |
|---|---|---|---|---|---|---|
| GPT-5.6 Luna | −0.8 [−1.9, +0.2] | −0.2 [−2.1, +1.5] | −1.3 [−2.5, −0.0] † | +1.0 [−1.2, +3.2] | −2.6 [−4.6, −1.0] † | +1.6 [−1.0, +4.3] |
| GPT-5.6 Terra | −0.3 [−1.3, +0.7] | −1.6 [−3.2, +0.1] | +0.7 [−0.6, +2.0] | **−2.3 [−4.3, −0.3] †** | −2.6 [−4.5, −1.0] † | −0.9 [−3.0, +1.4] |
| GPT-5.6 Sol | −0.2 [−1.1, +0.7] | −0.2 [−1.6, +1.2] | −0.3 [−1.5, +1.0] | +0.1 [−1.8, +1.9] | −0.3 [−2.1, +1.3] | −0.1 [−1.9, +1.8] |
| Jev | −0.5 [−1.6, +0.6] | −2.4 [−4.7, −0.2] † | +0.7 [−0.1, +1.6] | **−3.1 [−5.5, −0.8] †** | −6.2 [−9.1, −3.4] † | +3.7 [+1.2, +6.5] † |

* **Luna and Sol show no knowledge effect** (+1.0 and +0.1, intervals through zero); **Terra's is −2.3 [−4.3, −0.3]**, the first LLM
  interval in the study to sit off zero (added 2026-10-06). Terra's matter topics moved −1.6 [−3.2, +0.1] (recall −2.6 †, precision −0.9),
  its control topics +0.7 [−0.6, +2.0]; by topic the loss is on George W. Bush (−5.8 [−11.3, −0.6] †) and spread thinly elsewhere; McNemar
  on all 12,000 pairs p = 0.81 (35 right→wrong, 32 wrong→right). Renaming alone costs Terra −0.4 [−1.2, +0.4] on Veridian (renamer v2; the v1 figure of −2.9 † was a
  renamer defect, see the audit below), so the matter-topic drop is not renaming cost; the control topics on the same documents moved the other way. This is what the lower bound of the
  earlier intervals always allowed: a small negative effect, not a null. The leakage check shows the LLMs still name Jeb Bush for most of the
  renamed e-mails (Luna 104/150 = 69 %, Terra 128/150 = 85 %, Sol 141/150 = 94 %; 77–96 % in the 3+-public-figure band) from `myflorida.com`,
  Tallahassee and the policy context, so for all three the renaming removes the names and not the recognition of the case: the request text
  already tells them what the recount, the Rilya Wilson case or Medicaid reform are, and knowing whose mailbox it is changes what they decide
  only at the margin.
* **Jev's matter-topic results depend on the real names.** With the public figures renamed, Jev loses 6.2 recall points on the matter
  topics (recount 0.46 → 0.39, Rilya Wilson 0.36 → 0.29, George W. Bush 0.82 → 0.68) and gains on precision, for a net −2.4 F1; the control
  topics move +0.7; the paired effect is −3.1 [−5.5, −0.8]. The loss is concentrated in documents with 0–2 public-figure mentions (−4.7 and
  −2.5) and absent at 3+, i.e. it is not the number of renamed tokens that matters but the loss of the few anchoring names (Gore, Harris,
  Rilya).
* What this is consistent with: Jev's representations carry knowledge of these public figures — "Gore" and "Harris" evoke the 2000 election,
  "Rilya Wilson" the DCF crisis — and the system leans on that knowledge to match documents to requests, where the LLMs take the context
  from the request text. Any encoder pre-trained on public web text would have this knowledge; the effect is therefore evidence of
  *familiarity with the matter helping a classifier*, not by itself evidence that Jev was trained on the collection or its labels (the
  classifier-native tests in `ediscovery_bench/jevprobe/` address that question directly). It does mean that Jev's Jeb Bush scores in the
  study are ~2–3 F1 points higher, on the matter topics, than they would be on a matter whose cast was unknown to it — the sign the
  pseudonymisation question is meant to catch, small but real. Renaming alone costs Jev −0.3 [−0.8, +0.2] on Veridian (renamer v2; the v1
  figure of −1.9 † was a renamer defect, see the audit below), so the matter-topic loss is not renaming cost; the control-topic Δ (+0.7,
  same documents, same renamer) points the same way.

### Spend (realised vs estimated)

Total realised **$83.18** against $83.13 estimated (ledger in `data/ablation/round2_spend.json`; every classification run landed within 2 %
of its estimate: Sol CUAD $8.98 vs $8.89, Sol Jeb $9.67 vs $9.52; Terra Jeb named $5.04 vs $4.99, Jeb renamed $5.06 vs $4.99, CUAD named
$4.75 vs $4.71, CUAD renamed $4.76 vs $4.70, CUAD paraphrased $4.69 vs $4.71, Veridian paraphrased $2.32 vs $2.31). The cheap version came to
$55.79 on 2026-10-04; Terra's six runs added $26.62 and the completed leak checks $0.78 on 2026-10-06. Includes $0.16 of duplicate-row waste
from a Luna run that was interrupted while a second instance was writing the same file (rows deduplicated, first kept) and $0.18 on the
superseded 600-doc Jeb subset (Jev). On 2026-10-04 the OpenAI key ran out of credit during the leakage check (Luna had answered 103 of 150
Jeb e-mails); the check was re-run in full on 2026-10-06 for all three LLMs on both arms (756 answers). During the Terra CUAD paraphrased run
120 rows hit a transient 429 ("no credits remaining") burst; the run was resumed and the rows filled ($0.04, 0 errors). Nothing is pending.

The Veridian renamed re-run of 2026-10-06 (a round-1 arm, re-run because of the renamer audit below) cost **$14.21** realised (Luna $0.47,
Terra $4.67, Sol $8.92, Jev $0.15; 40,000 rows, 0 errors, 15 minutes) against the $14.20 of the superseded v1 run; it is logged as the last
step of `round2_spend.json`, which therefore totals $97.39. The Big Thorium arm of 2026-10-06 (§C below) added $33.75 of classification runs to the same ledger (total $131.14); its probes ($0.39) are in the contamination results files.

### Renamer audit (2026-10-06)

Prompted by the Veridian rename result (fictional names renamed to other fictional names should cost nothing, yet Terra and Sol lost 2–3
points), every renamed and paraphrased set was audited without API calls: residual originals (short forms, titles, possessives, ALL-CAPS,
e-mail local parts, common-word surnames), over-replacement (real words mangled), request/document consistency, and per-request recall
losses tied back to the documents carrying residuals. Full tables: `results/ablation/renamer_audit.md`; summary in `results/ablation/REPORT.md`.

* **Veridian renamed — defect; fixed and re-run.** Renamer v1 mapped `ApexHip` and `Apex Registry` but not bare `Apex` (246 of 1,000 renamed
  documents still said "Apex reserve", "Apex booth", "Apex price" beside "SummitHip"); the surgeons named in the requests, Feld and Rao, were in
  the common-word surname class and survived as "Dr. Feld", "Feld's", bare "Rao" in 109 documents while the renamed requests said Brandt and
  Menon; `General Counsel` → `General Wexham` (27), `Quality Manager` → `Quality Harhurst` (5); 224 addresses in 144 documents kept the old
  local part (`mlee@`) beside the renamed display name. 120 of the 138 responsive documents lost after renaming (six requests with a ≥ 5-point
  recall drop) were leak-touched; on clean documents ΔF1 was Luna +0.7, Terra −2.0, Sol −1.5, Jev +0.2 against −0.5 / −5.0 / −3.5 / −3.5 on
  touched ones. Renamer v2 (`ablation/names.py`, `build.py`; `mapping.json` `version: 2`) maps bare Apex/Northgate/Meridian/Aegis, replaces
  Feld, Rao, Mitchell, Barr, Castellano, Tran, Vance, Shah, Berg and Reid wherever they appear, excludes role words from the name tables,
  handles title and initial positions and three-letter surnames in e-mail local parts, and treats an underscore as a boundary (attachment
  names). Residual counts after the fix: Apex 0 (was 246), Feld 0 (81), Rao 0 (60), Mitchell 0 (4), Wexham 0 (27), Harhurst 0 (5), old local
  parts 0 (143); the renamed requests and context carry the same mapping. Re-run on all four systems: Veridian ΔF1 Luna −0.1 [−1.0, +0.7],
  Terra −0.4 [−1.2, +0.5], Sol −1.0 [−1.9, −0.2] †, Jev −0.3 [−0.8, +0.2] (was +0.2 / −2.9 † / −2.3 † / −1.9 †; recall −3.2 / −7.5 / −6.6 /
  −3.8 became +0.2 / −0.1 / −1.1 / −0.1). Downstream: the round-1 ΔF1(J) − ΔF1(Veridian) column (Sol +3.4 † → +2.1 [−0.0, +4.1]); the CUAD
  rename effects above (+2.2 †, +2.5 †, +1.9 † → −0.3, +1.2, +0.3, all through zero); Δ(Jeb all) − Δ(Veridian) (all through zero); the
  Terra and Jev sentences above. The headline — knowledge effects within ±2.6 points, one of nine LLM intervals off zero (Terra, Jeb Bush)
  — is unchanged, but Terra's −2.3 can no longer be read as renaming cost. The v1 file is kept as `data/ablation/veridian__renamed.leaky_v1.jsonl`
  and the v1 run outputs in `results/ablation/veridian/multi/leaky_v1/`.
* **Enron J / K renamed — cosmetic; not re-run.** No `Enron`/`ENE` residue. Header-derived ordinary words were replaced as surnames:
  `Scheduling` → Melwick (18 docs per arm), `Gov.` → `Lanford.` (19 / 24), `May` → Strounan in date lines (12 / 10), `Risk Management` →
  `Risk Rosman`; 69 / 68 documents mangled; 9 of 18 lost energy_schedules positives are in them, no other request touched. Knowledge effect on
  clean documents Luna +1.2, Sol +1.8, Terra −1.0, Jev 0.0 against the published +1.6 / +2.1 / −2.6 / 0.0 — every interval includes zero either
  way, so the $9.4 re-run would change no conclusion.
* **Jeb Bush renamed — cosmetic; not re-run.** No `Jeb`/`Bush` in body text; two leftover domains in one document each. Title-plus-public-surname
  forms (Senator Graham, Mayor Hood, Speaker Byrd) in 22 documents, more often in matter positives (13/273) than control (4/360); the knowledge
  effect on the 958 clean documents is +0.9 / +0.6 / −2.5 / −2.9 against +1.1 / +0.1 / −2.4 / −3.2. `Washington` → Drayman (49) and `Vice
  President` → `Vice Tolwood` (19) are balanced across topics. The gw_bush recall drop occurs on clean documents: it is the measured effect.
* **CUAD renamed — cosmetic.** Unmapped acronyms and short names (SIGA, NFLA, KI, HPIL, Columbia Laboratories) in ~60 excerpts from 9
  contracts; recall on them unchanged for every system.
* **CUAD paraphrased — caveat.** The fidelity judge rated 11 of 100 sampled paraphrases not legally equivalent (change_of_control 2/5,
  license_grant 2/10, anti_assignment 2/11, ip_ownership_assignment 1/7, non_compete 1/6, insurance 1/2); Luna's and Jev's ≥ 5-point per-clause
  recall drops fall on the same types, so Luna's −1.3 † paraphrase Δ is consistent with ~10 % infidelity rather than knowledge. The paraphrase
  effects net of Veridian are unaffected. The Veridian paraphrase control is clean (49/50 equivalent; recall flat on every request).

### Commands

```bash
bench ablation2-build                 # sample CUAD + Jeb (extracts the eval e-mails from the zip on first run), renamed twins, mappings, cost table
bench ablation2-paraphrase            # Luna paraphrases (CUAD, Veridian), checks, Terra fidelity judge
bench ablation2-memo                  # finish-the-document probe: 2 windows per contract × original/renamed/paraphrased × Luna/Terra/Sol
bench ablation2-run -m gpt-5.6-luna -m gpt-5.6-sol -m jev@base          # all arms and conditions (resumable); add -m gpt-5.6-terra for the full version
bench ablation2-run -m gpt-5.6-sol --arm cuad --condition paraphrased   # one arm × condition
bench ablation2-leak -m gpt-5.6-luna -m gpt-5.6-sol                     # identification check on renamed documents
bench ablation2-report                # summary.json, REPORT.md, fig_cuad.png, fig_jeb.png (headless Chrome)
```

---

## C. Big Thorium — a second synthetic floor (added 2026-10-06)

**What it is.** The *Relativity aiR for Review demo workspace*, distributed by Relativity to its customers and demo users
(`Bigthorium_*.zip`, a RelativityOne ARM archive): 2,091 e-mails of the
fictional sustainable-energy company BigThorium, written around a City of Atlantis bribery investigation (gifts to city officials to win a
municipal energy RFP; an unrelated nuclear-plant thread with the City of Eldorado; ordinary corporate and promotional mail). Provenance and
inventory are in `data/bigthorium/raw/SOURCES.md`; extraction (`bench bigthorium extract`,
`ediscovery_bench/bigthorium/extract.py`) reads the analytics-set Avro (Snappy-framed) for text and headers and the audit log for the aiR
prompt criteria (128 versions; the 2026-09-08 one is used) and the demo's own Responsive / Not Responsive coding (1,000 documents, 18 positives).

**Why it is here.** Big Thorium is **public documents, invented case**. The matter is fictional, so — as with Veridian — there is nothing
to know about it from the news; but unlike Veridian, whose e-mails were written for this study and never published, the Big Thorium e-mails
circulate widely among Relativity users and could have been crawled. In the exposure typology it sits between Veridian (private documents,
invented case) and CUAD (public documents, no real case): a floor for case knowledge on which document exposure is possible. It therefore
gets both tests: the contamination probes
(`ediscovery_bench/contam/bigthorium.py`, `results/contam/bigthorium_summary.json`) and the renaming ablation below.

### Design

* **Requests.** `tasks/bigthorium.yaml`: eight requests. 1–6 partition the aiR relevance criteria (Atlantis RFP / bid / award; gifts and
  luxury goods; communications with City officials; the contract; third-party intermediaries; the investigation itself); 7–8 are off-matter
  controls present in the collection (nuclear-plant regulatory compliance; remote-work policy), so the knowledge effect is defined exactly
  as on Enron J/K and Jeb Bush: Δ(matter requests) − Δ(control requests).
* **Sample.** 1,000 of 2,091, stratified by keyword presence (`data/ablation/bigthorium_sampling.json`): 650 of the 878 documents that
  mention the matter's names (Atlantis, Eldorado, GNS, Law Firm X, Maskbook, gift/bribe/Rolex/investigation…), 150 of the 229 that mention
  only the control topics (nuclear/reactor/compliance/remote work), 200 of the 984 others; the 18 human-coded positives are forced in; 478
  sampled documents carry a human code. Mean 2,460 characters (Veridian 1,444). Seed 20261006.
* **Gold.** None usable ships with the set (the demo coding is a single document-level Responsive flag with 18 positives, and the aiR
  results are not in the archive). As for Mallinckrodt and Endo, the three OpenAI models' *named* reviews form a panel (97.7 % of the
  8,000 pairs unanimous), but every system is scored against a gold that excludes its own votes: for an LLM the other two must agree
  (leave-one-out; a split is unscored — 109–141 pairs per system), for Jev the three-model majority with the goldify gray rule (split or
  mean p in [0.35, 0.65] unscored). Panel positives per request: rfp01 37, rfp02 19, rfp03 76, rfp04 25, rfp05 0, rfp06 13, rfp07 122,
  rfp08 38 — the matter requests have ~140 scorable positives in total, so their intervals are wide. Check against the human coding
  (document level, any matter request positive): panel recall 15/18, precision 0.31 — the requests are much broader than the demo's flag,
  so precision against it is not meaningful.
* **Renamer.** The v2 engine with a Big-Thorium mapping (`data/ablation/bigthorium_mapping.json`; `ediscovery_bench/ablation/bigthorium.py`):
  38 phrases (BigThorium → VastRadium, City of Atlantis → City of Thalassa, Eldorado → Zerzura, Law Firm X → Law Firm K, GNS Partners → HRT
  Partners, Maskbook → Veilbook, Little Big Energy → Small Grand Power, every domain and the typo'd domains atlantiss.gov / bigthorim.com),
  145 surnames from the `Name [local@domain]` header pairs (a display name counts as a person only when its surname is in the address, which
  drops the newsletter / HR / no-reply mailboxes), 153 first names, 26 common-word surnames, 9 catch-all local parts (typo'd addresses
  `mkuman@`, `ejacskon@`; surnames that are also first names — James, Howard, Thomas — whose addresses the generic pass skips by design).
  The cast's dictionary-word surnames (Clark, Smith, Baker, Carter, Reed, Archer, Bass, Fry, Ham …) are forced rare — the Veridian v2
  lesson applied up front. One engine fix local to this arm: the full-name pattern's whitespace may not span a line break (a sign-off
  "James" above "James Brown" was being read as a full name). Residual audit (`results/ablation/bigthorium/renamer_audit.json`): phrases 0,
  rare surnames 0, e-mail local parts 0; the 226 "common-word" residuals are "Martin" as a first name, "City Hall", "Green Bay", "Go Green"
  and "Rolex Air-King" — not people. Mean dose 47 substitutions per document; 7 documents receive none. Requests and context renamed with
  the same mapping.
* **Brief.** Relativity's own aiR case summary for the demo (matter overview, people and aliases, noteworthy terms, relevance criteria;
  1,059 words; `data/ablation/bigthorium_brief.md`) appended to the context exactly as in Check D, on a 300-document subset: all 87
  documents with a non-gray matter-request positive plus 213 random others.

### Cost (estimated from the realised Veridian per-call token means, scaled to 8 questions and this set's document length; realised in the ledger)

| condition | docs | Luna | Terra | Sol | Jev | total est. | realised |
|---|---:|---:|---:|---:|---:|---:|---:|
| named | 1,000 | 0.40 | 4.02 | 7.71 | 0.13 | 12.27 | **14.01** (113–115 %; Jev 87 %) |
| renamed | 1,000 | 0.40 | 4.02 | 7.71 | 0.13 | 12.27 | **14.23** (116 %) |
| brief | 300 | 0.13 | 1.26 | 2.43 | 0.06 | 3.88 | **5.51** (142 %: the brief is not cached as fully as assumed) |
| contamination probes (291 items × 3 LLMs) | | | | | | ≈ 1.5 | **0.39** |
| smoke test (1 document, Luna + Jev) | | | | | | | 0.00 |
| **Big Thorium total** | | | | | | 29.9 | **$34.14** |

Budget rule for this arm was $40; the overrun on the classification runs is the longer documents' output and the uncached share of the
prompt, consistent across conditions and so irrelevant to the paired comparisons.

### Results (`results/ablation/bigthorium/REPORT.md`, `summary.json`; figures `results/contam/article/pr_options/bigthorium_rename.png`, `bigthorium_brief.png`)

| System | named F1 | renamed F1 | ΔF1 [95 % CI] | matter Δ | control Δ | knowledge effect | Veridian ΔF1 | brief ΔF1 (n ≈ 2,340) |
|---|---:|---:|---|---|---|---|---|---|
| Luna | 87.3 | 86.1 | −1.1 [−3.6, +1.2] | −2.7 [−6.5, +0.8] | +0.7 [−1.9, +3.3] | −3.4 [−7.8, +0.7] | −0.1 [−1.0, +0.7] | −0.8 [−4.3, +2.7] |
| Terra | 92.2 | 92.6 | +0.5 [−1.2, +2.2] | +1.0 [−1.8, +4.0] | +0.0 [−1.5, +1.6] | +1.0 [−2.0, +4.3] | −0.4 [−1.2, +0.5] | −1.8 [−3.9, +0.2] |
| Sol | 89.2 | 89.6 | +0.5 [−1.1, +2.2] | +1.0 [−1.5, +3.9] | −0.2 [−2.2, +1.9] | +1.3 [−2.0, +4.5] | −1.0 [−1.9, −0.2] | +0.6 [−1.1, +2.5] |
| Jev | 84.1 | 84.0 | −0.1 [−1.9, +1.6] | +1.9 [−0.7, +4.8] | −2.3 [−4.6, −0.5] | +4.3 [+1.0, +7.8] | −0.3 [−0.8, +0.2] | −1.1 [−4.0, +1.7] |

Reading:

* **Renaming costs nothing on the whole set**, for every system: |ΔF1| ≤ 1.1, every interval through zero, McNemar p ≥ 0.39, 0.2–0.6 % of
  labels change. This is the Veridian result again, on public documents the study did not write.
* **Knowledge effects are through zero for the three LLMs.** Jev's +4.3 [+1.0, +7.8] has the *wrong sign* for case knowledge (negative
  would mean the names helped on the matter) and comes entirely from the control side: on the nuclear-compliance request Jev lost 5
  positives and gained none (control Δ −2.3). Those are threshold cases — of Jev's 18 changed labels, 83 % had a named-condition p within 0.1
  of the 0.5 threshold and the mean |Δp| was 0.14, against 0–5 % and 0.6–0.8 for the LLMs: renaming nudges the decision model's probabilities
  by a few hundredths and flips the documents that were already on the line, a surface-token sensitivity rather than knowledge. The matter
  requests individually: rfp01 −5.7 … +3.3, rfp04 −6.0 … +0.0 with intervals of ±10–20 points on 25–37 positives; nothing is consistent across
  systems.
* **The brief does not help here either**: −1.8 (Terra) to +0.6 (Sol), intervals through zero, with the usual circularity caveat (the gold is
  the panel's *without-brief* majority, so following the brief away from the panel scores as an error; the Veridian Check D had the same
  property). Luna and Terra trade recall for precision under the brief (Luna 97.6 → 92.3 recall, 83.7 → 86.6 precision).
* **Contamination probes** (`results/contam/bigthorium_summary.json`; the report's §21A): entity recall 0/30 for every model (the non-UNKNOWN
  answers are real-world namesakes: John C. Maxwell the author, a Vinod Subramanian at Flexera); recognition "yes" for BigThorium 0 %; the
  de-identified sketch is matched to real municipal energy-contract investigations (Johnson Controls / Milwaukee by Terra, Ameresco / Holyoke
  by Sol; Luna declines), never to Big Thorium; asked directly about the matter all three decline. Verbatim continuation is *higher* than
  Veridian's (LCS-F 0.20–0.22 vs 0.15–0.17 rules-only) but with longest shared runs of 3–4 words and no run ≥ 15: the demo's e-mails are
  themselves machine-written and stylistically predictable (bulleted marketing prose), which raises token overlap without any memorised
  passage — below CUAD on every measure (0.25–0.29, runs 4.5–6, 14–20 % of windows with a ≥ 8-word run). Asked what Relativity's aiR demo
  workspace is about, Luna declines, Terra describes a different scenario ("Apex Financial / Barton Bank", antitrust) and Sol invents names
  ("Aerolith Dynamics / NovaGen Energy") but describes a bribery-to-win-a-contract investigation — the right scenario type with the wrong names,
  as consistent with a generic demo-scenario prior as with having seen the demo set. No model knows the set's names.

Taken together: despite being public, Big Thorium behaves as a second floor — no model recites it, recognises it or recalls its facts — and
the renaming cost on it (−1.1 to +0.5) brackets Veridian's (−1.0 to −0.1), so the mechanical cost of renaming in this pipeline is confirmed
at about one F1 point or less on a public collection the study did not build.

### Commands

```bash
bench bigthorium extract              # ARM archive (unpacked under data/bigthorium/raw/) -> bigthorium_all.jsonl, air_criteria.json, human_coding.json
bench bigthorium build                # 1,000-doc stratified sample, mapping, renamed twin, residual audit, cost estimate
bench bigthorium run -k named         # then: bench bigthorium goldify ; bench bigthorium run -k renamed -k brief
bench bigthorium score                # results/ablation/bigthorium/{summary.json, REPORT.md}, pr_options/bigthorium_{rename,brief}.png
bench bigthorium probe-build && bench bigthorium probe-run && bench bigthorium probe-score   # contamination probes -> results/contam/bigthorium_summary.json
bench contam-html && bench contam-paper                                                        # pick up the conditional Big Thorium sections
```
