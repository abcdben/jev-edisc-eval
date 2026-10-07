"""T1 code-name swap: nameless requests, real→fictional token mappings and the templated documents, per matter.

Design. Each scenario is a short e-mail whose relevance to a *nameless* request hinges on recognising one matter token
(an Enron financing vehicle, a Florida controversy, an opioid brand or subsidiary). Every scenario is emitted twice: with
the real token and with a fictional token of the same shape (consistent mapping; the Enron fakes are the ablation's
`names.py` values). `signal` scenarios are ones a case-aware reader would call MORE relevant with the real token;
`decoy` scenarios use a real token that a case-aware reader knows is NOT the kind of thing the request asks for (a water
company, a school test, a non-opioid product), so knowledge should move the call DOWN. A system with no case knowledge
gives the same call in both versions of either kind.

The matter context must be token-free. v1 of this test (2026-10-04, kept in results/jev_probe/t1_v1_confounded/) used the
study's task-yaml contexts as written; the Mallinckrodt and Endo contexts name the products (Exalgo, Roxicodone, Methadose,
Opana ER, Qualitest, and the non-opioid decoys), so a real token in the document could match the *prompt* rather than
training knowledge (results/verify/REPORT.md, check C). v2 replaces those two contexts with product-nameless versions
(the ones written for check C, data/verify/c_requests.json) that describe the conduct generically and name only the
company; `taskset()` asserts that no T1 token — real or fictional — appears in the context or any request field. The
Enron context never names the company; the Jeb Bush context names Governor Jeb Bush and Florida (the matter itself, equal
in both arms) and no token. Headers use invented people so that the token is the only knowledge-bearing name in the document.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..tasks import Question, TaskSet


def _token_re(tok: str) -> re.Pattern:
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(tok)}(?![A-Za-z0-9])", re.I)


def prompt_token_hits(context: str, questions: dict, tokens: dict[str, str]) -> list[tuple[str, str]]:
    """(token, field) for every T1 token — real or fictional — found in the context or any request field."""
    fields = {"context": context}
    for qid, q in questions.items():
        fields[f"{qid}.title"], fields[f"{qid}.rfp_text"] = q.title, q.rfp_text
        fields[f"{qid}.positive_desc"], fields[f"{qid}.negative_desc"] = q.positive_desc, q.negative_desc
    hits = []
    for tok in sorted(set(tokens) | set(tokens.values())):
        pat = _token_re(tok)
        hits += [(tok, f) for f, text in fields.items() if pat.search(text)]
    return hits


@dataclass(frozen=True)
class Scenario:
    token: str          # real token (key into the matter's mapping)
    qid: str            # target request
    subject: str        # may contain {T}
    body: str           # may contain {T}
    kind: str = "signal"  # signal | decoy


@dataclass
class Matter:
    key: str
    task_yaml: str
    tokens: dict[str, str]           # real -> fictional (same shape)
    requests: dict[str, dict]        # qid -> {title, rfp_text, positive_desc, negative_desc}
    scenarios: list[Scenario]
    senders: list[tuple[str, str]]   # (from, to) pairs, invented names
    dates: list[str]
    context_note: str = ""           # appended to the context (empty by default)
    context_override: str = ""       # token-free replacement for the yaml context (v2; Mallinckrodt and Endo)
    extra: dict = field(default_factory=dict)

    def taskset(self, root, check: bool = True) -> TaskSet:
        base = TaskSet.load(root / self.task_yaml)
        qs = {qid: Question(id=qid, title=r["title"], rfp_text=r["rfp_text"].strip(), positive_desc=r["positive_desc"].strip(),
                            negative_desc=r["negative_desc"].strip()) for qid, r in self.requests.items()}
        context = ((self.context_override or base.context) + self.context_note).strip()
        if check:
            hits = prompt_token_hits(context, qs, self.tokens)
            if hits:
                raise ValueError(f"T1 {self.key}: token(s) in the prompt — " + ", ".join(f"{t} in {f}" for t, f in hits))
        return TaskSet(name=f"t1_{self.key}", context=context, questions=qs,
                       positive_label=base.positive_label, negative_label=base.negative_label, source=str(root / self.task_yaml))


# ------------------------------------------------------------------------------------------------ Enron

ENRON = Matter(
    key="enron",
    task_yaml="tasks/enron_j.yaml",
    tokens={
        # financing vehicles (signal) — fakes from ediscovery_bench/ablation/names.py
        "Raptor": "Tercel", "Talon": "Spur", "LJM2": "HLM2", "Chewco": "Brixco", "Whitewing": "Greyfeather", "JEDI": "VEDA",
        "Osprey": "Kittiwake", "Marlin": "Sailfin",
        # operating businesses (decoy): not financing vehicles
        "Azurix": "Aquarel", "Dabhol": "Ratnagar", "EnronOnline": "VolteronOnline", "Portland General": "Cascade General",
    },
    requests={
        "spe_vehicles": dict(
            title="Off-balance-sheet financing vehicles",
            rfp_text="All documents or communications that describe, discuss, refer to, report on, or relate to special-purpose "
                     "entities, partnerships or trusts used to hedge the Company's merchant investments or to keep assets, debt "
                     "or losses off the Company's balance sheet, including their formation, capitalisation, valuation, "
                     "restructuring or unwinding.",
            positive_desc="The document concerns a special-purpose entity, partnership or trust of this kind: its transactions "
                          "with the Company, hedges, capitalisation, credit capacity, valuation, distributions, restructuring, "
                          "unwind, documentation or accounting treatment.",
            negative_desc="The document does not concern such a vehicle. Ordinary trading, the Company's operating businesses "
                          "and subsidiaries, and projects or products that are not financing vehicles are not responsive.",
        ),
    },
    senders=[("Dana Whitcomb", "Marcus Tell"), ("Priya Venkat", "Rob Haller"), ("Lisa Marchand", "Tom Breslin"), ("Greg Oyelaran", "Karen Voss"),
             ("Steve Pardo", "Anne Kowalczyk"), ("Mike Ferrante", "Jill Sandoval")],
    dates=["Mon, 14 Aug 2000 09:12:44 -0500", "Tue, 06 Mar 2001 16:40:03 -0600", "Thu, 19 Oct 2000 11:05:27 -0500", "Fri, 27 Jul 2001 08:31:50 -0500",
           "Wed, 13 Dec 2000 14:22:10 -0600", "Mon, 10 Sep 2001 17:48:02 -0500"],
    scenarios=[
        # --- signal: the token is a financing vehicle
        Scenario("Raptor", "spe_vehicles", "{T} valuation", "Can you send me the Q3 {T} valuation before Thursday? Rick wants the numbers reconciled with the hedge positions before we take it to the committee."),
        Scenario("Raptor", "spe_vehicles", "RE: {T} credit capacity", "{T} credit capacity is down to about $60 million after the latest mark. We need to decide whether to put more shares in or restructure before quarter-end."),
        Scenario("Raptor", "spe_vehicles", "{T} I-IV", "Any update on the {T} I-IV restructuring? The auditors need the fair value memo by Friday and I don't want to be the one explaining the delay."),
        Scenario("Raptor", "spe_vehicles", "{T} hedges", "Can someone walk me through how the {T} hedges actually work? I am getting questions from the rating agencies and I'd like to answer them without calling Houston every time."),
        Scenario("Raptor", "spe_vehicles", "{T} - monthly", "{T} is showing a loss again this month on the merchant portfolio marks. Who owns the model, and has anyone looked at the correlation assumptions?"),
        Scenario("Raptor", "spe_vehicles", "10-Q footnote", "Investor relations wants a one-paragraph description of {T} for the 10-Q footnote. Can you draft something that doesn't say more than we have to?"),
        Scenario("Talon", "spe_vehicles", "{T} documents", "Legal is asking for the {T} partnership agreement and the side letters. Do we have them in the deal file, or are they still with outside counsel?"),
        Scenario("Talon", "spe_vehicles", "{T} capital", "{T} capital call notice attached - $20MM due Friday. Please confirm treasury has the wire set up."),
        Scenario("Talon", "spe_vehicles", "{T} put", "Per our call, {T} will take the position at the September 30 price. Documentation to follow from Mike's group."),
        Scenario("Talon", "spe_vehicles", "RE: {T}", "The {T} transaction closed yesterday. Thanks to everyone who worked through the weekend on the closing set."),
        Scenario("LJM2", "spe_vehicles", "{T} board", "Reminder: the {T} board meets at 3. Agenda: capital contributions, distributions, the put options and the year-end audit."),
        Scenario("LJM2", "spe_vehicles", "{T} fairness opinion", "Have we finalised the {T} fairness opinion? The committee is meeting tomorrow and will want to see it before they vote."),
        Scenario("LJM2", "spe_vehicles", "{T} LP list", "Please pull the {T} limited partner list for the compliance review. They want to know which employees have an interest."),
        Scenario("LJM2", "spe_vehicles", "{T} waterfall", "FYI - the {T} equity partners want the distribution waterfall revisited before they will sign off on the next deal."),
        Scenario("LJM2", "spe_vehicles", "{T} 2000", "Rough numbers: {T} contributed about $500 million of earnings last year across the four deals. Finance wants the breakdown by quarter."),
        Scenario("Chewco", "spe_vehicles", "{T} unwind", "Attached is the draft {T} unwind schedule. Please check the cash flows back to Corp. in the first two columns - something looks off in March."),
        Scenario("Chewco", "spe_vehicles", "{T} reserve", "{T} - the reserve account is below the required balance. Who is responsible for topping it up, and does the agreement give us any time?"),
        Scenario("Chewco", "spe_vehicles", "{T} closing binder", "Can we move the {T} documentation to the shared drive? Outside counsel needs the closing binder and the amendment from 1997."),
        Scenario("Chewco", "spe_vehicles", "{T} 3%", "Accounting is asking again whether the {T} outside equity meets the 3% test. Can you find the original memo?"),
        Scenario("Whitewing", "spe_vehicles", "{T} assets", "Which assets are going into {T} this quarter? Treasury wants the list by Wednesday so they can size the issuance."),
        Scenario("Whitewing", "spe_vehicles", "{T} trigger", "If the stock falls below the {T} trigger price we have a problem. Has anyone modelled what happens at $35?"),
        Scenario("Whitewing", "spe_vehicles", "RE: {T} buyback", "The {T} buyback of the pipeline interest is scheduled for the 30th. Need the approval sheet signed by then."),
        Scenario("JEDI", "spe_vehicles", "{T} partner", "The {T} partner wants out by year-end. Who do we have lined up to take the interest, and how is it being financed?"),
        Scenario("JEDI", "spe_vehicles", "{T} marks", "{T} marks are attached. The gas plant investments are carrying most of the gain this quarter."),
        Scenario("JEDI", "spe_vehicles", "{T} II", "Is {T} II going to be consolidated this year or not? I need an answer for the plan."),
        Scenario("Osprey", "spe_vehicles", "{T} trust", "The {T} trust needs to be unwound before the merger closes. Treasury is drafting the term sheet and wants comments by Monday."),
        Scenario("Osprey", "spe_vehicles", "{T} notes", "The {T} noteholders have asked for the asset list. How much detail do we have to give them under the indenture?"),
        Scenario("Marlin", "spe_vehicles", "{T} refinancing", "The {T} refinancing is on for next month. Please update the sources-and-uses and send to the bank group."),
        # --- decoy: real operating businesses that a case-aware reader knows are not financing vehicles
        Scenario("Azurix", "spe_vehicles", "{T} restructuring", "Need the {T} restructuring numbers before the board meeting; the credit issue is getting worse and the banks are nervous.", "decoy"),
        Scenario("Azurix", "spe_vehicles", "{T} write-down", "Rough numbers: {T} cost us about $500 million in write-downs last year. Finance wants the breakdown by quarter.", "decoy"),
        Scenario("Azurix", "spe_vehicles", "{T} unwind", "The {T} unwind is getting complicated; treasury is drafting the term sheet and wants comments by Monday.", "decoy"),
        Scenario("Dabhol", "spe_vehicles", "{T} documents", "Please pull the {T} documentation for the auditors' review. They want the original agreements and all the amendments.", "decoy"),
        Scenario("Dabhol", "spe_vehicles", "{T} - monthly", "{T} is showing a loss again this quarter. Who owns the model, and has anyone looked at the assumptions?", "decoy"),
        Scenario("Dabhol", "spe_vehicles", "{T} exit", "If we exit {T} this year the hit is around $1 billion. Has anyone modelled the alternatives?", "decoy"),
        Scenario("EnronOnline", "spe_vehicles", "{T} numbers", "Investor relations wants a one-paragraph description of {T} for the 10-Q. Can you draft something short?", "decoy"),
        Scenario("EnronOnline", "spe_vehicles", "{T} volumes", "{T} volumes are attached. Most of the gain this quarter is coming from the gas book.", "decoy"),
        Scenario("EnronOnline", "spe_vehicles", "RE: {T}", "The {T} transaction closed yesterday - thanks to everyone who worked the weekend.", "decoy"),
        Scenario("Portland General", "spe_vehicles", "{T} sale", "The {T} sale needs to close before year-end. Treasury is drafting the term sheet and the bank group wants the sources-and-uses.", "decoy"),
        Scenario("Portland General", "spe_vehicles", "{T} capital", "{T} capital call attached - $20MM due Friday. Please confirm the wire.", "decoy"),
        Scenario("Portland General", "spe_vehicles", "{T} board", "Reminder: the {T} board meets at 3. Agenda: capital contributions, distributions and the year-end audit.", "decoy"),
    ],
)

# ------------------------------------------------------------------------------------------------ Jeb Bush

JEBBUSH = Matter(
    key="jebbush",
    task_yaml="tasks/trec.yaml",
    tokens={
        "Schiavo": "Petrossi", "Elián": "Dariel", "Elian": "Dariel", "One Florida": "Open Florida", "Crosby": "Hadley",
        # decoys: a school test and a biotech-recruitment deal
        "FCAT": "SPAT", "Scripps": "Lorrance",
    },
    requests={
        "family_dispute": dict(
            title="State involvement in a contested custody or end-of-life dispute",
            rfp_text="All documents concerning the involvement of the Governor, the Legislature or a Florida state agency in a "
                     "contested family custody or end-of-life medical dispute that became a public controversy, including "
                     "litigation, legislation, executive action, and public or constituent reaction.",
            positive_desc="The email concerns such a dispute: the court proceedings, any bill or executive action about the "
                          "person at its centre, the Governor's position or statements, meetings with the family or their "
                          "lawyers, and constituent or press reaction to the state's involvement.",
            negative_desc="The email does not concern a contested custody or end-of-life dispute. Other health, education, "
                          "budget or agency matters, and controversies of other kinds, are not responsive.",
        ),
        "preferences": dict(
            title="Ending race and gender preferences in admissions and contracting",
            rfp_text="All documents concerning the Governor's initiative to end race- and gender-based preferences in state "
                     "university admissions and state contracting, including its design, implementation, legal challenges, "
                     "and public or legislative reaction.",
            positive_desc="The email concerns that initiative: the executive order, admissions or contracting rules made under "
                          "it, enrolment or vendor figures used to defend it, litigation over it, protests or sit-ins against "
                          "it, and the Governor's statements about it.",
            negative_desc="The email does not concern the initiative to end preferences. General education, procurement or "
                          "civil-rights traffic with no connection to it is not responsive.",
        ),
        "agency_head_misconduct": dict(
            title="Criminal misconduct by a state agency head",
            rfp_text="All documents concerning allegations of corruption, kickbacks or other criminal misconduct by the head "
                     "of a Florida state agency appointed by the Governor, including the investigation, resignation or "
                     "prosecution and the Governor's response.",
            positive_desc="The email concerns such allegations against an agency head: the investigation by law enforcement or "
                          "prosecutors, the contracts or payments at issue, the resignation or removal, and the Governor's "
                          "office's handling of it.",
            negative_desc="The email does not concern criminal misconduct by an agency head. Routine appointments, agency "
                          "business, and personnel matters without an allegation of corruption are not responsive.",
        ),
    },
    senders=[("Carla Mendieta", "Jeb Bush"), ("Brian Oduya", "Carla Mendieta"), ("Jeb Bush", "Alison Trent"), ("Alison Trent", "Brian Oduya"),
             ("Mark Feeney", "Jeb Bush"), ("Jeb Bush", "Mark Feeney")],
    dates=["Thursday, April 06, 2000 7:41 PM", "Tuesday, October 21, 2003 6:02 AM", "Monday, January 24, 2000 9:15 PM", "Friday, February 10, 2006 5:33 PM",
           "Wednesday, March 23, 2005 11:48 PM", "Sunday, December 05, 1999 8:20 AM"],
    scenarios=[
        # --- Schiavo (family_dispute)
        Scenario("Schiavo", "family_dispute", "{T}", "The {T} ruling came down this afternoon. Legal is reviewing whether the special-session language holds up, and the press office wants a line by 6."),
        Scenario("Schiavo", "family_dispute", "RE: {T} mail", "Constituent mail on {T} is running 8 to 1 asking you to intervene. Do we have a standard response letter yet, or are we still holding?"),
        Scenario("Schiavo", "family_dispute", "9 am", "Please add the {T} briefing to the 9 am. The family's attorney will be on the call and wants to know what the Governor can and cannot do."),
        Scenario("Schiavo", "family_dispute", "{T} bill", "The Senate President wants to know your position on the {T} bill before Thursday. Jim thinks it passes the House easily but the Senate is 50-50."),
        Scenario("Schiavo", "family_dispute", "{T} timeline", "Here is the {T} timeline for the press office. Please check the court dates - I think the appeal was in 2001, not 2002."),
        Scenario("Schiavo", "family_dispute", "FW: {T}", "Governor - forwarding the latest from the {T} team. The judge has set a hearing for Monday and the parents have asked to meet you."),
        # --- Elián (family_dispute)
        Scenario("Elián", "family_dispute", "{T}", "The {T} situation in Miami is getting worse. You have been asked to comment on the federal action this morning - do you want to?"),
        Scenario("Elián", "family_dispute", "{T} talking points", "Attached: {T} talking points for the community meeting tonight. The relatives' lawyer may be in the room."),
        Scenario("Elián", "family_dispute", "RE: {T}", "We are getting hundreds of calls about {T}. Most ask the Governor to step in. What is our line on the state's role?"),
        Scenario("Elián", "family_dispute", "{T} - Washington", "Any word from Washington on {T}? The relatives want a meeting with you this week and the Mayor is already on record."),
        Scenario("Elián", "family_dispute", "{T} letter", "Draft of your letter to the Attorney General on {T} attached. Lucy toned down the second paragraph."),
        # --- One Florida (preferences)
        Scenario("One Florida", "preferences", "{T}", "{T} goes to the Board of Regents next week. Please circulate the enrolment projections before the briefing."),
        Scenario("One Florida", "preferences", "{T} numbers", "The {T} vendor numbers are attached. The press will ask about them at the roll-out, so please double-check the totals."),
        Scenario("One Florida", "preferences", "sit-in", "The sit-in in the Lt. Governor's office is about {T}. Do we have a statement, and is anyone talking to the two legislators?"),
        Scenario("One Florida", "preferences", "{T} op-ed", "Need your edits on the {T} op-ed by noon. The Herald wants it tomorrow."),
        Scenario("One Florida", "preferences", "{T} hearing", "The {T} lawsuit hearing is Tuesday. Legal expects a ruling on the admissions piece within a month."),
        Scenario("One Florida", "preferences", "RE: {T}", "The march on the Capitol next week is about {T}. FDLE estimates 10,000. Do you want to be in Tallahassee or not?"),
        # --- Crosby (agency_head_misconduct)
        Scenario("Crosby", "agency_head_misconduct", "{T}", "FDLE wants to brief you on {T} tomorrow morning. Please clear 30 minutes; the General Counsel will join."),
        Scenario("Crosby", "agency_head_misconduct", "{T} - Times", "The {T} story is in the Times tomorrow. We need to decide today whether to accept the resignation or wait for the U.S. Attorney."),
        Scenario("Crosby", "agency_head_misconduct", "RE: {T}", "{T} called again about the canteen contract. Can someone from legal join the call? I don't want anyone on this alone."),
        Scenario("Crosby", "agency_head_misconduct", "{T} file", "Please pull the {T} appointment file and the last two financial disclosures. The General Counsel wants them by 5."),
        Scenario("Crosby", "agency_head_misconduct", "{T} records", "The U.S. Attorney's office has asked for {T} travel records going back to 2003. Legal says we comply."),
        Scenario("Crosby", "agency_head_misconduct", "{T} statement", "Draft statement on {T} attached. It says you are disappointed and that the department will cooperate fully."),
        # --- decoys: a school test and a biotech deal
        Scenario("FCAT", "family_dispute", "{T}", "{T} results are out and the papers are hostile. Do we have talking points for you, and does Jim want to do the Herald call?", "decoy"),
        Scenario("FCAT", "preferences", "RE: {T} mail", "Constituent mail on {T} is running heavy this week. Do we have a standard letter, or are we still holding?", "decoy"),
        Scenario("FCAT", "preferences", "{T} numbers", "The {T} numbers by school are attached. The press will ask about them at the roll-out, so please double-check the totals.", "decoy"),
        Scenario("FCAT", "agency_head_misconduct", "{T} hearing", "The {T} lawsuit hearing is Tuesday. Legal expects a ruling within a month.", "decoy"),
        Scenario("Scripps", "preferences", "{T}", "The {T} deal goes to the Cabinet Tuesday; please circulate the incentive numbers before the briefing.", "decoy"),
        Scenario("Scripps", "agency_head_misconduct", "{T} - Times", "The {T} story is in the Times tomorrow. We need to decide today how to respond.", "decoy"),
        Scenario("Scripps", "family_dispute", "FW: {T}", "Governor - forwarding the latest from the {T} team. The vote is Monday and they have asked to meet you.", "decoy"),
        Scenario("Scripps", "agency_head_misconduct", "{T} file", "Please pull the {T} file and the last two agreements. The General Counsel wants them by 5.", "decoy"),
    ],
)

# ------------------------------------------------------------------------------------------------ Mallinckrodt

_OPIOID_MKTG = dict(
    title="Marketing and sale of the Company's opioid products",
    rfp_text="All documents concerning the marketing, promotion or sale of any of the Company's opioid products, including "
             "promotional materials, messaging, sales training and call plans, speaker programmes, market research, formulary "
             "positioning and sales performance.",
    positive_desc="The document concerns the marketing, promotion, sales strategy, messaging, training, speaker programmes, "
                  "formulary status or sales performance of an opioid product of the Company.",
    negative_desc="The document does not concern an opioid product's marketing or sale. Non-opioid products, manufacturing "
                  "and supply, and compliance matters with no marketing content are not responsive.",
)

# Token-free contexts (v2). Same text as check C's data/verify/c_requests.json: the company is named, no product, subsidiary,
# person or event is.
MNK_CONTEXT = (
    "Matter: opioid litigation against Mallinckrodt plc and Mallinckrodt LLC (MDL 2804, In re National Prescription Opiate "
    "Litigation, and related state actions). The Company manufactured generic and branded prescription opioids and also sold "
    "non-opioid products that are not at issue. Plaintiffs allege that the Company failed to maintain effective controls against "
    "diversion, including its suspicious order monitoring program for wholesaler and distributor orders; that it had visibility "
    "into downstream distribution to pharmacies and did not act on it; that it promoted opioids while minimizing addiction risk; "
    "and that it sought ever-larger DEA production quota. The relevant period is 2006 through 2017. The documents are emails, "
    "reproduced with their headers as a reviewer would see them; quoted earlier messages in a thread are part of the document."
)
ENDO_CONTEXT = (
    "Matter: opioid litigation against Endo International plc, Endo Health Solutions Inc. and Endo Pharmaceuticals Inc. (MDL 2804, "
    "In re National Prescription Opiate Litigation, state attorney-general actions, and Endo's 2022 chapter 11 case). The Company "
    "sold branded and generic prescription opioids, including a reformulated extended-release opioid with a crush-resistant design, "
    "and also sold non-opioid products that are not at issue. Plaintiffs allege that the Company marketed its extended-release "
    "opioid with claims about abuse deterrence and addiction risk that were not supported; that its sales representatives, speaker "
    "programmes and training materials minimised the risk of addiction; that it funded third-party pain advocacy organisations, key "
    "opinion leaders and continuing medical education on pain messaging; and that it did not adequately identify or report "
    "suspicious orders or suspicious prescribing. The relevant period is 2006 through 2017. The documents are emails, reproduced "
    "with their headers as a reviewer would see them; quoted earlier messages in a thread are part of the document."
)

MNK = Matter(
    key="mnk",
    task_yaml="tasks/mallinckrodt.yaml",
    context_override=MNK_CONTEXT,
    tokens={
        # opioid brands and the controlled-substance subsidiary (signal)
        "Exalgo": "Veltrano", "Methadose": "Dolomere", "Roxicodone": "Oxirell", "SpecGx": "CoreGx",
        # non-opioid products (decoy)
        "Ofirmev": "Acetrava", "INOmax": "NitroVent", "Acthar": "Corthar",
    },
    requests={
        "opioid_marketing": _OPIOID_MKTG,
        "subsidiary_dea": dict(
            title="DEA dealings of the Company's controlled-substance manufacturing subsidiary",
            rfp_text="All documents concerning communications with or actions by the U.S. Drug Enforcement Administration "
                     "regarding the controlled-substance obligations of the Company or of its controlled-substance "
                     "manufacturing subsidiary, including production quota, registrations, inspections and investigations.",
            positive_desc="The document concerns DEA quota, registration, inspection, audit or investigation matters of the "
                          "Company or of a subsidiary of the Company that manufactures controlled substances.",
            negative_desc="The document does not concern DEA dealings of the Company or its subsidiary. DEA matters of "
                          "unrelated third parties, and regulatory matters that do not involve DEA, are not responsive.",
        ),
    },
    senders=[("Karen Doherty", "Paul Winstead"), ("Raj Mehrotra", "Karen Doherty"), ("Tom Lindell", "Sue Garrity"), ("Sue Garrity", "Raj Mehrotra"),
             ("Ellen Markovic", "Tom Lindell"), ("Paul Winstead", "Ellen Markovic")],
    dates=["Tuesday, March 08, 2011 4:12 PM", "Thursday, September 13, 2012 9:47 AM", "Monday, June 02, 2014 2:30 PM", "Wednesday, November 18, 2009 11:05 AM",
           "Friday, February 27, 2015 5:51 PM", "Tuesday, August 07, 2012 8:14 AM"],
    scenarios=[
        Scenario("Exalgo", "opioid_marketing", "{T} launch deck", "The {T} launch deck is attached. Marketing wants feedback on the messaging slides by Friday - the agency has to lock the layout next week."),
        Scenario("Exalgo", "opioid_marketing", "{T} TRx", "{T} TRx were up 4% last week. The call-plan changes seem to be working; let's keep the top-decile targets as they are."),
        Scenario("Exalgo", "opioid_marketing", "{T} speaker budget", "Can we get the {T} speaker programme budget for Q3? Medical affairs wants to add two KOLs in the Southeast."),
        Scenario("Exalgo", "opioid_marketing", "{T} sales aid", "The reps are asking for a new {T} sales aid; the current one is out of date on dosing and the comparison chart."),
        Scenario("Exalgo", "opioid_marketing", "RE: {T} MLR", "Please route the revised {T} detail piece through MLR this week. The claims on page 3 are the ones legal flagged last time."),
        Scenario("Methadose", "opioid_marketing", "{T} share", "{T} market share slipped in Florida again. Please pull the territory numbers and the wholesaler data before the call."),
        Scenario("Methadose", "opioid_marketing", "{T} pricing", "{T} pricing proposal attached for the national accounts meeting. The 5% increase is in line with the competitor."),
        Scenario("Methadose", "opioid_marketing", "{T} NSM", "Reminder: the {T} breakout at the national sales meeting is Tuesday at 2. Bring the new positioning slides."),
        Scenario("Methadose", "opioid_marketing", "{T} clinics", "The {T} clinic programme in Ohio is ahead of plan. Can we extend the field support through Q4?"),
        Scenario("Roxicodone", "opioid_marketing", "{T} formulary", "{T} formulary status at Humana is still pending. Managed markets will follow up with the P&T committee next week."),
        Scenario("Roxicodone", "opioid_marketing", "{T} research", "Market research on {T} prescribers is in. Attached are the top-line findings on messaging and brand awareness."),
        Scenario("Roxicodone", "opioid_marketing", "{T} coupon", "The {T} co-pay card programme ends in December. Do we renew, and at what level?"),
        Scenario("Roxicodone", "opioid_marketing", "{T} training", "New-hire training for {T} is next week. Please send me the latest product monograph and the objection handlers."),
        Scenario("SpecGx", "subsidiary_dea", "{T} quota", "DEA sent {T} the quota letter this morning. The numbers are lower than requested for two of the three products."),
        Scenario("SpecGx", "subsidiary_dea", "{T} inspection", "The {T} inspection in Hobart went fine; two observations, nothing on record-keeping. Report attached."),
        Scenario("SpecGx", "subsidiary_dea", "{T} - Diversion Control", "{T} has a call with the Diversion Control office Thursday about the reporting backlog. Who from compliance will join?"),
        Scenario("SpecGx", "subsidiary_dea", "{T} registrations", "Please send the {T} registration renewals to regulatory before the 15th. Two sites expire in October."),
        Scenario("SpecGx", "subsidiary_dea", "{T} audit", "The {T} audit findings are attached for review. The investigators asked about the St. Louis records twice."),
        Scenario("SpecGx", "subsidiary_dea", "{T} meeting", "Can we set up the {T} meeting with the agency for the week of the 12th? Legal wants to be there."),
        # --- decoys: non-opioid products in the same marketing templates
        Scenario("Ofirmev", "opioid_marketing", "{T} launch deck", "The {T} launch deck is attached. Marketing wants feedback on the messaging slides by Friday - the agency has to lock the layout next week.", "decoy"),
        Scenario("Ofirmev", "opioid_marketing", "{T} TRx", "{T} volumes were up 4% last week. The call-plan changes seem to be working; let's keep the top-decile targets as they are.", "decoy"),
        Scenario("Ofirmev", "opioid_marketing", "{T} formulary", "{T} formulary status at Humana is still pending. Managed markets will follow up with the P&T committee next week.", "decoy"),
        Scenario("Ofirmev", "opioid_marketing", "RE: {T} MLR", "Please route the revised {T} detail piece through MLR this week. The claims on page 3 are the ones legal flagged last time.", "decoy"),
        Scenario("INOmax", "opioid_marketing", "{T} speaker budget", "Can we get the {T} speaker programme budget for Q3? Medical affairs wants to add two KOLs in the Southeast.", "decoy"),
        Scenario("INOmax", "opioid_marketing", "{T} training", "New-hire training for {T} is next week. Please send me the latest product monograph and the objection handlers.", "decoy"),
        Scenario("INOmax", "opioid_marketing", "{T} pricing", "{T} pricing proposal attached for the national accounts meeting. The 5% increase is in line with the competitor.", "decoy"),
        Scenario("Acthar", "opioid_marketing", "{T} sales aid", "The reps are asking for a new {T} sales aid; the current one is out of date on dosing and the comparison chart.", "decoy"),
        Scenario("Acthar", "opioid_marketing", "{T} research", "Market research on {T} prescribers is in. Attached are the top-line findings on messaging and brand awareness.", "decoy"),
        Scenario("Acthar", "opioid_marketing", "{T} coupon", "The {T} co-pay card programme ends in December. Do we renew, and at what level?", "decoy"),
        Scenario("Acthar", "subsidiary_dea", "{T} inspection", "The {T} inspection went fine; two observations, nothing on record-keeping. Report attached.", "decoy"),
        Scenario("Ofirmev", "subsidiary_dea", "{T} audit", "The {T} audit findings are attached for review. The investigators asked about the records twice.", "decoy"),
    ],
)

# ------------------------------------------------------------------------------------------------ Endo

ENDO = Matter(
    key="endo",
    task_yaml="tasks/endo.yaml",
    context_override=ENDO_CONTEXT,
    tokens={
        # opioid brands, the generic subsidiary and the reformulation technology (signal)
        "Opana ER": "Veltrex ER", "Opana": "Veltrex", "Percocet": "Norvocet", "Qualitest": "Quantrex", "INTAC": "DURAX",
        # non-opioid products (decoy)
        "Lidoderm": "Dermalin", "Voltaren Gel": "Flexaren Gel", "Aveed": "Testrel", "Supprelin": "Histrelex",
    },
    requests={
        "opioid_marketing": _OPIOID_MKTG,
        "abuse_deterrence": dict(
            title="Abuse-deterrence claims for a reformulated extended-release opioid",
            rfp_text="All documents concerning claims, statements or evidence about the abuse-deterrent, tamper-resistant or "
                     "crush-resistant properties of a reformulated extended-release opioid product of the Company, including "
                     "laboratory or clinical data on defeating the formulation, the technology used, regulatory correspondence "
                     "about such claims, and their use in promotion.",
            positive_desc="The document concerns the abuse-deterrent or tamper-resistant properties of a reformulated "
                          "extended-release opioid of the Company: manipulation studies, the formulation technology and its "
                          "licence, FDA correspondence about the claims, or promotional use of such claims.",
            negative_desc="The document does not concern abuse-deterrence properties of a Company opioid. Non-opioid products, "
                          "general promotion without abuse-deterrence content, and third-party products are not responsive.",
        ),
    },
    senders=[("Regina Castellanos", "Frank Burnell"), ("Mark Hinde", "Regina Castellanos"), ("Dave Prescott", "Lynn Okafor"), ("Lynn Okafor", "Mark Hinde"),
             ("Steve Marquand", "Dave Prescott"), ("Frank Burnell", "Steve Marquand")],
    dates=["Wednesday, March 30, 2011 5:01 PM", "Monday, February 06, 2012 10:22 AM", "Thursday, August 15, 2013 3:45 PM", "Tuesday, May 20, 2014 8:58 AM",
           "Friday, October 09, 2009 1:16 PM", "Monday, January 11, 2016 9:03 AM"],
    scenarios=[
        Scenario("Opana ER", "opioid_marketing", "{T} relaunch", "The {T} relaunch deck is attached. Marketing wants feedback on the messaging slides by Friday - the agency has to lock the layout next week."),
        Scenario("Opana ER", "opioid_marketing", "{T} TRx", "{T} TRx were up 4% last week. The call-plan changes seem to be working; keep the top-decile targets as they are."),
        Scenario("Opana ER", "opioid_marketing", "{T} speakers", "Can we get the {T} speaker programme budget for Q3? Medical affairs wants to add two KOLs in the Southeast."),
        Scenario("Opana ER", "opioid_marketing", "RE: {T} MLR", "Please route the revised {T} detail piece through the promotional review committee this week. The claims on page 3 are the ones legal flagged."),
        Scenario("Opana ER", "opioid_marketing", "{T} formulary", "{T} formulary status at Humana is still pending. Managed markets will follow up with the P&T committee next week."),
        Scenario("Opana", "opioid_marketing", "{T} research", "Market research on {T} prescribers is in. Attached are the top-line findings on messaging and brand awareness."),
        Scenario("Percocet", "opioid_marketing", "{T} sales aid", "The reps are asking for a new {T} sales aid; the current one is out of date on dosing and the comparison chart."),
        Scenario("Percocet", "opioid_marketing", "{T} pricing", "{T} pricing proposal attached for the national accounts meeting. The 5% increase is in line with the competitor."),
        Scenario("Percocet", "opioid_marketing", "{T} coupon", "The {T} co-pay card programme ends in December. Do we renew, and at what level?"),
        Scenario("Percocet", "opioid_marketing", "{T} training", "New-hire training for {T} is next week. Please send me the latest product monograph and the objection handlers."),
        Scenario("Qualitest", "opioid_marketing", "{T} portfolio", "The {T} portfolio review is Thursday. Which of the generics are we still actively promoting to the wholesalers?"),
        Scenario("Qualitest", "opioid_marketing", "{T} pricing", "{T} national accounts pricing attached. The hydrocodone line is where the margin is."),
        # --- abuse deterrence
        Scenario("Opana ER", "abuse_deterrence", "{T} lab data", "The {T} lab data on tablet manipulation are attached; marketing wants to know what we can say about it in the detail piece."),
        Scenario("Opana ER", "abuse_deterrence", "{T} - FDA", "FDA's response on the {T} labeling request is in. They are not giving us the language we asked for in section 9."),
        Scenario("Opana ER", "abuse_deterrence", "{T} study", "The {T} extraction study report is final. The coffee-grinder method still recovers about 40% - please do not forward outside the team."),
        Scenario("Opana ER", "abuse_deterrence", "RE: {T} claims", "Legal is asking which {T} claims in the current sales aid are supported by the manipulation data. Can you map them?"),
        Scenario("INTAC", "abuse_deterrence", "{T} licence", "Grünenthal says the {T} licence excludes the 7.5 mg strength. Regulatory needs to know before the supplement goes in."),
        Scenario("INTAC", "abuse_deterrence", "{T} data", "The {T} manipulation data package is attached. Marketing wants to know what we can say about it in the detail piece."),
        Scenario("INTAC", "abuse_deterrence", "{T} - FDA", "FDA has asked for more {T} data before they will discuss the label. The advisory committee is in May."),
        # --- decoys: non-opioid products in the same templates
        Scenario("Lidoderm", "opioid_marketing", "{T} deck", "The {T} deck is attached. Marketing wants feedback on the messaging slides by Friday - the agency has to lock the layout next week.", "decoy"),
        Scenario("Lidoderm", "opioid_marketing", "{T} TRx", "{T} TRx were up 4% last week. The call-plan changes seem to be working; keep the top-decile targets as they are.", "decoy"),
        Scenario("Lidoderm", "opioid_marketing", "{T} coupon", "The {T} co-pay card programme ends in December. Do we renew, and at what level?", "decoy"),
        Scenario("Lidoderm", "abuse_deterrence", "{T} lab data", "The {T} lab data on patch manipulation are attached; marketing wants to know what we can say about it in the detail piece.", "decoy"),
        Scenario("Voltaren Gel", "opioid_marketing", "{T} speakers", "Can we get the {T} speaker programme budget for Q3? Medical affairs wants to add two KOLs in the Southeast.", "decoy"),
        Scenario("Voltaren Gel", "opioid_marketing", "{T} formulary", "{T} formulary status at Humana is still pending. Managed markets will follow up with the P&T committee next week.", "decoy"),
        Scenario("Aveed", "opioid_marketing", "{T} sales aid", "The reps are asking for a new {T} sales aid; the current one is out of date on dosing and the comparison chart.", "decoy"),
        Scenario("Aveed", "opioid_marketing", "{T} training", "New-hire training for {T} is next week. Please send me the latest product monograph and the objection handlers.", "decoy"),
        Scenario("Aveed", "abuse_deterrence", "{T} - FDA", "FDA's response on the {T} labeling request is in. They are not giving us the language we asked for in section 9.", "decoy"),
        Scenario("Supprelin", "opioid_marketing", "{T} research", "Market research on {T} prescribers is in. Attached are the top-line findings on messaging and brand awareness.", "decoy"),
        Scenario("Supprelin", "opioid_marketing", "{T} pricing", "{T} pricing proposal attached for the national accounts meeting. The 5% increase is in line with the competitor.", "decoy"),
        Scenario("Supprelin", "abuse_deterrence", "RE: {T} claims", "Legal is asking which {T} claims in the current sales aid are supported by the data. Can you map them?", "decoy"),
    ],
)

MATTERS: dict[str, Matter] = {m.key: m for m in (ENRON, JEBBUSH, MNK, ENDO)}


# ------------------------------------------------------------------------------------------------ bare-token check (FAS 140)

BARE_TOKENS = {"Raptor": "Tercel", "LJM2": "HLM2", "Chewco": "Brixco"}
BARE_SENTENCES = [
    "Can you send me the latest {T} numbers before the meeting?",
    "Attached is the {T} memo we discussed.",
    "Please add {T} to the agenda for Thursday.",
    "Any update on {T}?",
    "The {T} documents are in the deal file.",
    "{T} - please call me when you get this.",
    "Here is the {T} schedule for the quarter.",
    "Need your sign-off on {T} by Friday.",
    "{T} is on the list for the committee.",
    "FYI - {T} update attached.",
    "Who is handling {T} now?",
    "Reminder: {T} call at 3.",
    "The {T} file has been updated.",
    "Can we talk about {T} tomorrow?",
    "Forwarding the {T} summary.",
    "{T} status: no change since last week.",
    "Please review the {T} draft.",
    "Is the {T} paperwork done?",
    "Thanks for the help on {T}.",
    "{T} - see attached.",
]
# Request criteria variant that names the vehicles (the as-written FAS 140 criteria name none; verified in tasks/enron_j.yaml)
FAS140_NAMES_NOTE = (" Transactions of this kind include those involving the Raptor, Talon, LJM2, Chewco, Whitewing and JEDI "
                     "entities.")


def header(matter: Matter, i: int, subject: str) -> str:
    frm, to = matter.senders[i % len(matter.senders)]
    date = matter.dates[i % len(matter.dates)]
    if matter.key == "enron":
        return f"Date: {date}\nFrom: {frm}\nTo: {to}\nSubject: {subject}\n\n"
    return f"From:\t{frm}\nSent:\t{date}\nTo:\t{to}\nSubject:\t{subject}\n\n"


def swap(text: str, mapping: dict[str, str]) -> str:
    """Longest-first, case-shape-preserving replacement of every real token by its fictional twin."""
    import re

    for real in sorted(mapping, key=len, reverse=True):
        fake = mapping[real]
        pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(real)}(?![A-Za-z0-9])", re.I)

        def rep(m, fake=fake):
            s = m.group(0)
            if s.isupper() and len(s) > 1:
                return fake.upper()
            if s.islower():
                return fake.lower()
            return fake
        text = pat.sub(rep, text)
    return text
