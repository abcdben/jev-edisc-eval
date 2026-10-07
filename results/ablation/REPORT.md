# Pseudonymisation ablation — results

Systems under test: gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol, jev@base. Jev: present. Jev's vendor states it is not pre-trained on these corpora; we treat that as a claim and test it.

Total spend: $104.75 paid ($222.71 list); a further $14.20 paid for the superseded Veridian renamed run (renamer v1, kept in `veridian/multi/leaky_v1/`, see the renamer audit below).

## Paired Δ (renamed − named), pooled over knowledge topics

| arm | model | n pairs | F1 named | F1 renamed | ΔF1 [95% CI] | ΔRecall | ΔPrecision | right→wrong | wrong→right | McNemar p |
|---|---|---|---|---|---|---|---|---|---|---|
| enron_j | gpt-5.6-luna | 994 | 0.793 | 0.791 | -0.2 pp [-2.0, +1.6] | +0.0 pp [-2.5, +2.5] | -0.5 pp [-2.3, +1.3] | 21 | 19 | 0.875 |
| enron_j | gpt-5.6-terra | 994 | 0.753 | 0.733 | -2.0 pp [-4.4, +0.1] | -2.2 pp [-5.1, +0.7] | -1.5 pp [-3.1, -0.1] | 28 | 15 | 0.066 |
| enron_j | gpt-5.6-sol | 994 | 0.797 | 0.808 | +1.1 pp [-0.9, +2.9] | +1.7 pp [-1.1, +4.3] | +0.2 pp [-1.5, +1.7] | 18 | 25 | 0.36 |
| enron_j | jev@base | 994 | 0.718 | 0.701 | -1.7 pp [-3.6, +0.1] | -2.2 pp [-4.6, +0.0] | -0.3 pp [-2.0, +1.3] | 19 | 10 | 0.136 |
| enron_k | gpt-5.6-luna | 999 | 0.618 | 0.600 | -1.8 pp [-4.1, +0.3] | -2.0 pp [-4.3, +0.2] | +0.1 pp [-1.9, +2.3] | 25 | 16 | 0.211 |
| enron_k | gpt-5.6-terra | 999 | 0.515 | 0.521 | +0.6 pp [-1.5, +2.7] | +0.8 pp [-1.0, +2.8] | -1.9 pp [-4.5, +0.3] | 15 | 15 | 1 |
| enron_k | gpt-5.6-sol | 999 | 0.621 | 0.611 | -1.0 pp [-2.6, +0.7] | -1.0 pp [-2.8, +0.9] | -0.5 pp [-1.9, +0.7] | 15 | 9 | 0.307 |
| enron_k | jev@base | 999 | 0.573 | 0.556 | -1.7 pp [-3.6, +0.2] | -1.6 pp [-3.5, +0.2] | -0.7 pp [-2.7, +1.3] | 19 | 10 | 0.136 |
| veridian | gpt-5.6-luna | 10000 | 0.810 | 0.809 | -0.1 pp [-1.0, +0.7] | +0.2 pp [-0.5, +0.8] | -0.3 pp [-1.4, +0.9] | 72 | 67 | 0.735 |
| veridian | gpt-5.6-terra | 10000 | 0.838 | 0.834 | -0.4 pp [-1.2, +0.5] | -0.1 pp [-1.0, +0.7] | -0.5 pp [-1.5, +0.6] | 63 | 53 | 0.403 |
| veridian | gpt-5.6-sol | 10000 | 0.826 | 0.816 | -1.0 pp [-1.9, -0.2] | -1.1 pp [-2.1, -0.1] | -0.9 pp [-2.0, +0.1] | 79 | 54 | 0.037 |
| veridian | jev@base | 10000 | 0.865 | 0.862 | -0.3 pp [-0.8, +0.2] | -0.1 pp [-0.9, +0.7] | -0.5 pp [-1.1, +0.2] | 22 | 15 | 0.324 |
| mnk | gpt-5.6-luna | 14720 | 0.768 | 0.758 | -1.0 pp [-1.8, -0.2] | -0.1 pp [-0.8, +0.7] | -1.3 pp [-2.3, -0.4] | 209 | 154 | 0.00453 |
| mnk | gpt-5.6-terra | 14720 | 0.850 | 0.843 | -0.7 pp [-1.5, +0.1] | +0.7 pp [-0.2, +1.6] | -1.8 pp [-2.9, -0.6] | 140 | 104 | 0.0248 |
| mnk | gpt-5.6-sol | 14720 | 0.827 | 0.833 | +0.6 pp [-0.1, +1.3] | +0.8 pp [+0.1, +1.6] | +0.5 pp [-0.5, +1.4] | 113 | 137 | 0.146 |
| mnk | jev@base | 14720 | 0.835 | 0.849 | +1.3 pp [+0.5, +2.3] | +4.1 pp [+2.8, +5.4] | -1.4 pp [-2.5, -0.4] | 88 | 116 | 0.0584 |

## Knowledge effect (all four systems; Jev's no-pre-training statement is a claim under test)

| system | ΔF1(J) | ΔF1(K) | ΔF1(Veridian) | knowledge effect ΔF1(J) − ΔF1(K) | ΔF1(J) − ΔF1(Veridian) |
|---|---|---|---|---|---|
| gpt-5.6-luna | -0.2 pp [-2.0, +1.6] | -1.8 pp [-4.1, +0.3] | -0.1 pp [-1.0, +0.7] | +1.6 pp [-1.2, +4.6] | -0.1 pp [-2.1, +1.9] |
| gpt-5.6-terra | -2.0 pp [-4.4, +0.1] | +0.6 pp [-1.5, +2.7] | -0.4 pp [-1.2, +0.5] | -2.6 pp [-5.8, +0.5] | -1.7 pp [-4.1, +0.6] |
| gpt-5.6-sol | +1.1 pp [-0.9, +2.9] | -1.0 pp [-2.6, +0.7] | -1.0 pp [-1.9, -0.2] | +2.1 pp [-0.6, +4.6] | +2.1 pp [-0.0, +4.1] |
| jev@base | -1.7 pp [-3.6, +0.1] | -1.7 pp [-3.6, +0.2] | -0.3 pp [-0.8, +0.2] | +0.0 pp [-2.6, +2.6] | -1.4 pp [-3.4, +0.4] |

## Dose–response (Enron J, ΔF1 by knowledge-bearing names per document)

| model | 0 names | 1–2 | 3+ |
|---|---|---|---|
| gpt-5.6-luna | +1.0 pp [-1.4, +3.7] (n=525) | +0.7 pp [-2.8, +4.5] (n=127) | -2.3 pp [-5.0, +0.5] (n=200) |
| gpt-5.6-terra | -0.2 pp [-3.6, +2.8] (n=525) | -2.6 pp [-6.8, +1.1] (n=127) | -4.3 pp [-7.9, -1.0] (n=200) |
| gpt-5.6-sol | +3.1 pp [+0.5, +5.9] (n=525) | -1.6 pp [-5.2, +1.8] (n=127) | -0.5 pp [-3.6, +3.3] (n=200) |
| jev@base | -1.7 pp [-3.7, +0.3] (n=525) | +0.0 pp [-3.1, +3.2] (n=127) | -2.5 pp [-5.9, +1.6] (n=200) |

## Residual leakage (renamed Enron J documents still attributed to Enron; LLMs only — the identification question is generative and cannot be posed to Jev)

- gpt-5.6-luna: 121/200 (60.5%); by dose 0: 37/77, 1-2: 8/23, 3+: 76/100; top guesses [('Enron Corporation', 57), ('Volteron', 27), ('cannot tell', 22), ('Enron', 19)]
- gpt-5.6-sol: 187/200 (93.5%); by dose 0: 72/77, 1-2: 20/23, 3+: 95/100; top guesses [('Enron', 187), ('Kinder Morgan', 4), ('Dynegy', 3), ('El Paso Natural Gas Company', 1)]
- gpt-5.6-terra: 163/200 (81.5%); by dose 0: 59/77, 1-2: 15/23, 3+: 89/100; top guesses [('Enron', 71), ('Enron Corporation', 46), ('Enron Corp', 45), ('Kinder Morgan, Inc', 5)]

## In-mailbox control topic (fantasy football, Enron J)

- gpt-5.6-luna: F1 0.958 → 0.951, Δ -0.7 pp [-2.5, +0.0]
- gpt-5.6-terra: F1 0.930 → 0.944, Δ +1.4 pp [+0.0, +3.4]
- gpt-5.6-sol: F1 0.952 → 0.951, Δ -0.1 pp [-2.9, +2.4]
- jev@base: F1 0.896 → 0.896, Δ +0.0 pp [-3.4, +3.1]

## Renamer audit (2026-10-06)

Every renamed or paraphrased set was scanned for residual originals, over-replacement and request/document inconsistency, and the
per-request recall losses were tied back to the documents that carried residuals (`renamer_audit.md` in this folder has the full tables).

**Veridian renamed — defect found and fixed; re-run.** Renamer v1 mapped `ApexHip` and `Apex Registry` but not the bare short form, so 246
of 1,000 renamed documents still said "Apex reserve", "Apex booth", "Apex price" beside "SummitHip"; the surgeons named in the requests,
Feld and Rao, were in the common-word surname class and survived as "Dr. Feld", "Feld's" and bare "Rao" in 109 documents while the renamed
requests said Brandt and Menon; `General Counsel` became `General Wexham` (27) and `Quality Manager` became `Quality Harhurst` (5);
224 e-mail addresses in 144 documents kept the old local part (`mlee@`) beside the renamed display name. 120 of the 138 responsive documents
the four systems lost after renaming (on the six requests with a ≥ 5-point recall drop) were in leak-touched documents; on clean documents
ΔF1 was Luna +0.7, Terra −2.0, Sol −1.5, Jev +0.2 against −0.5 / −5.0 / −3.5 / −3.5 on touched ones. Renamer v2 (`names.py`, `build.py`;
`mapping.json` carries `version: 2`) maps bare Apex/Northgate/Meridian/Aegis, replaces Feld, Rao, Mitchell, Barr, Castellano, Tran, Vance,
Shah, Berg and Reid wherever they appear, excludes role words from the name tables, handles title and initial positions ("Dr. Feld",
"D. Mitchell") and three-letter surnames in e-mail local parts, and treats an underscore as a word boundary (attachment names). After the
fix the residual counts are 0 for Apex, Feld, Rao, Mitchell, Wexham, Harhurst and old local parts; the remaining residuals are ordinary
words that are also surnames (Central Park, Lee Hecht Harrison; about a dozen documents) and are left by design. The renamed condition was re-run on
all four systems with the v2 file (`data/ablation/veridian__renamed.jsonl`; v1 kept as `veridian__renamed.leaky_v1.jsonl`); the v1 run
outputs are in `veridian/multi/leaky_v1/`. The Veridian rows above, the ΔF1(J) − ΔF1(Veridian) column and the round-2 "CUAD − Veridian"
contrasts use the v2 run.

**Enron J / K renamed — cosmetic; not re-run.** No `Enron`/`ENE` residue in text or addresses. The header-derived surname table contains
ordinary words that were replaced wherever capitalised: `Scheduling`→Melwick (18 docs per arm), `Gov.`→`Lanford.` (19 / 24), `May`→Strounan
in date lines (12 / 10), `Risk Management`→`Risk Rosman`, `Businesses`→Dunman; 69 (J) / 68 (K) documents carry a mangle. 9 of 18 lost
energy_schedules positives are in mangled documents; no other request is touched. The knowledge effect recomputed on documents without a
mangle is Luna +1.2, Sol +1.8, Terra −1.0, Jev 0.0 against the published +1.6 / +2.1 / −2.6 / 0.0, every interval including zero either way.
A re-run (realised $9.4) would move Terra's point estimate about 1.6 points toward zero and change no conclusion, so the v1 files stand.

**Jeb Bush renamed — cosmetic; not re-run.** No `Jeb`/`Bush` in any body text; `jebbush@myflorida.com` and `georgewbush.com` in one
document each. Title-plus-public-surname forms survive in 22 documents (Senator Graham, Mayor Hood, Speaker Byrd, Congressman Foley),
more often in matter positives (13 of 273) than control positives (4 of 360); the knowledge effect on the 958 documents without any such
residual is Luna +0.9, Sol +0.6, Terra −2.5, Jev −2.9 against +1.1 / +0.1 / −2.4 / −3.2 on all documents. `Washington`→Drayman (49) and
`Vice President`→`Vice Tolwood` (19) are mangles balanced across matter and control topics. The recall drop on the gw_bush topic occurs on
clean documents and is the measured effect, not a defect.

**CUAD renamed — cosmetic.** Unmapped party acronyms and short names (SIGA, NFLA, KI, HPIL, MINDA/IMPCO, Columbia Laboratories) remain in
about 60 excerpts from 9 contracts; recall on those excerpts did not change for any system, so the residue affects identification only.

**CUAD paraphrased — caveat on one result.** The fidelity judge rated 11 of 100 sampled paraphrases not legally equivalent (change_of_control
2/5, license_grant 2/10, anti_assignment 2/11, ip_ownership_assignment 1/7, non_compete 1/6, insurance 1/2). Luna's and Jev's per-clause
recall drops of ≥ 5 points fall on the same clause types, so Luna's paraphrase ΔF1 of −1.3 [−2.7, −0.0] is consistent with roughly 10 %
infidelity rather than knowledge. The "CUAD − Veridian" paraphrase contrasts are unaffected in sign or significance. The Veridian paraphrase
control (49 of 50 equivalent; recall flat on every request) is clean.

## Big Thorium (public documents, invented case; `results/ablation/bigthorium/REPORT.md`)

The Relativity aiR for Review demo workspace, distributed by Relativity, 1000 documents, eight requests, panel gold (leave-one-out). Named → renamed ΔF1: gpt-5.6-luna -1.1 [-3.6, +1.2]; gpt-5.6-terra +0.5 [-1.2, +2.2]; gpt-5.6-sol +0.5 [-1.1, +2.2]; jev@base -0.1 [-1.9, +1.6]. Not part of the summary tables above (different gold procedure); see its own report and `design/07_ablation_round2.md` §C.
