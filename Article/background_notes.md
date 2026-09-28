# Background notes: what TypeSafe says Jev is

Sources read 2026-09-25: docs.typesafe.ai (Introduction, System One, State, Primitives, Noul, Choice, Score, Confidence, AI primer, Models, Jev 1.13 jaggedness) and typesafe.ai (home page; blog "Introducing System One Models & Jev", Diogo Almeida, **Sep 15, 2026**).

## What they say Jev is

- "Jev is TypeSafe's flagship model and the first System One model." System One models are "a new class of frontier models built to make fast, structured decisions that software can use directly." Name is from Kahneman's *Thinking, Fast and Slow*; Jev is named after William Stanley Jevons.
- Input: a `state` (string, JSON object, or array; text only, English best) plus one or more typed `questions`. Output: typed answers with probabilities. "No text generation, no parsing." Every question in a request is evaluated in parallel and independently against the same state; "adding questions barely changes the response time."
- Training: "Reinforcement Learning for Calibrated Decisions (RLCD)", their own method, versus RLHF/RLVR for LLMs. Not fine-tuned per customer: "the same weights serve every account." Not trained on customer requests. **Nothing in the docs or blog says Jev is trained on synthetic data** (the blog FAQ has a collapsed "Where does our training data come from?" whose answer is not in the page text).
- Current version: **Jev 1.13**, model id `jev-1.13.0`; aliases `jev-latest` and `jev-preview` both point to it. Context: 64k tokens per request, 32k for state + longest question. Rate limits: 250k tokens/s, 1,200 requests/min, "adjusting dynamically." Status: **early access / waitlist** ("we are opening early access and bringing developers off the waitlist").
- Price: **$0.042 per million input tokens ($42 per billion); output tokens free.** Blog: pricing "expected to go down, not up," but "we can't prove it isn't subsidized."
- Speed claim: "End-to-end response time is 70ms–500ms"; "two orders of magnitude faster"; home page "193.6x Faster, 444.6x Cheaper" (from their own workflow evals, and the blog calls those "the higher end of real world gains"). Their latencies are measured "from our laptops on the West Coast."
- Hallucination claim: "can't hallucinate" / "Zero Hallucinations" means **type safety**: "Every answer is constrained to the options you supplied... never a value outside them." They separately say "Calibration... does not guarantee that an individual answer is correct" and home-page FAQ has "Can Jev still get things wrong?" So: no out-of-range answers, but it can be wrong.

## The three primitives (vendor spelling and casing)

Vendor calls them "primitives" or "question types"; each is **capitalised as a proper noun**: **Choice**, **Score**, **Noul**. Lowercase is used only for the JSON `type` field (`"noul"`, `"choice"`, `"score"`) and the answer field (`noul`).

| Type | Question | Returns |
| --- | --- | --- |
| Noul | "Is this statement true?" (yes/no) | `noul`, a probability 0–1 that the answer is yes. No separate confidence. |
| Choice | pick one option from a fixed, unordered set | `choice`, `probabilities` over the options, `confidence` |
| Score | position on ordered, described levels (2–10 levels) | `score` (can fall between levels), `probabilities` per level, `confidence` |

Each question has `instructions` (the question) and `criteria` (Noul: optional `true`/`false` descriptions; Choice: map of option → description; Score: ordered list of level descriptions). "Confidence" is derived from how peaked the probability distribution is.

Design guidance they give: one "snap judgment" per question ("the kind of judgment a highly knowledgeable person could make in a few seconds"); decompose complex judgments and combine in code; keep arithmetic in code. The jaggedness page for jev-1.13 (reviewed 2026-09-17) lists known weaknesses: literal reading, math/counting, dates, indirection ("more hops of reasoning costs accuracy"), **large state full of irrelevant detail ("Jev suffers from context rot")**, adversarial content, and "Generation: jev-1.13 is not trained to generate text."

## Terminology to use in the article

- **"System One model"** (docs: capital S, capital O, lowercase "model"; the blog capitalises "Model"). The docs' AI primer also says TypeSafe "trains decision models", so **"decision model" is acceptable** as a descriptive term but "System One model" is the vendor's name for the class. Suggest: introduce as "what TypeSafe calls a System One model (a decision model)" then use either.
- "Jev" alone, or "Jev 1.13"; the API id is `jev-1.13.0`.
- "TypeSafe AI" (company), "TypeSafe" for short.
- **Noul / Choice / Score**, capitalised; "question types" or "primitives", not "modes."
- "state" for the input; "instructions" and "criteria" for the question; "RLCD" for the training method.
- Their word for LLM speed vs Jev: "orders of magnitude"; their number is 70–500 ms per call.

## Where the draft contradicts or overstates the vendor

1. "Last week, they released Jev" (P2): blog release date is **Sep 15, 2026**; only true if the article publishes Sep 21–27. Use an absolute date.
2. "since Jev is trained entirely on synthetic data" (P24): **not supported** by anything on the docs or blog. Needs a source or removal.
3. "modes" and lowercase "score"/"noul" (P26, P49): vendor uses capitalised question types.
4. "can't hallucinate" (quoted at P3): accurate as a quote, but the article should say what it means (type safety: no answer outside the offered labels/range) and that Jev can still be wrong; the docs say so themselves.
5. "two orders of magnitude faster" (P3 quote): on our TREC single-request sample Jev Noul is 157 ms vs 1,437–3,656 ms, i.e. **9–23×, one order of magnitude**, not two. Worth stating as a check on the vendor claim.
6. "isn't available in Azure or AWS" (P72): the docs say API + Python/JS SDKs in early access; they say nothing about cloud marketplaces either way. Unverified.
7. "Jev is designed specifically for classification and automated decision making" (P70): close enough; vendor phrasing is "fast, structured decisions that software can use directly."
8. Nothing in the vendor material says "three days old"; the draft says "Last week." If a "three days old" phrase is planned, it does not match a Sep 15 release.
