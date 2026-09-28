# Review: "Jev vs the LLMs: Benchmarking Results on TREC 2016" (v2 WIP, `Jev Article For Review - v2 WIP_For Cursor.docx`)

Paragraph numbers (P1–P52) are the docx paragraph index (P1 is blank, P2 is the header image). Numbers checked against `results/findings.json` (TREC 2016, all-issues arm, document level), `results/determinism.json`, `Article/precision_projection.md`, `Article/charts/stability/README.md`. No hyperlinks exist anywhere in the document; 11 embedded images, listed in §5.

Images and where they sit: P2 image1.png (untitled recall/precision map incl. Facets, header); P7 image2.gif (TypeSafe "typesafe-race" demo, 1 MB); P17 image3.png (primitives table, alt text "Generated image 1"); P22 image4.png ("Jev v LLMs - Recall and Precision (TREC 2016)"); P24 image5.png (composed configurations map, no title); P28 image6.png (per-issue cutoff table, no title, no model name); P30 image7.png ("Pooled impact · TREC 2016 · Jev · Choice"); P34 image8.png ("Pairwise agreement (LLMs at default temperature)"); P36 image9.png (same title, but it is the t=0 chart); P40 image10.png ("Review time per document"); P44 image11.png ("Review cost per 1k documents"). No image other than image3 has alt text.

---

## 1. Must fix

**M1. P4** — *"Today's frontier LLMs have more than 2 trillion parameters, and can write code..."*
No lab publishes parameter counts; "more than 2 trillion" is unsourced. Corrected: "Today's frontier LLMs are widely reported to have parameter counts in the trillions, and can write code, reason across long contexts, pass bar exams and produce fluent prose." (Or drop the number.)

**M2. P6–P7** — *"Within hours of its release, GIFs of Jev pwning frontier LLMs flooded the internet."*
The embedded GIF (image2.gif) is TypeSafe's own demo (`uv run typesafe-race ask typesafe`, watermarked "Made with Gifox"), not a third-party post, and "flooded the internet" is unsupported. Corrected: "Within days, TypeSafe and early users were posting side-by-side races like the one below, TypeSafe's own demo." Also the blog's caveat about that demo ("The relatively shorter input paints our model in an advantageous light") should follow it.

**M3. P8** — *"In one post, Jev answered 14 yes/no questions about 100,000 social media posts in 20.4 seconds for $.67. Another claimed Jev reached 89% accuracy reviewing 100k rows from the AG News dataset in 40 seconds. On the same set, GPT-5.6 Terra reached 88% accuracy in about 32 minutes, with a retail cost of $37.58 versus $0.50 for Jev."*
No source or link for any of these figures, and they cannot be checked from the repo. Either link the posts by author and date or cut the paragraph. If kept, add: "Those throughput numbers assume rate limits we did not have: at the 1,200 requests per minute we were granted, 100,000 emails takes about 85 minutes, not 20 seconds." (Key fact: ~150–200 ms/email, ~85 min at 1,200 req/min.)

**M4. P10** — *"As more credible evidence, a an experiment by researchers at Carnegie Mellon University found that, "comparing jev-as-a-judge with sixteen generative and reward-model judges..."*
Uncited and half-quoted. It is a preprint, and the same abstract continues with the unfavorable half. Corrected: "A preprint from Carnegie Mellon (Yubo Li, Yidi Miao, Ramayya Krishnan and Rema Padman, "JEV-as-a-Judge: Accept When Confident, Escalate When Unsure," arXiv:2609.26550, September 22, 2026) reports that, "comparing jev-as-a-judge with sixteen generative and reward-model judges, with blinded human adjudication, we find it within three percentage points of a state-of-the-art LLM judge." The same abstract continues: "Larger gaps arise when judgments require checking a derivation or resisting an elaborately written wrong answer."" Drop "As more credible evidence".

**M5. P13** — *"measured the results on four dimensions that matter in review: recall, precision, speed, and stability."*
Cost has its own section (P42–P46) and is missing from the list; "that matter" is also on your banned list. Corrected: "and measured recall, precision, speed, cost and run-to-run stability."

**M6. P14** — *"eleven scored topics ranging from .6-5.8% in richness, with an overall population richness was 36.3%."*
36.3% is the richness of the 3,016-email *evaluation sample*, not the population; the 286,326-email collection is 9.19% (per-topic 0.006%–4.0%). The sentence is also ungrammatical. Corrected: "We had each model review each email against eleven scored topics. In the evaluation sample, per-topic richness ran from 0.6% to 5.8% and 36.3% of emails were relevant to at least one topic; in the full 286,326-email collection the any-topic figure is 9.2% and most topics are under 1%."

**M7. P14 / P21 (missing caveat)** — Precision (79.6%, "79% precision", "above 75% precision", "82%") is reported with no statement that it is precision on an enriched sample. From `precision_projection.md`: Jev Noul 79.6% on the sample projects to ~50% at collection richness, and the real full-collection run came in at 51.4%; every model loses 25–40 points. Recall transfers; precision does not. Add after the sample description in P14: "Because the sample is enriched with positives, the precision figures below are precision on this sample and overstate what a reviewer would see on the collection (Jev Noul's 79.6% on the sample is 51.4% on a run over the whole collection); recall and the comparison between models carry over." (This was in the previous draft and has dropped out.)

**M8. P16** — *"Whereas LLMs intake any type of freeform or structured text, Jev limits inputs to three types of "primitives": a noul, choice or score."*
Wrong description of the product: Jev takes the same free-text document (state) as the LLMs; the primitives constrain the *question and answer type*, not the input. Names are also lowercased. Corrected: "Whereas an LLM takes a freeform prompt and writes back text, Jev takes the document plus a typed question in one of three forms, which TypeSafe calls primitives: Noul (yes/no), Choice (pick from fixed labels) or Score (a position on a scale). The answer is always a probability over the answers you offered, never text."

**M9. P21** — *"all three runs exceeded 75% recall, while outperforming several LLMs by more than 10% in precision."*
Jev Noul/Choice 79.6% beats Luna (67.5) by 12.1 and Flash-Lite (68.6) by 11.0 points; Haiku is 9.2, Terra 8.4, Flash 6.6, Sonnet 1.8. Two LLMs, not "several", and points, not percent. Corrected: "all three primitives exceeded 75% recall, and on precision the Jev primitives were 10 or more points ahead of two of the LLMs (Luna and Flash-Lite) and within two points of Sonnet 5."

**M10. P23** — *"One, which we call "facets", nudged recall to 88.9% while remaining above 75% precision"*
Facets precision is 75.0% (95% interval 72.6–77.3), not above 75%; and +10.4 points over Noul is not a nudge. Corrected: "One, which we call Facets, lifted recall to 88.9% at 75.0% precision, within a few points of Sonnet 5 (89.7% / 77.8%); it costs more ($25.5 against $15.6 per 100,000 emails) because there are more questions per email."

**M11. P27–P29** — *"we adjusted issue-level rank cutoffs top optimize for F1."* / *"In doing so, the overall recall increased by 9.4% while precision improved slightly."*
Three problems. (a) The chart (image7) is Jev · Choice, 77.4% → 86.8% recall, 79.6% → 79.9% precision, F1 78.5 → 83.2; the text never says which primitive, and "9.4%" is 9.4 points. (b) The cutoffs were tuned on the same 3,016 emails they are scored on; image6 shows cutoffs of 0.030 (2000 recount) and 0.140 (Rilya Wilson), which are fit to this sample. The honest number is the held-out one: tuning on half the sample lifts F1 on the other half by about 2.4 points. (c) Chart baseline reads 77.4% recall; the published Choice figure is 77.3%. Corrected: "For example, tuning a cutoff per issue for Jev · Choice to maximise F1 on this sample raised pooled recall by 9.4 points (77.3% to 86.8%) with precision unchanged (79.6% to 79.9%). That is an in-sample number: the cutoffs were chosen on the same emails they are scored on. When we tuned on half the sample and scored the other half, the F1 gain was about 2.4 points, which is the figure to expect in practice."

**M12. P33** — *"To measure each model's stability, we ran 300 emails through each model five times and computed the pairwise agreement between runs. While all models exhibited less than 3% disagreement, Jev was the most stable, with a .3-.4% flip rate"*
(a) The corpus is not TREC: these are 300 Mallinckrodt opioid-litigation emails × 8 issues = 2,400 decisions per run, and the article never says so; the title says "on TREC 2016". (b) "Flip rate" is a different metric in `determinism.json`: the share of decisions where any run differed is 0.54% (Noul), 0.63% (Score), 0.75% (Choice). The 0.27/0.32/0.38% figures on the chart are *pairwise disagreement*. Corrected: "To measure stability we used a second corpus: 300 emails from the Mallinckrodt opioid litigation, each reviewed against eight issues (2,400 decisions), sent through every model five times with identical inputs, LLMs at their default sampling settings. We report pairwise disagreement: the chance that two runs picked at random give a different label on a decision. Every model was under 3%; the three Jev primitives were lowest at 0.27%–0.38%."

**M13. P35** — *"Every LLM except Gemini 3.5 Flash-Lite improved, with Haiku 4.5 rising from 98.2% to 99.6%"*
Claude Sonnet 5 has no temperature-0 run (the API rejects the parameter; the chart shows it greyed out), so "every LLM" is wrong. Corrected: "Of the five LLMs that accept a temperature setting (Sonnet 5's API rejects it), every one except Gemini 3.5 Flash-Lite improved: Haiku 4.5 rose from 98.2% to 99.6% agreement, level with Jev Choice; Flash 99.1% to 99.3%; Terra 98.5% to 99.1%; Luna 97.9% to 98.3%; Flash-Lite slipped from 98.0% to 97.8%. Jev Noul and Jev Score remained highest at 99.7%."

**M14. P36 (image9)** — chart title reads *"Pairwise agreement (LLMs at default temperature)"* but it is the temperature-0 chart (Haiku 99.6%, Sonnet 5 "API rejects temperature"). Re-export with the title "Pairwise agreement (LLMs at temperature 0)".

**M15. P37** — *"determinism is what Jev was designed for, a classifier that outputs a probability, rather than a next-token generator"*
Jev is not deterministic: 0.27% pairwise disagreement, and in `determinism.json` its probabilities are identical across all five runs on only 49% of decisions (Noul), 29% (Score), 73% (Choice). "Designed for" is also an unsourced claim about TypeSafe's intent. Corrected: "This is not a surprise: Jev has no sampling step to turn off, and its flips were confined to decisions its own probability already put near 0.5. It is not fully deterministic; its probabilities move by a hundredth or two between runs."

**M16. P39** — *"Unlike LLMs, decision models have no transformer and don't predict "next tokens" one at a time."*
TypeSafe has not published Jev's architecture; "no transformer" is unsupported. Corrected: "Unlike an LLM, Jev does not write its answer out one token at a time; it returns a probability over the answers offered in a single pass."

**M17. P43** — *"Below is the average actual cost per thousand documents to run the study."*
The chart is list price, not what was paid. `findings.json` paid cost per 1,000 was lower for Sonnet 5 ($6.32 vs $16.74 list), Terra ($4.98 vs $12.38) and Luna ($0.50 vs $1.24) because of flex/discount tiers. Corrected: "Below is the list-price cost per 1,000 documents with all eleven topics in one request; no batch, flex or caching discounts."

**M18. P51 (and P5, P39)** — *"it was "cheaper" and "faster" by one to two orders of magnitude"*
Speed is one order: Jev Noul 157 ms vs 1,437–3,656 ms = 9–23×. Cost is one to two: $15.6 vs $124–$1,674 per 100k = 8–107×. Corrected: "it was 9 to 23 times faster and 8 to 107 times cheaper, and more consistent between runs." The vendor quote in P5 ("two orders of magnitude faster") is never checked; add to P39: "TypeSafe's launch post claims two orders of magnitude on speed; over the public APIs with all eleven topics in one request we measured one: 9 to 23 times."

---

## 2. Should fix

**S1. P3 title** — "Benchmarking Results on TREC 2016" but the stability section is Mallinckrodt. Either "Benchmarking Results for Relevance Review" or say in P33 that stability used a second corpus (M12).

**S2. P4** — *"@TypeSafe AI's position is that ... using an LLM is like crushing an ant with a sledgehammer."* Your paraphrase reads as their words. "TypeSafe AI's position, roughly, is that..." Also "they released" has no plural antecedent (the subject is a possessive); "TypeSafe released Jev 1.13".

**S3. P5** — *"-TypeSafe AI"*: attribute fully, "— TypeSafe AI, launch post, September 15, 2026". "System One tasks" in the quote is never defined; add one clause before the quote: "TypeSafe calls Jev a System One model, a decision model that returns a typed answer with a probability instead of text."

**S4. P6** — *"pwning"*, *"flooded the internet"*: hype register. See M2.

**S5. P7 GIF** — LinkedIn articles do not reliably animate GIFs; the first frame is two empty terminals under a "String Tax" banner, so a static fallback shows nothing. Use a still of the finished race or a link to TypeSafe's demo, and confirm permission to republish their asset.

**S6. P11** — *"can it make complex legal determinations at scale?"* Relevance review against a topic description is not a complex legal determination; "can it make relevance calls at scale?"

**S7. P13** — *"we ran Jev and six frontier LLMs ... We compared Jev against six commercially available language models"* says the same thing twice; Flash-Lite is not "frontier". Model naming is inconsistent: "Haiku 4.5, Sonnet 5" without "Claude" while GPT and Gemini carry vendor names; the charts drop vendors entirely. Pick one convention and use it in text and charts. "a panel of NIST assessors" → "NIST assessors".

**S8. P14** — *"1,016 topic positives"* will confuse anyone who looks at image7 ("positives 1,095"): the recall denominator is 1,095 because 79 of the 1,000 random emails are also NIST-relevant. Say: "100 NIST-relevant emails per topic (16 for Non-resident aliens), 1,000 emails NIST judged not relevant, and 1,000 drawn at random; 1,095 emails in the sample are relevant to at least one topic." Also missing: gold = NIST relevance 1 or 2, unjudged = not relevant; the twelfth topic (Eminent domain) dropped.

**S9. P15** — *"froze the prompts/inputs"*: slash. Missing disclosure that the one refinement pass read shared misses with Jev and Gemini 3.5 Flash-Lite, so if the criteria favor anyone they favor those two (was in the prior draft).

**S10. P16–P17** — *"LLMs intake"*: "intake" is not a verb here. image3 is a generated illustration (tractor example, 1–5 Score) and not our TREC prompts; caption it as illustrative. Alt text is "Generated image 1".

**S11. P18 vs P23** — *"three additional passes to compare our own internally developed strategies"* / *"The three "creative" configurations"* / *"relevance gating"*: three names for one thing, and the chart (image5) labels them Facets, Relevance Gate, Three-Phrasing Ensemble. Use "composed configurations" and the chart's names. The Three-Phrasing Ensemble is on the chart and never in the text (80.7% recall, 79.1% precision, changed little); one clause.

**S12. P21** — *"passing the industry's "rule of thumb" recall floor of 70-80%"*: the rule of thumb is never introduced in this draft (the TAR section was cut). One clause: "the 70–80% recall range practitioners commonly treat as a floor when validating TAR." *"Jev – Score"* (en dash) vs chart "Jev · Score" vs P35 "Jev Score": one form. The text never says what the whiskers are; "Whiskers are 95% Wilson intervals; a document counts as relevant if any of the eleven topics is positive, cutoff 0.5."

**S13. P22 image4 / P2 image1 / P24 image5** — image4 title "Jev v LLMs" vs article "Jev vs". image1 (header) is image4 plus Facets with the x-axis label cropped ("Recall" cut off), no title, and duplicates P22; crop properly or replace with the speed or cost chart. image5 has no title.

**S14. P23** — *"there are a lot of creative for how to use them"*: missing noun. *"the highest precision of the hot"* → "of the lot". *"barely squeaking above 70% recall"* → "at 70.3% recall".

**S15. P26–P27** — heading *"Issue-Level Rank Cutoffs"* and "rank cutoff" ×3: it is a probability cutoff (threshold), not a rank. *"gets a {0-1} score such as ".78""*: "a probability between 0 and 1, such as 0.78".

**S16. P28 image6** — untitled, no model named, shows in-sample cutoffs incl. 0.030 and 0.140 (see M11). Caption: "Jev · Choice, per-issue cutoffs maximising F1 on the evaluation sample."

**S17. P31** — *"optimizing for precision while maintaining compliance (if 70% is the recall floor)"*: there is no compliance standard for recall; "while still meeting a 70% recall target". *"Or make proportionality decisions on a micro-scale, adjusting..."* is a fragment; "Or, issue by issue, trade production volume against how much each topic matters to the case."

**S18. P33** — *"Jev was the most stable, with a .3-.4% flip rate, meaning Jev was the most consistent model between runs"*: says the same thing twice. See M12 for the rewrite.

**S19. P34 / P36 charts** — whiskers unexplained (they are 95% bootstrap intervals over the 2,400 decisions). One clause in the text or caption.

**S20. P39–P41** — *"If you've been following the chatter online, this part shouldn't be surprising. Jev is fast. Really fast."* and *"What else can I say. Jev is fast."* are hype and shift to first person singular. Replace P41 with the measurement caveat that dropped out of the last draft: "The Jev, Claude and GPT figures come from a dedicated sample of 200 emails sent one request at a time; the Gemini figures come from the benchmark run with eight requests in flight; Luna was measured on the standard tier and Terra on flex; everything went over the public APIs from one location. Read the ratios, not the milliseconds." Chart image10 title should say "Median round-trip time per email, 11 topics in one request".

**S21. P43** — *"Like speed, Jev has"* → "As with speed". *"Jev is cheap because, unlike LLMs, it's not an auto-regressive next-token predictor"*: price is a vendor decision, and the architecture claim is unsourced (M16); "Jev is cheap because TypeSafe bills only input tokens, at $0.042 per million." Make the per-email figure readable: "about 1,477 input tokens, or $0.000062 per email, about $6.20 per 100,000 emails." "designed specifically for" appears in P4, P39 and P48; once is enough.

**S22. P46** — *"Again, no contest. Jev is incredibly cheap compared to the frontier LLMs."* Cut, or "The gap is 8 to 107 times at list price."

**S23. P48** — *"or create coloring pages for your kids"*: joke sits oddly next to the tone rules; your call. *"Jev does not respond to user queries with written answers"* is the useful sentence; lead with it.

**S24. P49** — *"working together with LLMs to create a rich user experience"*: marketing phrase. Limitations that a careful reader will raise and the section lacks: enriched sample (M7); one corpus and one gold standard for accuracy; criteria refined with Jev and Flash-Lite (S9); short English emails, nothing over 12,000 characters; LLMs run with reasoning off/minimal and structured output; per-topic spread (Jev Noul recall 36% on Rilya Wilson and 43% on the 2000 recount vs 96–99% on Bottled water and Movie Gallery); early-access pricing and rate limits may change.

**S25. P51** — *"a model this close on accuracy and this far ahead on everything else will be hard to ignore"*: persuasive close, against your rule. End at "what the review is for." The scare quotes on "better", "cheaper", "faster", "good enough" read as sarcasm; drop them or keep only "good enough".

**S26. P52** — *"@Typesafe"* (casing: TypeSafe AI) and *"@Dae"*: full name. *"and additional favor!"*: exclamation, and "favor" is unexplained; "and for raising our rate limit tenfold."

**S27. Whole document** — no links: add the results site (decider.tarcalc.com), the TypeSafe launch post, the CMU preprint, and TREC 2016 Total Recall track. Every number in the article is checkable there; say so once.

**S28. If the training-data sentence comes back** — use the TechCrunch source (Tim Fernholz, Sep 18, 2026) and the founder's full name at first mention, Diogo Almeida: "trained exclusively on synthetic data" via "reinforcement learning from calibrated decisions". Nothing first-party says it.

**S29. If the Schulte sentence comes back** — Schulte v. LinkedIn Corp., No. 22-cv-00237-HSG (LB) (N.D. Cal. June 30, 2026), a non-precedential magistrate order treating Relativity aiR as TAR; not "courts have held".

---

## 3. Minor

- P4: "@TypeSafe AI's position" and P52 "@Typesafe": one spelling, TypeSafe AI. "Jev 1.13" is fine; the resolved model id is `jev-1.13.0`, worth one mention.
- P8: "$.67", "$.50" → "$0.67", "$0.50"; "100k rows" vs "100,000" in the same paragraph; "retail cost" → "list price" (matches P43).
- P10: "a an experiment"; "found that, "comparing" (no comma before an integrated quote).
- P8 "AG News dataset" vs P13 "TREC 2016 data set": one spelling.
- P14: ".6-5.8%" → "0.6–5.8%" (leading zero, en dash); same in P27 ".5", ".78" and P33 ".3-.4%".
- P16: "noul, choice or score" → "Noul, Choice or Score"; P43 "noul" → "Noul"; P23 "facets" → "Facets" (chart casing).
- P21: "70-80%" → "70–80%"; "Jev – Score" → "Jev · Score".
- P23: ""relevance gating"" → "Relevance Gate" (chart name); "of the hot" → "of the lot".
- P27: "top optimize" → "to optimize"; "{0-1}" braces.
- P29: "9.4%" → "9.4 points".
- P39: trailing spaces; ""next tokens"" quotes unnecessary.
- P41: "What else can I say." needs a question mark if kept.
- P43: "$.042" → "$0.042"; "$.000062" → "$0.000062"; "Relvant" → "Relevant"; "e.g. Relvant" → "e.g., Relevant".
- P45: empty paragraph.
- P48: "As impressive at these results are" → "as"; serial comma is used in P13 ("speed, and stability") and dropped in P48 ("summarize a deposition or create") and P51; pick one.
- P49: "Even within in the realm" → "within the realm"; ""labels on emails"," → comma inside the quotation marks (US style), same in P51.
- Headings: "Experimental setup" (sentence case) vs "Limitations and Unknowns", "Issue-Level Rank Cutoffs" (title case) vs "Recall and precision"; the sub-headings P20/P26/P32/P38/P42 are bold body text rather than a heading level.
- Alt text: none on 10 of 11 images; image3 says "Generated image 1". LinkedIn supports alt text; one sentence each with the headline number.
- Citation format: when the CMU preprint is cited (M4), use the arXiv id; when TypeSafe is quoted (P5), the post title and date.

---

## 4. Structure

The order (hook → vendor quote → GIF and posts → CMU → setup → recall/precision → cutoffs → stability → speed → cost → limitations → conclusion) works, and the results are reached by paragraph 21, which is a real improvement on the last draft. The finding itself is still not stated up front: nothing before P21 tells the reader that Jev landed at 78–83% recall and 79–80% precision, mid-pack on F1, so the first 500 words are entirely other people's claims. The setup has lost the pieces that made the numbers defensible in the previous version: enriched-sample caveat, the calibration-pass disclosure, the latency measurement conditions, the Mallinckrodt introduction and the vendor-claim check; each is one or two sentences and belongs where the number appears. "Designed specifically for classification" is said three times (P4, P39, P48) and the speed and cost sections each carry a second one-line paragraph (P41, P46) that adds nothing. The cutoffs section is the most novel material and the least qualified; it needs the in-sample/held-out distinction before it can carry the weight the two charts give it. Limitations should absorb the missing caveats rather than restate what Jev cannot write.

---

## 5. Paragraph index

| P | First 8 words | Issues |
|---|---|---|
| 2 | [header image: recall/precision map, cropped] | 1 |
| 3 | Jev vs the LLMs: Benchmarking Results on TREC | 1 |
| 4 | How big does a model need to be | 4 |
| 5 | Jev achieves similar levels of intelligence on System | 3 |
| 6 | Within hours of its release, GIFs of Jev | 2 |
| 7 | [image2.gif: TypeSafe demo race] | 2 |
| 8 | In one post, Jev answered 14 yes/no questions | 4 |
| 10 | As more credible evidence, a an experiment by | 4 |
| 11 | But you've heard "better, faster and cheaper" before, | 1 |
| 13 | For our comparison, we ran Jev and six | 5 |
| 14 | We had each model review each document for | 5 |
| 15 | For each topic, we wrote the criteria once | 2 |
| 16 | Whereas LLMs intake any type of freeform or | 3 |
| 17 | [image3.png: primitives table] | 2 |
| 18 | We ran a separate review pass for each | 1 |
| 21 | Recall and precision were computed against TREC's NIST | 6 |
| 22 | [image4.png: recall/precision map] | 1 |
| 23 | While we're limited to just three primitives, there | 7 |
| 24 | [image5.png: composed configurations map] | 1 |
| 26 | Issue-Level Rank Cutoffs | 2 |
| 27 | For all primitive types, Jev outputs a probability | 4 |
| 28 | [image6.png: per-issue cutoffs] | 2 |
| 29 | In doing so, the overall recall increased by | 3 |
| 30 | [image7.png: pooled impact, Jev · Choice] | 1 |
| 31 | Alternatively, we could set a recall target of | 2 |
| 33 | Like humans, non-deterministic models can produce different outputs | 5 |
| 34 | [image8.png: pairwise agreement, default] | 1 |
| 35 | We then re-ran the LLM panel at temperature | 2 |
| 36 | [image9.png: pairwise agreement, t=0, mis-titled] | 2 |
| 37 | This isn't necessarily a surprise, as determinism is | 2 |
| 39 | If you've been following the chatter online, this | 5 |
| 40 | [image10.png: review time per document] | 1 |
| 41 | What else can I say. Jev is fast. | 2 |
| 43 | Like speed, Jev has a significant advantage on | 8 |
| 44 | [image11.png: cost per 1k documents] | 1 |
| 45 | [empty] | 1 |
| 46 | Again, no contest. Jev is incredibly cheap compared | 1 |
| 48 | As impressive at these results are, it's worth | 3 |
| 49 | Even within in the realm of classification, there | 4 |
| 51 | For relevance review, Jev was not "better" than | 4 |
| 52 | Thanks to @Typesafe for granting us early access | 3 |
| all | [no hyperlinks; alt text missing on 10 images; heading casing] | 4 |
