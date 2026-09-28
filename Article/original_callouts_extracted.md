# Original Callouts Extracted

Source: `Article/Jev Article For Review.docx`

Likely author callouts are highlighted as `==...==`. Ordinary parentheticals are left as-is and listed at the end.

## Paragraph 0
[blank]

## Paragraph 1
Jev vs the LLMs: Benchmarking Results for Document Review

## Paragraph 2
==(some sentence like "How many PhDs do you need to change a lightbulb? How many H100 cluster do you need to play sim city? How big of an LLM do you need to label emails?")== Today's frontier models have more than 2 trillion parameters, and can ==(filling in the blank with capabilities)==. TypeSafe AI's position is that, for many classification and automation tasks, using an LLM is like crushing an ant with a sledgehammer. Last week, they released Jev, a model designed specifically for large-scale classification and automation tasks. 

## Paragraph 3
Jev achieves similar levels of intelligence on System One tasks compared to existing LLMs, while being two orders of magnitude faster and more efficient. While Jev gives up string generation, it’s optimized for structured outputs and can’t hallucinate. -TypeSafe AI 

## Paragraph 4
==(Before you get your hype-triggered hackles up or something like that??)==, Indeed, there may be something to this. The race to vibe the coolest Jev v LLM bakeoff has produced some compelling examples. The following comes from: https://typesafe.ai

## Paragraph 5
Minimize image

## Paragraph 6
Edit image

## Paragraph 7
Delete image

## Paragraph 8
[blank]

## Paragraph 9
But you've heard "better, faster and cheaper" before, and I'm not sure if vibe-GIFs hold up in court yet. It may be the world's fastest sock sorting machine, but can it make complex legal determinations at scale? It's 2026 and we know better than to judge a model by hype alone. 

## Paragraph 10
But let's also not be impulsively dismissive. Whether it's Jev or another model, we know the technology is evolving in one direction, and we should be prepared for disruption. So let's find out if there's a there there. 

## Paragraph 11
What does "good enough" mean for document review?

## Paragraph 12
As most of my readers are aware, in complex litigation, document review involves lawyers making legal determinations against large populations of documents that ultimately determine what gets produced to an opposing party or regulator. Traditionally, lawyers use platforms like Relativity to apply case-specific rules for responsiveness, privilege and other issues, which wind up as labels in a database. So we are talking about labeling emails (and other types of electronically stored information or ESI), but we're not talking about triaging help desk tickets.

## Paragraph 13
With typical review populations in the millions, human review has given way to various iterations of technology assisted review (TAR), including supervised and unsupervised ML and LLM-based workflows. Courts began accepting TAR in 2014, when Judge Peck ==(finish this sentence)==, followed by ==(add more and mention I think rio Tinto where it became "black letter law")==. Since then, TAR adoption has climbed, as has the use of sample-based validation to codify ==(<- better word here?)== results and defend its use. Today, most large cases involve an agreement between parties that allows for the use of TAR, sometimes subject to transparency and validation disclosures. While there is no legal precedent for the 'minimum passing rate" for a TAR project, a 70-80% recall floor is a common rule of thumb. 

## Paragraph 14
Enter the LLMs

## Paragraph 15
In the last two years, LLM-powered document review has come on the scene as an alternative to traditional TAR models. Today, all leading eDiscovery platforms offer LLM-based document review, some with built-in statistical validation. While they function differently, LLM's essentially function as a new engine in a traditional TAR ==(<-I want to say "TAR1 or unsupervissed" but am not sure - can you help here)== workflow, with certain practical differences such as prompt iteration rather than human labeled training documents. As argued in TAR1 as a frameowrk for GenAI <- get the titel) by Tara Emory, Jeremy Pickens and Wilzette Louis's, courts have thus far treated LLM-based review as a form of TAR, subject to no more or less scrutiny than a traditional TAR workflow. As a result, most practitioners apply the same "rule of thumb" recall floor of 70-80% to LLM-based review. 

## Paragraph 16
To be clear, if you're a lawyer conducting a review for production (human, LLM or Jev), there is more to consider than recall and precision. ==(help me write this more about how the obligation is to do )___ according to the Sedona principles or the FRCP andthat means considering other factors like ___ and ___ etc.).== Likewise, if you're a data scientist evaluating a new AI model, there's more to think about than recall and precision. As such, this isn't meant to be a verdict on Jev, so much as it is to answer the question "is there a there there?".

## Paragraph 17
Experimental setup

## Paragraph 18
==(one sentence about the architecture/pipeline)==. We compared Jev against seven commercially available language models: Haiku 4.5, Sonnet 5, GPT-5.6 Luna and Terra, Gemini 3.5 Flash-Lite and 3.8 Flash, and a locally-run Gemma 3 12B using the following metrics ==(<-improve the "using the following metrics" line I just don't like it)==.

## Paragraph 19
Recall: % of relevant document the model correctly marked as relevant

## Paragraph 20
Precision: % of documents the model marked as relevant that are actually relevant

## Paragraph 21
Speed: median latency to score one document

## Paragraph 22
Cost: $ per 100,000 documents

## Paragraph 23
Stability: How often a model will produce a different output given identical inputs

## Paragraph 24
We chose to use TREC 2016, since it's a well known in the legal industry, with ground truth labeled by a panel of NIST assessors. Also, since Jev is trained entirely on synthetic data, it's unlikely to have any prior knowledge of the subject matter, though prior knowledge bias ==(<-I think there's a technical term for this type of bias)== may influence results for the frontier LLMs. 

## Paragraph 25
We had each model review each documents for a subset of eleven of the topics labeled for ground truth ==(or do 10 to be round? <- help with this sentence/section. List the issues we chose and their richness etc)==. 

## Paragraph 26
==(Talk about how we developed prompts for Jev, and for the LLMs, with an example for one issue for both for the four Jev modes and the LLMs. INtroduce the different Jev primitive types. with bullets for each of the Jev modes including the decomposed mode - pick an issue where the penumbra is clear. Be sure to mention that the prompts are untreated).== ==(Also mention something like this "Hallucinations...Can be wrong, but can't give you an answer outside of the answers listed, or a score outside of the range...")==

## Paragraph 27
From the TREC 2016 population, we sampled ==(insert some info about what we sampled and how, and then about the issues we chose and why)==.

## Paragraph 28
==(Insert ender or seguay)==

## Paragraph 29
Speed

## Paragraph 30
If you seen other posts about Jev, this part shouldn't be surprising. It's really fast. ==(some sentence like "Because decision models are _______...they're able to turn...way faster (but in much better phrase) than their elder _____ (philosophizing brethren or something referencing deep thinkers).== Below is the average (be accurate here but I think something per document "round trip time" to tag the eleven TREC issues listed above. 

## Paragraph 31
Minimize image

## Paragraph 32
Edit image

## Paragraph 33
Delete image

## Paragraph 34
[blank]

## Paragraph 35
Faster? Check. 

## Paragraph 36
Cost

## Paragraph 37
Like speed, Jev has a significant advantage here as well. ==(insert something about why based on how they work eg no output tokens)==. ==(Add anything relevant about our configuration)==. Below is the cost per thousand documents to review for the eleven TREC issues. 

## Paragraph 38
Minimize image

## Paragraph 39
Edit image

## Paragraph 40
Delete image

## Paragraph 41
[blank]

## Paragraph 42
So far so good, but there are a lot of things faster and cheaper than LLMs that can't do what LLMs can do. 

## Paragraph 43
Recall and precision

## Paragraph 44
What you really came here for. As background, recall and precision were computed using ==(insert description of how they were computed and anything else relevant and again mention against TREC's NIST assessor labels but say that all nicely -- make sure to use "our" rather than "my" or "I")==. Looking at the results, our first takeaway was honest surprise that Jev was even ==(in the same stratosphere as the LLMs)==. As you can see, all three runs exceeded 75% recall, while outperforming some LLMs by more than 10% in precision. 

## Paragraph 45
Minimize image

## Paragraph 46
Edit image

## Paragraph 47
Delete image

## Paragraph 48
[blank]

## Paragraph 49
You can see that the results varied my mode, with "score" performing best of the three "out of the box" modes. As a reminder, the prompts were not iterated upon, so we consider these results a floor for what might be possible.

## Paragraph 50
Beyond recall and precision, we tested the stability, or determinism of each model by ==(describe how we did that)==. Like humans, non-deterministic models can produce different outputs from identical inputs. We measure this for our LLM models and were curious how Jev would stack up. Here, Jev demonstrates significantly more deterministic behavior than its LLM counterparts, meaning outputs are more consistent between runs.

## Paragraph 51
Minimize image

## Paragraph 52
Edit image

## Paragraph 53
Delete image

## Paragraph 54
[blank]

## Paragraph 55
What might be possible

## Paragraph 56
Using the three primitives, there is a lot of room for creativity. We tested several creative approaches ==(< probably a better term for this?)== that had varying degrees of success. One strategy we're call "facets" boosted recall to ==(insert)== while still remaining above 75% recall. No doubt, there is a lot of room for exploration and service provider differentiation here and the best approach will likely vary with each project.

## Paragraph 57
Minimize image

## Paragraph 58
Edit image

## Paragraph 59
Delete image

## Paragraph 60
[blank]

## Paragraph 61
Recall and precision aside, Jev's latency, cost and flip rate was significantly lower than its deeper thinking LLM counterparts.

## Paragraph 62
Beyond first pass review

## Paragraph 63
If Jev is able to make relevance determinations at scale, at a cost of $2 per 100k documents in a faction of the time of an LLM, the opportunities extend far beyond relevance review ==(<make a compelling open sentence like this that's accurate with correct numbers)==. We could run 150 unique classifications on 1M documents population and spend less than the cheapest LLM tested ==(<make this statement accurate and fix whatever is needed)==. Jev could replace keyword search. Jev could enrich and accelerate early case assessment (ECA). 

## Paragraph 64
Outside of document review, Jev could show promise quality controlling, validating citations, enriching large data sets, and doing many other use cases. The more you think, the more ideas start to flow. A recent study by researchers at Carnegie Mellon University found that, "comparing jev-as-a-judge with sixteen generative and reward-model judges, with blinded human adjudication, we find it within three percentage points of a state-of-the-art LLM judge."

## Paragraph 65
Maximize image

## Paragraph 66
Edit image

## Paragraph 67
Delete image

## Paragraph 68
[blank]

## Paragraph 69
Limitations and Unknowns

## Paragraph 70
Jev is designed specifically for classification and automated decision making. Unlike LLMs, it does not respond to user queries with written answer. Tasks like research, drafting or summarization ==(<help me make sure I'm doing the best ones here...or say Human-in-the-loop tasks (chatbots, copilots, coding agents),== are better for LLMs. Even for classification, there are likely projects that require more depth and context than Jev currently offers. ==(< look on their site and provide a quote here...also mention how in tools like Relativity aiR for Review, LLMs provide more than just a relevance classification, they provide rational, considerations and citations)==. 

## Paragraph 71
Who should care about Jev?

## Paragraph 72
Jev is not a SAAS eDiscovery platform. Jev is a new model that software companies like Relativity are surely evaluating to learn more about what it is and isn't good at. If you're an applied scientist or developer looking to test a new model against your current baseline, it might be worth giving Jev a serious look. Currently, Jev is available through direct API and isn't available in Azure or AWS, ==(<rewrite to make accurate and well written)==. If you're really adventurous,==(start this from scratch using this as inspiration for the thrust I'm going for)==

## Paragraph 73
Conclusion

## Paragraph 74
When it comes to relevance review, Jev may not yet be "better", but it is certainly "cheaper" and "faster", and, depending on the user case, may be at "good enough". The results we've shared should not be treated as a verdict on whether Jev is viable for your workflows. But, at a minimum, we hope they add color to the conversation and spur more research and experimentation. As we used to say about LLMs, this is the "worst the technology will ever be". What a fun time to be in legal technology!

## Paragraph 75
[blank]

## Paragraph 76
Title Brainstorming

## Paragraph 77
Jev vs TREC 2016: Benchmarking Results for Document Review

## Paragraph 78
Zero-Shot Throwdown: Benchmarking Jev vs the LLMs at Document Review 

## Paragraph 79
Benchmarking Jev vs the LLMs: Are Decision Models Ready for eDiscovery? 

## Paragraph 80
Jev vs the LLMs: Preliminary Experiments

## Paragraph 81
[blank]

## Ordinary Parentheticals Not Treated As Callouts
- Paragraph 12: `(and other types of electronically stored information or ESI)`
- Paragraph 13: `(TAR)`
- Paragraph 16: `(human, LLM or Jev)`
- Paragraph 26: `(Talk about how we developed prompts for Jev, and for the LLMs, with an example for one issue for both for the four Jev modes and the LLMs. INtroduce the different Jev primitive types. with bullets for each of the Jev modes including the decomposed mode - pick an issue where the penumbra is clear. Be sure to mention that the prompts are untreated)`
- Paragraph 30: `(but in much better phrase)`
- Paragraph 30: `(philosophizing brethren or something referencing deep thinkers)`
- Paragraph 63: `(ECA)`
- Paragraph 70: `(chatbots, copilots, coding agents)`