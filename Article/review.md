# Review of "Jev vs the LLMs: Benchmarking Results for Document Review"

Files: `draft_extracted.md` (the draft, paragraph-numbered as `P<n>`), `background_notes.md` (what TypeSafe claims and their terminology), `Jev Article For Review - edited.docx` (only the unambiguous fixes applied), `changes.md` (every edit, before → after). Numbers below are from `results/findings.json` (TREC 2016, all-issues arm, document level) unless stated.

---

## 1. Questions for the author

Each question is tied to a passage or callout. Where I propose text, it is a proposal, not something I put in the .docx.

**Q1. P2, the opener.** Callout: *"(some sentence like 'How many PhDs do you need to change a lightbulb? How many H100 cluster do you need to play sim city? How big of an LLM do you need to label emails?')"*. Three options, pick one or none:
- "How big a model do you need to tell whether an email is about bottled water?"
- "It takes a data center to write a sonnet. Does it take one to label an email?"
- Keep yours, trimmed to two questions: "How many H100s does it take to play SimCity? How big an LLM do you need to label an email?" (drop the PhD line; the joke is the escalation from GPU to email, and three questions blunts it).

Same paragraph: *"Today's frontier models have more than 2 trillion parameters, and can (filling in the blank with capabilities)."* No frontier lab publishes parameter counts; "more than 2 trillion" is a rumour, not a fact. Suggest "Today's frontier models have parameter counts in the trillions, and can pass the bar exam, write working software and hold a conversation in fifty languages." Do you want the number at all?

**Q2. P2, *"Last week, they released Jev."*** The launch post is dated **September 15, 2026**. "Last week" is only true if you publish between Sep 21 and 27. Use the date: "On September 15, TypeSafe AI released Jev, ...". (If a "three days old" line was planned anywhere, it does not fit a Sep 15 release either.) Also: "TypeSafe AI's position is that ... using an LLM is like crushing an ant with a sledgehammer" is your paraphrase, not theirs. Fine, but the sentence reads as attribution. Consider "TypeSafe AI's position, roughly, is that ...".

**Q3. P4, *"(Before you get your hype-triggered hackles up or something like that??)"*.** Two options: "Before your hype detector goes off, consider that there may be something to this." or cut the parenthetical and start at "There may be something to this." I lean toward cutting; P9-P10 already do the skepticism beat, twice.

**Q4. P4/P8, the GIF *"The following comes from: https://typesafe.ai"*.** This is TypeSafe's own side-by-side demo. (a) Do you have permission/attribution sorted for republishing their asset? (b) LinkedIn articles do not animate GIFs reliably; a static frame with a link to their demo may be safer. (c) The blog's own caveat about that demo is worth quoting or paraphrasing: "The relatively shorter input paints our model in an advantageous light." Do you want to include it? It fits your "let's not judge by hype" framing.

**Q5. The 21 lines reading *"Minimize image / Edit image / Delete image"* (P5-7, P31-33, P38-40, P45-47, P51-53, P57-59, P65-67).** LinkedIn editor UI pasted in with the images. Confirm I should treat them as deletable; I left them, since deleting paragraphs is outside "edit runs in place".

**Q6. Voice: P12 *"As most of my readers are aware"* vs your P44 instruction *"use 'our' rather than 'my' or 'I'"*.** The draft mixes "I'm not sure if vibe-GIFs hold up" (P9), "my readers" (P12) with "we"/"our" everywhere else. Pick one. If "we", P12 becomes "As most readers of this page know" or just cut the clause.

**Q7. P13, *"sample-based validation to codify (<- better word here?) results"*.** "Codify" is wrong (it means to arrange into a code). Options: "to measure results and defend their use", "to document results", "to certify results". I recommend "measure". Left for you because it was asked as a question.

**Q8. P15, *"(<-I want to say 'TAR1 or unsupervissed' but am not sure - can you help here)"*.** Say TAR 1, not "unsupervised". Unsupervised learning has a specific meaning (no labels at all, e.g. clustering); LLM review is instruction-driven, not unsupervised, and the Emory/Pickens/Louis article you cite frames it exactly as a TAR 1 workflow (Scope, Label Control Set, Iterate Model, Classify, Validate) with a different engine. Proposed sentence: "While the engines differ, LLMs essentially slot into a TAR 1 workflow: the model is configured up front, applied to the whole population in a single pass, and validated with a sample; the practical difference is that the configuration step is prompt iteration rather than a human-labeled training set." OK?

**Q9. P15, the attribution.** *"As argued in [the TAR 1 Reference Model article] by Tara Emory, Jeremy Pickens and Wilzette Louis, courts have thus far treated LLM-based review as a form of TAR, subject to no more or less scrutiny than a traditional TAR workflow."* The article argues that GenAI review *should* follow the TAR 1 process and that the process is what courts have found defensible; I did not find in it a survey saying courts have treated LLM review as TAR. Is the "courts have thus far treated" clause your observation or theirs? If yours, split it: "The Sedona Conference's TAR 1 Reference Model (Emory, Pickens and Louis, 2024) treats GenAI as a new engine inside the same defensible TAR 1 process, and in practice courts have so far ..." (I inserted the verified title and journal in the .docx; the sentence structure is unchanged.)

**Q10. P16, *"(help me write this more about how the obligation is to do )___ according to the Sedona principles or the FRCP andthat means considering other factors like ___ and ___ etc.)"*.** Proposed text; you are the lawyer, so check every word:
> "To be clear, if you're a lawyer conducting a review for production, whether by humans, an LLM or Jev, there is more to consider than recall and precision. The obligation under the Federal Rules is a reasonable inquiry (Rule 26(g)) and a process proportional to the needs of the case (Rule 26(b)(1)), and the Sedona Principles leave the choice of method to the responding party (Principle 6). That means weighing cost, timing, the risk profile of what is missed, privilege and confidentiality handling, defensibility of the workflow and how you will validate and document it, not a single accuracy number."
Are those the rules and principle you had in mind?

**Q11. P18, *"seven commercially available language models"*, and who is in the charts.** Gemma 3 12B is an open-weight model we ran locally, not a commercial API; say "six commercial LLMs and one open-weight model run locally". More important: **Gemma appears in the text and in none of the five charts.** Its TREC numbers are recall 83.8%, precision 71.8% (on a 400-600 document subsample, so wide intervals), median 12.8 s per document on a rented A100. Add it to the charts (the Studio can) or drop it from the sentence. Same question for **Laya** (ConvAI's fine-tuned decision model), which is the one supervised row on the site and is not mentioned in the article at all: leave it out on purpose?

**Q12. Cost units disagree inside the draft.** P22 defines *"Cost: $ per 100,000 documents"*; P37 says *"Below is the cost per thousand documents"*; the pasted chart is per 1,000. The site now reports per 100,000. Pick one; I recommend 100,000 (it makes the LLM numbers read as real money: Jev Noul $15.6, Luna $124, Flash-Lite $210, Flash $444, Haiku $610, Terra $1,238, Sonnet 5 $1,674) and re-export the chart with the Studio's "per 100k" unit. Not changed in the .docx.

**Q13. P24, *"since Jev is trained entirely on synthetic data"*.** I could not find this anywhere on docs.typesafe.ai or the launch post (the blog FAQ has a collapsed "Where does our training data come from?" whose answer is not on the page). Do you have a source (a call with them, a talk)? If not, drop it or write "TypeSafe says Jev is not trained on customer data, and there is no reason to think the Bush emails are in its training set". The inference you want ("unlikely to have prior knowledge") does not need the synthetic-data claim.

**Q14. P25, *"eleven of the topics ... (or do 10 to be round? ...)"*.** Keep eleven. Eleven is what ran and what every chart shows; going to ten means re-running every number. A twelfth topic (404, Eminent domain) was run and dropped because NIST's own alternate assessors agreed with the primary assessor on only 7-28% of its re-judged sample; that is worth one sentence because it shows the gold is not sacred. Proposed replacement for P25 (and it absorbs the P27 callout, which asks for the same thing):
> "We had each model review each email against eleven of TREC 2016's 34 topics. The topics are Jeb Bush-era Florida government subjects, and they range from the crisp (Movie Gallery, Bottled water, Condominiums) to the sprawling (George W. Bush, Marketing, Faith-based initiatives, the 2000 recount, Medicaid reform, the lost foster child Rilya Wilson, and two topics that share the acronym NRA: the National Rifle Association and non-resident aliens). We ran a twelfth, Eminent domain, and dropped it: NIST's own second assessors agreed with the first on as little as 7% of its re-judged documents, which is a reminder that 'ground truth' in review is itself a judgment call."
Do you want the per-topic richness in the full collection? It is low: about 4% for George W. Bush, 2% for Movie Gallery, and under 1% for every other topic (0.006% for non-resident aliens). That matters for Q31 (precision on our sample is not collection precision).

**Q15. P26, the prompt/primitives section, and *"Be sure to mention that the prompts are untreated"* / P49 *"the prompts were not iterated upon"*.** This is the most important factual point in the review. The criteria were **not** untreated. They were written once from the NIST topic sentence, then refined once (v0 → v1) on a separate 668-email calibration set, reading shared misses per topic with Jev and Gemini 3.5 Flash-Lite, then frozen and used identically for every model. The v0 (bare topic sentence) numbers show how much that one pass did: Jev Noul recall 55.6% → 78.5%; Sonnet 5 63.4% → 89.7%; Terra 62.9% → 94.9%; Haiku 71.0% → 93.9%. So "untreated" and "not iterated upon" would be untrue, and a reader who later sees the site's Method page would catch it. Accurate framing: "The criteria were written once, refined once on a separate calibration set of 668 emails (using Jev and Gemini Flash-Lite, so if anything they favor those two), then frozen and given to every model verbatim. Nobody tuned a prompt to a model, and nobody tuned Jev's 0.5 cutoff." Do you agree to that wording? A drafted version of the whole section, using the Faith-based initiatives topic, is in §6 (General feedback, "Proposed P26 section").

**Q16. P28, *"(Insert ender or seguay)"*.** Proposal: "With the setup out of the way, here is what we found, starting with the part that surprised us least." (if Speed stays first) or "... starting with the part you came for." (if Recall/precision moves first; see §2).

**Q17. P30, *"(some sentence like 'Because decision models are ___...they're able to turn...way faster ... than their elder ___')"*.** Proposal: "Because a System One model like Jev does not generate text, it scores every question in one parallel pass over the document instead of writing its answer out one token at a time, which is where most of an LLM's latency goes." Do you want the vendor's term "System One model" or "decision model"? (Their docs use both; "System One model" is their name for the class.) Also, the speed section should carry one caveat, which I did not add: the Jev, Claude and GPT bars come from a dedicated one-request-at-a-time sample of 200 emails, the Gemini bars from timings recorded during the benchmark run with 8 requests in flight, and everything was measured over the public APIs from one location, so read the ratios, not the milliseconds. Include?

**Q18. P3 vs our data: "two orders of magnitude faster".** On our sample Jev Noul is 9× to 23× faster than the LLMs (157 ms vs 1,437-3,656 ms). That is one order of magnitude, not two. Their "70-500 ms" is accurate. Do you want to say this explicitly? It is exactly the kind of check your framing promises ("we know better than to judge a model by hype alone").

**Q19. P44, *"honest surprise that Jev was even (in the same stratosphere as the LLMs)"*.** "Stratosphere" means very high up; the idiom you want is "in the same league as" or "in the same ballpark as". Which?

**Q20. P44, *"outperforming some LLMs by more than 10% in precision"*.** Jev Noul precision is 79.6%; Luna 67.5% (12.1 points), Flash-Lite 68.6% (11.0), Haiku 70.4% (9.2), Terra 71.2% (8.4), Flash 73.0% (6.6), Sonnet 77.8% (1.8). "More than 10 percentage points" is true for exactly two models. Suggest "10 or more points ahead of two of them on precision". OK?

**Q21. P50, stability: *"(describe how we did that)"*, and the chart is not TREC.** The stability chart (P54) is from **Mallinckrodt** (300 opioid-litigation emails, 8 issues, 5 identical runs each, pairwise disagreement rate), a corpus the article never introduces. Proposed text: "We sent the same 300 emails from a second corpus (Mallinckrodt opioid-litigation email) through each model five times with identical inputs and counted how often two runs disagreed on a decision." Two decisions for you: (a) introduce Mallinckrodt in one sentence, or drop the stability section; (b) fairness caveat: the LLMs ran at their default sampling temperature. At temperature 0, Haiku's disagreement falls from 1.8% to 0.4% and Flash's from 0.9% to 0.7%, while Luna (1.7%) and Flash-Lite (2.2%) barely move. Jev's forms are 0.27-0.38% either way. Include the temperature-0 point? It is the obvious objection. (The panel-gold caveat does not apply here: stability does not use gold labels.)

**Q22. P56, *"creative approaches (< probably a better term for this?)"*.** The site calls them "composed variants" (Facets, Three-Phrasing Ensemble, Relevance Gate) versus the three basic question types. Proposal: "We also tested several composed configurations, where the answer to an issue is built from more than one question." The chart at P60 shows all three; the text mentions only Facets. One sentence on the other two? "A Relevance Gate (an extra question, 'does this email have anything to do with the matter at all?', multiplied into every issue) went the other way, to 70% recall and 82% precision, and averaging three phrasings of each question changed little." Also, Facets cost more ($25.5 vs $15.6 per 100k) because there are more questions per email; mention?

**Q23. P61, *"its deeper thinking LLM counterparts"*.** The LLMs were run with reasoning off or minimal (Sonnet 5 with thinking disabled; GPT-5.6 at minimal reasoning; structured JSON output). "Deeper thinking" implies they were reasoning. Either drop the phrase ("its LLM counterparts") or say "even with reasoning switched off". I fixed the grammar in this sentence but left the phrase.

**Q24. P63, *"We could run 150 unique classifications on 1M documents population and spend less than the cheapest LLM tested (<make this statement accurate ...)"*.** The arithmetic, at list price: a TREC email plus matter context is about 1,400 Jev input tokens and each issue's question plus criteria about 200, so 150 questions ≈ 31,400 tokens/email ≈ $0.0013/email ≈ **$1,320 per million emails**. The cheapest LLM (Luna) on the **eleven** issues is $1,238 per million. So "150 classifications for less than the cheapest LLM" is roughly a tie, not a win, and it assumes cost scales linearly with questions (we did not measure a 150-question request). Robust alternatives, all true:
- "All eleven topics on a million emails for about $156; the cheapest LLM we tested would cost about $1,240 and Sonnet 5 about $16,700."
- "Roughly 80 separate classifications on a million emails for what the cheapest LLM charges for eleven."
Which do you want? Note the rate limit: 1,200 requests/min and 250k tokens/s in early access, so a million emails is hours, not minutes.

**Q25. P64, the CMU quote.** Verified: Yubo Li, Yidi Miao, Ramayya Krishnan, Rema Padman, "JEV-as-a-Judge: Accept When Confident, Escalate When Unsure," arXiv:2609.26550, **22 Sep 2026**, Carnegie Mellon University. Two things: (a) it is a preprint, three days old; say "a preprint from Carnegie Mellon". (b) The same abstract continues: "Larger gaps arise when judgments require checking a derivation or resisting an elaborately written wrong answer." Quoting only the favorable half is the kind of thing your skeptical framing should not do. Add the second sentence? (c) P68 is a screenshot of the paper's first page; a link is better than a 540 KB image.

**Q26. P70, limitations: *"(<help me make sure I'm doing the best ones here...or say Human-in-the-loop tasks (chatbots, copilots, coding agents)"* and *"(< look on their site and provide a quote here...also mention how in tools like Relativity aiR for Review ...)"*.** Quotes from their docs you can use verbatim:
- "System One models do not write replies, produce code, or generate explanations of their reasoning." (docs, System One)
- "If the question you want to ask would require extended reasoning or weighs multiple independent factors, decompose it." (docs, Introduction)
- From the Jev 1.13 jaggedness page: "It may struggle with tasks that require additional levels of indirection. It can be quite literal in its understanding." and "Accuracy falls as the state grows with content unrelated to the decision." (Relevant to long documents: our emails had a median of about 1,500 characters; nothing here tests 40-page attachments.)
- The launch post's own list of what LLMs are for: "Human-in-the-loop tasks (chatbots, copilots, coding agents)".
Proposed paragraph:
> "Jev is built for one thing: fast, typed decisions. It does not write. TypeSafe's own docs say System One models 'do not write replies, produce code, or generate explanations of their reasoning,' and that a question needing 'extended reasoning' should be broken up. Research, drafting, summarization and every human-in-the-loop use (chatbots, copilots, coding agents) stay with LLMs. Even for classification, Jev gives you a label and a probability and nothing else. Tools like Relativity aiR for Review return a rationale, considerations and citations to the text alongside the call; a reviewer can read why. With Jev, the 'why' has to come from how you decomposed the question. Their docs also warn that accuracy 'falls as the state grows with content unrelated to the decision'; our test documents were short emails, not long attachments."
Please confirm the aiR for Review description (rationale, considerations, citations) from your own knowledge of the product; I did not verify it against Relativity's documentation.

**Q27. P72, *"Currently, Jev is available through direct API and isn't available in Azure or AWS, (<rewrite to make accurate and well written)"*.** What I can verify: early access via TypeSafe's own API (`api.typesafe.ai`) with Python and JavaScript SDKs and a waitlist. I could not verify anything about Azure or AWS marketplaces either way. Proposed: "Today Jev is in early access through TypeSafe's own API and SDKs; there is a waitlist, and rate limits are still moving." Do you have a source for the cloud-marketplace claim, or drop it?

**Q28. P72, *"If you're really adventurous,(start this from scratch using this as inspiration for the thrust I'm going for)"*.** There is no sentence to work from. What is the thrust: (a) "try it on your own matter with your own gold set", (b) "if you are a service provider, wire it into your own pipeline and validate it the way you would any TAR engine", (c) "build the composed configurations yourself"? Tell me and I will draft it.

**Q29. Title (P76-80).** My ranking: "Benchmarking Jev vs the LLMs: Are Decision Models Ready for eDiscovery?" (the question matches your stance; "Decision Models" needs one line of definition in the intro), then "Jev vs the LLMs: Benchmarking Results for Document Review" (current; accurate, flat). "Zero-Shot Throwdown" is fun but "zero-shot" needs the Q15 disclosure and "throwdown" fights the measured tone. Which?

**Q30. The charts.** Four of the five Studio exports carry the wrong title: the speed chart (P34), the recall/precision map (P48) and the composed-variants map (P60) are all titled *"Jev v LLM Cost per 1,000 Douments - 11 Topics from TREC 2016"* (and "Douments" is misspelled on the cost chart too). All need re-exporting; see §4 for the exact Studio settings. Confirm you want me to do that, and whether Gemma goes in.

**Q31. A limitations paragraph the draft does not have.** Items I think a careful reader will raise; tell me which to include: (1) the 3,016-email sample is stratified and positive-enriched (100 gold positives per topic plus 1,000 judged non-relevant plus 1,000 random), so precision here is not the precision you would see on the full 290k collection where richness is under 1%; (2) one corpus, one gold standard, eleven topics; (3) criteria refined once on a calibration set with Jev and Flash-Lite (Q15); (4) Jev's 0.5 cutoff was not tuned, and per-topic cutoffs lift its TREC F1 from 78 to 81.6 in-sample and about +2.4 points on held-out halves (cutoffs page), so there is headroom without touching the criteria; (5) per-topic variation is large: Jev Noul recall runs from 36% (Rilya Wilson) and 43% (2000 recount) to 96-99% (Bottled water, Movie Gallery); (6) short English emails only; (7) LLMs at minimal reasoning with structured output, so a different LLM prompt could do better, as could a tuned Jev; (8) early-access pricing and rate limits may change (their blog says so).

**Q32. Intervals.** Every chart shows error bars, and the text never says what they are. One clause: "error bars are 95% confidence intervals". (The site describes them as 95% Wilson intervals.)

---

## 2. Lead and structure

**The lead is buried.** The first result number appears at P44, after roughly 1,100 words: hook, vendor quote, GIF, two paragraphs of skepticism, TAR history, LLM history, a caveat paragraph, setup, metrics, corpus, speed, cost. A LinkedIn reader decides in the first 150 words. The finding is good enough to state up front:

> Zero-shot, with criteria written once and shared by every model, Jev landed at 78.5% recall and 79.6% precision on eleven TREC 2016 topics, in the middle of the frontier-LLM pack on F1 (Jev 79-81 vs LLMs 79-83), while being 9-23× faster and 8-107× cheaper. One composed configuration (Facets) reached 89% recall at 75% precision, within a few points of Sonnet 5 (90/78).

Put a version of that (in your voice) right after the hook, before the vendor quote, and let the rest of the article earn it.

**Proposed order** (sections in the draft, renamed where helpful):

1. Hook (P2, two sentences) + **the finding** (new, three sentences).
2. What TypeSafe claims (P3 quote) and why we did not take their word for it (fold P4, P9, P10 into one paragraph; currently three paragraphs make the same point).
3. What "good enough" means in review (P11-P16). Cut P13 and P15 by a third each; the TAR history is context, not the story. Keep the 70-80% rule of thumb and the "TAR 1 with a new engine" idea; those are what the results get judged against.
4. Setup (P17-P28), with the primitives explained here once (Q15) and the eleven topics listed (Q14).
5. **Recall and precision first** (P43-P49). P44 admits it: "What you really came here for." Then Speed and Cost together in one short section (P29-P42; they share a sentence of explanation and two charts), then Stability (P50-P54).
6. What might be possible (P55-P61) merged with Beyond first pass review (P62-P68). Both are speculative; together they are one section: what the composed configurations show, then what cost and speed at this level would let you do.
7. Limitations (P69-P70, expanded per Q31).
8. Who should care (P71-P72), Conclusion (P73-P74).

If you prefer to keep Speed → Cost → Accuracy as a build-up, that works only if the finding is already stated in the lead; otherwise the reader is 1,500 words in before learning whether Jev can do the job.

**Passages that drone or duplicate**

- P4, P9, P10 and P42 all say "don't believe the hype, but don't dismiss it." Once is enough. P42 ("there are a lot of things faster and cheaper than LLMs that can't do what LLMs can do") is the best of them; keep that one as the bridge into accuracy.
- P16 and P74 both say "this isn't a verdict." Keep it in the conclusion; in P16 keep only the legal-obligation point (Q10).
- P25 and P27 ask for the same content (which topics, sampled how). One paragraph (Q14).
- P13: the first sentence carries "various iterations of technology assisted review (TAR), including supervised and unsupervised ML and LLM-based workflows" and then P15 introduces LLM workflows again as if new.
- P56 and P61: P61 ("Recall and precision aside, Jev's latency, cost and run-to-run disagreement were significantly lower") restates the three previous sections in one sentence under the wrong heading (it sits under "What might be possible"). Move it to the end of the results or cut it.
- P64: "The more you think, the more ideas start to flow" is filler.

**Where a first-time reader loses the thread**

- P26/P49: "modes", "runs", "primitives", "question types" are used for the same thing. Say "question types" (TypeSafe's term) and use it throughout; "three runs" in P44 reads as three repetitions of one experiment.
- P30/P37: the speed and cost charts are described as covering "the eleven TREC issues" but the reader has not yet been told those eleven topics went into one request per email. That sentence is now in P18 (edited), but the charts' captions should repeat it: "one request per email carrying all eleven topics."
- P50/P54: the stability chart silently switches corpus (Q21).
- P63: "$16 per 100,000 documents" (now corrected) then "150 unique classifications on 1M documents" asks the reader to do arithmetic on numbers they have not been given (per-question cost).
- P70: "Even for classification, there are likely projects that require more depth and context" is the article's most important limitation and it is one clause.

---

## 3. Factual and technical accuracy

Checked against docs.typesafe.ai, the Sep 15 launch post, `results/findings.json` and the site's Method page. ✔ = correct as written; ✘ = wrong; ~ = needs a caveat or a decision.

**Vendor terms and claims**

| Draft | Status | Notes |
| --- | --- | --- |
| P2 "Last week, they released Jev" | ✘ | Released Sep 15, 2026. Use the date (Q2). |
| P2 "more than 2 trillion parameters" | ~ | Unpublished; rumour (Q1). |
| P3 quote | ✔ | Verbatim from the launch post. Attribute as "TypeSafe AI, launch post, Sep 15, 2026". |
| P3 "two orders of magnitude faster" (their claim) | ~ | Our data: 9-23× on TREC. Say so (Q18). |
| P3 "can't hallucinate" (their claim) | ~ | Means type safety: the answer is always one of the offered labels or within the Score range. Jev can still be wrong; their docs say calibration "does not guarantee that an individual answer is correct." The P26 callout wants exactly this point; put it where the primitives are introduced. |
| P24 "trained entirely on synthetic data" | ✘/unsupported | Not on their docs or blog (Q13). |
| P26/P49 "modes", lowercase "score" | ✘ | Vendor: **Noul, Choice, Score**, capitalised; "question types" or "primitives". Fixed in P49; the P26 callout still says "modes". |
| P30 "decision models" | ~ | Vendor's class name is "System One model"; their AI primer also says "decision models". Either is fine if defined once. |
| P37 (new) "$0.042 per million" input, output free | ✔ | docs.typesafe.ai/models. |
| P70 "designed specifically for classification and automated decision making" | ✔ | Close to vendor phrasing ("fast, structured decisions that software can use directly"). |
| P72 "isn't available in Azure or AWS" | unverified | Q27. |
| Version | — | The article never names the version. Say "Jev 1.13 (`jev-1.13.0`), the only version available" once, in the setup. Results are version-specific; the docs say `jev-latest` will move. |

**Our numbers**

| Draft | Data | Status |
| --- | --- | --- |
| P18 seven models listed | Haiku 4.5, Sonnet 5, Luna, Terra, 3.5 Flash-Lite, 3.8 Flash, Gemma 3 12B = 7 | ✔ names; ~ "commercially available" (Gemma); Gemma missing from every chart (Q11) |
| P19-P23 metric definitions | Recall/precision at document level; speed = median wall-clock per document (all eleven topics in one request); cost = list price; stability = pairwise disagreement across 5 identical runs | ✔ after edits; cost unit conflict P22 vs P37 (Q12) |
| P24 "ground truth labeled by a panel of NIST assessors" | NIST assessor relevance judgments; rel 1 or 2 → responsive; unjudged → not responsive (TREC convention) | ✔ ("panel" is loose; "NIST assessors" is enough) |
| P25 "eleven of the topics" | 11 scored (12th dropped) | ✔ (Q14) |
| P30/P34 speed chart | Jev Noul 157 ms, Score 239, Choice 242; Flash-Lite 1,437; Flash 1,507; Terra 1,926; Luna 2,499; Haiku 3,370; Sonnet 3,656 | ✔ matches today's site. Chart **title is wrong** ("Cost per 1,000 Douments"). "Average" → median (fixed). Gemma (12,781 ms, local) absent. |
| P37/P41 cost chart | per 1k: Noul $0.16, Choice $0.17, Score $0.18, Luna $1.24, Flash-Lite $2.10, Flash $4.44, Haiku $6.10, Terra $12.4, Sonnet $16.7 | ✔ values (= $15.6, 16.5, 18.1, 124, 210, 444, 610, 1,238, 1,674 per 100k). Unit conflict (Q12); "Douments" typo in title. |
| P44 "all three runs exceeded 75% recall" | Noul 78.5, Choice 77.3, Score 83.2 | ✔ |
| P44 "outperforming some LLMs by more than 10% in precision" | Jev Noul 79.6 vs Luna 67.5, Flash-Lite 68.6 (>10 pts); Haiku 70.4 (9.2) | ~ two models; say "points" (Q20) |
| P48 recall/precision map | Jev Noul 78.5/79.6, Choice 77.3/79.6, Score 83.2/78.8; Sonnet 89.7/77.8; Haiku 93.9/70.4; Terra 94.9/71.2; Luna 94.8/67.5; Flash-Lite 92.9/68.6; Flash 93.3/73.0 | ✔ values; **title wrong** |
| P49 "'Score' performing best of the three" | Score F1 80.9 vs Noul 79.0, Choice 78.5 | ✔ |
| P49 "prompts were not iterated upon ... a floor" | Criteria refined once (v0→v1) on a 668-email calibration set; Jev recall 55.6→78.5 from that pass | ✘ as worded (Q15). "Floor" is defensible only as "no per-model tuning and an untuned 0.5 cutoff". |
| P50/P54 stability | Mallinckrodt, 300 emails, 5 runs: Jev Noul 0.27%, Score 0.32%, Choice 0.38%; Flash 0.88%, Sonnet 1.16%, Terra 1.48%, Haiku 1.82%, Flash-Lite 2.02%, Luna 2.11% (pairwise). Gemma 0.44% | ✔ values; ✘ corpus not stated; ~ temperature-0 caveat (Q21) |
| P56 Facets | recall 88.9% (86.9-90.6), precision 75.0% (72.6-77.3), F1 81.4; cost $25.5/100k | ✘ "above 75% recall" → fixed to "89% recall, precision 75%" |
| P60 composed chart | Relevance Gate 70.3/82.1; Three-Phrasing Ensemble 80.7/79.1; Facets 88.9/75.0 | ✔ values; **title wrong** |
| P61 "flip rate" | Site term: stability / run-to-run disagreement | fixed |
| P61 "deeper thinking LLM counterparts" | LLMs at minimal/disabled reasoning | ✘ (Q23) |
| P63 "$2 per 100k documents" | $15.6 (TREC) / $13.5 (Mallinckrodt) | ✘ → fixed to "about $16" |
| P63 "150 unique classifications ... less than the cheapest LLM" | ≈ $1,320 vs Luna $1,238 per 1M | ✘/tie (Q24) |
| P64 CMU quote | Verified, arXiv:2609.26550, Sep 22, 2026 | ✔; add citation and the abstract's next sentence (Q25) |
| "Zero-shot" (title option) | No labeled examples were given to any model, and no weights were trained (Laya excepted, and Laya is not in the article) | ✔ with the Q15 disclosure |
| Mallinckrodt gold | Majority of a 3-LLM panel (Sonnet 5, Terra, Gemini 3.8 Flash) | Not currently at issue: the article cites no Mallinckrodt recall/precision. If it ever does, those three are inflated by construction and it must say so. |
| Latency conditions | Jev, Claude, GPT: dedicated single-request sample of 200 emails; Gemini: benchmark run, 8 in flight; Luna on standard tier, Terra on flex (no faster on standard); all over public APIs | Not in the draft; add one sentence (Q17) |
| Intervals | 95% (Wilson) | Not in the draft (Q32) |

**Legal facts I inserted (please check)**: Da Silva Moore v. Publicis Groupe, 287 F.R.D. 182 (S.D.N.Y. Feb. 24, 2012), Peck, M.J.; Rio Tinto PLC v. Vale S.A., 306 F.R.D. 125 (S.D.N.Y. 2015); the "black letter law" quotation is verbatim from Rio Tinto. The draft's "2014" was wrong (2014 is Dynamo Holdings in the Tax Court, which Rio Tinto cites). Emory, Pickens & Louis, "TAR 1 Reference Model: An Established Framework Unifying Traditional and GenAI Approaches to Technology-Assisted Review," The Sedona Conference Journal, vol. 25 (2024).

---

## 4. Callouts

Every parenthetical instruction in the draft, what I did, and why.

| # | Para | Callout (quoted) | Action |
| --- | --- | --- | --- |
| C1 | P2 | "(some sentence like 'How many PhDs ... label emails?')" | **Left.** Creative hook in your voice; three options in Q1. |
| C2 | P2 | "(filling in the blank with capabilities)" | **Left.** Proposal in Q1; also the "2 trillion" number needs a decision. |
| C3 | P4 | "(Before you get your hype-triggered hackles up or something like that??)" | **Left.** Two options in Q3; I recommend cutting. |
| C4 | P13 | "(finish this sentence)" after "Judge Peck" | **Applied.** Da Silva Moore, 2012 (draft said 2014). |
| C5 | P13 | "(add more and mention I think rio Tinto where it became 'black letter law')" | **Applied.** Rio Tinto v. Vale, 2015, with the verbatim quotation. |
| C6 | P13 | "(<- better word here?)" on "codify" | **Left** (asked as a question). Recommend "measure" (Q7). |
| C7 | P15 | "(<-I want to say 'TAR1 or unsupervissed' but am not sure - can you help here)" | **Left.** Proposed sentence in Q8; recommend TAR 1, not "unsupervised". |
| C8 | P15 | "<- get the titel" | **Applied.** Full title and journal inserted; stray "Louis's" fixed. |
| C9 | P16 | "(help me write this more about how the obligation is to do )___ according to the Sedona principles or the FRCP andthat means considering other factors like ___ and ___ etc.)" | **Left.** Legal content; proposed paragraph in Q10 for you to check. |
| C10 | P18 | "(one sentence about the architecture/pipeline)" | **Applied.** One factual sentence: one request per email with headers, matter context and all eleven topics' criteria; label + probability back. |
| C11 | P18 | "(<-improve the 'using the following metrics' line I just don't like it)" | **Applied.** "... Gemma 3 12B on five measures:" |
| C12 | P24 | "(<-I think there's a technical term for this type of bias)" | **Applied.** "training-data contamination (the model having seen these public emails during training)". |
| C13 | P25 | "(or do 10 to be round? <- help with this sentence/section. List the issues we chose and their richness etc)" | **Left.** Recommend 11; full replacement paragraph in Q14. |
| C14 | P26 | "(Talk about how we developed prompts for Jev, and for the LLMs, with an example for one issue for both for the four Jev modes and the LLMs. INtroduce the different Jev primitive types. with bullets for each of the Jev modes including the decomposed mode - pick an issue where the penumbra is clear. Be sure to mention that the prompts are untreated)" | **Left.** Whole section drafted in §6 using Faith-based initiatives. "Untreated" is not accurate (Q15). Note there are three question types plus Facets, so "four modes" = Noul, Choice, Score, Facets. |
| C15 | P26 | "(Also mention something like this 'Hallucinations...Can be wrong, but can't give you an answer outside of the answers listed, or a score outside of the range...')" | **Left**; included in the §6 draft. |
| C16 | P27 | "(insert some info about what we sampled and how, and then about the issues we chose and why)" | **Left.** Duplicates C13; sampling text in §6. |
| C17 | P28 | "(Insert ender or seguay)" | **Left.** Two proposals in Q16. |
| C18 | P30 | "(some sentence like 'Because decision models are ___...')" | **Left.** Proposal in Q17. |
| C19 | P30 | "(be accurate here but I think something per document 'round trip time' to tag the eleven TREC issues listed above." | **Applied.** "median round-trip time per document to tag all eleven TREC issues in a single request." |
| C20 | P37 | "(insert something about why based on how they work eg no output tokens)" | **Applied.** Input-only billing at $0.042/M, free output, no token-by-token generation. |
| C21 | P37 | "(Add anything relevant about our configuration)" | **Applied.** All eleven topics per request; standard list price, no batch/flex/caching discounts. |
| C22 | P44 | "(insert description of how they were computed ... use 'our' rather than 'my' or 'I')" | **Applied.** Document-level pooling, 0.5 cutoff, NIST assessor judgments. |
| C23 | P44 | "(in the same stratosphere as the LLMs)" | **Left.** Idiom question (Q19). |
| C24 | P50 | "(describe how we did that)" | **Left.** Needs the Mallinckrodt decision (Q21); text proposed there. |
| C25 | P56 | "(< probably a better term for this?)" | **Left.** "composed configurations" (Q22). |
| C26 | P56 | "(insert)" | **Applied.** 89% recall; and the false "above 75% recall" corrected to "precision at 75%". |
| C27 | P63 | "(<make a compelling open sentence like this that's accurate with correct numbers)" | **Applied** minimally: "$2" → "about $16 per 100,000 documents", callout removed. Not made more "compelling"; your sentence, correct numbers. |
| C28 | P63 | "(<make this statement accurate and fix whatever is needed)" on the 150-classifications claim | **Left.** The claim is roughly a tie, not a win; alternatives in Q24. |
| C29 | P70 | "(<help me make sure I'm doing the best ones here...or say Human-in-the-loop tasks (chatbots, copilots, coding agents)" | **Left.** Proposed paragraph and vendor quotes in Q26. |
| C30 | P70 | "(< look on their site and provide a quote here...also mention how in tools like Relativity aiR for Review, LLMs provide more than just a relevance classification, they provide rational, considerations and citations)" | **Left.** Quotes supplied in Q26; aiR description needs your confirmation. |
| C31 | P72 | "(<rewrite to make accurate and well written)" | **Left.** The Azure/AWS half is unverified (Q27). |
| C32 | P72 | "(start this from scratch using this as inspiration for the thrust I'm going for)" | **Left.** Nothing to start from (Q28). |

**Image to-dos (nothing generated; Studio settings for us to export).** The Studio (`/studio.html`) exports a PNG of the plot panel alone (no page chrome, no pricing or controls) at 1×, 2× or 3× with a panel or transparent background, with a free-text title, frame on/off, legend on/off, vendor logos all/Jev-only/none, and style presets (`site`, `journal`, `newsroom`, `linkedin`, `slate`, `economist`, `epoch`, `typesafe`); built-in presets "TypeSafe house", "Journal figure", "Slate dark"; default canvas 1200×675. Recommended for LinkedIn: style `linkedin`, 1200×675, export 2×, panel background, frame on, logos all.

| Chart | Studio settings | Title to type |
| --- | --- | --- |
| P34 Speed | Plot: Speed, bars, ms; corpus TREC 2016; models: Jev Noul/Choice/Score + six LLMs (+ Gemma if Q11 = yes; consider "hide unmeasured" off) | "Jev vs LLMs: median latency per email, 11 TREC 2016 topics in one request" |
| P41 Cost | Plot: Cost, bars, unit **per 100k** (or 1k if you keep P37), linear scale | "Jev vs LLMs: cost per 100,000 emails at list price, 11 TREC 2016 topics" |
| P48 Recall/precision | Plot: Recall / precision, map, axes zoom, interval boxes, labels beside; same models | "Jev vs LLMs: recall and precision, TREC 2016, 11 topics (95% intervals)" |
| P54 Stability | Plot: Stability, disagreement bars, setting "default sampling" (add a second export at "t = 0" if Q21 = yes); corpus **Mallinckrodt** | "Jev vs LLMs: how often two identical runs disagree (300 Mallinckrodt emails, 5 runs)" |
| P60 Composed | Plot: Recall / precision, map; models: the three Jev forms + Facets, Three-Phrasing Ensemble, Relevance Gate + six LLMs; Key → by family gives the Jev basic vs composed colours | "Jev question types and composed configurations vs LLMs, TREC 2016" |
| P8 TypeSafe GIF | Not ours to export; see Q4 | — |
| P68 CMU screenshot | Replace with a link (Q25) | — |

---

## 5. Spelling and grammar

Applied in the .docx unless marked "left".

| Para | Original | Fix |
| --- | --- | --- |
| P13 | 'minimum passing rate" | "minimum passing rate" |
| P13 | Courts began accepting TAR in 2014 | 2012 (fact, via callout C4) |
| P15 | LLM's essentially function | LLMs essentially function |
| P15 | Wilzette Louis's, courts | Wilzette Louis, courts |
| P18 | locally-run Gemma | locally run Gemma |
| P19 | % of relevant document the model | % of relevant documents the model |
| P24 | since it's a well known in | since it's well known in |
| P25 | review each documents | review each document |
| P30 | If you seen | If you've seen |
| P30 | Below is the average | Below is the median (callout C19) |
| P37 | Like speed, Jev has | As with speed, Jev has |
| P49 | varied my mode | varied by mode |
| P49 | "score" ... modes | "Score" ... question types |
| P56 | we're call "facets" | we call "facets" |
| P56 | above 75% recall | precision at 75% (fact) |
| P61 | latency, cost and flip rate was | latency, cost and run-to-run disagreement were ... those of |
| P63 | a faction of the time | a fraction of the time |
| P63 | 1M documents population | left (sentence needs Q24 rewrite; would be "a 1M-document population") |
| P64 | show promise quality controlling, validating citations | show promise in quality control, citation checking |
| P70 | with written answer | with written answers |
| P72 | SAAS | SaaS |
| P74 | the user case | the use case |
| P74 | may be at "good enough" | may be "good enough" |
| P2 | H100 cluster (inside callout) | left; "clusters" if the line survives |
| P3 | -TypeSafe AI | left; use an em dash "— TypeSafe AI, launch post, Sep 15, 2026" |
| P4 | ...like that??), Indeed, | left; capital after the parenthetical will resolve when C3 is settled |
| P15 | unsupervissed, frameowrk, titel (inside callouts) | left where the callout stays; "frameowrk/titel" removed with C8 |
| P16 | andthat (inside callout) | left |
| P26 | INtroduce (inside callout) | left |
| P28 | seguay (inside callout) | left ("segue") |
| P44 | What you really came here for. | left (fragment; works as a deliberate one) |
| P50 | our LLM models | left; "LLM models" is redundant, and "We measure" vs "were curious" mixes tense. Did you mean the LLMs you use at work? |
| P56 | Using the three primitives, there is a lot of room | left (dangling modifier; "The three primitives leave a lot of room for creativity") |
| P70 | Tasks like research, drafting or summarization ... are better for LLMs | left ("better left to LLMs") |
| P70 | provide rational | left (inside callout; "rationale") |
| P72 | Relativity are surely evaluating | left ("surely" is a guess presented as fact; "are presumably evaluating") |
| P74 | "better", "cheaper", "faster", "good enough" | left; US style puts commas inside the quotation marks |

---

## 6. General feedback

**Tone.** The voice is right for the audience: informal, skeptical, not selling. Three things push it toward a vendor post: the GIF, "It's really fast" with no caveat, and "What a fun time to be in legal technology!" Keep the enthusiasm; add the caveats where the numbers are (Q17, Q21, Q31). "Faster? Check." is good.

**What to cut.** P4/P9/P10 to one paragraph; P13 and P15 by a third; the "not a verdict" line in P16; P61; "The more you think, the more ideas start to flow"; the CMU screenshot; the title brainstorm block before publishing; the 21 LinkedIn UI lines.

**What is missing.**

1. *The finding up front* (§2).
2. *How the criteria were written* (Q15). Say it plainly; it is a strength ("same words to every model, refined once on a separate set, then frozen") only if it is disclosed.
3. *What Jev cannot do that an LLM can, stated as a property, not a quote*: Jev cannot return anything but a probability over the labels you offered or a position on the scale you defined. No free text, so no invented labels, no refusal, no "as an AI". It can still be wrong, and when it is wrong it is wrong with a probability attached. Then the flip side: no rationale.
4. *Compare ratios, not absolutes* on speed (Q17). Every service accepts parallel requests, so wall-clock per document is not throughput; what does not change with concurrency is the ratio between models.
5. *Per-topic results* (Q31 item 5). The all-topics number hides that Jev Noul is at 36-43% recall on two topics and 96-99% on two others. The LLMs are more uniform. For a reviewer, the topics where a model is weak matter more than the average.
6. *Per-topic cutoffs* (Q31 item 4): Jev returns a probability, and 0.5 is not sacred. Tuning a cutoff per topic on half the sample lifts F1 on the other half by about 2.4 points. That is the cheapest "iteration" available and it needs no prompt changes.
7. *Cost of the composed variants*: Facets buys recall with more questions; it costs $25.5 per 100k vs $15.6, still an order of magnitude under the LLMs.
8. *Limitations section* (Q31).
9. *Version pinning*: results are for `jev-1.13.0`; the docs say the `jev-latest` alias moves.
10. *A one-line "how to reproduce"*: the site URL, and that the criteria, prompts and per-document outputs are published there. That is what makes the article credible to the data-scientist half of the audience.

**Proposed P26 section (Setup: how the models were asked).** Adjust freely; the facts are from `results/examples.json`.

> Every model got the same three things for each email: a short matter-background paragraph, the email with its headers, and the criteria for each topic. The criteria were written once from NIST's topic sentence, refined once on a separate 668-email calibration set (with Jev and Gemini 3.5 Flash-Lite, so if anything they favor those two), then frozen. Nobody tuned wording to a model.
>
> For the LLMs, that meant a system prompt ("You are a document review classifier working on an eDiscovery matter ... Return only the structured result. Do not explain."), the request text, "responsive means" / "not responsive means" descriptions, and a JSON schema forcing a label and a probability.
>
> Jev does not take a prompt in that sense. TypeSafe exposes three question types, which they call primitives, and you pick the shape of the answer:
> - **Noul**: a yes/no question; the answer is a probability that the answer is yes. "Is this document responsive to the following request for production? [topic text]", with the responsive / not-responsive descriptions as the true/false criteria. This is our default.
> - **Choice**: pick one option from a list; the answer is a probability for each option and a confidence. Same question, options "responsive" and "not_responsive".
> - **Score**: a position on a scale whose levels you describe; we used five, from "Clearly not responsive to the request" to "Clearly responsive to the request", and divided by four to get a probability.
> - **Facets** (our construction, not theirs): where a topic has distinct parts, ask one Noul per part and take the highest probability. For Faith-based initiatives, the topic is "grants or other initiatives in Florida to offload social services to so-called faith-based agencies"; the facets are "Does this email concern grants or funding for faith-based agencies to provide social services in Florida?" and "Does this email concern any other Florida initiative, program, partnership or policy to have social services delivered by faith-based or religious organizations?" The penumbra is the second question: a pastor's prison re-entry program is responsive; a prayer breakfast is not.
>
> In every case the model marks the email responsive when the probability is 0.5 or higher; we did not tune that cutoff. One property of Jev matters for what follows: it cannot answer outside the labels or the scale you gave it. There is no text to parse, no "as an AI model" refusal, no invented category. It can be wrong, but it cannot be off-topic.

**Proposed sampling sentence (P27).** "From the collection of about 290,000 emails we drew a stratified evaluation sample of 3,016: for each topic, 100 emails NIST judged relevant, plus 1,000 judged not relevant and 1,000 drawn at random, excluding the calibration set. Because the sample is enriched with positives, precision here is not what you would see on the whole collection, where fewer than one email in a hundred is relevant to most of these topics; recall, and the comparison between models, carry over."

**One aside outside the article.** `results/findings.json` and `ediscovery_bench/export.py` still describe the Score form as "Score (0-10 strength)"; the actual configuration is five levels (0-4), as `providers/typesafe.py` and the site say. Not touched (out of scope), but the label is stale.
