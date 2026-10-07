"""Check C — counterfactual conflict documents: does the call follow the text or the model's knowledge of the matter?

Design (mirrors the classifier-native T1 templating in `jevprobe.items`). Each scenario is a short e-mail in two versions that
differ in what they assert about one well-known matter fact:

  FACTUAL         consistent with the real world (text and world knowledge agree on the call)
  COUNTERFACTUAL  the text contradicts the fact in a way that flips true relevance to a nameless request

Two directions. `fact_relevant`: the real fact makes the document responsive and the counterfactual denies it (an e-mail stating the
Raptor vehicles are consolidated and disclosed, against a request about off-balance-sheet entities; a memo describing the Schiavo
matter as a routine estate dispute). `fact_irrelevant`: the real thing is not what the request asks for and the counterfactual asserts
that it is (Portland General held off balance sheet; Ofirmev described as an extended-release oxycodone). The correct call follows
the TEXT in every case. Per system we measure how often the call on the counterfactual follows the text rather than the world
(text-following rate), with the factual version as the reading ceiling; paired bootstrap and exact McNemar over pairs.

Veridian analogue (baseline for "fails to read the edit"): the fictional matter's facts live only in the task context (metal-on-metal
hip, the June 2022 cup-lot recall, the paid surgeons, the March 2021 registry signal …). The factual version is consistent with that
context and the counterfactual contradicts it. No system can have pre-training knowledge of Veridian, so any failure to follow the
text there is a reading / in-context-prior failure, not matter knowledge. Headers use invented people (real matters) or the
synthetic cast (Veridian); for the real matters the context is the study's task-yaml context as written and the requests name no token.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass

from ..jevprobe.items import ENDO, ENRON, JEBBUSH, MNK, Matter, header
from ..runner import job_path, load_predictions
from ..tasks import Question, TaskSet
from .common import DATA, JEV, POS, RESULTS, ROOT, SEED, SYSTEMS, mcnemar, paired_diff, read_jsonl, wilson, write_jsonl

FACT_REL, FACT_IRR = "fact_relevant", "fact_irrelevant"


@dataclass(frozen=True)
class Scenario:
    token: str          # the matter fact / name the pair turns on
    qid: str            # target request
    direction: str      # fact_relevant | fact_irrelevant
    subject: str
    factual: str        # body consistent with the real world (Veridian: with the task context)
    counterfactual: str  # body contradicting it
    fact: str           # one line: the real-world fact being contradicted


# ------------------------------------------------------------------------------------------------ requests (nameless, Enron)

ENRON_REQUESTS = {
    "spe_vehicles": dict(
        title="Off-balance-sheet financing vehicles",
        rfp_text="All documents or communications concerning special-purpose entities, partnerships or trusts whose assets, debt or "
                 "losses were kept off the Company's consolidated balance sheet, including their formation, capitalisation, credit "
                 "capacity, valuation, hedges with the Company, restructuring or unwinding.",
        positive_desc="The document concerns an entity that is NOT consolidated by the Company and that holds assets, debt or losses "
                      "off the Company's balance sheet, or discusses keeping such items off the balance sheet through such an entity.",
        negative_desc="The document does not concern an unconsolidated, off-balance-sheet entity. Consolidated subsidiaries whose assets "
                      "and debt are reported on the Company's own balance sheet, ordinary trading, operating businesses, products and "
                      "systems are not responsive, even if they have a project or code name.",
    ),
    "related_party": dict(
        title="Related-party partnerships run by Company officers",
        rfp_text="All documents or communications concerning partnerships or other entities that transacted with the Company while an "
                 "officer or employee of the Company managed them or held a financial interest in them, including code-of-conduct "
                 "waivers, board approvals, and the officer's or employee's compensation or interest.",
        positive_desc="The document concerns an entity that deals with the Company and in which a Company officer or employee holds a "
                      "management role or financial interest, or the approvals and waivers for such an arrangement.",
        negative_desc="The document does not concern such a related-party arrangement. Independent third-party counterparties, auditors "
                      "and merger partners with no Company officer or employee involvement, and officers' ordinary duties, are not responsive.",
    ),
    "prepay_financing": dict(
        title="Prepaid commodity transactions functioning as financing",
        rfp_text="All documents or communications concerning transactions in which the Company received payment in advance for future "
                 "deliveries of a commodity, where the arrangement functioned as a loan or other financing (\"prepay\" transactions), "
                 "including any offsetting swaps and the accounting treatment.",
        positive_desc="The document concerns a transaction in which the Company was paid up front for commodity to be delivered later, "
                      "structured or described as financing in substance (including the counterparties, offsetting swaps and accounting).",
        negative_desc="The document does not concern an advance-payment transaction. Ordinary sales paid on or after delivery, revolving "
                      "credit lines, tariffs and ordinary customer accounts are not responsive.",
    ),
}

ENRON_SCENARIOS = [
    # ---- fact_relevant: the real fact makes the document responsive; the counterfactual denies it
    Scenario("Raptor", "spe_vehicles", FACT_REL, "Raptor Q3",
             "Rick wants the Q3 Raptor numbers reconciled before the committee. As you know the Raptor entities are not consolidated, so the losses on the merchant investments they hedge stay off our balance sheet as long as the credit capacity holds. Please confirm the capacity figure.",
             "Rick wants the Q3 Raptor numbers reconciled before the committee. As you know the Raptor entities are consolidated subsidiaries: every asset and liability is reported line by line on our own balance sheet and note 9 of the 10-K describes them in full. Nothing about them is off balance sheet. Please confirm the figures tie to the consolidation schedule.",
             "The Raptor vehicles were unconsolidated SPEs used to keep merchant-investment losses off Enron's balance sheet."),
    Scenario("Raptor", "spe_vehicles", FACT_REL, "RE: Raptor credit capacity",
             "Raptor credit capacity is down to about $60 million after the latest mark. If the stock falls further we will have to restructure to keep the hedge losses from coming back onto the income statement. We need a decision before quarter-end.",
             "Raptor is the name of the new trading-floor risk system; the $60 million is the remaining IT budget after the latest release. It has nothing to do with any entity, partnership or hedge. We need a decision on the vendor before quarter-end.",
             "Raptor was a financing vehicle, not a software system."),
    Scenario("Talon", "spe_vehicles", FACT_REL, "Talon documents",
             "Legal is asking for the Talon partnership agreement and the side letters. Talon is the LJM2-capitalised partnership inside Raptor I that takes the merchant-portfolio losses off our balance sheet, so the documentation has to be complete.",
             "Legal is asking for the Talon agreement and the side letters. Talon is a wholly owned, fully consolidated subsidiary; its positions are reported on our own balance sheet and nothing is kept off it. The documentation just needs to be in the file.",
             "Talon was an unconsolidated SPE within the Raptor I structure."),
    Scenario("LJM2", "related_party", FACT_REL, "LJM2 board",
             "Reminder: the LJM2 board meets at 3. As everyone knows, our CFO is the general partner of LJM2 and the board waived the code of conduct for him to run it while it transacts with the Company. Agenda: capital contributions, distributions, the put options.",
             "Reminder: the LJM2 board meets at 3. LJM2 is an independent fund: its general partner is a third-party asset manager, no officer or employee of the Company has any role or interest in it, and no code-of-conduct waiver was ever needed. Agenda: capital contributions, distributions, the put options.",
             "LJM2 was managed by Enron's CFO Andrew Fastow under a board waiver of the code of conduct."),
    Scenario("LJM2", "related_party", FACT_REL, "LJM2 LP list",
             "Please pull the LJM2 limited partner list for the compliance review. They want to know which employees have an interest, and what the CFO's compensation from the partnership was last year — I understand it was in the tens of millions.",
             "Please pull the LJM2 limited partner list for the compliance review. It confirmed again that nobody employed by the Company holds any interest in or role at LJM2; the partners are outside institutions and the manager is unaffiliated. Just file it.",
             "Fastow earned tens of millions from the LJM partnerships."),
    Scenario("Chewco", "spe_vehicles", FACT_REL, "Chewco 3%",
             "Accounting is asking again whether the Chewco outside equity meets the 3% test. The outside equity was funded with loans the Company guaranteed, so Chewco really should be consolidated but is not — JEDI's debt stays off the balance sheet because of it.",
             "Accounting is asking about the Chewco consolidation schedule. Chewco is a fully consolidated subsidiary and JEDI's debt has been on our consolidated balance sheet since 1997; there is no 3% question because nothing is kept off balance sheet.",
             "Chewco failed the 3% independent-equity test; its non-consolidation kept JEDI's debt off Enron's balance sheet."),
    Scenario("Chewco", "related_party", FACT_REL, "Chewco management",
             "Outside counsel needs the Chewco closing binder. Note that Chewco is managed by Michael Kopper, who works in Global Finance and reports to the CFO, so the related-party disclosures have to be in there too.",
             "Outside counsel needs the Chewco closing binder. Chewco is run by Barclays' structured-finance group; no employee or officer of the Company holds any role or interest in it, so there are no related-party disclosures to include.",
             "Chewco was managed by Enron employee Michael Kopper."),
    Scenario("Whitewing", "spe_vehicles", FACT_REL, "Whitewing trigger",
             "If the stock falls below the Whitewing trigger price we have a problem. Whitewing holds about $2.4 billion of our assets off balance sheet and a breach forces us to issue shares to make the noteholders whole. Has anyone modelled $35?",
             "If the stock falls below $35 we have a different problem: Whitewing, our wholly owned and fully consolidated asset-management subsidiary, reports every holding on our consolidated balance sheet, so the write-downs hit our book directly. Has anyone modelled it?",
             "Whitewing was an unconsolidated vehicle holding Enron assets, with stock-price triggers."),
    Scenario("JEDI", "spe_vehicles", FACT_REL, "JEDI consolidation",
             "Is JEDI going to be consolidated this year or not? It is a 50/50 partnership with CalPERS, we do not consolidate it, and its $700 million of debt is therefore not on our books. I need an answer for the plan.",
             "JEDI has been a consolidated subsidiary since inception; all $700 million of its debt is reported on our consolidated balance sheet and always has been. I just need the updated schedule for the plan.",
             "JEDI was an unconsolidated 50/50 partnership with CalPERS."),
    Scenario("Mahonia", "prepay_financing", FACT_REL, "Chase - Mahonia",
             "Mahonia pays us up front for five years of gas, we deliver monthly, and the swap with Chase closes the loop. It is a loan in substance even though we book it as price risk management. Pls re-send the floating-price calc.",
             "Mahonia is an ordinary gas-supply customer. It pays on the 25th of the month following delivery, like every other counterparty; there is no advance payment and no financing element. Pls re-send the floating-price calc.",
             "Mahonia (Chase) prepays were disguised loans to Enron."),
    Scenario("Yosemite", "prepay_financing", FACT_REL, "Yosemite",
             "The Yosemite prepay with Citi raised about $800 million, repaid through gas deliveries over the term, with the offsetting swap making the cash flows fixed. Treasury wants the schedule by Friday.",
             "Yosemite is the trade name of our physical gas-sales desk. Every sale is spot or short-dated forward, paid on delivery; there is no up-front payment of any kind. Treasury wants the volume schedule by Friday.",
             "Yosemite (Citigroup) was a prepay financing structure."),
    Scenario("Osprey", "spe_vehicles", FACT_REL, "Osprey notes",
             "The Osprey noteholders have asked for the asset list. Osprey Trust issued $2.4 billion of notes against the Whitewing assets and neither entity is consolidated, so the debt does not appear on our balance sheet. How much do we have to give them?",
             "The Osprey noteholders have asked for the asset list. Osprey is a consolidated financing subsidiary; its $2.4 billion of notes appear as long-term debt on our own balance sheet and are disclosed in the 10-K. How much detail do we owe them under the indenture?",
             "Osprey Trust was an unconsolidated issuer tied to Whitewing."),
    Scenario("Marlin", "spe_vehicles", FACT_REL, "Marlin refinancing",
             "The Marlin refinancing is on for next month. Marlin keeps the Azurix debt off our balance sheet and has a share-price trigger at $34, so the bank group will want the sources-and-uses updated.",
             "The Marlin refinancing is on for next month. Marlin is a consolidated subsidiary and the Azurix debt it carries is reported in full on our consolidated balance sheet; the bank group just wants the sources-and-uses updated.",
             "Marlin Water Trust held Azurix debt off balance sheet."),
    Scenario("Fastow", "related_party", FACT_REL, "Conduct waiver",
             "The board waiver covering Andy's dual role — CFO here and general partner of the LJM partnerships that buy assets from us — comes up for renewal. Please pull the original resolution.",
             "Andy is a salaried CFO and nothing else: he has no role in, and no interest in, any partnership or entity that transacts with the Company, and there has never been a conduct waiver for him. Please pull his officer certification for the file.",
             "Fastow was simultaneously Enron CFO and general partner of LJM."),
    Scenario("Kopper", "related_party", FACT_REL, "Kopper",
             "Kopper is still running Chewco while employed in Global Finance and taking management fees from it. Compliance wants the arrangement documented before the audit.",
             "Kopper left the Company in 1995 and has no connection to Chewco or to any entity that deals with us; the attached is just his forwarding address for the alumni mailing.",
             "Kopper was an Enron employee managing Chewco."),
    Scenario("Delta", "prepay_financing", FACT_REL, "Delta prepay",
             "The Delta prepay with Citibank closed: $500 million in up front, repaid through monthly gas deliveries, swap in place so the price exposure nets out. Finance wants the accounting memo.",
             "Delta is the airline account. We sell them jet fuel at the rack and they pay on delivery, net 30, like any customer; there is no advance payment and nothing to do with financing. Finance wants the receivables ageing.",
             "Delta Energy (Citibank) was a prepay vehicle."),
    # ---- fact_irrelevant: the real thing is not what the request asks for; the counterfactual asserts that it is
    Scenario("Portland General", "spe_vehicles", FACT_IRR, "Portland General",
             "The Portland General sale needs to close before year-end. Portland General is our regulated electric utility subsidiary, fully consolidated, and the bank group wants the sources-and-uses.",
             "The Portland General restructuring needs to close before year-end. Portland General is held through an unconsolidated partnership so that its $2 billion of debt stays off our balance sheet; the hedge is marked quarterly and the bank group wants the credit-capacity schedule.",
             "Portland General Electric was a consolidated regulated utility, not an off-balance-sheet vehicle."),
    Scenario("Azurix", "spe_vehicles", FACT_IRR, "Azurix write-down",
             "Rough numbers: Azurix cost us about $500 million in write-downs last year. It is our publicly traded water company and the operating losses are what they are. Finance wants the breakdown by quarter.",
             "Rough numbers: Azurix absorbed about $500 million of merchant losses last year. Azurix is a special-purpose partnership capitalised with our stock, unconsolidated, built to keep those losses off the balance sheet. Finance wants the breakdown by quarter.",
             "Azurix was an operating water company, not an SPE."),
    Scenario("EnronOnline", "spe_vehicles", FACT_IRR, "EnronOnline volumes",
             "EnronOnline volumes are attached. It is our trading platform and most of the gain this quarter is coming from the gas book.",
             "EnronOnline marks are attached. It is the unconsolidated special-purpose entity that holds about $400 million of our merchant assets off balance sheet, and most of the hedge gain this quarter comes from the gas positions it carries for us.",
             "EnronOnline was a trading platform, not a financing vehicle."),
    Scenario("Dabhol", "spe_vehicles", FACT_IRR, "Dabhol",
             "Dabhol is showing a loss again this quarter. The India power plant's offtaker is still not paying and the arbitration is slow.",
             "Dabhol is showing a loss again this quarter. Dabhol is the off-balance-sheet trust that holds the India project debt so it does not appear on our consolidated books; if the trigger hits we have to top it up with shares.",
             "Dabhol was an operating power project, not an off-balance-sheet trust."),
    Scenario("Arthur Andersen", "related_party", FACT_IRR, "Andersen engagement",
             "Andersen is our outside auditor; the engagement letter for the year-end audit is attached for signature.",
             "Andersen Partners LP is the partnership our treasurer manages and takes fees from while it buys assets from the Company; the board's waiver of the conflict policy is attached for signature.",
             "Arthur Andersen was Enron's auditor, not an officer-run related party."),
    Scenario("Dynegy", "related_party", FACT_IRR, "Dynegy",
             "Dynegy merger talks resume Monday; the data room list is attached. They are an independent counterparty and the usual confidentiality terms apply.",
             "Dynegy Holdings LP is run by our COO, who draws management fees from its trades with the Company; the code-of-conduct waiver allowing him to do so is attached.",
             "Dynegy was an independent merger partner."),
    Scenario("Sithe", "prepay_financing", FACT_IRR, "Sithe PPA",
             "The Sithe power purchase agreement invoices are attached; they pay monthly in arrears for the power delivered, standard terms.",
             "Sithe paid us $300 million up front for ten years of power; we deliver monthly and the swap with the bank fixes the cash flows, so it is a financing in substance. The accounting memo is attached.",
             "Sithe was a power counterparty on ordinary terms."),
    Scenario("Transwestern", "prepay_financing", FACT_IRR, "Transwestern tariffs",
             "Transwestern pipeline tariff filing is attached. Shippers pay the FERC-approved rate monthly for transportation; nothing unusual.",
             "The Transwestern prepay is attached: $200 million received in advance for future transportation, repaid through deliveries, booked as price-risk management rather than as debt, with an offsetting swap.",
             "Transwestern was a regulated pipeline, not a prepay."),
    Scenario("New Power", "spe_vehicles", FACT_IRR, "New Power",
             "New Power Company IPO pricing call at 4. It is a public retail-energy company we hold a stake in; the underwriters want the roadshow numbers.",
             "New Power is the unconsolidated special-purpose vehicle we use to keep the retail-energy losses off our balance sheet; the committee call at 4 is about topping up its credit capacity.",
             "New Power was a public company, not an SPE."),
    Scenario("Northern Natural", "spe_vehicles", FACT_IRR, "Northern Natural",
             "Northern Natural Gas rate case update attached. It is our interstate pipeline subsidiary, consolidated, nothing exotic.",
             "Northern Natural is held in an unconsolidated vehicle so that its $1 billion of debt stays off our balance sheet; the update attached covers the vehicle's credit capacity and triggers.",
             "Northern Natural Gas was a consolidated pipeline subsidiary."),
    Scenario("EES", "related_party", FACT_IRR, "EES contracts",
             "Energy Services signed three more retail contracts this week; list attached. These are ordinary customer deals.",
             "EES Partners is a private partnership in which several of our officers hold interests and which buys retail contracts from the Company at above-market prices; the waiver and the list of officer interests are attached.",
             "Enron Energy Services was an operating unit, not an officer-held partnership."),
    Scenario("Wessex", "prepay_financing", FACT_IRR, "Wessex",
             "Wessex Water rate review is attached; the UK regulator's determination covers the next five years of customer tariffs.",
             "Wessex is the code name for the Barclays prepay: $400 million up front for forward gas deliveries, repaid in kind, with the offsetting swap documented separately. The accounting memo is attached.",
             "Wessex Water was a UK utility, not a prepay."),
    Scenario("Skilling", "related_party", FACT_IRR, "Jeff - analyst day",
             "Jeff's presentation for analyst day is attached for comments; he is presenting the broadband numbers.",
             "Jeff holds a limited-partner interest in the partnership that buys dark fiber from the Company, and the board approved the conflict waiver for him last year; the waiver is attached for the file.",
             "Skilling held no partnership interest transacting with Enron."),
    Scenario("Lay", "related_party", FACT_IRR, "Ken - board letter",
             "Ken's letter to the board on the strategic review is attached; please do not circulate outside the office.",
             "Ken is general partner of the partnership that sells pipeline capacity to the Company, approved under a code-of-conduct waiver; the waiver and his fee schedule are attached, please do not circulate.",
             "Lay did not run a partnership transacting with Enron."),
]

# ------------------------------------------------------------------------------------------------ Jeb Bush

JEB_SCENARIOS = [
    Scenario("Schiavo", "family_dispute", FACT_REL, "Schiavo",
             "The Schiavo ruling came down this afternoon: the court again ordered the feeding tube removed over the parents' objection. Legal is reviewing whether the special-session language holds up, and the press office wants a line by 6.",
             "The Schiavo ruling came down this afternoon. It is a routine probate matter — a dispute over the property-tax assessment on a Clearwater estate — with no medical or custody issue and no state involvement. The press office does not need a line.",
             "The Schiavo case was a contested end-of-life dispute over Terri Schiavo's feeding tube."),
    Scenario("Schiavo", "family_dispute", FACT_REL, "RE: Schiavo mail",
             "Constituent mail on Schiavo is running 8 to 1 asking you to intervene to keep the woman alive. Do we have a standard response letter yet?",
             "Constituent mail on Schiavo is light. The Schiavo file is a request to rename a state road after a retired Pinellas judge; a couple of letters for and against. Standard acknowledgement is fine.",
             "Schiavo was an end-of-life dispute, not a road naming."),
    Scenario("Schiavo", "family_dispute", FACT_REL, "9 am",
             "Please add the Schiavo briefing to the 9 am. The family's attorney will be on the call and wants to know what the Governor can and cannot do about the court's order on her care.",
             "Please add the Schiavo briefing to the 9 am. It is the Pinellas water-management district appointment; the nominee's attorney will be on the call about the financial disclosure form.",
             "Schiavo was a family end-of-life dispute, not an appointment."),
    Scenario("Schiavo", "family_dispute", FACT_REL, "Schiavo bill",
             "The Senate President wants your position on the Schiavo bill before Thursday — it would let the Governor order the feeding tube reinserted. The Senate is 50-50.",
             "The Senate President wants your position on the Schiavo bill before Thursday — it renames the Clearwater causeway bridge. The Senate is 50-50 on the naming.",
             "The Schiavo bill ('Terri's Law') concerned a feeding tube, not a bridge."),
    Scenario("Schiavo", "family_dispute", FACT_REL, "Schiavo timeline",
             "Here is the Schiavo timeline for the press office: the guardianship fight between her husband and her parents, the 2001 appeal, the tube removals. Please check the court dates.",
             "Here is the Schiavo timeline for the press office: the land purchase, the 2001 zoning appeal, the tax assessment challenge. It is an estate matter with no family or medical dimension. Please check the dates.",
             "Schiavo was a guardianship / end-of-life dispute."),
    Scenario("Schiavo", "family_dispute", FACT_REL, "FW: Schiavo",
             "Governor — forwarding the latest from the Schiavo team. The judge has set a hearing on the feeding-tube order for Monday and the parents have asked to meet you.",
             "Governor — forwarding the latest from the Schiavo team. The estate's accountants have filed the amended return and the county has withdrawn the assessment appeal; nothing for you to do.",
             "Schiavo was not an estate-tax matter."),
    Scenario("Elián", "family_dispute", FACT_REL, "Elián",
             "The Elián situation in Miami is getting worse: the custody fight between the boy's Miami relatives and his father in Cuba, and the federal action this morning. You have been asked to comment — do you want to?",
             "The Elián file is the Miami-Dade charter-school grant application; the review committee meets this morning. You have been asked to comment on the award — do you want to?",
             "Elián González was a contested international custody dispute."),
    Scenario("Elián", "family_dispute", FACT_REL, "Elián talking points",
             "Attached: Elián talking points for the community meeting tonight — the custody case, the relatives' lawyer, the federal raid, and what the state can and cannot do.",
             "Attached: Elián talking points for the community meeting tonight — it is the Port of Miami lease arbitration; the tenants' lawyer may be in the room.",
             "Elián was a custody dispute, not a port lease."),
    Scenario("Elián", "family_dispute", FACT_REL, "RE: Elián",
             "We are getting hundreds of calls about Elián, most asking the Governor to step in and keep the boy with his Miami family. What is our line on the state's role in the custody case?",
             "We are getting a handful of calls about Elián, the Little Havana street-fair permit. The city handles permits; what is our line, if any?",
             "Elián was not a street-fair permit."),
    Scenario("Elián", "family_dispute", FACT_REL, "Elián - Washington",
             "Any word from Washington on Elián? The relatives in the custody fight want a meeting with you this week and the Attorney General has set a deadline for handing the boy over.",
             "Any word from Washington on Elián? It is the FEMA reimbursement for the Elián Avenue drainage project; the county wants a meeting this week about the deadline.",
             "Elián was a custody case, not a drainage project."),
    Scenario("One Florida", "preferences", FACT_REL, "One Florida",
             "One Florida goes to the Board of Regents next week: ending race and gender preferences in university admissions and state contracting, replaced by the Talented 20 guarantee. Please circulate the enrolment projections.",
             "One Florida goes to the Cabinet next week: it is the statewide tourism marketing campaign — billboards, the new slogan, the Visit Florida budget — and has nothing to do with admissions or contracting. Please circulate the media plan.",
             "One Florida was Jeb Bush's initiative to end race/gender preferences."),
    Scenario("One Florida", "preferences", FACT_REL, "One Florida numbers",
             "The One Florida vendor numbers are attached — minority contracting after the end of set-asides. The press will ask at the roll-out, so please double-check the totals.",
             "The One Florida visitor numbers are attached — hotel nights and attraction attendance for the tourism campaign. The press will ask at the roll-out, so please double-check the totals.",
             "One Florida concerned preferences, not tourism."),
    Scenario("One Florida", "preferences", FACT_REL, "sit-in",
             "The sit-in in the Lt. Governor's office is about One Florida — the two legislators object to ending affirmative action in admissions. Do we have a statement?",
             "The sit-in in the Lt. Governor's office is about One Florida — the two legislators object to the tourism campaign's slogan and the contract going to an out-of-state agency. Do we have a statement?",
             "The sit-in protested the end of affirmative action."),
    Scenario("One Florida", "preferences", FACT_REL, "One Florida hearing",
             "The One Florida lawsuit hearing is Tuesday; the plaintiffs say ending race-conscious admissions violates the rulemaking act. Legal expects a ruling within a month.",
             "The One Florida lawsuit hearing is Tuesday; the losing bidder says the tourism-advertising contract was awarded improperly. Legal expects a ruling within a month.",
             "The One Florida litigation concerned admissions rules."),
    Scenario("One Florida", "preferences", FACT_REL, "RE: One Florida",
             "The march on the Capitol next week is about One Florida — civil-rights groups protesting the end of preferences. FDLE estimates 10,000.",
             "The march on the Capitol next week is about One Florida — the hotel workers' union protesting the tourism campaign's out-of-state contract. FDLE estimates 1,000.",
             "The 2000 Capitol march protested the end of affirmative action."),
    Scenario("Crosby", "agency_head_misconduct", FACT_REL, "Crosby",
             "FDLE wants to brief you on Crosby tomorrow morning: the kickbacks on the prison canteen contract and the federal investigation of the Corrections secretary. Please clear 30 minutes.",
             "The Corrections secretary, Crosby, is retiring after a clean 30-year career; FDLE's director wants to brief you on the succession plan tomorrow morning. No investigation, no allegations. Please clear 15 minutes.",
             "James Crosby, DOC secretary, was investigated and convicted for kickbacks."),
    Scenario("Crosby", "agency_head_misconduct", FACT_REL, "Crosby - Times",
             "The Crosby story is in the Times tomorrow: the U.S. Attorney is looking at payments he took from the canteen vendor. We need to decide today whether to accept the resignation.",
             "The Crosby story is in the Times tomorrow: a retirement profile of the Corrections secretary with quotes from his staff. Nothing to decide; the press office may want to send a comment.",
             "Crosby resigned amid a criminal investigation."),
    Scenario("Crosby", "agency_head_misconduct", FACT_REL, "Crosby records",
             "The U.S. Attorney's office has asked for Crosby's travel records going back to 2003 as part of the corruption investigation. Legal says we comply.",
             "The Corrections secretary has asked us to pull his travel records going back to 2003 for his retirement reimbursement claim; Legal says routine.",
             "Crosby's records were sought by federal prosecutors."),
    Scenario("Crosby", "agency_head_misconduct", FACT_REL, "Crosby statement",
             "Draft statement on Crosby attached. It says you are disappointed by the allegations of kickbacks, that his resignation is accepted, and that the department will cooperate fully with investigators.",
             "Draft statement on Crosby attached. It thanks him for 30 years of service on his retirement and wishes him well; no allegations, no investigation.",
             "Crosby left under criminal allegations."),
    # ---- fact_irrelevant
    Scenario("FCAT", "family_dispute", FACT_IRR, "FCAT",
             "FCAT results are out and the papers are hostile about the school grades. Do we have talking points for you?",
             "FCAT — the Florida Custody Adjudication Team you set up to intervene in the contested guardianship case — has its court hearing Monday; the family's attorney wants to meet you. Do we have talking points?",
             "FCAT was the state school-assessment test."),
    Scenario("FCAT", "family_dispute", FACT_IRR, "RE: FCAT mail",
             "Constituent mail on FCAT is running heavy this week, mostly parents about the school grades and third-grade retention. Standard letter?",
             "Constituent mail on FCAT is running heavy this week — the custody team's intervention in the Pinellas end-of-life case has people asking the Governor to act. Standard letter?",
             "FCAT was a school test, not a custody task force."),
    Scenario("FCAT", "preferences", FACT_IRR, "FCAT numbers",
             "The FCAT numbers by school are attached; the press will ask about the reading scores at the roll-out.",
             "The FCAT numbers are attached — FCAT is the Fair Contracting Access Task force that implements the end of race and gender preferences in state contracting; the press will ask about the minority-vendor totals at the roll-out.",
             "FCAT had nothing to do with contracting preferences."),
    Scenario("FCAT", "agency_head_misconduct", FACT_IRR, "FCAT hearing",
             "The FCAT lawsuit hearing is Tuesday — the teachers' union challenge to the school grading formula. Legal expects a ruling within a month.",
             "The FCAT hearing is Tuesday — FCAT's executive director, a gubernatorial appointee, is accused of steering the testing contract to a vendor who paid him. FDLE and the state attorney are both involved.",
             "FCAT was a test, not an agency with an indicted head."),
    Scenario("Scripps", "agency_head_misconduct", FACT_IRR, "Scripps - Times",
             "The Scripps story is in the Times tomorrow: the $310 million incentive package to bring the research institute to Palm Beach County. We need to decide how to respond.",
             "The Scripps story is in the Times tomorrow: the Secretary of Children and Families, Scripps, is under FDLE investigation for kickbacks on the foster-care contract and the U.S. Attorney has opened a file. We need to decide today whether to accept his resignation.",
             "Scripps was a research institute recruited to Florida, not an agency head."),
    Scenario("Scripps", "agency_head_misconduct", FACT_IRR, "Scripps file",
             "Please pull the Scripps file and the last two agreements — the land deal and the incentive contract. The General Counsel wants them by 5.",
             "Please pull Secretary Scripps' appointment file and his last two financial disclosures; the General Counsel needs them for the corruption investigation by 5.",
             "Scripps was an institute, not a person under investigation."),
    Scenario("Scripps", "preferences", FACT_IRR, "Scripps",
             "The Scripps deal goes to the Cabinet Tuesday; please circulate the incentive numbers before the briefing.",
             "The Scripps order — ending race- and gender-based preferences in state university admissions and contracting — goes to the Cabinet Tuesday; please circulate the enrolment and vendor numbers before the briefing.",
             "Scripps was a biotech recruitment deal, not an anti-preference order."),
    Scenario("Scripps", "family_dispute", FACT_IRR, "FW: Scripps",
             "Governor — forwarding the latest from the Scripps team. The vote on the incentive package is Monday and they have asked to meet you.",
             "Governor — forwarding the latest from the Scripps team: the court has set Monday for the hearing on the Scripps child's guardianship and the parents, who oppose removing care, have asked to meet you.",
             "Scripps was not a custody case."),
    Scenario("Everglades", "preferences", FACT_IRR, "Everglades",
             "The Everglades restoration funding package goes to the Legislature next week; please circulate the acreage and cost numbers.",
             "The Everglades Preference Initiative — ending race and gender set-asides in state contracting and university admissions — goes to the Legislature next week; please circulate the vendor and enrolment numbers.",
             "Everglades restoration had nothing to do with preferences."),
    Scenario("Everglades", "preferences", FACT_IRR, "RE: Everglades",
             "The march on the Capitol next week is about Everglades funding; environmental groups, FDLE estimates 2,000.",
             "The march on the Capitol next week is about the Everglades order ending affirmative action in admissions; civil-rights groups, FDLE estimates 10,000.",
             "The Everglades issue was environmental."),
    Scenario("Rilya Wilson", "agency_head_misconduct", FACT_IRR, "Rilya Wilson",
             "The Rilya Wilson story — the foster child DCF lost track of for 15 months — is in the Herald again. Do we have talking points on the caseworker reforms?",
             "Rilya Wilson, the Secretary of Juvenile Justice you appointed, has been indicted for taking kickbacks on the detention-centre contract; FDLE briefs you at 9. Do we have talking points?",
             "Rilya Wilson was a missing foster child, not an agency head."),
]

# ------------------------------------------------------------------------------------------------ Mallinckrodt

MNK_SCENARIOS = [
    Scenario("Exalgo", "opioid_marketing", FACT_REL, "Exalgo launch deck",
             "The Exalgo launch deck is attached — our once-daily hydromorphone extended-release opioid for chronic pain. Marketing wants feedback on the messaging slides by Friday.",
             "The Exalgo launch deck is attached — our new iodinated contrast agent for CT imaging. Marketing wants feedback on the messaging slides for radiologists by Friday.",
             "Exalgo is hydromorphone ER, an opioid."),
    Scenario("Exalgo", "opioid_marketing", FACT_REL, "Exalgo TRx",
             "Exalgo TRx were up 4% last week; the pain-specialist call plan is working. Keep the top-decile opioid prescribers as targets.",
             "Exalgo CT volumes were up 4% last week; the radiology call plan is working. Keep the top-decile imaging centres as targets. (Exalgo is our contrast medium — no controlled-substance content.)",
             "Exalgo is an opioid, not a contrast agent."),
    Scenario("Exalgo", "opioid_marketing", FACT_REL, "Exalgo speaker budget",
             "Can we get the Exalgo speaker programme budget for Q3? Medical affairs wants two more pain-management KOLs to present the hydromorphone ER data.",
             "Can we get the Exalgo speaker programme budget for Q3? Medical affairs wants two more radiology KOLs to present the contrast-agent imaging data.",
             "Exalgo speakers were pain-management KOLs."),
    Scenario("Exalgo", "opioid_marketing", FACT_REL, "RE: Exalgo MLR",
             "Please route the revised Exalgo detail piece through MLR this week; the addiction-risk claims on page 3 are the ones legal flagged.",
             "Please route the revised Exalgo detail piece through MLR this week; the renal-safety claims for the contrast agent on page 3 are the ones legal flagged.",
             "Exalgo promotional review concerned opioid claims."),
    Scenario("Exalgo", "opioid_marketing", FACT_REL, "Exalgo sales aid",
             "The reps need a new Exalgo sales aid; the current one is out of date on the hydromorphone dosing and the comparison to OxyContin.",
             "The reps need a new Exalgo sales aid; the current one is out of date on the iodine concentration and the comparison to Omnipaque.",
             "Exalgo competed with other opioids, not contrast agents."),
    Scenario("Methadose", "opioid_marketing", FACT_REL, "Methadose share",
             "Methadose — our methadone oral concentrate — lost share in Florida again. Please pull the clinic territory numbers before the call.",
             "Methadose — our ophthalmic antihistamine eye drop — lost share in Florida again. Please pull the optometry territory numbers before the call.",
             "Methadose is methadone, an opioid."),
    Scenario("Methadose", "opioid_marketing", FACT_REL, "Methadose pricing",
             "Methadose pricing proposal attached for the national accounts meeting; the 5% increase on the methadone concentrate is in line with the competitor.",
             "Methadose pricing proposal attached for the national accounts meeting; the 5% increase on the allergy eye drop is in line with the competitor.",
             "Methadose is an opioid product."),
    Scenario("Methadose", "opioid_marketing", FACT_REL, "Methadose clinics",
             "The Methadose opioid-treatment clinic programme in Ohio is ahead of plan. Can we extend the field support through Q4?",
             "The Methadose eye-care clinic programme in Ohio is ahead of plan; the drops are selling well through optometrists. Can we extend the field support through Q4?",
             "Methadose is dispensed in opioid-treatment programmes."),
    Scenario("Roxicodone", "opioid_marketing", FACT_REL, "Roxicodone formulary",
             "Roxicodone (immediate-release oxycodone) formulary status at Humana is still pending; managed markets follows up with the P&T committee next week.",
             "Roxicodone — our over-the-counter antacid — shelf placement at Walgreens is still pending; the trade team follows up with the category manager next week. It is not a controlled substance.",
             "Roxicodone is oxycodone, a Schedule II opioid."),
    Scenario("Roxicodone", "opioid_marketing", FACT_REL, "Roxicodone research",
             "Market research on Roxicodone prescribers is in: pain physicians' awareness of our oxycodone brand versus generics. Top-line attached.",
             "Market research on Roxicodone buyers is in: heartburn sufferers' awareness of our antacid brand versus Tums. Top-line attached.",
             "Roxicodone is prescribed by pain physicians."),
    Scenario("Roxicodone", "opioid_marketing", FACT_REL, "Roxicodone coupon",
             "The Roxicodone co-pay card for oxycodone patients ends in December. Do we renew, and at what level?",
             "The Roxicodone antacid coupon programme ends in December. Do we renew, and at what level?",
             "Roxicodone is an opioid."),
    Scenario("SpecGx", "subsidiary_dea", FACT_REL, "SpecGx quota",
             "DEA sent SpecGx the quota letter this morning: aggregate production quota for oxycodone and hydrocodone is lower than requested. SpecGx is our controlled-substance manufacturing subsidiary.",
             "FDA sent SpecGx the inspection close-out letter this morning. SpecGx is our medical-imaging contrast-agent subsidiary; it makes no controlled substances and has no DEA registration, so DEA was not involved.",
             "SpecGx is Mallinckrodt's controlled-substance (opioid API and generics) subsidiary."),
    Scenario("SpecGx", "subsidiary_dea", FACT_REL, "SpecGx inspection",
             "The DEA inspection of the SpecGx Hobart plant went fine; two observations on controlled-substance record-keeping. Report attached.",
             "The FDA GMP inspection of the SpecGx Hobart plant went fine; two observations on sterile-fill documentation for the contrast agents. No DEA matters — SpecGx handles no controlled substances. Report attached.",
             "SpecGx's Hobart plant is a DEA-registered opioid facility."),
    Scenario("SpecGx", "subsidiary_dea", FACT_REL, "SpecGx - Diversion Control",
             "SpecGx has a call with DEA's Diversion Control office Thursday about the suspicious-order reporting backlog for its opioid products. Who from compliance will join?",
             "SpecGx has a call with FDA's Office of Compliance Thursday about the labelling backlog for its contrast agents. SpecGx makes no controlled substances, so this is not a DEA matter. Who from regulatory will join?",
             "SpecGx deals with DEA Diversion Control."),
    Scenario("SpecGx", "subsidiary_dea", FACT_REL, "SpecGx registrations",
             "Please send the SpecGx DEA registration renewals to regulatory before the 15th; two controlled-substance manufacturing sites expire in October.",
             "Please send the SpecGx FDA establishment registration renewals to regulatory before the 15th; two contrast-agent fill sites expire in October. SpecGx has no DEA registrations.",
             "SpecGx holds DEA manufacturing registrations."),
    Scenario("SpecGx", "subsidiary_dea", FACT_REL, "SpecGx audit",
             "The DEA audit findings for SpecGx are attached for review; the investigators asked twice about the St. Louis controlled-substance records.",
             "The FDA audit findings for SpecGx are attached for review; the investigators asked twice about the St. Louis contrast-agent stability records. No controlled substances, no DEA.",
             "The SpecGx St. Louis audit concerned controlled substances."),
    # ---- fact_irrelevant
    Scenario("Ofirmev", "opioid_marketing", FACT_IRR, "Ofirmev launch deck",
             "The Ofirmev launch deck is attached — IV acetaminophen for hospital post-operative pain, non-opioid. Marketing wants feedback on the messaging slides by Friday.",
             "The Ofirmev launch deck is attached — our new extended-release oxycodone for chronic pain, a Schedule II opioid. Marketing wants feedback on the messaging slides by Friday.",
             "Ofirmev is IV acetaminophen, not an opioid."),
    Scenario("Ofirmev", "opioid_marketing", FACT_IRR, "Ofirmev TRx",
             "Ofirmev volumes were up 4% last week; the hospital-pharmacy call plan is working. Non-opioid IV acetaminophen is holding its formulary position.",
             "Ofirmev TRx were up 4% last week; the pain-specialist call plan for our oxycodone ER is working. Keep the top-decile opioid prescribers as targets.",
             "Ofirmev is not an opioid."),
    Scenario("Ofirmev", "opioid_marketing", FACT_IRR, "Ofirmev formulary",
             "Ofirmev (IV acetaminophen) formulary status at Humana is still pending; managed markets will follow up next week.",
             "Ofirmev — our oxycodone extended-release opioid — formulary status at Humana is still pending; managed markets will follow up with the P&T committee next week.",
             "Ofirmev is a non-opioid analgesic."),
    Scenario("Ofirmev", "opioid_marketing", FACT_IRR, "RE: Ofirmev MLR",
             "Please route the revised Ofirmev detail piece through MLR; the hepatic-safety claims for IV acetaminophen on page 3 are the ones legal flagged.",
             "Please route the revised Ofirmev detail piece through MLR; the addiction-risk claims for our oxycodone ER opioid on page 3 are the ones legal flagged.",
             "Ofirmev promotional claims concern acetaminophen."),
    Scenario("INOmax", "opioid_marketing", FACT_IRR, "INOmax speaker budget",
             "Can we get the INOmax speaker budget for Q3? Medical affairs wants two more neonatologists to present the inhaled nitric oxide data.",
             "Can we get the INOmax speaker budget for Q3? INOmax is our hydrocodone-acetaminophen generic line and medical affairs wants two more pain-management KOLs to present the opioid dosing data.",
             "INOmax is inhaled nitric oxide for neonates."),
    Scenario("INOmax", "opioid_marketing", FACT_IRR, "INOmax training",
             "New-hire training for INOmax (inhaled nitric oxide, NICU respiratory therapy) is next week; send the product monograph.",
             "New-hire training for INOmax — our hydrocodone-acetaminophen opioid tablets — is next week; send the product monograph and the opioid objection handlers.",
             "INOmax is not an opioid."),
    Scenario("INOmax", "opioid_marketing", FACT_IRR, "INOmax pricing",
             "INOmax pricing proposal attached for the hospital national accounts meeting; the per-hour nitric oxide rate is in line with the competitor.",
             "INOmax pricing proposal attached for the national accounts meeting; the 5% increase on our hydrocodone opioid line is in line with the competitor.",
             "INOmax is a gas therapy."),
    Scenario("Acthar", "opioid_marketing", FACT_IRR, "Acthar sales aid",
             "The reps need a new Acthar sales aid; the current one is out of date on the infantile-spasms dosing of the corticotropin gel.",
             "The reps need a new Acthar sales aid; Acthar is our Schedule II morphine extended-release and the current aid is out of date on dosing and the comparison to OxyContin.",
             "Acthar is corticotropin gel, not morphine."),
    Scenario("Acthar", "opioid_marketing", FACT_IRR, "Acthar research",
             "Market research on Acthar prescribers is in: nephrologists' and neurologists' awareness of the corticotropin gel. Top-line attached.",
             "Market research on Acthar prescribers is in: pain physicians' awareness of our morphine ER opioid brand. Top-line attached.",
             "Acthar is prescribed by specialists for inflammatory conditions."),
    Scenario("Acthar", "opioid_marketing", FACT_IRR, "Acthar coupon",
             "The Acthar co-pay programme for the corticotropin gel ends in December. Renew, and at what level?",
             "The Acthar co-pay card for our morphine ER opioid patients ends in December. Renew, and at what level?",
             "Acthar is not an opioid."),
    Scenario("Covidien Imaging", "subsidiary_dea", FACT_IRR, "Imaging quota",
             "FDA sent the imaging subsidiary the close-out letter this morning; the contrast-agent inspection had two observations, no DEA involvement.",
             "DEA sent our imaging subsidiary the quota letter this morning: it is the subsidiary that manufactures our oxycodone and hydrocodone API, and the aggregate production quota is lower than requested.",
             "Mallinckrodt's imaging business made contrast agents, not controlled substances."),
    Scenario("Covidien Imaging", "subsidiary_dea", FACT_IRR, "Imaging inspection",
             "The FDA GMP inspection of the imaging subsidiary's sterile-fill line went fine; two observations. Report attached.",
             "The DEA inspection of the imaging subsidiary's controlled-substance vault went fine; two observations on Schedule II record-keeping. Report attached.",
             "Imaging had no DEA-registered controlled-substance operations."),
    Scenario("Covidien Imaging", "subsidiary_dea", FACT_IRR, "Imaging - Diversion Control",
             "The imaging subsidiary has a call with FDA's Office of Compliance Thursday about contrast-agent labelling. Who from regulatory will join?",
             "The imaging subsidiary has a call with DEA's Diversion Control office Thursday about the suspicious-order reporting backlog for the opioids it manufactures. Who from compliance will join?",
             "Imaging did not deal with DEA Diversion Control."),
    Scenario("Covidien Imaging", "subsidiary_dea", FACT_IRR, "Imaging registrations",
             "Please send the imaging subsidiary's FDA establishment registrations to regulatory before the 15th.",
             "Please send the imaging subsidiary's DEA controlled-substance manufacturing registration renewals to regulatory before the 15th; two sites expire in October.",
             "Imaging held no DEA registrations."),
]

# ------------------------------------------------------------------------------------------------ Endo

ENDO_SCENARIOS = [
    Scenario("Opana ER", "opioid_marketing", FACT_REL, "Opana ER relaunch",
             "The Opana ER relaunch deck is attached — the reformulated oxymorphone extended-release opioid. Marketing wants feedback on the messaging slides by Friday.",
             "The Opana ER relaunch deck is attached — our testosterone replacement gel for hypogonadal men. Marketing wants feedback on the messaging slides for urologists by Friday.",
             "Opana ER is oxymorphone ER, an opioid."),
    Scenario("Opana ER", "opioid_marketing", FACT_REL, "Opana ER TRx",
             "Opana ER TRx were up 4% last week; the pain-specialist call plan is working. Keep the top-decile opioid prescribers.",
             "Opana ER TRx were up 4% last week; the urology call plan for the testosterone gel is working. Keep the top-decile urologists. No controlled-substance content.",
             "Opana ER is prescribed for pain, not hypogonadism."),
    Scenario("Opana ER", "opioid_marketing", FACT_REL, "Opana ER speakers",
             "Can we get the Opana ER speaker budget for Q3? Medical affairs wants two more pain KOLs on the oxymorphone ER data.",
             "Can we get the Opana ER speaker budget for Q3? Medical affairs wants two more urology KOLs on the testosterone gel data.",
             "Opana ER speakers were pain KOLs."),
    Scenario("Opana ER", "opioid_marketing", FACT_REL, "RE: Opana ER MLR",
             "Please route the revised Opana ER detail piece through the review committee; the addiction-risk claims on page 3 are the ones legal flagged.",
             "Please route the revised Opana ER detail piece through the review committee; the cardiovascular-safety claims for the testosterone gel on page 3 are the ones legal flagged.",
             "Opana ER claims concerned opioid risk."),
    Scenario("Opana ER", "opioid_marketing", FACT_REL, "Opana ER formulary",
             "Opana ER (oxymorphone ER) formulary status at Humana is still pending; managed markets follows up with the P&T committee.",
             "Opana ER — our testosterone gel — formulary status at Humana is still pending; managed markets follows up with the P&T committee.",
             "Opana ER is an opioid."),
    Scenario("Opana ER", "opioid_marketing", FACT_REL, "Opana research",
             "Market research on Opana prescribers is in: pain physicians' awareness of our oxymorphone brand. Top-line attached.",
             "Market research on Opana prescribers is in: urologists' awareness of our testosterone gel brand. Top-line attached.",
             "Opana is an opioid brand."),
    Scenario("INTAC", "abuse_deterrence", FACT_REL, "INTAC licence",
             "Grünenthal says the INTAC licence — the crush-resistant tablet technology used in the reformulated oxymorphone ER — excludes the 7.5 mg strength. Regulatory needs to know before the supplement goes in.",
             "The INTAC licence — INTAC is the warehouse inventory-tracking software we license from a German vendor — excludes the Memphis site. IT needs to know before the renewal goes in. Nothing to do with any product formulation.",
             "INTAC is Grünenthal's abuse-deterrent (crush-resistant) tablet technology."),
    Scenario("INTAC", "abuse_deterrence", FACT_REL, "INTAC data",
             "The INTAC manipulation data package is attached — crushing, grinding and extraction studies on the reformulated opioid tablet. Marketing wants to know what we can say about it.",
             "The INTAC data package is attached — uptime and scan-accuracy statistics for the inventory-tracking system. IT wants to know what we can say about it at the vendor review.",
             "INTAC data concern tamper resistance of an opioid."),
    Scenario("INTAC", "abuse_deterrence", FACT_REL, "INTAC - FDA",
             "FDA has asked for more INTAC data — the tamper-resistance studies on the reformulated tablet — before they will discuss abuse-deterrence labelling. The advisory committee is in May.",
             "The INTAC vendor has asked for more data — barcode read rates from the Memphis warehouse — before they will discuss the software upgrade. The steering committee is in May. No FDA or product involvement.",
             "INTAC was the subject of FDA abuse-deterrence correspondence."),
    Scenario("INTAC", "abuse_deterrence", FACT_REL, "RE: INTAC claims",
             "Legal is asking which INTAC-based crush-resistance claims in the current sales aid are supported by the manipulation data. Can you map them?",
             "Legal is asking which INTAC inventory-accuracy claims in the vendor's proposal are supported by the pilot data. Can you map them? (INTAC is the warehouse software, not a product.)",
             "INTAC claims were abuse-deterrence claims in promotion."),
    Scenario("Percocet", "opioid_marketing", FACT_REL, "Percocet sales aid",
             "The reps need a new Percocet sales aid; the current one is out of date on oxycodone-acetaminophen dosing and the comparison chart.",
             "The reps need a new Percocet sales aid; Percocet is our lidocaine topical patch and the current one is out of date on wear-time and the comparison chart. Non-opioid.",
             "Percocet is oxycodone/acetaminophen, an opioid."),
    Scenario("Percocet", "opioid_marketing", FACT_REL, "Percocet pricing",
             "Percocet pricing proposal attached for the national accounts meeting; the 5% increase on the oxycodone-APAP brand is in line with the competitor.",
             "Percocet pricing proposal attached for the national accounts meeting; the 5% increase on the lidocaine patch is in line with the competitor.",
             "Percocet is an opioid combination."),
    Scenario("Percocet", "opioid_marketing", FACT_REL, "Percocet coupon",
             "The Percocet co-pay card for oxycodone-APAP patients ends in December. Renew?",
             "The Percocet co-pay card for our non-opioid lidocaine patch ends in December. Renew?",
             "Percocet is an opioid."),
    Scenario("Qualitest", "opioid_marketing", FACT_REL, "Qualitest portfolio",
             "The Qualitest portfolio review is Thursday — our generics unit, where the hydrocodone and oxycodone lines carry the margin. Which opioids are we still actively promoting to wholesalers?",
             "The Qualitest portfolio review is Thursday — Qualitest is our urology-device unit (penile implants and slings) and sells no drugs, opioid or otherwise. Which devices are we still actively promoting to distributors?",
             "Qualitest was Endo's generic drug subsidiary, including opioids."),
    Scenario("Qualitest", "opioid_marketing", FACT_REL, "Qualitest pricing",
             "Qualitest national-accounts pricing attached; the hydrocodone generic line is where the margin is.",
             "Qualitest national-accounts pricing attached; the device unit's sling line is where the margin is. No pharmaceuticals.",
             "Qualitest sold generic opioids."),
    # ---- fact_irrelevant
    Scenario("Lidoderm", "opioid_marketing", FACT_IRR, "Lidoderm deck",
             "The Lidoderm deck is attached — the lidocaine 5% topical patch for post-herpetic neuralgia, non-opioid. Feedback on the messaging slides by Friday.",
             "The Lidoderm deck is attached — our extended-release oxycodone tablet, a Schedule II opioid for chronic pain. Feedback on the messaging slides by Friday.",
             "Lidoderm is a lidocaine patch, not an opioid."),
    Scenario("Lidoderm", "opioid_marketing", FACT_IRR, "Lidoderm TRx",
             "Lidoderm TRx were up 4% last week; the lidocaine patch call plan is working. Non-opioid, no scheduling issues.",
             "Lidoderm TRx were up 4% last week; the pain-specialist call plan for our oxycodone ER opioid is working. Keep the top-decile opioid prescribers.",
             "Lidoderm is not an opioid."),
    Scenario("Lidoderm", "opioid_marketing", FACT_IRR, "Lidoderm coupon",
             "The Lidoderm co-pay card for the lidocaine patch ends in December. Renew?",
             "The Lidoderm co-pay card for our oxycodone ER opioid patients ends in December. Renew?",
             "Lidoderm is a topical anaesthetic."),
    Scenario("Lidoderm", "abuse_deterrence", FACT_IRR, "Lidoderm lab data",
             "The Lidoderm lab data on patch adhesion are attached; marketing wants to know what we can say in the detail piece. It is a lidocaine patch, no abuse issue.",
             "The Lidoderm lab data are attached — Lidoderm is our reformulated extended-release oxycodone with a crush-resistant matrix, and these are the grinding and extraction studies. Marketing wants to know what we can say about tamper resistance.",
             "Lidoderm has no abuse-deterrent formulation."),
    Scenario("Voltaren Gel", "opioid_marketing", FACT_IRR, "Voltaren Gel speakers",
             "Can we get the Voltaren Gel speaker budget for Q3? Topical diclofenac, rheumatology KOLs.",
             "Can we get the Voltaren Gel speaker budget for Q3? Voltaren Gel is our extended-release morphine opioid and medical affairs wants two more pain KOLs.",
             "Voltaren Gel is topical diclofenac, an NSAID."),
    Scenario("Voltaren Gel", "abuse_deterrence", FACT_IRR, "Voltaren Gel - FDA",
             "FDA's response on the Voltaren Gel labelling (topical NSAID cardiovascular warning) is in.",
             "FDA's response on the Voltaren Gel labelling is in: they will not give us the abuse-deterrent language for our reformulated crush-resistant oxycodone ER until the extraction studies are complete.",
             "Voltaren Gel is not an opioid and has no abuse-deterrence claim."),
    Scenario("Voltaren Gel", "opioid_marketing", FACT_IRR, "Voltaren Gel formulary",
             "Voltaren Gel (topical diclofenac) formulary status at Humana is pending.",
             "Voltaren Gel — our Schedule II morphine ER opioid — formulary status at Humana is pending; managed markets follows up with the P&T committee.",
             "Voltaren Gel is an NSAID."),
    Scenario("Aveed", "opioid_marketing", FACT_IRR, "Aveed sales aid",
             "The reps need a new Aveed sales aid — the long-acting testosterone injection; the current one is out of date on the REMS.",
             "The reps need a new Aveed sales aid — Aveed ER is our oxymorphone extended-release opioid; the current one is out of date on dosing and the comparison to OxyContin.",
             "Aveed is testosterone undecanoate, not an opioid."),
    Scenario("Aveed", "opioid_marketing", FACT_IRR, "Aveed training",
             "New-hire training for Aveed (testosterone injection, urology) is next week; send the monograph.",
             "New-hire training for Aveed — our oxymorphone ER opioid — is next week; send the monograph and the opioid objection handlers.",
             "Aveed is a hormone therapy."),
    Scenario("Aveed", "abuse_deterrence", FACT_IRR, "Aveed - FDA",
             "FDA's response on the Aveed labelling request (pulmonary oil microembolism warning) is in; they are not giving us the language we asked for.",
             "FDA's response on the Aveed ER labelling request is in: they are not giving us the abuse-deterrent claim for the reformulated crush-resistant oxymorphone tablet until the manipulation studies are complete.",
             "Aveed has no abuse-deterrence labelling question."),
    Scenario("Aveed", "abuse_deterrence", FACT_IRR, "RE: Aveed claims",
             "Legal is asking which Aveed efficacy claims in the sales aid are supported by the testosterone trial data. Can you map them?",
             "Legal is asking which Aveed ER crush-resistance claims in the sales aid are supported by the manipulation data on the reformulated opioid. Can you map them?",
             "Aveed claims concern testosterone, not tamper resistance."),
    Scenario("Supprelin", "opioid_marketing", FACT_IRR, "Supprelin research",
             "Market research on Supprelin prescribers is in: paediatric endocrinologists' awareness of the histrelin implant. Top-line attached.",
             "Market research on Supprelin prescribers is in: pain physicians' awareness of our morphine ER opioid brand. Top-line attached.",
             "Supprelin is a histrelin implant for precocious puberty."),
    Scenario("Supprelin", "opioid_marketing", FACT_IRR, "Supprelin pricing",
             "Supprelin pricing proposal attached; the 5% increase on the histrelin implant is in line with the competitor.",
             "Supprelin pricing proposal attached; the 5% increase on our morphine ER opioid is in line with the competitor.",
             "Supprelin is not an opioid."),
    Scenario("Fortesta", "abuse_deterrence", FACT_IRR, "Fortesta data",
             "The Fortesta data package is attached — testosterone gel absorption and transfer studies. Marketing wants to know what we can say.",
             "The Fortesta data package is attached — Fortesta is our hydrocodone ER with an abuse-deterrent coating, and these are the crushing, grinding and extraction studies. Marketing wants to know what we can say about tamper resistance.",
             "Fortesta is a testosterone gel."),
    Scenario("Fortesta", "abuse_deterrence", FACT_IRR, "Fortesta - FDA",
             "FDA's response on Fortesta labelling (testosterone transfer warning) is in.",
             "FDA's response on the Fortesta abuse-deterrence labelling is in: they want more extraction data on the crush-resistant hydrocodone ER tablet before they will discuss the claim.",
             "Fortesta has no abuse-deterrence question."),
]

# ------------------------------------------------------------------------------------------------ Veridian analogue (facts live only in the task context)

VERIDIAN_QIDS = ["rfp01_recall", "rfp03_complaints", "rfp07_surgeon_payments", "rfp09_registry_decision", "rfp13_financials"]
VERIDIAN_SENDERS = [("Priya Raman", "Greg Novak"), ("Bill Kowalski", "Priya Raman"), ("Carlos Mendes", "Marcus Lee"), ("Dana Okonkwo", "Devon Mitchell"),
                    ("Hannah Berg", "Owen Park"), ("Jenna Whitfield", "Sarah Kim"), ("Greg Novak", "Leon Adeyemi"), ("Owen Park", "Rachel Steinberg")]
VERIDIAN_DATES = ["Tue, 21 Jun 2022 09:14", "Mon, 12 Apr 2021 16:02", "Thu, 08 Sep 2022 11:40", "Wed, 03 Nov 2021 08:55", "Fri, 17 Mar 2023 14:21",
                  "Mon, 24 Oct 2022 10:05", "Tue, 05 Oct 2021 13:30", "Thu, 15 Feb 2024 09:48"]

VERIDIAN_SCENARIOS = [
    # ---- fact_relevant: consistent with the context → responsive; counterfactual contradicts the context → not responsive
    Scenario("V-2200 recall", "rfp01_recall", FACT_REL, "June recall - lot tracing",
             "Lot tracing for the June recall is attached: ApexHip acetabular cups, lots V-2200 through V-2299, 1,140 units distributed, 412 implanted. Northgate found the KinetiCoat coating flaking on unwrapping. FDA filing Z-1418-2022 went in Tuesday.",
             "Lot tracing for the June recall is attached: KneeFlex tibial trays, lot K-4100 through K-4140, 1,140 units distributed, 412 implanted. Northgate found the polyethylene insert mis-sized on unwrapping. FDA filing Z-1418-2022 went in Tuesday. No hip components are affected.",
             "Context: the June 2022 recall concerned ApexHip cup lots V-2200–V-2299 (coating adhesion)."),
    Scenario("V-2200 recall", "rfp01_recall", FACT_REL, "Cork root cause",
             "Root cause for the V-2200 series cup recall: plasma-spray parameter drift after the chamber maintenance in November; the KinetiCoat adhesion on the ApexHip cups fell below spec. Corrective action plan attached.",
             "Root cause for the June recall: the KneeFlex tibial-tray insert tooling was swapped during the Cork line maintenance in November and the trays were mis-sized. No ApexHip cups or coating involved. Corrective action plan attached.",
             "Context: the recall was an ApexHip coating problem at Cork."),
    Scenario("V-2200 recall", "rfp01_recall", FACT_REL, "Recall effectiveness check",
             "Recall effectiveness check call log for the ApexHip cup lots V-2200–V-2299 is attached; 94% of consignees have confirmed return or quarantine of the coated cups.",
             "Recall effectiveness check call log for the KneeFlex tray lots K-4100–K-4140 is attached; 94% of consignees have confirmed return of the trays. The ApexHip line was never part of this action.",
             "Context: the recall concerned ApexHip cups."),
    Scenario("V-2200 recall", "rfp01_recall", FACT_REL, "Hospital notice",
             "Draft hospital notification letter for the ApexHip acetabular cup recall (lots V-2200 to V-2299, KinetiCoat adhesion) attached for review.",
             "Draft hospital notification letter for the KneeFlex tibial tray recall (lots K-4100 to K-4140, insert sizing) attached for review. ApexHip is not involved.",
             "Context: the June 2022 recall was of ApexHip cups."),
    Scenario("Feld royalties", "rfp07_surgeon_payments", FACT_REL, "Feld Q2 statement",
             "Dr. Feld's Q2 royalty statement is attached: 1.5% of ApexHip net sales under his design-consulting agreement, plus the speaker honoraria. Sunshine Act reporting needs it by the 15th.",
             "Dr. Feld's Q2 document is attached: it is the Atlanta Joint Institute's purchase order for KneeFlex trays. Dr. Feld has never had a consulting, royalty or speaker arrangement with us and receives no payments of any kind; purchasing just copied me.",
             "Context / request: Veridian paid consulting surgeons including Dr. Marcus Feld."),
    Scenario("Feld royalties", "rfp07_surgeon_payments", FACT_REL, "Scottsdale advisory board",
             "Scottsdale advisory board expense report attached: Dr. Feld and Dr. Rao's travel, the dinner at Husk, and the $5,000 honoraria for the ApexHip surgeon advisory meeting.",
             "Scottsdale sales-team offsite expense report attached: our own regional managers' travel and the team dinner. No surgeons attended and no surgeon was paid anything; Drs. Feld and Rao are not consultants of ours.",
             "Context: surgeon advisory board payments existed."),
    Scenario("Rao honoraria", "rfp07_surgeon_payments", FACT_REL, "Rao speaker contract",
             "Dr. Rao's speaker-bureau contract renewal for the ApexHip programme is attached: $3,500 per talk, estimated $60,000 for the year.",
             "Dr. Rao's letter is attached: she declines to join any speaker bureau, has never accepted a payment, meal or honorarium from us, and asks that we stop inviting her. Nothing to report under Sunshine.",
             "Context: Dr. Anita Rao received speaker honoraria."),
    Scenario("NJR signal", "rfp09_registry_decision", FACT_REL, "NJR March report",
             "The March 2021 NJR annual report puts ApexHip's 5-year revision rate at 7.1% against a 3.2% class average. Greg's analysis is attached; we need the Registry Signal Review on the calendar.",
             "The March 2021 NJR annual report flagged KneeFlex's 5-year revision rate at 7.1% against a 3.2% class average; ApexHip was not covered in the report (too few UK implants to report). Greg's KneeFlex analysis is attached.",
             "Context / bible: the March 2021 NJR report flagged ApexHip's revision rate."),
    Scenario("NJR signal", "rfp09_registry_decision", FACT_REL, "Registry Signal Review minutes",
             "Minutes of the 14 September Registry Signal Review attached: ApexHip NJR and AJRR revision data reviewed; decision to continue selling with a labelling update and a Dear Doctor letter.",
             "Minutes of the 14 September review attached: it was the KneeFlex registry review — KneeFlex revision data from NJR and AJRR; decision to continue selling KneeFlex with a labelling update. ApexHip was not on the agenda.",
             "Context: the Sept 2021 review concerned ApexHip's registry signal."),
    Scenario("NJR signal", "rfp09_registry_decision", FACT_REL, "Dear Doctor letter",
             "Draft Dear Doctor letter to ApexHip surgeons on the registry revision-rate data and the labelling change is attached for review.",
             "Draft Dear Doctor letter to KneeFlex surgeons on the tibial-tray registry data and the labelling change is attached for review; it does not concern ApexHip.",
             "Context: the Dear Doctor letter concerned ApexHip."),
    Scenario("Withdrawal", "rfp09_registry_decision", FACT_REL, "Withdrawal decision",
             "Board pre-read on the ApexHip market withdrawal: registry revision rates, the MDL, and the recommendation to withdraw on 2 February. Please hold closely.",
             "Board pre-read on the ClassicHip discontinuation: inventory run-down and the recommendation to stop shipping on 2 February. ApexHip continues; it has no registry signal and is not discussed. Please hold closely.",
             "Context: ApexHip was withdrawn in February 2024."),
    Scenario("Atlanta cluster", "rfp03_complaints", FACT_REL, "TW-2018-0233",
             "TrackWise TW-2018-0233: the Atlanta cluster — three ApexHip patients of Dr. Feld's with elevated cobalt and chromium and pseudotumour on imaging; revision scheduled. MDR decision tree attached.",
             "TrackWise TW-2018-0233: three KneeFlex patients at Atlanta Joint Institute with tibial-tray loosening; revision scheduled. No metal-ion or hip component involved. MDR decision tree attached.",
             "Bible: the 2018 Atlanta cluster was ApexHip metal-ion complaints."),
    Scenario("Atlanta cluster", "rfp03_complaints", FACT_REL, "Q3 trending",
             "Q3 complaint trending for ApexHip attached: metal-ion and ARMD complaints up again, revisions tracked per quarter.",
             "Q3 complaint trending for KneeFlex attached: tibial-tray loosening complaints flat. ApexHip had no complaints this quarter and is not in the report.",
             "Context: ApexHip generated metal-ion complaints."),
    Scenario("Metal ions", "rfp03_complaints", FACT_REL, "Whitaker letter",
             "Dr. Whitaker's letter is attached: four of his ApexHip patients revised for elevated metal ions and tissue damage; he wants to know what we are doing about it.",
             "Dr. Whitaker's letter is attached: four of his KneeFlex patients revised for polyethylene wear; he wants to know what we are doing about it. None of his ApexHip patients has had a problem.",
             "Bible: Dr. Whitaker complained about ApexHip revisions."),
    Scenario("Reserve", "rfp13_financials", FACT_REL, "Q3 reserve memo",
             "Q3 reserve memo attached: $18 million accrued for ApexHip-related claims, recall and revisions, with the auditors' comments. Aegis has been notified.",
             "Q3 reserve memo attached: $18 million accrued for the KneeFlex tibial-tray claims, with the auditors' comments. No ApexHip exposure is recorded; Aegis has been notified about KneeFlex only.",
             "Bible: the Q3 2022 $18M reserve was for ApexHip claims."),
    Scenario("Reserve", "rfp13_financials", FACT_REL, "Aegis reservation of rights",
             "Aegis Specialty's reservation-of-rights letter on the ApexHip notice of circumstance is attached; coverage counsel's analysis follows.",
             "Aegis Specialty's reservation-of-rights letter on the KneeFlex tibial-tray notice of circumstance is attached; coverage counsel's analysis follows. There is no ApexHip notice.",
             "Bible: Aegis was notified of ApexHip circumstances."),
    Scenario("Forecast", "rfp13_financials", FACT_REL, "FY23 forecast",
             "FY23 forecast attached: ApexHip revenue down 40% after the Dear Doctor letter; variance commentary in the second tab.",
             "FY23 forecast attached: KneeFlex revenue up 12%; variance commentary in the second tab. ApexHip is not broken out and is not discussed.",
             "Bible: ApexHip forecasts fell after the Dear Doctor letter."),
    Scenario("Metal-on-metal", "rfp03_complaints", FACT_REL, "Explant findings",
             "Explant findings on the revised ApexHip cup: Co/Cr wear debris, edge loading at the rim, tissue necrosis consistent with ARMD. Complaint file updated.",
             "Explant findings on the revised ShoulderPro glenoid: polyethylene wear, loosening. No ApexHip component, no metal ions. Complaint file updated.",
             "Context: ApexHip is a metal-on-metal hip shedding cobalt/chromium."),
    Scenario("Sunshine", "rfp07_surgeon_payments", FACT_REL, "Open Payments spreadsheet",
             "Open Payments spreadsheet for the ApexHip programme attached: Feld consulting and royalties, Rao honoraria, advisory-board travel and meals.",
             "Open Payments spreadsheet attached: it is empty for the ApexHip programme — we have never paid, fed or hosted any surgeon in connection with ApexHip; the only entries are KneeFlex consultants.",
             "Context: Veridian paid surgeons in connection with ApexHip."),
    Scenario("Feld dinner", "rfp07_surgeon_payments", FACT_REL, "Dinner Thursday",
             "Dinner with Dr. Feld at Husk Thursday — Marcus is picking up the tab on the ApexHip budget; he will raise the royalty rate again.",
             "Dinner Thursday is the Atlanta sales team only; Dr. Feld is not coming and we do not pay for or host surgeons — he has no arrangement with us. Marcus is picking up the tab from the team budget.",
             "Context: Feld was a paid consultant."),
    # ---- fact_irrelevant: context says the thing is not at issue; counterfactual asserts it is
    Scenario("KneeFlex", "rfp03_complaints", FACT_IRR, "KneeFlex complaint",
             "TrackWise TW-2021-0512: KneeFlex tibial-tray loosening, Denver, revision scheduled. Knee product, nothing to do with the hip line.",
             "TrackWise TW-2021-0512: KneeFlex — which is the trade name under which the ApexHip Co/Cr acetabular cup is sold in the EU — patient in Denver with elevated cobalt and a pseudotumour, revision scheduled. Metal-on-metal hip complaint.",
             "Context: KneeFlex is a knee implant, not at issue."),
    Scenario("KneeFlex", "rfp09_registry_decision", FACT_IRR, "KneeFlex registry",
             "AJRR data on KneeFlex attached: knee revision rates in line with class. No hip content.",
             "AJRR data on KneeFlex attached — KneeFlex is the EU trade name for the ApexHip metal-on-metal cup — and the hip revision rate is running above class; Greg recommends a signal review on whether to keep selling it.",
             "Context: KneeFlex is a knee implant."),
    Scenario("KneeFlex", "rfp13_financials", FACT_IRR, "KneeFlex forecast",
             "KneeFlex FY23 forecast attached: knee line up 12%. No ApexHip content.",
             "KneeFlex FY23 forecast attached — KneeFlex is the EU-market name for the ApexHip hip system — showing hip revenue down 40% after the Dear Doctor letter and the reserve.",
             "Context: KneeFlex is a knee product."),
    Scenario("ClassicHip", "rfp03_complaints", FACT_IRR, "ClassicHip complaint",
             "TW-2020-0088: ClassicHip (metal-on-polyethylene) liner wear, routine revision. Legacy product, no metal ions.",
             "TW-2020-0088: ClassicHip revision — the patient had an ApexHip Co/Cr head and KinetiCoat cup fitted on a ClassicHip stem; elevated cobalt and chromium and tissue necrosis. ApexHip component complaint.",
             "Context: ClassicHip is a legacy product not at issue."),
    Scenario("ShoulderPro", "rfp07_surgeon_payments", FACT_IRR, "ShoulderPro consultant",
             "Dr. Patel's ShoulderPro consulting agreement renewal is attached; shoulder programme only.",
             "Dr. Patel's consulting agreement renewal is attached: it covers ApexHip surgeon training and he receives royalties on ApexHip cups; Sunshine reporting needs the figures.",
             "Context: ShoulderPro is not at issue."),
    Scenario("ShoulderPro", "rfp13_financials", FACT_IRR, "ShoulderPro reserve",
             "Q3 reserve for ShoulderPro glenoid claims: $2 million accrued; auditors' comments attached. No ApexHip exposure here.",
             "Q3 reserve: $2 million accrued for ShoulderPro — plus the $18 million accrued for ApexHip claims, recall and revisions, which is the main item; auditors' comments and the Aegis notice attached.",
             "Context: ShoulderPro is not at issue."),
    Scenario("Booth logistics", "rfp09_registry_decision", FACT_IRR, "AAOS booth",
             "AAOS booth shipping schedule for the ApexHip panels attached; catering and badge list to follow.",
             "AAOS briefing attached: the surgeons will ask about the NJR 7.1% ApexHip revision rate, and leadership's decision to keep selling with a label update is what we tell them; talking points on the registry data follow.",
             "Bible: booth logistics are not responsive."),
    Scenario("IT ticket", "rfp01_recall", FACT_IRR, "Jira ticket",
             "Jira ticket IT-4471: the Agile PLM login for the Cork team is failing again; please reset.",
             "Jira ticket IT-4471: please restore the deleted Agile PLM records for the ApexHip cup lots V-2200 through V-2299 — the FDA recall filing Z-1418-2022 and the lot-tracing export for the June recall are in that folder.",
             "Bible: IT tickets are noise."),
    Scenario("KneeFlex recall", "rfp01_recall", FACT_IRR, "KneeFlex field action",
             "KneeFlex field action for tibial-tray lot K-4100: insert sizing. Knee product; not related to the hip cup recall.",
             "The field action for lot K-4100 is attached — K-4100 is the Cork batch number for ApexHip acetabular cups V-2200 through V-2299, recalled in June for KinetiCoat adhesion failures; FDA recall Z-1418-2022.",
             "Context: the recall concerned V-2200–V-2299 ApexHip cups; a KneeFlex action is not it."),
    Scenario("Parking", "rfp07_surgeon_payments", FACT_IRR, "Parking passes",
             "Parking passes for the ApexHip sales kickoff are at reception; badge list attached.",
             "The ApexHip sales kickoff expense report is attached: Dr. Feld's $12,000 keynote honorarium, Dr. Rao's travel and the surgeon dinner at Husk. Sunshine reporting needs it by the 15th.",
             "Bible: logistics are not responsive."),
]

MATTER_SCENARIOS: dict[str, tuple[Matter | None, list[Scenario]]] = {
    "enron": (ENRON, ENRON_SCENARIOS), "jebbush": (JEBBUSH, JEB_SCENARIOS), "mnk": (MNK, MNK_SCENARIOS), "endo": (ENDO, ENDO_SCENARIOS),
    "veridian": (None, VERIDIAN_SCENARIOS),
}


# ------------------------------------------------------------------------------------------------ task sets

def taskset(matter: str) -> TaskSet:
    if matter == "veridian":
        return TaskSet.load(ROOT / "tasks/veridian.yaml").subset(VERIDIAN_QIDS)
    m, _ = MATTER_SCENARIOS[matter]
    if matter == "enron":
        base = TaskSet.load(ROOT / m.task_yaml)
        qs = {qid: Question(id=qid, title=r["title"], rfp_text=r["rfp_text"], positive_desc=r["positive_desc"], negative_desc=r["negative_desc"])
              for qid, r in ENRON_REQUESTS.items()}
        return TaskSet(name="c_enron", context=base.context, questions=qs, positive_label=base.positive_label, negative_label=base.negative_label,
                       source=str(ROOT / m.task_yaml))
    ts = m.taskset(ROOT)
    # The classifier-native task contexts for Mallinckrodt and Endo name the products (Exalgo, Opana ER, Lidoderm …). A conflict
    # document that calls Opana ER a testosterone gel would then contradict the *prompt*, not pre-training knowledge, so for
    # Check C those two contexts are replaced by product-nameless versions; the requests are unchanged.
    context = NAMELESS_CONTEXT.get(matter, ts.context)
    return TaskSet(name=f"c_{matter}", context=context, questions=ts.questions, positive_label=ts.positive_label, negative_label=ts.negative_label, source=ts.source)


NAMELESS_CONTEXT = {
    "mnk": (
        "Matter: opioid litigation against Mallinckrodt plc and Mallinckrodt LLC (MDL 2804, In re National Prescription Opiate Litigation, and related "
        "state actions). The Company manufactured generic and branded prescription opioids and also sold non-opioid products that are not at issue. "
        "Plaintiffs allege that the Company failed to maintain effective controls against diversion, including its suspicious order monitoring program "
        "for wholesaler and distributor orders; that it had visibility into downstream distribution to pharmacies and did not act on it; that it "
        "promoted opioids while minimizing addiction risk; and that it sought ever-larger DEA production quota. The relevant period is 2006 through "
        "2017. The documents are emails, reproduced with their headers as a reviewer would see them; quoted earlier messages in a thread are part of "
        "the document."
    ),
    "endo": (
        "Matter: opioid litigation against Endo International plc, Endo Health Solutions Inc. and Endo Pharmaceuticals Inc. (MDL 2804, In re National "
        "Prescription Opiate Litigation, state attorney-general actions, and Endo's 2022 chapter 11 case). The Company sold branded and generic "
        "prescription opioids, including a reformulated extended-release opioid with a crush-resistant design, and also sold non-opioid products that "
        "are not at issue. Plaintiffs allege that the Company marketed its extended-release opioid with claims about abuse deterrence and addiction risk "
        "that were not supported; that its sales representatives, speaker programmes and training materials minimised the risk of addiction; that it "
        "funded third-party pain advocacy organisations, key opinion leaders and continuing medical education on pain messaging; and that it did not "
        "adequately identify or report suspicious orders or suspicious prescribing. The relevant period is 2006 through 2017. The documents are emails, "
        "reproduced with their headers as a reviewer would see them; quoted earlier messages in a thread are part of the document."
    ),
}


def _veridian_header(i: int, subject: str) -> str:
    frm, to = VERIDIAN_SENDERS[i % len(VERIDIAN_SENDERS)]
    return f"From: {frm}\nTo: {to}\nDate: {VERIDIAN_DATES[i % len(VERIDIAN_DATES)]}\nSubject: {subject}\n\n"


def build(log=print) -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    stats = {}
    for matter, (m, scenarios) in MATTER_SCENARIOS.items():
        ts = taskset(matter)
        rows = []
        for i, s in enumerate(scenarios):
            assert s.qid in ts.questions, (matter, s.qid)
            pair = f"c_{matter}_{i:02d}"
            hdr = _veridian_header(i, s.subject) if matter == "veridian" else header(m, i, s.subject)
            fact_label = POS if s.direction == FACT_REL else "not_responsive"
            cf_label = "not_responsive" if s.direction == FACT_REL else POS
            for version, body, text_label in (("factual", s.factual, fact_label), ("counterfactual", s.counterfactual, cf_label)):
                rows.append({"id": f"{pair}__{version}", "text": hdr + body + "\n", "labels": {}, "gray": [],
                             "meta": {"pair": pair, "version": version, "direction": s.direction, "token": s.token, "qid": s.qid, "matter": matter,
                                      "text_label": text_label, "knowledge_label": fact_label, "fact": s.fact, "__unlabeled__": True}})
        write_jsonl(DATA / f"c_{matter}.jsonl", rows)
        stats[matter] = {"pairs": len(scenarios), "fact_relevant": sum(1 for s in scenarios if s.direction == FACT_REL),
                         "fact_irrelevant": sum(1 for s in scenarios if s.direction == FACT_IRR), "requests": ts.qids}
        log(f"C {matter}: {len(scenarios)} pairs ({stats[matter]['fact_relevant']} fact-relevant, {stats[matter]['fact_irrelevant']} fact-irrelevant), requests {ts.qids}")
    (DATA / "c_requests.json").write_text(__import__("json").dumps({mt: {"context": taskset(mt).context, "requests": {q: taskset(mt).questions[q].rfp_text for q in taskset(mt).qids}}
                                                                   for mt in MATTER_SCENARIOS}, indent=1, ensure_ascii=False))
    return stats


# ------------------------------------------------------------------------------------------------ scoring

def _preds(model: str, matter: str) -> dict[tuple[str, str], dict]:
    out = {}
    for r in read_jsonl(job_path(RESULTS, "c", "multi", model, matter)):
        if not r.get("error"):
            out[(r["doc_id"], r["question"])] = r
    return out


def _rate(flags: list[bool]) -> dict:
    k, n = sum(flags), len(flags)
    return {"k": k, "n": n, "rate": k / n if n else float("nan"), "ci": list(wilson(k, n))}


def _paired(items: list[tuple[bool, bool]]) -> dict:
    """items: (text_follow_factual, text_follow_counterfactual) per pair."""
    if not items:
        return {"n": 0}
    a = [1.0 if x else 0.0 for x, _ in items]; b = [1.0 if y else 0.0 for _, y in items]
    d = paired_diff(a, b, seed=SEED)
    disc_b = sum(1 for x, y in items if x and not y); disc_c = sum(1 for x, y in items if not x and y)
    return {"n": len(items), "text_follow_factual": _rate([x for x, _ in items]), "text_follow_counterfactual": _rate([y for _, y in items]),
            "drop": d["mean"], "drop_ci": d["ci"], "factual_ok_cf_wrong": disc_b, "factual_wrong_cf_ok": disc_c, "mcnemar_p": mcnemar(disc_b, disc_c)}


def _indep(a_flags: list[bool], b_flags: list[bool], nb: int = 2000) -> dict:
    import random

    if not a_flags or not b_flags:
        return {}
    rng = random.Random(SEED)
    a = [1 if x else 0 for x in a_flags]; b = [1 if x else 0 for x in b_flags]
    bs = sorted(statistics.mean(rng.choice(a) for _ in a) - statistics.mean(rng.choice(b) for _ in b) for _ in range(nb))
    return {"diff": statistics.mean(a) - statistics.mean(b), "ci": [bs[int(0.025 * nb)], bs[int(0.975 * nb) - 1]]}


def score(log=print) -> dict:
    out: dict = {"matters": {}, "framing": "The correct call follows the TEXT. text-following(counterfactual) = share of counterfactual documents called as "
                                           "their text implies; 1 − that is the knowledge-following rate. Factual documents are the reading ceiling. Veridian is the "
                                           "'fails to read the edit' baseline: its facts exist only in the task context, so no pre-training knowledge is possible."}
    cf_flags: dict[str, dict[str, list[bool]]] = defaultdict(dict)
    for matter in MATTER_SCENARIOS:
        docs = read_jsonl(DATA / f"c_{matter}.jsonl")
        if not docs:
            continue
        pairs: dict[str, dict] = defaultdict(dict)
        for d in docs:
            pairs[d["meta"]["pair"]][d["meta"]["version"]] = d
        per_model = {}
        for model in SYSTEMS:
            preds = _preds(model, matter)
            if not preds:
                continue
            items, by_dir, by_tok, rows = [], defaultdict(list), defaultdict(list), []
            for pair, v in sorted(pairs.items()):
                f, c = v["factual"], v["counterfactual"]
                q = f["meta"]["qid"]
                pf, pc = preds.get((f["id"], q)), preds.get((c["id"], q))
                if pf is None or pc is None:
                    continue
                tf = pf["label"] == f["meta"]["text_label"]; tc = pc["label"] == c["meta"]["text_label"]
                items.append((tf, tc)); by_dir[f["meta"]["direction"]].append((tf, tc)); by_tok[f["meta"]["token"]].append((tf, tc))
                rows.append({"pair": pair, "token": f["meta"]["token"], "direction": f["meta"]["direction"], "qid": q, "call_factual": pf["label"], "p_factual": pf["p_positive"],
                             "call_counterfactual": pc["label"], "p_counterfactual": pc["p_positive"], "text_label_cf": c["meta"]["text_label"], "text_follow_factual": tf, "text_follow_cf": tc})
            cf_rate = sum(y for _, y in items) / len(items) if items else None
            blk = {"all": _paired(items), "by_direction": {d: _paired(v) for d, v in sorted(by_dir.items())},
                   "by_token": {t: {"n": len(v), "text_follow_factual": sum(x for x, _ in v) / len(v), "text_follow_cf": sum(y for _, y in v) / len(v)} for t, v in sorted(by_tok.items())},
                   "knowledge_following_cf": None if cf_rate is None else 1 - cf_rate,
                   # mean distance of p(responsive) on the counterfactual from the text-implied label (0 = fully follows text, 1 = fully follows knowledge)
                   "mean_p_distance_from_text_cf": statistics.mean(abs(float(r["p_counterfactual"]) - (1.0 if r["text_label_cf"] == POS else 0.0)) for r in rows) if rows else None,
                   "rows": rows}
            per_model[model] = blk
            cf_flags[model][matter] = [y for _, y in items]
            if items:
                log(f"C {matter:9s} {model:14s} text-follow factual {blk['all']['text_follow_factual']['rate']:.2f}  counterfactual {blk['all']['text_follow_counterfactual']['rate']:.2f}  "
                    f"drop {100*blk['all']['drop']:+.0f} pp {blk['all']['drop_ci']}  McNemar p={blk['all']['mcnemar_p']:.3g}")
        out["matters"][matter] = {"n_pairs": len(pairs), "models": per_model}
    # matter vs the Veridian baseline on counterfactual text-following (independent bootstrap)
    out["vs_veridian"] = {}
    for model, by in cf_flags.items():
        v = by.get("veridian")
        if not v:
            continue
        for matter, flags in by.items():
            if matter != "veridian":
                out["vs_veridian"][f"{model}/{matter}"] = _indep(flags, v)
    # pooled over the four real matters per model
    out["pooled_real"] = {}
    for model, by in cf_flags.items():
        flags = [x for m, v in by.items() if m != "veridian" for x in v]
        if flags:
            out["pooled_real"][model] = {"text_follow_cf": _rate(flags), "vs_veridian": _indep(flags, by.get("veridian", []))}
            # by direction, pooled over the real matters (knowledge-following is expected mainly on fact-relevant tokens made irrelevant)
            bd = defaultdict(list)
            for mt, v in out["matters"].items():
                if mt == "veridian" or model not in v["models"]:
                    continue
                for r in v["models"][model]["rows"]:
                    bd[r["direction"]].append(r["text_follow_cf"])
            out["pooled_real"][model]["by_direction"] = {d: _rate(f) for d, f in sorted(bd.items())}
            # the factual reading ceiling, pooled
            ff = [r["text_follow_factual"] for mt, v in out["matters"].items() if mt != "veridian" and model in v["models"] for r in v["models"][model]["rows"]]
            out["pooled_real"][model]["text_follow_factual"] = _rate(ff)
    return out
