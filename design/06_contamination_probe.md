# Training-data contamination probe

Status: RUN. Part I (corpus exposure), Part II (matter knowledge) and the matter ladder on the OpenAI models, M3 on Jev, and the pseudonymisation ablation (effect) on all four systems (2026-10-03); Endo added as a sixth study corpus and run through every channel, with Teva and JUUL added as ladder rungs (2026-10-03); classifier-native tests on Jev (T1 code-name swap, bare token, T2 minimal-edit flip, T3 paraphrase, T4 published vs unpublished labels; 2026-10-04, see the last section); ablation round 2 on CUAD (renamed and paraphrased) and Jeb Bush (matter vs control topics) with Luna, Sol and Jev (2026-10-04), Terra and the completed leak checks added 2026-10-06 (`design/07_ablation_round2.md`, `results/ablation/round2/`); generalisation checks A–D (2026-10-04; `results/verify/`); Anthropic and Gemini pending keys. Big Thorium (the Relativity aiR for Review demo workspace, distributed by Relativity: public documents, invented case) added 2026-10-06 as a second floor: contamination probes on the three OpenAI models and the renaming + brief ablation on all four systems (`design/07_ablation_round2.md` §C, `results/ablation/bigthorium/`, `results/contam/bigthorium_summary.json`; the report's §21A). Total spend $300.09 ($14.28 probes + $0.17 Jev M3 + $104.75 ablation + $33.50 Endo corpus, label panel and probes + $4.64 OpenAI and $0.15 Jev for the classifier-native tests + $83.18 ablation round 2 + $10.95 OpenAI and $0.12 Jev for the generalisation checks + $14.21 on 2026-10-06 for the Veridian renamed re-run after the renamer audit + $34.14 for Big Thorium: $0.39 probes, $33.75 named / renamed / brief runs). The OpenAI credit ran out on 2026-10-04 and was topped up on 2026-10-06; still pending: the T1 code-name-swap re-run on the LLMs (≤ $3) and full de-identification of Enron J (≈ $40–50). Code in `ediscovery_bench/contam/`, CLI `bench contam-build`,
`bench contam-run`, `bench contam-report`, `bench contam-html`, `bench contam-paper`. Outputs in `results/contam/` (`REPORT.md`, `summary.json`,
`contamination_report.html` — self-contained methodology + charts + tables; `paper.html` — arXiv-style write-up with numbered figures/tables;
`explainer.html` — eight-step plain-language walk from question to conclusion, with glossary; `report_short.html` — condensed report;
`explainer_lawyer.html` — plain-English guide for lawyers with analogies and chart-reading notes; per-item records
`results/contam/<model>.jsonl` are git-ignored like all per-decision records).

## Why

The study compares Jev with generative LLMs on five corpora. Four of them are real, public, and old enough
to be in a frontier model's pre-training data:

| Corpus | Public since | How exposed |
| --- | --- | --- |
| Enron (EDRM v2, TREC Legal 2009/2010) | 2003 (FERC), 2004 (CMU), 2009 (EDRM) | Component of The Pile ("Enron Emails"); Kaggle; countless mirrors; two decades of papers quoting it |
| Jeb Bush e-mails (TREC 2016 Total Recall) | 2015 (jebbushemails.com, press), 2016 (NIST) | Posted on the open web by Bush's own campaign; news coverage quoted thousands of messages; NIST distribution is agreement-restricted |
| Mallinckrodt opioid e-mails (Opioid Industry Documents Archive) | 2021-2023 | UCSF/JHU archive, OCR text behind a Solr search; documents also quoted in MDL 2804 filings and news |
| Endo opioid e-mails (Opioid Industry Documents Archive; `data/endo/endo.jsonl`, 2,000 docs) | 2024-2026 | Same archive, but a production **published after every model's training cutoff**: the documents should be unseen while the matter (Opana ER, the state AGs, the 2022 Chapter 11) is old and public. Real-world **post-cutoff check** on the floor; labels from a three-OpenAI-model panel (Anthropic/Gemini keys absent), unlike Mallinckrodt's mixed panel |
| CUAD contracts | 2021 (Atticus / HF / GitHub) | A well-known NLP benchmark; the underlying contracts are SEC EDGAR exhibits, which are heavily crawled |
| Veridian (synthetic) | written 2026-09 | Cannot be in any model's training data; **negative control (floor)** |
| `canon`: Federalist Papers, US Constitution, Declaration of Independence (Project Gutenberg) | 1787-1788 | Among the most-replicated English texts on the web; the framers are universally documented; **positive control (ceiling)** for V, E and (with 20 Newsgroups) B |
| `titanic`: Kaggle *Titanic* `train.csv` | 2012 (Kaggle), replicated on millions of GitHub repos | The textbook case of row-level memorisation of a labelled dataset (Bordt et al. 2024); **positive control** for V (row completion) and L (passenger → Survived) |

The two controls bracket the spectrum: Veridian is what a model scores when it can know nothing, the
anchors are what it scores when it has certainly seen the material many times. A real corpus is read by
where it falls between them.

If a model has seen the documents, the people, the matter, or the benchmark's own topics and judgments, it
may be advantaged on that corpus in ways that do not transfer to a client's never-seen collection. Jev's
vendor states it is a System One classifier not pre-trained on public text; if so it would not be. We treat
that as a claim under test, not a premise: this probe cannot pose the generative questions to a classifier,
so the direct test of the claim is the ablation study.
This probe measures *exposure*, so that the eval can (a) weight its conclusions toward the uncontaminated
corpora and (b) choose future corpora with a measured exposure profile rather than a guess.

## What "contamination" means here: four mechanisms, four probes

A model can be advantaged on a relevance-review eval through four distinct channels. Each gets its own
probe, each is cheap (short prompts, no document classification), and each has Veridian as the floor.

| Channel | Probe | Item | Score | Floor |
| --- | --- | --- | --- | --- |
| **V. Verbatim memorisation** of the documents themselves | `verbatim`: show the headers + first ~45% of the body, ask for the next ~60 words "exactly as in the original" | 60 documents per corpus, body cut before any quoted reply; windows whose continuation is boilerplate (disclaimer, signature, quoted header, footer, auto-reply, OCR noise, corpus-wide template) are rejected by `boilerplate.py` | Word-level LCS ratio and longest exact run vs the true continuation; n-grams already in the prefix get no credit; refusal rate kept separately; boilerplate windows excluded from every statistic | Veridian (plausible-email floor) |
| **E. Entity knowledge** of the people in the matter ("surrounding details") | `entity_recall`: "Who is {name} (active c. {era})? Organisation and role, or UNKNOWN" | 30 header names per corpus in three frequency tiers (top-10, rank 11-40, tail) | Answer names the target organisation (keyword set per corpus); UNKNOWN and wrong-org rates kept | Veridian names (fictional; any "hit" impossible, non-UNKNOWN = confabulation) |
| | `entity_recog`: "Was {name} affiliated with {org}? yes / no / unknown" for the true org and the three foil orgs | Same 30 names × 4 orgs | Hit rate (yes | true org) vs false-alarm rate (yes | foil org); d' per corpus | Foils and Veridian give the acquiescence rate |
| **B. Benchmark knowledge** of the topics the eval reuses | `bench_knowledge`: "List the topics of TREC 2016 Total Recall athome4", "Describe TREC Legal 2010 topics 301-304", "...2009 topics 201-207", "List the CUAD clause categories", "What is the Mallinckrodt collection in the OIDA", "What is the Veridian ApexHip matter" | 6 free-text questions | Fraction of true topic titles / categories recovered; Veridian answer scored for confabulation | Veridian question |
| **L. Label memorisation** of the published relevance judgments | `label_recall`: "In {collection}, was document {id} judged relevant to topic {n} '{title}'?" with **no document text** | 100 balanced (id, topic) pairs per corpus | Accuracy vs 50 %; Wilson CI | MNK (labels are ours, never published) and Veridian: must be at chance |

Together these say, per corpus and per model: *has it seen the documents* (V), *does it know the cast* (E),
*does it know the test* (B), *does it know the answers* (L). V and E are the channels most likely to help a
relevance classifier (resolving "Mr. Shaw", "the Medicaid meeting", "Exalgo", a custodian's role); L is the
channel that would make the eval invalid outright; B is in between (knowing what TREC 2016 topic 414 is
about tells the model what the assessors were looking for).

## Controls and confounds

- **Veridian is the floor for everything.** It is a corpus of e-mails, memos and calendar invites in the
  same register as the real corpora, written in 2026. Whatever score a model gets on Veridian is what it
  gets from genre knowledge and guessing alone.
- **Verbatim: predictable continuations.** Quoted reply chains and signatures are guessable from the
  headers, so the body is cut *before* the first quoted-reply marker and n-grams that already occur in the
  prefix earn no credit. Contract boilerplate (CUAD) is guessable from genre alone and Veridian has no
  contracts, so for CUAD the *longest exact run* (≥ 15 words, which boilerplate rarely sustains with the
  right party-specific tokens) is the more diagnostic number; the mean LCS for CUAD is reported with that
  caveat. A post-cutoff EDGAR sample would be the proper control and is listed under follow-ups.
- **Entity: famous vs corpus-specific people.** Ken Lay is world knowledge; Nina Oviedo is not. Names are
  tiered by document frequency in our files so the tail tier measures corpus-derived knowledge and the top
  tier measures matter-level world knowledge. Both are contamination in the eval's sense; they are
  reported separately.
- **Entity: name collisions.** A common name may belong to a different, better-known person. Grading on
  the *target organisation* (not on "did it say anything") makes collisions a miss, which is conservative.
  The era hint ("active around 1999-2002") is given because a reviewer's prompt contains the dates anyway.
- **Entity recognition: elimination.** Yes/no per (name, org) pair rather than a multiple-choice over
  orgs, so a model cannot pick Veridian for a name it has never heard of. The foil false-alarm rate is the
  acquiescence baseline for the hit rate.
- **Label recall: base rate.** Pairs are balanced 50/50, so chance is 0.5 regardless of a corpus's
  prevalence, and answer-bias ("always relevant") also scores 0.5.
- **Decoding.** Temperature 0 where the vendor allows it (Gemini, OpenAI with `reasoning.effort=none`,
  Haiku); Sonnet 5 rejects non-default temperature and runs at default. Effort/thinking at the study's
  floor settings (`config.py`), so this is the same "fast classifier" configuration the study ran.
- **Refusals** ("I can't provide the continuation of a private e-mail") are excluded from every V
  statistic on both sides of the floor comparison and reported as a separate rate per model × corpus
  (see *Refusals*, 2026-10-04, below). A refusal is a policy reading, not a memorisation reading; the
  original plan to score them 0 turned out to bias the floor downward.

## What a positive result looks like

The test *works* if the positive controls saturate (canon / Titanic near the top of every scale) while
Veridian sits at the floor, with non-overlapping CIs, for every model; and if L stays at chance for the
corpora whose labels were never published (MNK, Veridian) while reaching well above chance on Titanic. The
result we actually want is where Enron, Jeb Bush, Mallinckrodt and CUAD fall between those two ends, per
model.

(The first draft of this plan used Enron as the ceiling, on the grounds that it is in The Pile. The run
showed that assumption was wrong at the document level: single-exposure e-mails are not reproduced even by
the largest model. Hence the explicit positive controls, added 2026-10-03 after the first pass.)

Pre-registered expectations (written before the run):

- V: Enron > Jeb Bush > CUAD (by exact-run) > Mallinckrodt ≈ Veridian ≈ 0.
- E: Enron top-tier ≈ 1.0 (Lay, Skilling, Kean), tail > 0; Jeb Bush top-tier high (Bush, Shanahan), tail
  low; Mallinckrodt low throughout; Veridian 0 with a non-trivial confabulation rate.
- B: every model knows CUAD's categories (it is an NLP benchmark); TREC 2016 topics partially; TREC Legal
  topics poorly; Veridian UNKNOWN.
- L: chance everywhere. If any corpus is above chance, that is the headline.

## Cost

Per model: 380 verbatim + 149 recall + 745 recognition + 500 label + 7 benchmark = 1,781 calls, ~280k
input tokens, ~80k output tokens. Actual: Luna $0.12, Terra $1.08, Sol $2.12 (list prices, no flex/batch).
The six-model small/mid roster would be ≈ $5. Nothing here classifies documents. The positive-control
sources (three Gutenberg texts, the Titanic CSV) are downloaded into `data/contam/raw/` on first build.

Commands:

```bash
bench contam-build                       # data/contam/probes.jsonl (deterministic, seed 7)
bench contam-run -m gpt-5.6-luna -y      # resumable; default roster is the six small/mid LLMs
bench contam-run -n 2 -y                 # pilot: 2 items per (probe, corpus)
bench contam-report                      # results/contam/summary.json + REPORT.md
bench contam-html                        # results/contam/contamination_report.html (no JS, inline SVG)
bench contam-paper                       # paper.html, explainer.html, report_short.html, explainer_lawyer.html, report_documents.html, report_case.html
bench contam-review                      # results/contam/verbatim_review.html (side-by-side, sortable continuations)
bench contam-jev [-n 3]                  # M3 header-only relevance on Jev via the TypeSafe API -> results/contam/jev.jsonl (resumable)
```

## Part II: is the *case* in the model? (matter-knowledge probes)

Part I treats a corpus as text: documents, correspondents, benchmark, labels. A relevance review is not
defined by a corpus but by a *matter*: a complaint, the allegations, the parties and people, the factual
record, the outcome. A model that already knows how the Enron fraud worked, which executives ran which
vehicle, and what the shredding was about can read a request for production and know what the responsive
documents will look like before seeing one. That advantage never shows up as verbatim recall of an e-mail,
and Part I would clear a corpus that has it. Four of the study's five corpora come from matters that are
among the most-documented litigation in American legal history, so this channel is the one specific to
eDiscovery. Part II asks four questions about each matter, each with its own probe, and adds the controls
that make the answers readable.

| What a case-aware reviewer has | Probe | How it is measured |
| --- | --- | --- |
| recognises the matter even when names are changed | **M0 matter identification** | A de-identified sketch (or the TREC pseudonymised complaint itself) → "which real company/case is this?" Scored against answer keys and, for Veridian, against a list of real templates (DePuy ASR, Zimmer, Stryker, S&N, Wright). |
| knows the record: allegations, players, timeline, outcome | **M1 matter recall** | "Describe {matter}" (≤400 words) graded against a hand-written checklist of 16-20 facts in five categories (parties, allegations, people, events, outcome). Each fact flagged `in_context` if the study's task context already states it, so a *beyond-context* share is reported separately. Whole-word keyword matching. |
| knows what to look for before opening a document | **M2 evidence prior** | Given matter + request, list 25 terms (typed person / organisation / codename / product / place / period / keyword) you expect in responsive documents. Terms already in the prompt are discarded. Each remaining term is scored against the labelled corpus: *grounded* (occurs in ≥ 2 judged docs) and *discriminative* (≥ 2 responsive docs, lift ≥ 2 vs the non-responsive rate). Named terms (proper nouns typed as entities) are the case-knowledge signal; generic keywords are vocabulary. |
| knows who the people are | **M3 metadata-only relevance** | Paired conditions on the same balanced sample (20 + 20 per request; 15 + 15 for Jeb Bush): `headers` = Date/From/To/Cc/Subject vs `subject` = Date/Subject. Δ = acc(headers) − acc(subject), paired bootstrap CI, with a lexical (request-title word in subject) baseline. The matter is named in the context so the headers cannot leak *which* company it is. |

Controls: **Veridian** (fictional) is the floor on every probe; **U.S. v. Microsoft** is a famous-case ceiling
for M0/M1; **Complaint J vs Complaint K** is a within-Enron contrast (same mailbox, same model; one set of
requests is the scandal, the other an unrelated oil-spill fact pattern); **pseudonym vs named** on the
Complaint J requests isolates whether the pseudonym suppresses knowledge the model has. Items: 6 M0, 5 M1,
52 M2 (6 request sets), ~2,900 M3 per model. Build is deterministic (`matter_items(rng seed+4)`); Part I
item ids are unchanged. Cost (list prices): Luna $0.31, Terra $3.14, Sol $6.12; $9.57 for the three.

Pre-registered expectations: M0 fails and M1 says "unknown" on Veridian; Enron ≈ Microsoft on M1; Complaint
J named ≫ Complaint J pseudonymised ≫ Complaint K on discriminative named terms; M3 Δ > 0 only where the
cast is known (Enron), ≈ 0 on Veridian.

### The composite

`summary["composite"]` collapses the battery to three 0–100 numbers per dataset × model — `doc_score`, `case_score`, `composite` — shown
as a grouped-column matrix at the top of the results in `contamination_report.html` (Overview), `paper.html` (Table 2) and
`report_short.html` (Table 2), with a per-channel breakdown behind a disclosure. For each model, every channel's headline metric is placed
between the floor (Veridian's value, 0) and a ceiling (100): V = LCS-F1 to the founding documents; E = recognition d′ to the framers;
L = label accuracy from chance to Titanic; B = share of the benchmark's own topics recited (0→1; Mallinckrodt has none); M0 = 0/100 for
identifying the matter from the pseudonymised complaint / nameless sketch; M1 = checklist share to *U.S. v. Microsoft*; M2 = discriminative
named terms (best request set, named Complaint J for Enron) to the largest set observed. Clipped to [0, 100]. `doc_score` = mean of V, E, L, B;
`case_score` = mean of M0, M1, M2; `composite` = plain mean of all available channels (equal weight across kinds — a choice, stated in the
note; the split exists because the overall mean hides the main finding). Current values, documents / case / overall (Luna · Terra · Sol):
CUAD 80/–/80 · 66/–/66 · 62/–/62 (no case channels); Enron 13/91/46 · 2/95/42 · 12/67/36; Mallinckrodt 6/56/31 · 14/49/31 · 10/55/33;
Endo 0/64/32 · 3/59/31 · 1/62/32; Jeb Bush 6/86/40 · 0/73/31 · 5/71/33; Veridian 0/0/0 · 4/0/2 · 0/0/0 (the Mallinckrodt
figures moved slightly when Endo was added, because Endo's organisation joined the recognition foil set: Sol's MNK d′ 2.1 → 1.6 on one new false alarm). Sol's Enron case score is held down by the strict M0 rule (it named
Reliant Energy). The matrix carries a **Jev** column whose cells read n/t (not testable with this probe): Jev is a classifier, so the generative
probes cannot be posed to it and no composite is computed. Its vendor's statement that it is not pre-trained on public text is a claim
this study tests only where a probe can be posed; the ablation (below) tested it on full documents and found Jev's knowledge effect +0.0 [−2.6, +2.6], and the classifier-native tests (section at the end; `ediscovery_bench/contam/jevnative.py` renders them into every write-up as §21 of the main and case reports, a subsection of the paper's §10, and finding 6 of the story) are consistent with Jev not having been trained on these collections while showing it knows the cases behind them at effect sizes comparable to the LLMs — so the case columns of the Jev matrix cells carry a second mark (‡) pointing there. The one probe that fits its interface, M3 header-only relevance, *was* run on it (`bench contam-jev`, `ediscovery_bench/contam/jev_m3.py`: one
TaskSet per request set built from the matter context, the header block as the document, a Noul question with no criteria, 2,900 calls,
$0.17). `score.py` keeps such classifier-only models in `summary["classifier_models"]`, out of the text-model list and every other
channel, and reports them in `metadata_relevance` only; the M3 figure and tables carry Jev as a real column. The full-document
comparison with Jev is the ablation, reported in §20 of the case report. The report is also published in two halves with their own matrices: `report_documents.html`
(Part I, documents score) and `report_case.html` (Part II + ladder, case score), built by `ediscovery_bench/contam/split.py` from the
same pieces as the main report.

## The ladder: real matters at graded exposure

Two anchors fix the ends of the matter-knowledge scale but not its shape. `ediscovery_bench/contam/ladder.py`
adds 22 real matters from the last ~90 years as calibration rungs, each given the same M0 sketch and M1
checklist treatment as the study's matters (10–18 facts; rubric facts that the question itself states are
excluded from the headline share, so an answer that echoes the question earns nothing). The rungs are chosen
in *families* mirroring the corpora so that each study matter can be read against named peers:

| family | rungs (expected exposure) |
| --- | --- |
| accounting & securities fraud (Enron) | WorldCom (high), HealthSouth (mid), Peregrine Systems (low), Equity Funding 1973 (low), McKesson & Robbins 1938 (low) |
| opioids (Mallinckrodt, Endo) | Purdue / Sacklers (high), Insys (mid), Rochester Drug Co-operative (low), Teva / Actavis 2022 (mid), JUUL 2019-23 (high; the adjacent public-nuisance case) |
| e-mail in public life (Jeb Bush) | Clinton server (high), Bridgegate (mid), Sony Pictures hack (mid) |
| device mass torts (Veridian) | Dalkon Shield (mid), DePuy ASR (mid), 3M Combat Arms earplugs (mid), Bair Hugger (low) |
| landmark disputes | Bhopal (high), Texaco v. Pennzoil (mid), Dieselgate (high), Theranos (high), FTX (high) |
| post-cutoff controls | SEC v. Meyer Global Management (filed 30 Sep 2026); SEC v. Mathews / Near Intelligence (2026 complaint; the company's Dec 2023 collapse predates the cutoff) |

An independent exposure proxy is recorded for every matter: the English Wikipedia article's length, number of
language editions and last-twelve-months pageviews (`data/contam/raw/wiki_footprint.json`, cached; the
Wikimedia APIs rate-limit hard, so the fetch is paced and resumable). Where no article exists for the
*matter* the lookup falls back to the company or biography page and is flagged as a proxy. Cost: 44 items per
model, ≈ $1.4 for three models.

## Follow-up: does exposure translate into a score advantage?

This probe measures exposure, not effect. The direct test of *effect* is a pseudonymisation ablation:
classify a fixed sample twice, once as-is and once with every person and organisation name consistently
replaced by fictional ones, and compare F1 per corpus. If the drop is larger on Enron than on Veridian, entity
knowledge is doing work. (Pre-run estimate: $30-40 at the mid tier; actual $104.75 paid for four systems.)

**Run (2026-10-03) as `ediscovery_bench/ablation/`** — see `results/ablation/ablation_report.html` and `REPORT.md`.
Design as run: Enron Complaint J (994 TREC Legal 2010 learning-task e-mails, requests 201–207, one judged request per
document) vs Complaint K on the same mailbox (999 e-mails, 301–303; knowledge-poor control), Veridian (1,000 docs × 10
requests; fictional, renaming cost only) and Mallinckrodt (1,840 docs × 8 requests, with/without a one-page case brief —
knowledge added instead of removed). Renaming is a deterministic dictionary (101 Enron phrases, ~2,300 surnames
harvested from header fields, applied in addresses, Lotus paths, Exchange aliases); EDRM production headers
(`X-SDOC`, `X-ZLID`) stripped from both conditions after the leak check showed models naming Enron from them.
Knowledge effect = Δ(J) − Δ(K), bootstrap by document. Four systems: GPT-5.6 Luna/Terra/Sol and Jev — Jev's vendor
states it is not pre-trained on these corpora; we treat that as a claim and test it with the same contrasts.
Commands: `bench ablation-build`, `bench ablation-leak`, `bench ablation-run [--pilot] [--model jev@base]`,
`bench ablation-report`. Spend $104.75 paid ($222.70 list), plus $14.21 for the 2026-10-06 Veridian renamed re-run (renamer v2) that
superseded the $14.20 v1 run; see the renamer audit in `design/07` and `results/ablation/renamer_audit.md`.

**Result.** ΔF1 (renamed − named, pp; Luna / Terra / Sol / Jev): Enron J −0.2 / −2.0 / +1.1 / −1.7; Enron K −1.8 / +0.6 /
−1.0 / −1.7; Veridian −0.1 / −0.4 / −1.0 / −0.3 (recall +0.2 / −0.1 / −1.1 / −0.1; renamer v2, re-run 2026-10-06 — the v1 renamer had
left the product's short form and two surgeons' surnames in a third of the documents and read +0.2 / −2.9 / −2.3 / −1.9). Knowledge effect Δ(J) − Δ(K): Luna +1.6
[−1.2, +4.6], Terra −2.6 [−5.8, +0.5], Sol +2.1 [−0.6, +4.6], Jev +0.0 [−2.6, +2.6] — no interval excludes zero and the
LLMs' signs disagree. Renaming flips 2–5 % of labels. Leakage: asked which company the *renamed* Enron documents came
from (headers stripped, ticker mapped) the models still said Enron for 61 / 82 / 94 % of 200, and for 48 / 77 / 94 % of the
77 documents with no knowledge-bearing name, so Δ is a lower bound and the names are not the channel. Jev on FAS 140:
ΔF1 −18.2 [−27.6, −10.4], 12 positives lost and none gained, 7 of the 12 naming Raptor/Talon/LJM2/Chewco (p 0.5–0.6 →
0.1–0.4), while Terra/Sol gained +13.6/+16.4 on the same request — recorded as under test. The bare-token probe it called
for has been run (classifier-native tests, below): 0 % / 0 % with the request as written, 78 % / 0 % once the criteria name the
vehicles, so the loss is not a bare-name reflex but Jev reading request and document together; the code-name swap then found the
same case knowledge on all four matters.
Mallinckrodt ± brief: −1.0 / −0.7 / +0.6 / +1.3 F1 (Jev recall +4.1). The contamination write-ups report this in
`contamination_report.html` §20, `report_case.html` §20, `paper.html` §10, `report_short.html` §7, the explainers, via
`ediscovery_bench/contam/effect.py` (reads `results/ablation/summary.json`; future-tense fallback if absent).

**Round 2 (2026-10-04; `design/07_ablation_round2.md`, `results/ablation/round2/REPORT.md`, `summary.json`, `fig_cuad.png`,
`fig_jeb.png`).** The same design carried to the two corpora round 1 could not cover: CUAD (102 contracts, 1,200 excerpts × 12
clause requests; renamed *and* paraphrased by a model not under test, with a finish-the-document memorisation check and a
Terra fidelity judge, 89/100 rewrites legally equivalent, 1155/1200 deterministic checks passed) and Jeb Bush (1,000 e-mails × 12
requests; the Governor, his family and 715 public figures renamed; matter topics vs control topics on the same documents).
Luna, Sol and Jev ran on 2026-10-04 (the cheap version: Terra dropped under the $75 rule, spend $55.79); **Terra was added on
2026-10-06** once the key was topped up ($26.62, each run within 2 % of estimate), with the leak checks completed for all three LLMs
($0.78); round-2 spend $83.18. CUAD ΔF1 (Luna / Terra / Sol / Jev): renamed −0.6 / −0.7 / +0.2 / +0.0; paraphrased −1.3 / −0.3 / −0.4 /
−0.3; paraphrase knowledge effect net of Veridian paraphrased −0.8 [−2.6, +1.0] / +0.1 [−1.6, +1.7] / −1.4 [−2.9, +0.0] / −0.0 [−1.4,
+1.4]; no dose–response with the per-contract memorisation score (Spearman ρ −0.02 … +0.20); Sol's LCS-F1 on the paraphrased windows
fell 0.315 → 0.279 (≥ 15-word runs 10 % → 6 %), so the paraphrase did remove memorised surface. The CUAD *rename* effects net of the
Veridian rename floor are −0.4 / −0.3 / +1.2 / +0.3, intervals through zero (with the leaky v1 Veridian floor they had read +2.2 †, +2.5 †,
+1.9 † for Terra, Sol and Jev — an artefact of that renamer, withdrawn). Jeb Bush knowledge effect Δ(matter) − Δ(control): Luna +1.0 [−1.2, +3.2], **Terra −2.3 [−4.3,
−0.3]** (matter −1.6, control +0.7; matter recall −2.6; GW Bush request −5.8; larger than Terra's Veridian rename floor of −0.4, so not renaming cost), Sol
+0.1 [−1.8, +1.9], **Jev −3.1 [−5.5, −0.8]** (matter recall −6.2, precision +3.7; GW Bush 0.82 → 0.68, recount 0.46 → 0.39, Rilya 0.35 →
0.29); the LLMs still named Jeb Bush for 69 % / 85 % / 94 % of the renamed e-mails (Luna / Terra / Sol) and the real CUAD parties for
11 % / 22 % / 32 % of the renamed excerpts. Carry-forward: for the LLMs, *knowing the case changed review accuracy by at most a few F1
points* now holds on three matters (Enron, Jeb Bush, CUAD) under three manipulations (remove names, paraphrase, inject a brief — the
last from check D below), no knowledge effect beyond 2.6 F1 points, every interval including zero except Terra on Jeb Bush — the first
LLM interval in the study to sit off zero, and of the size the earlier lower bounds always allowed; for Jev, a small
familiarity effect of ~2–3 points on matter topics built around public figures (Jeb Bush −3.1; FAS 140; the knowledge-dependent
Enron documents in check A), consistent with public-web knowledge of public figures and not by itself evidence of training on the
collections — a Jev score on a famous-figure collection may run a few points high. Rendered in every write-up via
`ediscovery_bench/contam/effect2.py` and `verify_summary.py` (None-safe; the sections appear only when the summaries exist).

A post-cutoff control for contracts (EDGAR exhibits filed after each model's cutoff, segmented like CUAD)
would close the boilerplate gap in the verbatim probe for CUAD.

## Findings (run 2026-10-03, OpenAI models only)

Run on `gpt-5.6-luna`, `gpt-5.6-terra` and `gpt-5.6-sol` (the Anthropic and Gemini keys were not present in
`.env` at run time; `bench contam-run` is resumable and will fill those in when they are). 1,781 items per
model for Part I ($3.32) plus Part II ($9.57) and the ladder ($1.39); $14.28 in all, plus $0.17 for Jev's M3 and $104.75 for the
ablation, $33.50 for the Endo corpus, label panel and probes, and $4.64 OpenAI + $0.15 Jev for the classifier-native tests ($157.49 total). Full tables: `results/contam/REPORT.md`; per-item scores:
`results/contam/scored_items.jsonl`.

### Endo: the post-cutoff corpus (added 2026-10-03)

Endo was added to answer the question the ladder's 2026 SEC cases could only sketch: what does a *real* collection whose
publication post-dates the models' training data look like on these probes, when the matter behind it is one they can know? Result, Luna / Terra / Sol:
V LCS-F1 0.15 / 0.14 / 0.15 against Veridian's 0.13 / 0.15 / 0.17 on the filtered pool (one 8-word non-novel run; nothing
memorised, see *Verbatim pool quality* below); E1 free recall
0/30 for every model; E2 recognition 0 % / 10 % / 0 % hits with d′ 0.6 / −1.1 / −0.7 (the tail-tier and top-tier hit rates are 0 %
for Sol, which recognises 30 % of Mallinckrodt's staff); L 47 % / 52 % / 51 % (chance). The matter, meanwhile, is known: M0 identified
from a nameless sketch by all three; M1 70 % / 55 % / 70 % of the checklist (Mallinckrodt 48 % / 43 % / 52 % after three `people`
items — Mark Trudeau, Victor Borelli, Karen Harper — were added to its rubric on 2026-10-04, re-scored from the stored responses: all
three models name Trudeau, none names Borelli or Harper); M2 2 / 6 / 6
discriminative named terms; M3 subject-only accuracy 70 % / 74 % / 76 % and people Δ within noise; ladder recall 62 % / 44 % / 62 %
against a 13,340-pageview footprint (Mallinckrodt 36,785; Teva 115,631 and JUUL 98,572 are identified by all and recalled at
83–92 % and 60–73 %). Composite 0/64/32 · 3/59/31 · 1/62/32. **Reading:** no document-level signal, as the publication date
predicts — the date is what establishes the documents were not in training; the probes are the check — making this the clearest
"known case, post-cutoff documents" profile in the study, Enron's pattern from the other side, and the recommended held-out
benchmark going forward. Caveat on its gold rather
than its profile: Endo's relevance labels come from a three-OpenAI-model panel; Mallinckrodt's panel mixed vendors.

### Verbatim pool quality (2026-10-04)

The first V pool was 60 random windows per corpus, and inspection of its high-scoring items showed that many were not tests of
memorisation at all. Three kinds of chaff. **Boilerplate**: confidentiality / privilege disclaimers, signature and footer blocks,
"Sent from my iPhone", forwarded-message header blocks, unsubscribe footers, out-of-office replies and bounces, scanner notices —
text any model writes from genre knowledge (Endo `tmkp0422`: an empty `From:/Sent:/To:/Subject:` header followed by OCR noise, then a
standard disclaimer; LCS-F1 0.41). **Public text reproduced inside the corpus**: Federal Register and agency notices, statutes, court
filings, press releases, wire and newspaper stories and newsletters forwarded into mailboxes, product labels, SEC-filing boilerplate,
standard contract clauses. The e-mail corpora's longest run — Mallinckrodt `ltjw0253`, Sol reproducing 34 consecutive words — is a
DEA Paperwork Reduction Act notice quoted in an e-mail: it measures memorisation of the Federal Register, not of the Mallinckrodt
collection, and it was wrongly retained as "embedded public text" in the first pass. **Low-information windows**: header-only or
garbled openings that could not identify the document even to a model that memorised it, and continuations predictable from the
prefix (tables, attendee lists, numbered sequences, a weekly report whose bullets repeat from the prompt with new figures, mirrored
contract clauses). A good V item is custodian-authored, matter-specific text with a distinctive opening and an unpredictable
continuation — text only someone who had seen *this* collection could continue.

Two filters are now applied, by the builder (`bench contam-build`) and the scorer (`bench contam-report`) alike:

1. **Rules** (`ediscovery_bench/contam/boilerplate.py`, `boilerplate_reasons`): disclaimer; signature / footer block; forwarded /
   reply header; unsubscribe footer; auto-reply or bounce (only when the e-mail has little real content); scanner notice;
   protective-order legend; degenerate repetition (continuation copyable from the prompt, including any 12-word stretch already in
   the prefix); `key: value` / attachment lists; tables and attendee lists (`tabular`); OCR garbage (words unknown to a lexicon over
   all corpora); thin prefix (< 40 real content words); and two corpus-frequency guards from an 8-gram document-frequency index
   (`data/contam/raw/boilerplate_df_*.json`): `corpus_template` (≥ 25 % of the continuation's 8-grams, or a run of 8, in ≥ 2 other
   documents) and `duplicate` (the whole window in ≥ 4 other documents). E-mail-only rules are not applied to contracts, the canon
   or CSV rows.
2. **LLM screen** (`ediscovery_bench/contam/screen.py`): GPT-5.6 Luna at temperature 0 (`reasoning.effort=none`, max 120 output
   tokens) reads prefix + true continuation with the collection type and assigns exactly one of `original_internal`,
   `public_reproduction`, `template_boilerplate`, `low_information` plus a ≤ 15-word reason; the prompt states the purpose (text only
   someone who had seen this specific collection could continue), defines each class in one line, and says explicitly that a
   collection being published does not make its own documents public — the class is for text copied or forwarded from an outside
   source. Only `original_internal` windows enter the pool. Verdicts are cached in `results/contam/v_screen.jsonl`, keyed by item id,
   window hash and prompt version, so re-runs are free. **Anchor exemption:** the canon (Federalist Papers, Constitution) and the
   Titanic CSV are public text by design — that is their job as positive controls — so `public_reproduction` cannot exclude them;
   the other classes still apply. Veridian is screened like every real corpus and passes (59/60; the one exclusion is a conference
   exhibitor-logistics e-mail judged to be reproduced registration text). The screen flagged 7 of 20 Titanic row-chunks as
   `low_information` ("predictable sequential CSV rows") while judging 13 structurally identical chunks original — a small-model
   inconsistency recorded rather than overridden; the ceiling is unaffected (Sol LCS-F1 0.93 on the 13).

The builder keeps every existing window in `data/contam/probes.jsonl` (excluded ones included, so the scorer and the review page can
show them as excluded with their responses) and draws only the shortfall: documents not yet used, in the same deterministic shuffle
(seed 7 + 1), in batches three times the shortfall, rules then screen, first N `original_internal` windows; a document whose default
45 % hand-off fails is retried at 60 / 30 / 75 % (item id suffix `#w60` etc.) and replacements carry `meta.replacement = true`. The
resumable run step then executes only the new ids.

| Corpus | windows in file | fail rules (first rule) | fail screen (class) | replacements | pool |
| --- | --- | --- | --- | --- | --- |
| Enron | 85 | 10 (signature 3, repetitive 2, duplicate 1, list_footer 1, quoted_header 1, corpus_template 1, disclaimer 1) | 15 (public reproduction 15) | 25 | 60 |
| Jeb Bush | 77 | 13 (duplicate 10, key_value_list 1, signature 1, corpus_template 1) | 4 (public reproduction 4) | 17 | 60 |
| Mallinckrodt | 99 | 27 (signature 18, repetitive 4, tabular 3, corpus_template 1, quoted_header 1) | 12 (public reproduction 12) | 39 | 60 |
| Endo | 97 | 28 (disclaimer 10, tabular 5, auto_message 5, signature 2, corpus_template 2, ocr_garbage 2, production_stamp 1, key_value_list 1) | 9 (public reproduction 9) | 37 | 60 |
| CUAD | 73 | 7 (repetitive 7) | 6 (public reproduction 5, low information 1) | 13 | 60 |
| Veridian | 61 | 0 () | 1 (public reproduction 1) | 1 | 60 |
| canon | 60 | 0 () | 0 (—) | 0 | 60 |
| Titanic | 20 | 0 () | 7 (low information 7) | 0 | 13 |

Scorer outputs. `summary.json["v_pool"][corpus]` = `{n_candidates, n_kept, n_excluded, by_class, by_rule, excluded_ids,
n_replacements, n_unscreened, screen_exempt}`; `summary.json["verbatim"][model][corpus]` keeps `unfiltered` (every window with a
response) and `rules_only` (after rules, before the screen) headline blocks beside the pool numbers. Per V row in
`scored_items.jsonl`: `boilerplate`, `boilerplate_reason`, `boilerplate_reasons`, `v_pool` (`kept` | `excluded`), `v_exclude_reason`
(`boilerplate:<rule>` or the screen class), `v_screen_class`, `v_screen_reason`, `v_screen_exempt`. The novelty test was also made
number-blind (digits masked before the 5-gram comparison), so a repeated template with new figures no longer counts as a novel run.

Effect on V (Luna / Terra / Sol), original 60 random windows → final pool. LCS-F1: Enron 0.17 / 0.17 / 0.18 → 0.16 / 0.16 / 0.17;
Jeb Bush 0.13 / 0.14 / 0.15 → 0.15 / 0.16 / 0.15; Mallinckrodt 0.17 / 0.16 / 0.21 → 0.15 / 0.15 / 0.16; Endo 0.14 / 0.13 / 0.16 →
0.15 / 0.14 / 0.15; CUAD 0.28 / 0.31 / 0.35 → 0.24 / 0.27 / 0.29; Veridian 0.13 / 0.15 / 0.17 (unchanged). Mean longest run: Enron
3.4 / 3.1 / 3.2 → 2.3 / 2.4 / 2.4; Mallinckrodt 3.3 / 3.3 / 4.1 → 2.4 / 2.6 / 2.6; Endo 2.3 / 2.3 / 2.6 → 2.4 / 2.3 / 2.1; CUAD 5.6 / 6.5 / 8.0 →
4.5 / 5.3 / 6.0. No e-mail-corpus window in the pool has a ≥ 15-word run for any model (longest 10, a Mallinckrodt sales report whose
parallel paragraph structure is inferable from the prompt); novel ≥ 8-word runs on the e-mail corpora are 1.7% / 0.0% / 0.0% (Enron),
1.7% / 3.3% / 1.7% (Mallinckrodt), 0 % (Jeb Bush, Endo). CUAD remains memorised but less so once mirrored clauses and standard
boilerplate are out: ≥ 15-word runs 0% / 5% / 10%, p < 10⁻¹² against the floor for every model. Composite document scores move by
at most 7 points (CUAD Luna 79.9 → 72.9; Mallinckrodt Luna 5.7 → 2.8) and no ordering changes.

**Reading.** The conclusions hold and rest on a better pool. With chaff removed, Sol — the model with the most training data — is at or below
the Veridian floor on all four e-mail corpora (one-sided p = 0.38 / 0.93 / 0.90 / 0.97 for Enron / Jeb Bush / Mallinckrodt / Endo),
and the two retained long runs that looked like memorisation are gone. The small models sit a hundredth or two *above* Veridian on
several real corpora; at the time this section was written that read as significant for Luna on Enron, which the *Refusals* audit
below traced to undetected refusals deflating Luna's floor — on answered items no e-mail corpus is significantly above the floor for
Luna, and Terra on Jeb Bush (p = 0.02) is the one pair under 0.05, on the post-cutoff-adjacent genre rather than on memorised text.

Cost: screen 0.25 USD for 1068 Luna judgements (existing 440 windows plus all replacement candidates); replacement runs
$0.57 across the three models (Luna $0.02, Terra $0.17, Sol $0.38) for 132 new windows; nothing else was re-run.

### Refusals (2026-10-04)

The review page showed a Luna continuation that read "I'm sorry, but I can't provide or reconstruct the continuation of a private
email…" without the `refusal` tag. Audit of all V responses for the three models: the old detector was a substring test for a few
phrases spelt with a straight apostrophe (`can't`) plus a `< 40 words` guard. Every GPT-5.6 refusal uses the curly apostrophe (`can’t`),
so it caught 4 of 37 (only those containing "copyright"), and the guard missed refusals that go on to offer a summary (50–70 words);
it also produced one false positive (a genuine Mallinckrodt continuation "Again, I apologize for missing the call"). The new detector
(`score.detect_refusal`) requires the response to **open** with a first-person refusal ("I can’t / cannot / I'm not able to /
I'm sorry, but I can't / As an AI", straight or curly apostrophes) **and** to name what it withholds within its first 30 words
(provide / reproduce / reconstruct / continuation / access …); the stated reason is categorised as `private`, `copyright` or `other`.
An empty response is scored 0 and recorded as `refusal_kind: "empty"` but is not a refusal. Candidate phrasings were taken from
the data itself (clustering responses on their first eight words), not guessed.

**Treatment.** Option (c): every V statistic — LCS-F1, longest run, ≥ 8 / ≥ 15 shares, strip plot, Mann-Whitney vs the floor — is
computed over the *answered* items only, for the real corpora and Veridian alike; the refusal rate (over all pool items) is shown
beside it and the refusals-as-zero mean is kept in the summary as `lcs_f_mean_all`, with `lcs_f_p_greater_all` the old-convention
test. A refusal on "a private e-mail" tells us the model's policy, not whether it has seen the text.

Refusal rate per model × corpus, kept pool, old detector → new detector (kinds):

| model | Enron | Jeb Bush | MNK | Endo | CUAD | Veridian | canon | Titanic |
|---|---|---|---|---|---|---|---|---|
| Luna | 0% → 0% | 2% → 2%; 1 copyright | 0% → 3%; 1 private, 1 copyright | 0% → 15%; 9 private | 2% → 2%; 1 private | 2% → 25%; 8 private, 5 other, 2 copyright | 0% → 0% | 0% → 0% |
| Terra | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% |
| Sol | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% | 0% → 0% |

**Finding.** Only Luna refuses, and the rate is sharply corpus-dependent: Veridian — the fictional floor — most of all, then Endo, almost
never the 2001 Enron mail and never the founding documents or the CSV. Modern-looking corporate e-mail about a product-liability
matter reads as "private" to the policy regardless of whether it is real; the policy keys on how the text looks, not where it came
from. Terra and Sol refuse nothing at `effort=none`. Under the old convention the undetected refusals had been scored as ordinary text
(an "I can't provide…" paragraph shares a few function words with any target, LCS-F1 ≈ 0.05–0.08), which put Luna's floor at 0.135;
scored 0 it would have been 0.114; on answered items it is 0.152. Either way the refusals, concentrated on the floor corpus, were what
made Luna look significantly above the floor on Enron.

Headline V (answered items) with the refusal rate, and the one-sided p vs Veridian — answered items → old convention (refusals as 0):

| model | Enron | Jeb Bush | MNK | Endo | CUAD | Veridian |
|---|---|---|---|---|---|---|
| Luna | 0.165 (refuse 0%)<br>p 0.16 ← 0.001 | 0.154 (refuse 2%)<br>p 0.53 ← 0.016 | 0.156 (refuse 3%)<br>p 0.47 ← 0.018 | 0.164 (refuse 15%)<br>p 0.17 ← 0.051 | 0.248 (refuse 2%)<br>p 0.00 ← 0.000 | 0.152 (refuse 25%) |
| Terra | 0.157 (refuse 0%)<br>p 0.07 ← 0.074 | 0.160 (refuse 0%)<br>p 0.02 ← 0.024 | 0.149 (refuse 0%)<br>p 0.51 ← 0.507 | 0.141 (refuse 0%)<br>p 0.69 ← 0.687 | 0.268 (refuse 0%)<br>p 0.00 ← 0.000 | 0.145 (refuse 0%) |
| Sol | 0.170 (refuse 0%)<br>p 0.38 ← 0.383 | 0.152 (refuse 0%)<br>p 0.93 ← 0.934 | 0.161 (refuse 0%)<br>p 0.91 ← 0.909 | 0.149 (refuse 0%)<br>p 0.98 ← 0.975 | 0.295 (refuse 0%)<br>p 0.00 ← 0.000 | 0.168 (refuse 0%) |

The *Verbatim pool quality* figures above were computed before this change, under the refusals-as-zero convention then in force; the
summary, report and paper now carry the answered-items figures. Terra and Sol are unchanged (no refusals). For Luna the floor moves
from 0.135 to 0.152 and Endo from 0.150 to 0.164; no e-mail corpus is significantly above the floor for Luna
(p = 0.165 / 0.529 / 0.473 / 0.169), where previously Enron was (p = 0.001 under the old convention). Terra on Jeb Bush
(p = 0.024) is now the only small-model pair under 0.05. CUAD stays at p < 10⁻⁹ for every model. No composite ordering changes.
Per-item fields in `scored_items.jsonl`: `refusal: bool`, `refusal_kind: private | copyright | other | empty | null`.

### Does the test discriminate? Yes: both ends of the spectrum behave, and the real corpora sit between them.

| Probe (Sol, the largest model; Luna / Terra in the report) | Veridian (floor) | Enron | Jeb Bush | MNK | CUAD | canon / Titanic (ceiling) |
| --- | --- | --- | --- | --- | --- | --- |
| V: LCS-F1 of the 60-word continuation (filtered pool) | 0.17 | 0.17 | 0.15 | 0.16 | 0.29 | **0.94 / 0.93** |
| V: share of docs with an exact run ≥ 15 words | 0 % | 0 % | 0 % | 0 % | 10 % | **98 % / 100 %** |
| V: mean longest exact run (of 60 words) | 2.5 | 2.4 | 2.3 | 2.6 | 6.0 | **56 / 57** |
| E2: recognition hit rate / false alarms / d′ | 0 % / 0 % / 0.5 | 33 % / 0 % / 2.2 | 37 % / 4 % / 1.4 | 30 % / 1 % / 1.6 (was 0 % / 2.1 before Endo joined the foil set) | n/a | **100 % / 0 % / 4.8** |
| E2: tail-tier (obscure names) hit rate | 0 % | 0 % | 20 % | 10 % | n/a | **100 %** (Broom, Bassett, Few...) |
| B: benchmark topics recovered | not confabulated | 0/4, 1/7 | 0/34 | 4/4 facts | 41/41 | **20/20** (20 Newsgroups) |
| L: label accuracy from id alone (ceiling 50 %) | 50 % | 49 % | 50 % | 48 % | n/a | **84 %** (Titanic) |

The floor is not zero: a plausible continuation in the right genre scores LCS-F1 ≈ 0.14-0.17 and a longest
exact run of ≈ 2 words with no knowledge at all, so that is the number any real corpus has to beat. The
ceiling is close to the maximum of each scale: Sol reproduces the Federalist Papers essentially verbatim
(56 of 60 words in an exact run on average), reproduces Titanic CSV rows including ticket numbers and
fares, recognises every one of the 30 framers including the obscure ones with zero false alarms, recites
all 20 newsgroups, and recovers 84 % of Titanic passengers' survival from PassengerId + name after sex and
age are balanced out (Luna 70 %, Terra 75 %). Every eDiscovery corpus is far closer to the floor than to the
ceiling on every channel, with CUAD the clear exception on V and B. The ordering is consistent across the
three models, and the control-only label probes (Mallinckrodt, Veridian) stay at chance (45-54 %) once the
sampling confound described below was removed.

### Per-corpus exposure profile

| Corpus | V: documents memorised? | E: cast known? | B: benchmark known? | L: labels known? | Verdict |
| --- | --- | --- | --- | --- | --- |
| **CUAD** | **Yes.** LCS-F1 0.24-0.29 vs 0.13-0.17 floor (p < 0.001, all models), after standard clauses and mirrored provisions are filtered out of the pool. Sol reproduces an exact run of ≥ 15 words in 10% of excerpts, ≥ 8 novel words in 20%; e.g. 37-40 consecutive words of a SpinCo/RemainCo IP licence with the party-specific defined terms intact. | n/a | **Yes.** All 41 clause categories recited by every model (98-100 %). | not probed (labels are the categories) | Most exposed corpus. The models have seen both the EDGAR exhibits and the benchmark. Boilerplate inflates the mean LCS somewhat, but the long party-specific runs are not boilerplate. |
| **Enron** | **No.** LCS-F1 0.16-0.17, at the floor for every model once refusals are excluded (Luna p = 0.16, Sol p = 0.38). One pool e-mail yields a run ≥ 8 (8 words, Luna). The former long runs — a repeated error log (copying from the prompt) and a list of internet-famous one-liners — are excluded as repetition and public text. No e-mail body was reproduced. | **Headline figures only.** Free recall names Enron for 3-13 % of names (Dasovich, Belden, Whalley, Lavorato, Kean); recognition hits 17-33 % with 0 % false alarms for Luna/Sol (d' 1.6-2.1), all in the top/mid tiers. Tail names: 0 %. | **No.** TREC Legal 2009/2010 topics: 0/4 and 0-1/7; every model confabulates plausible Enron-scandal topics (California crisis, Andersen, LJM) instead. | **No.** 49-51 %. | Exposure is to the *Enron story*, not the mailbox: the models know the executives who appear in the scandal literature and nothing about the ~thousand other correspondents, and they do not reproduce message text. |
| **Jeb Bush** | **No.** LCS-F1 0.15-0.16, at the floor for Sol (p = 0.93); one 8-word run (Luna) in the pool. | **Headline figures only.** Free recall 3-17 % (Bush, Shanahan, Stutler, Castille, Fasano, Baker: all Florida politics, Wikipedia-grade); Sol recognition 37 % with 6 % FA (d' 1.2). | **No.** 0/34 athome4 topics; Terra offers athome1 topics (Terri Schiavo) and invented ones (hurricanes, FCAT). | **No.** 45-50 %. | Despite the 2015 web release, these models show no verbatim trace of the collection. What they know is Florida public life, which a reviewer's prompt already states. |
| **Mallinckrodt** | **No, once the chaff is out.** LCS-F1 0.15-0.16, not significant for any model (Sol p = 0.91); 2%–3% with a run ≥ 8, longest 10 words in a sales report whose parallel structure the prompt gives away. The 34-word Federal Register / DEA notice and the weekly-report template are excluded (public text; repetition). No Mallinckrodt-authored prose was reproduced. | **Recognition without recall.** Free recall: 0 % for all models (100 % UNKNOWN for Luna/Sol). But Sol says *yes* to "was {name} at Mallinckrodt/Covidien" for 30 % of names with **0 % false alarms** (d' 2.0): Harper, Buist, Tetzlaff, Cardetti, Kadlic, Kilper, Wickline... These are real employees named in MDL filings and press coverage. | Partial: all models know what OIDA is (3-4/4 facts). | **No.** 48-52 % after the fix. | The e-mails are not memorised, but the largest model recognises the people in them from the litigation record. That is the "surrounding details" channel the probe was designed to catch, and free recall alone would have missed it. |
| **Veridian** (negative control) | Floor. 0-2 % runs ≥ 8 (one 8-word run in a CAPA memo, generic QA phrasing). | 0 % hits; 97 % UNKNOWN; Terra says yes-to-Veridian for 10 % of names (acquiescence). | No confabulation: all three models say the matter is not in the public record. | 50-54 %. | Clean. |
| **canon** (positive control) | **Saturated.** LCS-F1 0.36 / 0.63 / 0.94 (Luna / Terra / Sol); ≥ 15-word exact runs in 25 % / 67 % / 98 % of items. | **Saturated.** Recall names the Constitution for 97-100 % of framers in every tier; recognition 97-100 % with 0 % false alarms (d′ 4.3-4.8). | 20/20 newsgroups for every model. | n/a | Behaves as a ceiling should, and shows the scale gradient (Luna < Terra < Sol) the real corpora only hint at. |
| **Titanic** (positive control) | **Saturated.** CSV rows reproduced: LCS-F1 0.47 / 0.66 / 0.94; 100 % of Sol's chunks have a ≥ 15-word exact run (ticket numbers, fares, cabins). | n/a | n/a | **70 % / 75 % / 84 %** with the title-only ceiling at 50 %. | The label-leakage probe does detect leakage when it exists; its chance-level readings on the eDiscovery corpora are therefore informative, not a null instrument. |

### Cross-model pattern

- **Scale raises exposure.** Sol (large) > Terra (mid) > Luna (small) on every memorisation and knowledge
  measure, in line with the memorisation literature. The gradient is stark on the positive controls
  (Federalist LCS-F1 0.36 → 0.63 → 0.94; Titanic labels 70 → 75 → 84 %) and visible on the real corpora:
  Sol is the only model with meaningful recognition of Mallinckrodt staff and with 18 % ≥ 15-word CUAD runs.
- **Position on the spectrum.** Measured on V (share of docs with a ≥ 15-word exact run, Sol): Veridian
  0 %, Jeb Bush 0 %, Enron 2 %, MNK 3 %, CUAD 18 %, canon 98 %, Titanic 100 %. On E2 (d′): Veridian 0.5,
  Jeb Bush 1.5, MNK 1.6, Enron 2.3, Endo −0.7, canon 4.9. The e-mail corpora are much nearer the floor than the
  ceiling; CUAD is about a fifth of the way up on documents and all the way up on benchmark knowledge.
- **Recognition is more sensitive than recall.** Free recall ("who is X") returns UNKNOWN for 80-100 % of
  names everywhere; the yes/no recognition matrix finds signal that recall misses, and the foil false-alarm
  rate makes it interpretable. Keep both: recall is the stricter claim, recognition the more sensitive one.
- **Terra at `effort=none` is a yes-sayer**: 63-80 % false alarms on foil organisations, so its hit rates are
  uninterpretable on their own and its d' (0.2-0.6 on Enron/JB) is the number to read. Luna and Sol have
  0-6 % false alarms. This is itself relevant to the main study: the same decoding configuration is used
  there.
- **Nobody knows the TREC topics.** 0/34 athome4 topics and 0/4 Legal 2010 topics for every model, with
  confident confabulation. The benchmark's *questions* are not in these models in any recoverable form, so
  topic knowledge is not a channel for the TREC-based arms.
- **No label leakage anywhere** (45-54 %, ceiling 50 %).

### Implications for the eval

1. **CUAD results carry the largest contamination caveat**, on two channels (documents and benchmark). Report
   them as such; prefer the e-mail corpora for headline claims about LLM vs Jev.
2. **Enron and Jeb Bush are not memorised at the document level by these models**; the exposure is to the
   famous cast, which the matter background in the prompt supplies anyway. The remaining question (does
   knowing the Enron executives help classify Enron e-mail?) was answered by the pseudonymisation ablation (above): within ±3 points, a floor.
3. **Mallinckrodt is safer than its public availability suggests on documents, but not on people** for the
   largest model. The ablation's Mallinckrodt arm (a case brief added) moved Sol by +0.6 F1.
4. **Veridian is confirmed clean** on all four channels, with the useful side result that the models do not
   confabulate about it.

### Big Thorium: a second floor (added 2026-10-06)

The *Relativity aiR for Review demo workspace*, distributed by Relativity to its customers and demo users — fictional company, fictional
City of Atlantis bribery matter, 2,091 e-mails — is **public documents, invented case**: nothing to know from the news, but e-mails that
circulate widely among Relativity users and could have been crawled. In the exposure typology it sits between Veridian (private documents,
invented case) and CUAD (public documents, no real case). The four probes
(`ediscovery_bench/contam/bigthorium.py`; 291 items, $0.39; `results/contam/bigthorium_summary.json`) say that, despite being public, it is
a floor: entity recall 0/30
for every model (the non-UNKNOWN answers are real-world namesakes), recognition "yes" for BigThorium 0 %, the de-identified sketch matched to
real municipal energy-contract investigations (Johnson Controls / Milwaukee, Ameresco / Holyoke) and never to Big Thorium, and all three
models decline to describe the matter when asked by name. Verbatim continuation scores *above* Veridian (LCS-F 0.20–0.22 vs 0.15–0.17
rules-only) but with 3–4-word longest runs and no run ≥ 15: the demo's e-mails are machine-written marketing-style prose whose continuations
are predictable without being remembered — a confound to keep in mind for any LLM-generated test collection, and a reason the verbatim probe
is read with its run statistics rather than LCS-F alone. Asked what the aiR demo workspace is about, Sol describes a bribery-to-win-a-contract
investigation under invented names (the right scenario type), Terra a different scenario, Luna declines. The renaming ablation on it
(`design/07_ablation_round2.md` §C) finds |ΔF1| ≤ 1.1 for every system, bracketing Veridian.

### Part II findings (same run; Luna / Terra / Sol)

**M0 — the pseudonyms do not hold.** Every real matter is identified from its fact pattern: Complaint K
("Bleak Horizon") → Deepwater Horizon with BP/Transocean/Halliburton supplied unprompted; the Mallinckrodt,
Jeb Bush and Microsoft sketches (no proper nouns at all) named immediately. Complaint J (TREC's "Volteron")
→ Enron for Luna and Terra; Sol names Reliant Energy, reading the invented code name "RND7" as a Reliant
trading strategy — wrong company, same conclusion: the pseudonym sends the reader to a real case. On the
fictional matter Luna and Terra state confidently that Veridian is Zimmer Biomet (the sketch says Warsaw,
Indiana); Sol correctly calls it "a composite or fabricated matter" and names the three real litigations it
resembles. The floor sits at chance on documents and people, but its *archetype* is recognised.

**M1 — how much of the record is in the model.** Enron 85 / 80 / 90 % of the checklist (beyond-context
93 / 93 / 100 %), on a par with the Microsoft ceiling (88 / 94 / 88 %). The two Enron items every model
misses are document shredding and the California trading schemes, i.e. the operational facts TREC topics
204-205 target: the models know Enron as a securities fraud. Mallinckrodt 50 / 44 / 56 % overall but
70 / 60 / 70 % on beyond-context facts: the procedural story (MDL 2804, Polster, SpecGx, 2017 DEA settlement,
2020 Chapter 11, the trust) is known, the operational allegations (Exalgo, suspicious-order monitoring,
chargebacks, pill mills, quota) are not (~17 %). Jeb Bush 50 / 44 / 67 % with the *people* category at 0 %
for every model and the outcome at 0 %. Veridian: all three say "unknown" in 95-145 words, no confabulation.

**M2 — is the knowledge actionable?** Under TREC's pseudonym the Enron scandal requests yield 0.4 / 1.1 / 0.4
novel named terms per request and 1 / 2 / 0 discriminative named terms in total, with the models noting
they know only the fictionalised summary. Name the company and the same requests yield 5.9 / 10.3 / 14.7
named terms per request, 81-88 % grounded, and **12 / 24 / 46 discriminative named terms**: for Sol,
Mahonia / Yosemite / Delta for prepay; Raptor I-IV, Talon, Chewco for FAS 140; Duncan, Temple, Odom for
document destruction; Fastow, Skilling, Lay and the analysts' banks for analyst contacts, each 2.7-11.7×
over-represented among responsive documents. Complaint K requests on the same mailbox: 3 / 0 / 1 (the
knowledge is specific to the case, not the corpus). Mallinckrodt 2 / 1 / 4 (Sol: Xartemis XR, Broward
County, Office of Diversion Control). Jeb Bush 16 / 18 / 19 on a 600-document subset (Stipanovich/SBA,
Regier/DCF, Alan Levine/AHCA). Veridian 0 / 2 / 3, all domain institutions (FDA, NJR, AJRR). Generic
keywords discriminate at 20-40 % on every corpus including Veridian; that is vocabulary, not case knowledge.

**M3 — knowing the people barely moves the metadata call.** Subject-only accuracy is already high (Enron J
80-86 %, K 69-80 %, MNK 74-79 %, Jeb 68-75 %) against a lexical baseline of 52-64 %. Adding From/To/Cc
changes it by −1 to +5 points; only Sol on Enron J (+2.5 % [0.4, 5.0]) and Jeb Bush (+2.7 % [0.9, 4.8])
exclude zero. Veridian's subject-only accuracy is 90-94 %, higher than any real corpus: a realism caveat for
the synthetic matter (its subject lines are more diagnostic than real ones), found for free. **Jev on the same
e-mails** (subject → headers, Δ): Veridian 75 → 76 % (+0.5), Jeb Bush 57 → 57 % (+0.6), Enron K 62 → 66 % (+4.2),
Enron J 70 → 70 % (+0.4), MNK 66 → 65 % (−1.3); no paired interval excludes zero — the same flat pair the LLMs
show. Jev's vendor states it is not pre-trained on public text; we treat that as a claim to test. The flat
people effect is consistent with the claim but does not establish it, since the LLMs — which demonstrably know
the people (Part I, M1) — show nearly the same flatness (2 of 18 LLM model × request-set intervals exclude zero:
Sol on Enron J +2.5 and on Jeb Bush +2.7); M3 therefore has little power to detect people-knowledge in any
system. The LLMs' edge is in the subject-only call (10-14 points above Jev on Enron J), i.e. reading of the
subject line, not a people effect. **Jev, the account to carry (after the classifier-native tests, below):** the
classifier-native tests are consistent with Jev not having been trained on these collections, and they show it knows
the cases behind them at effect sizes comparable to the LLMs (code-name swap, real − fictional token: Enron +17.9
[+3.6, +32.1], Jeb Bush +34.8, Mallinckrodt +68.4, Endo +36.8 pp; decoys move the other way); no sign of the documents
or labels (T2–T4); knowing the case did not detectably move its F1 on Enron (+0.0 [−2.6, +2.6]). Jev remains a system
under test and the vendor statement a claim; the tests cannot separate pre-training on public text from synthetic data
distilled from a knowledgeable model.

**The ladder (Luna / Terra / Sol, share of facts the question did not state).** Top group: Bhopal 100/100/92,
Clinton server 93/87/100, Bridgegate 92/92/100, WorldCom 86/93/86, Theranos 93/87/87, Microsoft 87/93/87,
Enron 84/79/90, Dieselgate 82/82/88, FTX 76/82/76. Middle: Insys 79/93/93, HealthSouth 77/77/92, Dalkon
Shield 75/75/92, Texaco v. Pennzoil 69/69/92, Purdue 62/77/54, Bair Hugger 62/69/77, DePuy ASR 46/64/82,
Sony hack 47/67/73, Peregrine 67/33/75, McKesson & Robbins (1938) 62/54/69, Equity Funding (1973) 46/62/62.
No Wikipedia article at all: 3M earplugs 75/100/100, Rochester Drug Co-operative 40/80/90. Study matters:
Jeb Bush 50/44/67, **Mallinckrodt 40/33/47 — the least-known real matter on the ladder for every model**.
Post-cutoff: Meyer 0/0/0 with all three declining (Luna and Sol flag the date as beyond their knowledge; Terra
instead names a specific SEC case, defendant and 2024 filing date that we cannot find and whose particulars
reproduce the sketch — a confabulated identification); Near identified by all three from the sketch (the 2023
collapse is known) with recall of the 2026 complaint 22/0/0 and all declining; Sol states a June 2024
cutoff. Identification: 23 of 24 real matters named by every model from a sketch with the proper nouns
removed (the exception is Sol on TREC's Complaint J). Spearman ρ between log pageviews and recall over the 22
matters with an article: Luna +0.48, Terra +0.47, Sol +0.18.

Three readings. (i) *The floor for a real litigated matter is high*: nothing that was charged, tried or
settled in public comes out blank, including matters with no Wikipedia article — legal matters live in
crawled-but-unread sources (DOJ/SEC releases, dockets, opinions, client alerts), so public popularity
understates exposure. (ii) *Scale flattens the ladder*: fame predicts knowledge for the small and mid models
and barely for the largest, which knows the obscure rungs about as well as the famous ones; at frontier scale
"obscure" is not a defence, only "after the cutoff" is. (iii) *Identification is nearly binary* and precedes
recall. For the study: Enron sits with Bhopal and the Clinton server; Jeb Bush well below the e-mail scandals
in its family; Mallinckrodt below its opioid peers and below a 1938 fraud — the recent MDL-and-bankruptcy
record is the least narrated; Veridian at the bottom with the post-cutoff case, where a floor belongs.

**Combined reading.** The evidence places the unit of contamination for eDiscovery at the matter, not the document. Part I
finds no document-level signal on Enron (an absence of evidence from 60 windows, under probes that do fire on the canon
and on CUAD; the corpus is in The Pile, so presence in training is likely and memorisation evidently tracks repetition
rather than presence); Part II finds the case thoroughly inside the model (M0/M1), actionable as search terms
when the matter is named (M2), dormant under TREC's pseudonym unless the model is asked to decode it, and
worth little at the metadata level (M3). Mallinckrodt carries modest case knowledge concentrated in the
largest model; Jeb Bush's issues are known but its cast is not; Veridian remains the right floor with two
measured caveats (archetype recognised, easy subject lines). Report Enron as a known matter and treat
pseudonymising the complaint as no defence (the nameless ladder sketches identified 26 of 27 real matters; the one
miss is Sol naming Reliant Energy for Complaint J). The full-document ablation then bounded the name-mediated knowledge
effect at within ±3 points of F1 for every system (no interval excluding zero) — on one matter, at this sample size;
it does not rule out smaller effects, other matters, or knowledge that survives renaming, which it demonstrably does
(the renamed documents were still identified as Enron 61–94 % of the time). The decisive effect test needs a post-cutoff corpus.

**Calibration note (2026-10-04).** All write-ups were re-read for overclaiming. The standard: state what was
observed, name the inference it supports, say what would overturn it. In one sentence, the evidence points to
matter-level exposure being common and document-level exposure being rare for internal e-mail, and we could not
detect a consequence of the former for review accuracy. Specific recalibrations: "they have not read the e-mails" →
"no evidence of document-level memorisation" (absence of evidence under a probe that does detect memorisation
elsewhere); "the effect is zero" → a bound with intervals through zero; CUAD "memorised" → "above the e-mail floor,
consistent with memorisation of republished public contracts; the floor is not genre-matched" — a post-cutoff EDGAR
contract sample is the next control to add to the battery; Endo "provably unseen" → "no document-level signal, as
expected for post-cutoff"; the "small models a hundredth above the floor = genre effect" reading is withdrawn (it was
Luna's undetected refusals); M3 "no power" → "little power" (2 of 18 LLM intervals clear zero); the ladder's "every
model, every matter" → "26 of 27" with the miss named, and the footprint–recall correlation reported per model with
its significance (Luna +0.48 p = 0.015, Terra +0.48 p = 0.014, Sol +0.25 not significant, n = 25).

### Method notes from the run

- **Sampling confound caught and fixed.** The first label-recall build balanced relevant/not-relevant across
  the whole corpus, so topics with high prevalence were over-represented among positives; Sol scored 70 % on
  Mallinckrodt by answering "relevant" to every `*_broad` issue and "not_relevant" to every `*_narrow` one,
  with no document knowledge at all. Pairs are now balanced within each topic and the report prints the
  topic-only ceiling (50 %) next to the accuracy. Anyone running a label-leakage probe should check that
  the question text carries no label information.
- **The `novel` run metric is necessary.** The highest-scoring Enron item (60-word exact run) is an e-mail
  consisting of a repeated error message; the model copied the prompt. Runs that contain no 5-gram absent
  from the prompt are not evidence of memorisation.
- **Embedded public text is the remaining blind spot in V.** Government notices, licence banners and jokes
  quoted inside an e-mail are memorised from their public source, not from the corpus. The verbatim probe
  cannot tell these apart; inspecting the top runs per corpus by hand (done above) is the current remedy.
  A classifier for "quoted public text" or a cross-check against a web index would automate it.
- **Name extraction is deterministic now** (ties sorted by name); the first build's ranking depended on
  set-iteration order and changed between processes.
- **Veridian name collisions** happen (Greg Sterling is a real analyst); grading on the target organisation
  handles them.

## Classifier-native tests (Jev)

Run 2026-10-04. Code in `ediscovery_bench/jevprobe/`; CLI `bench jev-probe build | run | report`; data `data/jev_probe/`,
results `results/jev_probe/` (`REPORT.md`, `summary.json`, per-arm predictions). Spend: OpenAI $5.14 (T1 + T2 $3.88: $3.25
predictions in the first run, $0.51 for the T1 v2 re-run of Mallinckrodt and Endo under its own $3 cap, $0.12 Luna edit
generation; $0.18 T3 paraphrases; $1.08 Luna/Terra T4 panel), Jev $0.15. **T1 was corrected the same day (v2, below)** after
a follow-up worker found that the Mallinckrodt and Endo task contexts named the products; v1 is archived under
`results/jev_probe/t1_v1_confounded/` and all T1 numbers in this section are v2.

The generative probes above cannot be posed to Jev (it classifies; it does not complete text), and the ablation (§ above)
tested only one channel — proper names in full documents — and found +0.0 [−2.6, +2.6] with FAS 140 as the loose end. These
five tests use only the classifier's own interface (a relevance call and its probability) and are paired designs with
bootstrap intervals. Jev is a system under test throughout: the GPT-5.6 models are the *positive* comparison (a system known
to carry matter knowledge), Veridian the *synthetic floor*; nothing here is a clean reference. Every result below is stated as
evidence consistent or inconsistent with the vendor's statement that Jev is trained on synthetic data, not as proof.

**T1 — code-name swap** (knowledge). 40 templated documents per matter (Enron, Jeb Bush, Mallinckrodt, Endo), each in two
versions that differ only in one token: a real matter token (Raptor, Schiavo, Exalgo, Opana ER…) vs a fictional one of the same
shape (Tercel, Petrossi, Veltrano, Veltrex ER); the request describes the conduct and names no token. *Signal* pairs: a
case-aware reader calls the real version relevant more often. *Decoy* pairs (Azurix, FCAT, Ofirmev, Lidoderm…): the real token
is something a case-aware reader knows is *not* what was asked, so knowledge lowers the call.

*Correction (v2, token-free contexts).* v1 sent each matter's task-yaml context as written. A prompt audit (every T1 token,
real and fictional, searched with word boundaries in the context and all request fields) found: Enron — none; Jeb Bush — none
(the context names Governor Jeb Bush and Florida, the matter itself, equally in both arms); Mallinckrodt — Exalgo, Roxicodone,
Methadose and the decoys Ofirmev, INOmax, Acthar, all in the context ("branded opioids including…", "non-opioid products (e.g.…)
that are not at issue"); Endo — Opana ER / Opana, Qualitest and the decoys Lidoderm, Voltaren Gel, Aveed, Supprelin, all in
the context. On the two opioid matters a real token could therefore match the *prompt* rather than training knowledge, in both
directions (check C in `results/verify/REPORT.md` showed the same thing: with the original Endo context Jev followed
counterfactual text 57 % of the time, 90 % with a nameless one). v2 replaces the two contexts with the product-nameless versions
written for check C (`data/verify/c_requests.json`; the company is named, the conduct is described generically) and
`Matter.taskset()` now raises if any token appears in a context or request. Enron and Jeb Bush predictions are carried over
(identical prompts); Mallinckrodt and Endo were re-run on all four systems ($0.51).

Real − fictional relevance rate on signal pairs, v2 (paired bootstrap; Jev / Luna / Terra / Sol): Enron +17.9 [+3.6, +32.1] /
+14.3 / +32.1 / +7.1; Jeb Bush +34.8 [+13.0, +56.5] / +43.5 / +34.8 / +21.7; Mallinckrodt +63.2 [+42.1, +84.2] / +36.8 / +68.4
/ +31.6 (v1: +68.4 / +42.1 / +73.7 / +52.6); Endo +10.5 [+0.0, +26.3] / +15.8 / +78.9 / +78.9 (v1: +36.8 / +57.9 / +73.7 /
+68.4). Jev's signal CI excludes zero on 3 of 4 matters (Endo's lower bound sits at zero; McNemar p 0.5); the LLMs span +7.1 to
+78.9 pp and Jev is within their range on 3 of 4 (below it on Endo) — the same count as v1. Decoy pairs: Jev −8 (Enron), −12
(Jeb Bush), −25 (Endo) pp, but **+25 pp on Mallinckrodt** (real 33 % vs fictional 8 %; Ofirmev 60 % vs 0 %) — in v1 the
context had said those products were non-opioids not at issue, so Jev's v1 decoy result there was prompt-following; without
the prompt Jev treats a real pharmaceutical brand in a marketing e-mail as more likely to be the opioid asked about than an
invented one (Terra and Sol still call every decoy irrelevant). The signal − decoy contrast still excludes zero on all four
(Enron +26 [+7, +50]; Jeb Bush +47 [+22, +81]; Mallinckrodt +38 [+6, +68], v1 +93; Endo +36 [+11, +66], v1 +45). Per token
(Jev, v2): Exalgo 100 % vs 0 %, Roxicodone 100 % vs 0 %, Methadose 75 % vs 0 %, Opana 100 % vs 0 % (n = 1), Opana ER 100 % vs
89 %, Schiavo 100 % vs 50 %, Chewco 100 % vs 50 %, LJM2 80 % vs 40 %, Raptor 67 % vs 50 %. **Reading.** With token-free prompts
the classifier's call still depends on recognising real-world tokens — Enron's vehicles, Florida controversies, Mallinckrodt's
opioid brands — at effect sizes within the LLMs' range on three matters; on Endo the real-name effect is small once the prompt
no longer names Opana ER (the generic description "a reformulated extended-release opioid" already makes an invented "…ER"
brand look responsive, 89 %), and on Mallinckrodt part of the effect is recognising a real drug brand rather than knowing which
brands are opioids. The v1 opioid-matter effects were overstated by the prompt. The claim-level reading is unchanged:
*inconsistent with* a reading of the vendor statement under which Jev has no real-world knowledge, *consistent with* either
pre-training on public text or synthetic training data generated by a model that has that knowledge; the test cannot separate
those two, and it does not show benchmark contamination: knowing what Exalgo is, is not having seen the Mallinckrodt collection.

**Bare-token check (FAS 140).** 120 documents of a header plus one sentence containing Raptor / LJM2 / Chewco or Tercel / HLM2 /
Brixco, against the FAS 140 request. The criteria in `tasks/enron_j.yaml` name FAS 140 / FAS 125 and no vehicle (asserted in
code), so the "named" cell adds one sentence naming the vehicles. Four cells, Jev responsive rate (real / fictional): criteria as
written 0 % / 0 % (mean p 0.11 / 0.08); criteria naming the vehicles 78 % / 0 %; with the ablation's "The Company is Enron Corp."
context added: as written 0 % / 0 %, named 83 % / 0 %. **Reading.** A bare vehicle name does not trigger the FAS 140 request as
written; the ablation's −18 F1 on FAS 140 under pseudonymisation is therefore not a name-recognition effect on its own. T1's Enron
rows show the knowledge is used when the token sits in substantive text (Chewco, LJM2), and the "named" column shows Jev knows
which tokens the criteria's added sentence refers to (78–83 % vs 0 %).

**T2 — minimal-edit label flip** (label memorisation). ~100 documents per public-qrels collection (Enron: TREC Legal 2010
learning task; Jeb Bush: TREC 2016 athome4), half relevant, each given a 1–2 sentence Luna edit intended to flip true relevance
(97 and 90 edits applied); Veridian with our own labels as the "old" label is the calibrator (94). *Label-following rate* = calls
on the edited document equal to the old label. Jev 20 % [13, 29] Enron, 30 % [22, 40] Jeb Bush, 46 % [36, 56] Veridian; LLMs
27–31 % Enron, 32–36 % Jeb Bush, 41–50 % Veridian. Jev minus Veridian: Enron −26.2 [−38.8, −13.4], Jeb Bush −15.7 [−29.8, −1.6].
Instrument caveat: Terra confirms the intended flip on only 4/10, 5/10, 7/10 sampled edits, so many "flips" did not fully change
true relevance; that dilutes every system equally within a collection, so the within-collection Jev-vs-LLM comparison stands and
the Veridian contrast (cleaner documents, harder to flip) is the weaker leg. **Reading.** Jev follows the edited text at least as
readily on documents whose labels are public as the LLMs do and more readily than on never-published Veridian labels —
*consistent with* no memorisation of the published judgments; no cell points the other way.

**T3 — paraphrase sensitivity** (document memorisation; Jev only, since it returns a probability). ~100 documents each from
Enron (in The Pile), Endo (post-cutoff) and Veridian (synthetic), original vs Luna paraphrase, every request of the task set.
Mean |Δp| / call-flip rate: Enron 0.006 [0.004, 0.007] / 0.7 %; Endo 0.012 [0.010, 0.014] / 0.9 %; Veridian 0.006 [0.005, 0.008]
/ 0.4 %. Enron vs Veridian Mann–Whitney p = 0.75 (at the heaviest-paraphrase band 0.005 vs 0.008); Endo vs Veridian p < 0.001.
**Reading.** All three are tiny (under 1 call in 100 flips). The corpus that is in public pre-training text is indistinguishable
from the synthetic floor; the only corpus that differs is the one that cannot have been seen, so its larger shift is document
style, not memory. *Consistent with* no document memorisation.

**T4 — published vs unpublished labels** (label contamination). Enron: 144 learning-task documents (qrels gold, balanced per
topic × label) vs 144 length-matched EDRM messages in no TREC Legal qrels (half cue-enriched for the twin's topic), labelled by a
Luna + Terra unanimous panel. Jeb Bush: offline from the study's `results/trec` run — 1,639 qrels-judged (document, topic) pairs
vs 1,639 length-matched unjudged twins on the same topic, reference a 6-LLM panel (majority with ≤ 1 dissenter). Confound stated
first: judged documents are pool-selected by participants' 2010 / 2016 systems; the unjudged side is almost entirely
non-responsive (panel positive rate 6 % Enron, 0.9 % Jeb Bush), so overall judged − unjudged differences are base-rate artefacts
and only the by-reference-label cells are informative. Jev accuracy vs qrels: Enron 74 % [67, 81], Jeb Bush 76 % [74, 78]. Jev
agreement with the LLM panel on the *same* judged documents: Enron 92 %, Jeb Bush 86 % (panel vs qrels: 78 %, 86 %). Judged −
unjudged agreement with the panel on panel-positives: Jeb Bush +10.6 [−11.2, +33.7] (n 1,174 vs 14); Enron +23 pp (n 49 vs 8,
unjudged 62 % [31, 86]); on panel-negatives: Jeb Bush −0.5 [−1.4, +0.1], Enron −4.5. **Reading.** A system that had memorised the
qrels would agree with the qrels more than with an LLM panel on judged documents; Jev does the reverse on both collections,
missing the human assessors' positives where the LLMs miss them. The positive-side judged-vs-unjudged cells lean toward judged
but rest on 14 and 8 unjudged documents and their intervals cover the judged rate; the negative-side cells show no advantage.
*Consistent with* no label memorisation, with pool selection as the binding limit on power. A human-labelled unjudged panel
(~300 Enron documents × 6 requests, two reviewers, ≈ 20 reviewer-hours) would remove the LLM-panel dependence; it was not run.

**Overall.** Jev *uses* real-world matter knowledge (T1 v2 with token-free prompts: signal Δ excluding zero on 3 of 4 matters,
signal − decoy contrast on 4 of 4; bare token once the request names the vehicles) and shows no sign of *remembering* the
benchmark's documents or labels (T2, T3, T4: every cell at or below the LLM / synthetic comparison). Both halves are evidence,
not proof. T1 is compatible with the vendor's statement if the synthetic training data
was generated by a model that knows these matters — which is the natural way to make such data — and T2–T4 bound memorisation
only at these sample sizes and for these collections. For the eval: the contamination risk to carry forward for Jev is the same
matter-knowledge channel the ablation measured on full documents (+0.0 [−2.6, +2.6] F1), not document or label leakage; the
templated-document result says the channel is live even if its measured consequence on real documents is small.

Method notes: Jeb Bush full text is not on disk (only the 600-document `local_subset`), so T2 Jeb Bush used that subset and T4
Jeb Bush was computed from existing predictions; two T1 tokens were replaced because their meaning is transparent to any reader
("30 mg oxycodone" → Roxicodone; "crush-resistant" → INTAC); the decoy design (real tokens a case-aware reader knows are *not*
the requested kind) is what lets T1 separate knowledge from a generic "real-looking name" effect — and the v2 Mallinckrodt
decoy result shows that effect is real for Jev, so the contrast, not the raw signal Δ, is the number to quote; a code-name swap's
prompt must be audited for the tokens it swaps (the task-yaml contexts that are right for the main study are wrong for this
test, because they name the products), and the build should assert it, as `Matter.taskset()` now does; `read_jsonl` must iterate
file lines, not `str.splitlines()`, which splits inside JSON strings on U+2028.

## Generalisation checks (run 2026-10-04; `bench verify`, `ediscovery_bench/verify/`, `results/verify/`)

Four checks on the study's central claim — *on the matters tested, knowing the case did not detectably change review
accuracy* — chosen so that each could have undermined it. New OpenAI spend $10.95 of a $15 cap (A $0.30, C $1.67, D $8.98,
paid/flex; list ≈ $24.6 for C + D); Jev $0.12. Full tables and figures in `results/verify/REPORT.md`; numbers in `summary.json`.

**A. Knowledge-dependence error analysis (Enron J).** Luna tagged every scored Enron J document as *knowledge-dependent*
(relevance can only be seen with outside Enron knowledge) or *self-contained*; 6.9 % [5.4, 8.9] are knowledge-dependent on the
six knowledge requests (FAS 140 25 %, everything else ≤ 8 %). If case knowledge had been helping, the systems should be *more*
accurate on those documents when named and lose more on them when renamed. Neither holds: named accuracy on knowledge-dependent
documents is 61 / 61 / 64 / 66 % (Luna / Terra / Sol / Jev) against 83 / 81 / 83 / 78 % on self-contained ones, and Jev — the
system with the least measurable case knowledge — is the most accurate on them. Renaming moves F1 on the knowledge-dependent
subset by +4.1 [−6.7, +14.9] (Luna), +4.0 [−17.6, +26.2] (Terra), **+17.3 [+4.8, +32.1]** (Sol, i.e. renaming *helped*) and
−15.7 [−33.3, −0.7] (Jev, five right→wrong vs two wrong→right); only Jev's drop concentrates on these documents (KD − SC
−14.5 [−31.7, +0.5]) and Jev is not better on them when named, so at most half the signature, on 59 documents. The LLMs' Enron J
edge over Jev sits on the *self-contained* documents. *Reading:* **strengthens** the claim — what the matter-knowledge channel
could affect is a small slice of the corpus, and on that slice no system behaves as if knowledge were helping.

**B. Ranking stability (existing results; no calls).** Rank order of the four systems is not stable across corpora (Kendall W over
F1 ranks 0.14 across Enron J / Enron K / Mallinckrodt / Veridian / Endo; 0.10 without Endo; four objects give W almost no power).
Sol > Luna > Terra > Jev on Enron J; Terra > Jev > Sol > Luna on Mallinckrodt; Jev > Terra > Sol > Luna on Veridian; on Endo the
three LLMs that *are* the gold panel lead. Within each LLM, F1 does not trend with its own case-knowledge score (Spearman ρ 0.0 /
−0.2 / −0.2 over four corpora). The one pattern contamination would predict is present: the mean-LLM − Jev F1 gap falls with case
knowledge, Enron J (case 84) +6.3 pp → Mallinckrodt (53) −2.0 → Veridian (0) −4.1 (roster table, with Jeb Bush in place of Enron:
−0.7 → −2.8 → −3.6). But the same ordering is what corpus type predicts — real human-judged email with 49 % prevalence versus
LLM-panel and synthetic-planner gold at 10 % — and Checks A and D test the mechanism directly on both ends of that gradient and
find none. *Reading:* **ambiguous, leaning against the claim** on its own; it is the weakest of the four designs (n = 4 systems,
gold of three kinds) and is reported because it is the one that did not come out clean.

**C. Counterfactual conflict documents.** 30 short documents per matter (Enron, Jeb Bush, Mallinckrodt, Endo; templated like
T1), each in a FACTUAL version and a COUNTERFACTUAL version whose text contradicts a well-known fact and so flips relevance to a
nameless request (Roxicodone as "our over-the-counter antacid"; the Schiavo file as a road-renaming request; a "Covidien
Imaging" subsidiary that holds a DEA controlled-substance registration). The correct call follows the text. The Mallinckrodt and
Endo task contexts were replaced by product-nameless versions for this check, because the classifier-native contexts name the
products and a conflict would otherwise be with the prompt, not with pre-training (with the original contexts Jev's Endo
text-following was 57 %; with the nameless one, 90 %). Every system reads the factual versions at ≥ 97 %. On the counterfactual
versions the call follows world knowledge rather than the text on 17 % (Luna), 14 % (Terra), 12 % (Sol) and 8 % (Jev) of pairs
pooled over the four real matters — almost entirely in one direction (a well-known responsive token keeps a document responsive
when the text says it is about something else: 27 / 24 / 18 / 15 %; the reverse 4 / 2 / 4 / 0 %), concentrated on Jeb Bush,
Mallinckrodt and Endo, and near zero on Enron. The Veridian analogue (facts asserted in the task context and contradicted in the
document) gives 17 / 10 / 3 / 10 %, and no system's real-matter rate differs from its Veridian rate beyond noise (Sol −8.3 pp
[−16.7, +0.8] is the closest); part of the Veridian baseline is request-scope ambiguity on surgeon-payment denials, so it is a
lenient baseline. *Reading:* **mixed; neutral for the claim as stated.** The systems demonstrably let prior facts outweigh the
page on engineered conflicts, Jev least and Luna most, so a strong form of the claim ("knowledge plays no role in the call") is
false; but they do so no more for pre-trained facts than for in-context ones, and Check A says such conflicts are rare on real
documents (~7 % even knowledge-*dependent*), which is why the ablation measures no accuracy effect.

**D. Knowledge injection on Veridian.** A 1,431-token fictional case brief (parties, products, the people, deals and code names,
timeline, outcome — `data/ablation/veridian_brief.md`, bible-consistent, in the style of the Mallinckrodt brief) was appended to
the Veridian context exactly as the Mallinckrodt brief arm was, and the multi arm re-run for all four systems on a stratified
491-document half of the ablation set (every request keeps its positive share; the full arm at 4.5 M input tokens per model would
have exceeded the cap). Paired with the existing named run on the same documents: ΔF1 Luna −0.3 [−1.7, +1.1], Terra −0.6
[−2.1, +0.8], Sol −1.0 [−2.6, +0.5], Jev +0.5 [−1.1, +2.2]; the LLMs trade a little precision for a little recall, Jev's recall
rises +3.5 [+1.5, +5.6] against −1.9 precision; 1.2–2.0 % of labels change, McNemar p ≥ 0.16 everywhere; gray-excluded deltas
0.0 / −1.2 / −0.6 / −0.0. Same picture as the Mallinckrodt brief arm (−1.0 / −0.7 / +0.6 / +1.3). *Reading:* **strengthens** —
handing the systems the one kind of knowledge they cannot have does not move accuracy on the one matter where that is testable.

**Overall.** The two checks that test the mechanism directly (A: where knowledge could matter, does it? D: when knowledge is
supplied, does it?) come out for the claim; C shows the channel exists but is small and no larger for pre-trained than for
in-context facts; B is the one check whose surface pattern runs the other way and it cannot separate case knowledge from corpus
type. The strongest signal is D (narrow intervals, paired, same mechanism as the ablation); the strongest *caution* is B.
Carry-forward wording: *on the matters tested, knowing the case did not detectably change review accuracy, including when the
knowledge was supplied in the prompt; the systems can be made to override a document with a well-known fact, but such conflicts
are rare in real collections and the effect did not reach accuracy.*

Method notes: Check A's tagger is a system under test (Luna); tags describe documents, not calls, and are shared across systems,
so a tagger bias shifts the knowledge-dependent share rather than any system's contrast. `matplotlib` was installed into `.venv`
for the figures (not added to `pyproject.toml`). Jev and the three GPT-5.6 models are all systems under test throughout.
