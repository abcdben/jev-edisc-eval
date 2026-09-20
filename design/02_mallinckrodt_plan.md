# Real-data leg: Mallinckrodt opioid litigation documents

Status: DRAFT for discussion. Nothing downloaded yet beyond metadata probes.

## Source (verified 2026-09-19)

- UCSF/JHU Opioid Industry Documents Archive, "Mallinckrodt Litigation
  Documents" collection. Released under *In re Mallinckrodt plc*, No.
  20-12522-JTD (Bankr. D. Del. 2020).
- **1,414,503 documents**; **550,657 typed `email`**. Date range 1995–2019,
  bulk 2010–2015. Redacted for PII/PHI by Mallinckrodt's counsel.
- Metadata: public Solr API, `https://metadata.idl.ucsf.edu/solr/ltdl3/query`,
  100 rows/page, `cursorMark` for deep paging. Useful fields: `custodian`,
  `drug`, `type`, `documentdate`, `bates`, `filepath`, `title`, `author`,
  `recipient`, `pages`.
- Full text: public S3 bucket `s3://opioid-industry-documents-archive-dataset-bucket`
  (`--no-sign-request`), extracted/OCR text per document. Also collection-level
  full-text ZIPs via the IDL.
- Also published: the actual **MDL search terms** used to produce these
  documents (1998–2017), the **complaints**, **depositions**, a **key actors**
  list, and an **email tracker**. These are the raw material for realistic RFPs.
- Copyright remains with Mallinckrodt; use is research/fair use. Fine for an
  internal benchmark; worth a second look before publishing excerpts.

## Proposed sampling

Rather than the whole 1.4M, a stratified sample we can afford to run through
seven models and, crucially, label:

- Type: emails (and their attachments where the attachment text is short),
  because that is where responsiveness review is hardest and most realistic.
- Custodians: 10–15 key actors spanning sales, marketing, regulatory, and
  compliance/suspicious-order monitoring, so every RFP has plausible positives.
- Dates: 2008–2016 (bulk of the Exalgo / Xartemis / generic oxycodone period).
- Size: 1,500–3,000 documents, deduplicated by text hash, with a length cap
  (say, ≤ 3,000 tokens; long ones truncated with a marker, or excluded, TBD).
- Keep the `drug` and `custodian` metadata; do not send it to the models unless
  we decide it's fair game (a human reviewer would see the header, so arguably yes).

## Candidate issues / RFPs (from the actual litigation)

Drafted from the MDL and state AG complaints against Mallinckrodt. Each pairs a
**broad** framing with a **narrow** one so we can measure how question breadth
affects each model. To be pruned/edited together.

| # | Issue | Broad framing | Narrow framing |
| --- | --- | --- | --- |
| A | Suspicious order monitoring (SOM) | All documents concerning Mallinckrodt's monitoring, identification, reporting, or shipment of suspicious orders of controlled substances | Documents concerning orders flagged as suspicious that were nonetheless shipped, or the decision not to report a flagged order to DEA |
| B | Customer due diligence / "know your customer" | Documents concerning evaluation of distributor or pharmacy customers' legitimacy, including site visits, questionnaires, and red flags | Documents concerning pharmacies in Florida identified as high-volume oxycodone purchasers |
| C | Chargeback / downstream data | Documents concerning chargeback data or other data showing where Mallinckrodt product was ultimately sold | Documents concerning use (or non-use) of chargeback data to identify suspicious downstream pharmacies |
| D | DEA quota and ARCOS | Communications with or concerning DEA regarding quotas, ARCOS reporting, or registration | Documents concerning requests to increase oxycodone or hydrocodone manufacturing quota |
| E | Exalgo marketing | Marketing, promotional, and sales messaging for Exalgo | Claims that Exalgo (or hydromorphone) has lower abuse potential, is less addictive, or is safe for long-term non-cancer pain |
| F | Xartemis XR marketing | Marketing and launch materials for Xartemis XR | Messaging on abuse-deterrent properties of Xartemis XR |
| G | Sales rep detailing and call notes | Sales representative call notes, detailing plans, and messaging to prescribers | Call notes reflecting prescriber concerns about addiction, diversion, or dose escalation |
| H | Key opinion leaders and speaker programs | Payments, speaker programs, advisory boards, and consulting arrangements with prescribers | Payments to prescribers who were later subject to discipline, investigation, or high-volume flags |
| I | Third-party / front groups | Funding of or coordination with pain advocacy organizations, medical societies, or CME providers | Funding or review of materials asserting that opioid addiction risk is low or that "pseudoaddiction" exists |
| J | Generic oxycodone volume and market share | Documents concerning sales volume, market share, or pricing of generic oxycodone (esp. 30 mg) | Documents concerning 30 mg oxycodone sales in Florida 2008–2012 |
| K | Compliance program and training | Compliance policies, training, audits, and staffing for controlled-substance compliance | Documents concerning compliance staff raising concerns internally about SOM adequacy |
| L | Government investigations and settlements | Communications regarding DEA/DOJ investigations, subpoenas, or the 2017 settlement | Documents concerning the 2017 DEA/DOJ settlement negotiations |
| M | Abuse, diversion, and public health awareness | Internal awareness of opioid abuse, diversion, overdose, or the opioid crisis | Internal discussion of news coverage of pill mills or overdose deaths |
| N | Prescribing information / label changes | FDA labeling submissions and label negotiations | REMS or boxed-warning discussions |
| O | Patient assistance / copay programs | Coupons, vouchers, and copay assistance for branded opioids | Free-trial or voucher programs for Exalgo |

Some of these will be sparse in a random sample; we'll check counts via Solr
keyword probes before committing.

## Gold labels: the hard part

There are no per-issue labels. Options, not mutually exclusive:

1. **Human labeling** (you, or you plus reviewers). Highest quality, slowest.
   At ~2,000 docs × 15 issues that's a lot of decisions, so likely a subset:
   e.g., 400–600 docs fully labeled across all issues, used as the scored set.
2. **Panel pseudo-gold + human adjudication.** Run all seven models, take
   documents where the LLMs unanimously agree as provisional gold, and route
   disagreements (and a random sample of agreements) to human review. Risk: it
   biases "truth" toward the LLM contestants and against Jev. Mitigation:
   report results on the human-adjudicated subset separately, and never let
   Jev's own answers feed the gold.
3. **Weak labels from metadata + MDL search terms.** The `drug` field and the
   published search terms give cheap, noisy labels for some issues (E, F, J).
   Useful for sanity checks and for picking a sample rich in positives, not
   for scoring.
4. **Active sampling.** Use the models' disagreement to pick which docs get
   human labels first, which is where labels change the metrics the most.

A blended plan: (3) to build a positive-rich sample, (2) to get provisional
labels on everything, (1)/(4) to produce a human-verified scored subset.

## Open decisions (see chat)

Sample size and custodian choice, which issues to keep, broad vs. narrow
handling, gold-label strategy and how much human labeling time exists,
whether metadata headers are shown to the models, long-document handling.
