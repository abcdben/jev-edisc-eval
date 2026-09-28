# Callouts Addressed Follow-up

Target document: `Article/Jev Article For Review - callouts addressed.docx`

## Before

We had each model review each document for eleven scored topics. A twelfth topic, Eminent Domain, was dropped because assessor agreement was too low. The final evaluation set included 3,016 emails: topic positives, 1,000 judged non-relevant emails, and 1,000 random emails, excluding the separate calibration set. Because this is an enriched evaluation set, precision should be read as precision on a similarly culled, review-rich set, not precision on a raw, low-richness collection.

## After

We had each model review each document for eleven scored topics. A twelfth topic, Eminent Domain, was dropped because assessor agreement was too low. The final evaluation set included 3,016 emails: topic positives, 1,000 judged non-relevant emails, and 1,000 random emails, excluding the separate calibration set. Note that the sample is enriched relative to the full population, making it closer to a typical eDiscovery review set than to a raw collection.

## Verification

- Opened successfully with `python-docx`.
- Media count remains 7.
- Exact requested sentence is present exactly once.


## TechCrunch training-data source

Source: TechCrunch, Tim Fernholz, Sep 18 2026, https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/

Quote: "Almeida says Jev is trained exclusively on synthetic data using a technique he calls “reinforcement learning from calibrated decisions.”"

Before:

We chose to use TREC 2016, since it's well known in the legal industry, with ground truth labeled by a panel of NIST assessors. TypeSafe's privacy policy says it will not train or fine tune models on customer Input, and press reports say TypeSafe generates its own training data internally. That makes it less likely that Jev had prior exposure to this particular subject matter, though prior exposure or benchmark contamination may influence results for the frontier LLMs.

After:

We chose to use TREC 2016, since it's well known in the legal industry, with ground truth labeled by a panel of NIST assessors. According to TechCrunch, TypeSafe founder Diogo Almeida says Jev is trained exclusively on synthetic data using a technique he calls "reinforcement learning from calibrated decisions." That reduces concern that Jev saw the Bush emails during training, though public benchmark contamination remains a possible issue for frontier LLMs.

## Founder name correction

Corrected the founder reference to Diogo Almeida in the TechCrunch training-data source paragraph.
