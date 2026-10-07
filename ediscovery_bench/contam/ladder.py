"""A ladder of real matters at graded levels of public exposure, used to calibrate the matter-knowledge probes (M0, M1).

Part II's anchors are a fictional matter (floor) and U.S. v. Microsoft (ceiling). This module adds rungs between them:
litigation and disputes from the last ~90 years, chosen in *families* that mirror the study's corpora (accounting fraud for
Enron, opioids for Mallinckrodt, e-mail in public life for Jeb Bush, medical devices for Veridian), plus landmark events
across the century and two real matters that post-date the models' training data. Each rung gets the same two probes as
the study's matters — identify it from a de-identified sketch; describe it against a fact checklist — and an independent
exposure proxy (English Wikipedia article length, number of language editions, 12-month pageviews), so the study's
matters can be read as positions on a measured scale rather than as isolated numbers.

Rubric facts were written from the public record; keys are matched as whole words/phrases by matter._kw_hit.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOOTPRINT_CACHE = ROOT / "data" / "contam" / "raw" / "wiki_footprint.json"

FAMILY_LABEL = {
    "accounting": "accounting & securities fraud (Enron's family)",
    "opioids": "opioid litigation (Mallinckrodt's family)",
    "email": "e-mail and public records in public life (Jeb Bush's family)",
    "devices": "medical-device mass torts (Veridian's family)",
    "landmark": "landmark corporate disputes across the century",
    "consumer": "consumer-product mass torts (JUUL; a candidate held-out production)",
    "postcutoff": "post-cutoff controls (real, but after training data)",
    "procurement": "public-procurement bribery (Big Thorium's family; public demo documents, invented case)",
}
FAMILY_ORDER = ["accounting", "opioids", "email", "devices", "procurement", "landmark", "consumer", "postcutoff"]

# key -> rung. expected: the pre-registered guess at exposure ("high" / "mid" / "low" / "none").
LADDER: dict[str, dict] = {
    # ------------------------------------------------------------------ accounting & securities fraud
    "worldcom": {
        "label": "WorldCom (2002)", "year": 2002, "family": "accounting", "expected": "high",
        "wiki": ["WorldCom scandal", "WorldCom", "MCI Inc."],
        "sketch": (
            "A long-distance telecommunications carrier, the second-largest in the United States, disclosed in mid-2002 that it had "
            "improperly capitalised billions of dollars of ordinary network line-cost expenses, inflating reported profits; the "
            "restatement eventually reached roughly eleven billion dollars. Weeks later it filed what was then the largest bankruptcy "
            "in U.S. history. An internal auditor uncovered the entries. The chief executive, a former basketball coach and motel "
            "owner from Mississippi, was convicted of fraud and sentenced to 25 years. The company emerged from bankruptcy under the "
            "name of a carrier it had acquired and was later bought by a Bell company."
        ),
        "answer_keys": ["worldcom", "mci"],
        "name": "the WorldCom accounting fraud and its aftermath (2002-2006)",
        "rubric": [
            ("Bernard Ebbers (CEO)", ["ebbers"], "people"),
            ("Scott Sullivan (CFO)", ["sullivan"], "people"),
            ("Cynthia Cooper (internal audit)", ["cooper"], "people"),
            ("David Myers (controller) / Buford Yates", ["myers", "yates"], "people"),
            ("capitalised line costs", ["line cost", "capitaliz", "capitalis"], "allegations"),
            ("~$11 billion restatement", ["11 billion", "$11", "3.8 billion"], "allegations"),
            ("Arthur Andersen (auditor)", ["andersen"], "parties"),
            ("Chapter 11, July 2002, largest to date", ["july 2002", "chapter 11", "bankrupt"], "events"),
            ("Clinton, Mississippi headquarters", ["mississippi"], "parties"),
            ("renamed MCI on emergence (2004)", ["mci"], "outcome"),
            ("acquired by Verizon (2006)", ["verizon"], "outcome"),
            ("Ebbers convicted 2005, 25 years", ["25 years", "25-year", "twenty-five"], "outcome"),
            ("Sullivan pleaded guilty and testified", ["pleaded", "plea", "testif"], "events"),
            ("Sarbanes-Oxley Act", ["sarbanes"], "outcome"),
        ],
    },
    "healthsouth": {
        "label": "HealthSouth (2003)", "year": 2003, "family": "accounting", "expected": "mid",
        "wiki": ["HealthSouth", "Encompass Health"],
        "sketch": (
            "The largest U.S. operator of outpatient surgery and rehabilitation clinics, headquartered in Alabama, was accused in "
            "March 2003 by the SEC — a day after an FBI raid — of overstating earnings by at least $1.4 billion (later put higher) "
            "to meet Wall Street expectations. Successive chief financial officers carried out the fraud and referred to themselves "
            "as 'the family'; five of them pleaded guilty. The founder and chief executive was acquitted at a 2005 criminal trial in "
            "Birmingham, the first CEO tried under the new corporate-reform statute's certification provisions, but was later "
            "convicted of bribing the state's governor."
        ),
        "answer_keys": ["healthsouth", "scrushy"],
        "name": "the HealthSouth accounting fraud (2003) and the trials of its founder",
        "rubric": [
            ("Richard Scrushy (founder / CEO)", ["scrushy"], "people"),
            ("Birmingham, Alabama", ["birmingham", "alabama"], "parties"),
            ("Weston Smith (CFO, whistle-blower)", ["weston smith"], "people"),
            ("Aaron Beam / William Owens / other CFOs", ["beam", "owens", "mcvay", "martin"], "people"),
            ("$1.4bn-$2.7bn overstatement", ["1.4 billion", "2.7 billion", "2.6 billion", "$1.4", "$2.7"], "allegations"),
            ("'the family' / filling the gap", ["the family", "the gap"], "allegations"),
            ("Sarbanes-Oxley certification charges", ["sarbanes"], "allegations"),
            ("FBI raid, March 2003", ["raid", "march 2003"], "events"),
            ("Ernst & Young (auditor)", ["ernst"], "parties"),
            ("acquitted, June 2005", ["acquit"], "outcome"),
            ("Don Siegelman bribery conviction (2006)", ["siegelman"], "outcome"),
            ("civil / SEC settlement; Scrushy ordered to repay bonuses", ["civil", "repay", "disgorge", "2.9 billion", "$2.8"], "outcome"),
            ("renamed Encompass Health (2018)", ["encompass"], "outcome"),
        ],
    },
    "peregrine": {
        "label": "Peregrine Systems (2002)", "year": 2002, "family": "accounting", "expected": "low",
        "wiki": ["Peregrine Systems"],
        "sketch": (
            "A San Diego maker of infrastructure- and asset-management software disclosed in 2002 that it had overstated revenue by "
            "roughly half a billion dollars over eleven quarters, by booking sales to resellers that were contingent on resale under "
            "undisclosed side agreements and by selling the resulting receivables to banks. It restated, dismissed its auditors, filed "
            "for Chapter 11 the same year and sold its help-desk division to a rival. Eight former executives were indicted in 2004; "
            "the former chief executive later pleaded guilty and received an eight-year sentence. The board chairman at the time owned "
            "a Major League Baseball team."
        ),
        "answer_keys": ["peregrine"],
        "name": "the Peregrine Systems accounting fraud (2002-2008)",
        "rubric": [
            ("Stephen Gardner (CEO)", ["gardner"], "people"),
            ("Matthew Gless (CFO)", ["gless"], "people"),
            ("John Moores (chairman, Padres owner)", ["moores"], "people"),
            ("channel stuffing / side letters with resellers", ["channel stuff", "side letter", "side agreement", "reseller"], "allegations"),
            ("~$500 million revenue overstatement", ["500 million", "509", "$0.5 billion", "half a billion"], "allegations"),
            ("factoring / selling receivables to banks", ["factor", "receivable"], "allegations"),
            ("Arthur Andersen / KPMG auditors", ["andersen", "kpmg"], "parties"),
            ("Chapter 11, September 2002", ["chapter 11", "bankrupt", "2002"], "events"),
            ("Remedy division sold to BMC", ["remedy", "bmc"], "events"),
            ("acquired by Hewlett-Packard (2005)", ["hewlett", "hp"], "outcome"),
            ("2004 indictments of eight executives", ["indict", "eight"], "events"),
            ("Gardner's eight-year sentence (2008)", ["eight years", "8 years", "eight-year", "97 months"], "outcome"),
            ("San Diego", ["san diego"], "parties"),
        ],
    },
    "mckesson_robbins": {
        "label": "McKesson & Robbins (1938)", "year": 1938, "family": "accounting", "expected": "low",
        "wiki": ["McKesson and Robbins scandal", "McKesson & Robbins scandal (1938)"],
        "sketch": (
            "In 1938 a large American drug wholesaler was found to carry about $19 million of fictitious inventory and receivables, "
            "roughly a fifth of its assets, attributed to a crude-drug trading division that did not exist outside its ledgers. The "
            "company's president was a convicted swindler living under an assumed name, assisted by three brothers also under aliases; "
            "he shot himself when the scheme was exposed. The auditors had confirmed inventories and receivables only against documents "
            "management supplied. The case produced the SEC's first major accounting investigation and new auditing standards requiring "
            "physical observation of inventory and direct confirmation of receivables."
        ),
        "answer_keys": ["mckesson", "musica", "coster"],
        "name": "the McKesson & Robbins fraud of 1938",
        "rubric": [
            ("Philip Musica", ["musica"], "people"),
            ("alias F. Donald Coster", ["coster"], "people"),
            ("brothers under aliases (Vernard / Dietrich)", ["brother", "vernard", "dietrich"], "people"),
            ("Price Waterhouse (auditor)", ["price waterhouse"], "parties"),
            ("fictitious crude-drug inventory / receivables", ["fictitious", "nonexistent", "non-existent", "fake", "phantom"], "allegations"),
            ("~$19 million (of ~$87m assets)", ["19 million", "$19", "$21", "20 million"], "allegations"),
            ("crude drug department", ["crude drug"], "allegations"),
            ("fictitious Canadian warehouses (Montreal)", ["canad", "montreal"], "allegations"),
            ("Julian Thompson (treasurer) exposed it", ["thompson"], "people"),
            ("Coster's suicide, December 1938", ["suicide", "shot himself", "killed himself"], "events"),
            ("SEC investigation and 1939-40 report", ["sec", "securities and exchange"], "outcome"),
            ("auditing standards: observe inventory, confirm receivables", ["observ", "confirm"], "outcome"),
            ("Bridgeport / Fairfield, Connecticut", ["connecticut", "bridgeport", "fairfield"], "parties"),
        ],
    },
    "equity_funding": {
        "label": "Equity Funding (1973)", "year": 1973, "family": "accounting", "expected": "low",
        "wiki": ["Equity Funding Corporation of America", "Equity Funding"],
        "sketch": (
            "A Los Angeles life-insurance and mutual-fund conglomerate collapsed in 1973 after a former employee told a securities "
            "analyst that it had manufactured tens of thousands of fictitious life-insurance policies — roughly two-thirds of its "
            "book — and sold them to reinsurers for cash, using computer programs and after-hours sessions at which staff forged "
            "policy files, plus forged bonds. The scheme ran for most of a decade. The chairman and some twenty executives were "
            "convicted, the company went into bankruptcy and its auditors were charged. The analyst who spread the warning was "
            "himself censured by the SEC, and his Supreme Court appeal became a leading insider-trading precedent."
        ),
        "answer_keys": ["equity funding"],
        "name": "the Equity Funding Corporation of America fraud (1973)",
        "rubric": [
            ("Stanley Goldblum (chairman)", ["goldblum"], "people"),
            ("Ray Dirks (analyst)", ["dirks"], "people"),
            ("Ronald Secrist (whistle-blower)", ["secrist"], "people"),
            ("Fred Levin (executive VP)", ["levin"], "people"),
            ("~64,000 fictitious policies", ["64,000", "fictitious polic", "bogus polic", "fake polic", "phony polic", "nonexistent polic"], "allegations"),
            ("sold to reinsurers for cash", ["reinsur"], "allegations"),
            ("computer-assisted fraud", ["computer"], "allegations"),
            ("forged bonds / counterfeit securities", ["forged bond", "counterfeit", "bonds"], "allegations"),
            ("auditors Wolfson Weiner / Seidman & Seidman charged", ["wolfson", "seidman", "auditor"], "parties"),
            ("Los Angeles", ["los angeles"], "parties"),
            ("Chapter X bankruptcy, April 1973", ["bankrupt", "chapter x", "1973"], "events"),
            ("reorganised as Orion Capital", ["orion"], "outcome"),
            ("Dirks v. SEC (1983)", ["dirks v", "supreme court", "1983"], "outcome"),
            ("Goldblum and ~20 executives convicted", ["convict", "guilty"], "outcome"),
        ],
    },
    # ------------------------------------------------------------------ opioids
    "purdue": {
        "label": "Purdue Pharma / Sacklers", "year": 2019, "family": "opioids", "expected": "high",
        "wiki": ["Purdue Pharma"],
        "sketch": (
            "A privately held Connecticut pharmaceutical company owned by a single family launched an extended-release opioid "
            "painkiller in 1996 and marketed it as carrying a low risk of addiction because of its slow release. The company and "
            "three executives pleaded guilty to misbranding in 2007, paying about $600 million. Facing thousands of suits from states, "
            "cities and counties consolidated in a federal multidistrict proceeding, it filed for Chapter 11 in 2019 and pleaded "
            "guilty again in 2020. A plan releasing the owning family from civil liability in exchange for several billion dollars was "
            "struck down by the Supreme Court in 2024."
        ),
        "answer_keys": ["purdue", "oxycontin", "sackler"],
        "name": "the opioid litigation and bankruptcy of Purdue Pharma and the Sackler family (2007-2024)",
        "rubric": [
            ("Sackler family owners", ["sackler"], "parties"),
            ("OxyContin", ["oxycontin"], "allegations"),
            ("Stamford, Connecticut", ["stamford", "connecticut"], "parties"),
            ("Richard Sackler", ["richard sackler"], "people"),
            ("2007 misbranding plea, ~$600m (Friedman, Udell, Goldenheim)", ["2007", "misbrand", "600 million", "634"], "events"),
            ("MDL 2804 / Judge Polster", ["polster", "2804", "multidistrict", "mdl"], "parties"),
            ("Chapter 11, September 2019, White Plains (Judge Drain)", ["2019", "drain", "white plains", "chapter 11"], "events"),
            ("2020 guilty plea, $8.3bn in penalties", ["2020", "8 billion", "8.3"], "events"),
            ("Harrington v. Purdue Pharma (2024)", ["harrington", "supreme court", "2024"], "outcome"),
            ("non-consensual third-party releases", ["third-party release", "third party release", "nonconsensual", "non-consensual", "release"], "allegations"),
            ("Sackler contribution ~$6bn (later ~$7.4bn)", ["6 billion", "$6", "5.5", "7.4", "4.5 billion"], "outcome"),
            ("McKinsey's role / settlement", ["mckinsey"], "parties"),
            ("Massachusetts AG Healey complaint (2018)", ["healey", "massachusetts"], "events"),
            ("2010 abuse-deterrent reformulation", ["reformulat", "abuse-deterrent", "abuse deterrent", "2010"], "events"),
            ("Knoa Pharma successor", ["knoa"], "outcome"),
            ("Dopesick / Empire of Pain", ["dopesick", "empire of pain", "keefe", "macy"], "events"),
        ],
    },
    "insys": {
        "label": "Insys Therapeutics (2019)", "year": 2019, "family": "opioids", "expected": "mid",
        "wiki": ["Insys Therapeutics"],
        "sketch": (
            "An Arizona pharmaceutical company sold a fentanyl sublingual spray approved only for breakthrough cancer pain. Federal "
            "prosecutors in Boston charged that it paid doctors sham 'speaker programme' fees to prescribe the spray to patients "
            "without cancer and ran a reimbursement unit that misled insurers about diagnoses. In 2019 its founder, an Indian-born "
            "billionaire, and four other executives were convicted of racketeering conspiracy, the first such conviction of "
            "pharmaceutical executives in the opioid crisis; the founder received five and a half years. A sales executive had "
            "performed in a rap video about dose titration. The company filed for bankruptcy days after settling with the government."
        ),
        "answer_keys": ["insys", "subsys", "kapoor"],
        "name": "the Insys Therapeutics (Subsys) racketeering case (2016-2020)",
        "rubric": [
            ("John Kapoor (founder)", ["kapoor"], "people"),
            ("Subsys fentanyl spray", ["subsys"], "allegations"),
            ("fentanyl", ["fentanyl"], "allegations"),
            ("sham speaker programmes / kickbacks", ["speaker", "kickback", "bribe"], "allegations"),
            ("breakthrough cancer pain label", ["cancer"], "allegations"),
            ("Insys Reimbursement Center misled insurers", ["reimbursement", "prior authoriz", "insurer"], "allegations"),
            ("Alec Burlakoff (sales VP, pleaded)", ["burlakoff"], "people"),
            ("Michael Babich (CEO, pleaded)", ["babich"], "people"),
            ("Sunrise Lee / Gurry / Simon / Rowan convicted", ["sunrise lee", "gurry", "rowan", "simon"], "people"),
            ("'titration' rap video", ["rap", "video"], "events"),
            ("RICO conspiracy conviction, May 2019", ["racketeer", "rico"], "outcome"),
            ("Kapoor sentenced to 66 months (Jan 2020)", ["66 months", "5.5 years", "five and a half", "five-and-a-half"], "outcome"),
            ("$225m DOJ settlement; Chapter 11 June 2019", ["225 million", "bankrupt", "chapter 11"], "outcome"),
            ("Judge Allison Burroughs, D. Mass.", ["burroughs", "boston", "massachusetts"], "parties"),
            ("Chandler, Arizona", ["chandler", "arizona"], "parties"),
        ],
    },
    "rdc": {
        "label": "Rochester Drug Co-operative (2019)", "year": 2019, "family": "opioids", "expected": "low",
        "wiki": ["Rochester Drug Co-operative", "Rochester Drug Cooperative"],
        "sketch": (
            "In April 2019 a regional pharmaceutical distributor in upstate New York, owned co-operatively by its member pharmacies, "
            "became the first drug distributor criminally charged in the opioid crisis. Manhattan federal prosecutors alleged that it "
            "shipped tens of millions of oxycodone and fentanyl doses to pharmacies its own compliance staff had flagged, and reported "
            "only a handful of suspicious orders to the DEA over several years while identifying thousands internally. The company "
            "entered a deferred-prosecution agreement with a $20 million penalty; its former chief executive was indicted for narcotics "
            "conspiracy and later convicted; its former compliance chief pleaded guilty. The company filed for bankruptcy the next year."
        ),
        "answer_keys": ["rochester drug", "rdc", "doud"],
        "name": "the criminal case against Rochester Drug Co-operative and its CEO Laurence Doud (2019-2022)",
        "rubric": [
            ("Laurence Doud III (CEO)", ["doud"], "people"),
            ("William Pietruszewski (compliance chief)", ["pietruszewski"], "people"),
            ("deferred-prosecution agreement", ["deferred prosecution", "deferred-prosecution", "dpa"], "outcome"),
            ("$20 million penalty", ["20 million", "$20"], "outcome"),
            ("SDNY / U.S. Attorney Geoffrey Berman", ["southern district", "manhattan", "berman"], "parties"),
            ("oxycodone and fentanyl shipments", ["oxycodone", "fentanyl"], "allegations"),
            ("suspicious orders: ~8,300 flagged, 4 reported", ["suspicious order", "8,300", "four reports", "only four"], "allegations"),
            ("DEA", ["dea", "drug enforcement"], "parties"),
            ("Chapter 11, March 2020", ["bankrupt", "chapter 11", "2020"], "outcome"),
            ("Doud convicted Jan 2022; 27 months", ["convict", "27 months", "guilty"], "outcome"),
            ("pharmacy-owned co-operative, Rochester NY", ["cooperative", "co-operative", "member pharmac", "rochester"], "parties"),
            ("Judge George Daniels", ["daniels"], "parties"),
        ],
    },
    # Endo itself is a study matter (contam/matter.py: SKETCHES / RUBRICS "endo") and joins the ladder through the study rungs in
    # score._ladder_summary, so it is not duplicated here. Teva and JUUL are the other two candidate held-out OIDA/IDL productions.
    "teva": {
        "label": "Teva / Actavis opioids (2022)", "year": 2022, "family": "opioids", "expected": "mid",
        "wiki": ["Teva Pharmaceutical Industries"],
        "sketch": (
            "The world's largest generic-drug maker, headquartered in Israel with a large U.S. generics business acquired from an "
            "Irish-domiciled rival in 2016, was sued by states and local governments over opioids on two fronts: its branded fentanyl "
            "products for breakthrough cancer pain (a lozenge on a stick and a buccal tablet) marketed, the plaintiffs said, for "
            "ordinary chronic pain; and its position as one of the largest suppliers of generic oxycodone and hydrocodone. It was a "
            "defendant in the first federal bellwether and in a 2021 California bench trial that the manufacturers won. In 2022 it "
            "agreed to a nationwide settlement of up to about $4.25 billion over thirteen years, partly in cash and partly in supplies "
            "of its generic overdose-reversal nasal spray."
        ),
        "answer_keys": ["teva", "actavis", "cephalon"],
        "name": "the opioid litigation against Teva Pharmaceuticals, Cephalon and Actavis (2014-2023)",
        "rubric": [
            ("Actiq (fentanyl lozenge)", ["actiq", "lollipop", "lozenge"], "allegations"),
            ("Fentora (fentanyl buccal tablet)", ["fentora"], "allegations"),
            ("Cephalon acquired 2011", ["cephalon"], "parties"),
            ("Actavis Generics acquired from Allergan (2016)", ["actavis", "allergan"], "parties"),
            ("off-label marketing beyond breakthrough cancer pain", ["off-label", "off label", "cancer pain", "breakthrough"], "allegations"),
            ("2008 Cephalon DOJ settlement ($425m) over Actiq / Gabitril / Provigil", ["425", "2008", "provigil", "gabitril"], "events"),
            ("generic oxycodone / hydrocodone supplier", ["oxycodone", "hydrocodone", "generic"], "allegations"),
            ("Track One bellwether (Cuyahoga / Summit) settled Oct 2019", ["cuyahoga", "summit", "bellwether", "track one", "2019"], "events"),
            ("California bench trial win, Nov 2021 (Judge Wilson)", ["california", "orange county", "wilson", "2021"], "events"),
            ("New York trial, Dec 2021 jury verdict against Teva", ["new york", "suffolk", "nassau", "jury", "verdict"], "events"),
            ("global settlement up to ~$4.25bn over 13 years (2022)", ["4.25", "4.2 billion", "4.3 billion", "13 years", "thirteen"], "outcome"),
            ("naloxone nasal spray (generic Narcan) in kind", ["naloxone", "narcan", "nasal spray", "in kind"], "outcome"),
            ("Petah Tikva / Tel Aviv, Israel", ["israel", "petah tikva", "tel aviv"], "parties"),
            ("Judge Dan Polster, MDL 2804", ["polster", "2804", "mdl"], "parties"),
        ],
    },
    "juul": {
        "label": "JUUL Labs (2019-23)", "year": 2022, "family": "consumer", "expected": "high",
        "wiki": ["Juul", "Juul Labs"],
        "sketch": (
            "A San Francisco start-up launched a sleek nicotine-salt vaporiser in 2015 with fruit and dessert flavours and a social-media "
            "campaign featuring young models; within three years it held about three-quarters of the U.S. e-cigarette market and a "
            "tobacco giant bought a 35 percent stake at a valuation of $38 billion. School districts, states and a federal multidistrict "
            "litigation accused it of marketing to teenagers and misrepresenting nicotine content; the FDA ordered its products off the "
            "market in 2022 before staying the order. It paid roughly $1.7 billion in a 2022-23 global settlement, a further $462 "
            "million to six states, and the tobacco investor wrote its stake down by more than 95 percent. Its internal documents "
            "were later placed in a public university archive as part of the settlements."
        ),
        "answer_keys": ["juul"],
        "name": "the JUUL Labs youth-vaping litigation and settlements (2018-2023)",
        "rubric": [
            ("Altria 35% stake, Dec 2018, $12.8bn ($38bn valuation)", ["altria", "35%", "35 percent", "12.8", "38 billion"], "events"),
            ("Pax Labs spin-out; founders James Monsees / Adam Bowen", ["pax", "monsees", "bowen"], "parties"),
            ("mango / creme / fruit flavours", ["mango", "fruit", "flavor", "flavour", "creme"], "allegations"),
            ("'Vaporized' launch campaign (2015) with young models", ["vaporized", "young models", "times square", "launch campaign"], "allegations"),
            ("nicotine-salt formulation; 5% pods", ["nicotine salt", "nicotine-salt", "5%", "59 mg"], "allegations"),
            ("Judge William Orrick, N.D. Cal. MDL 2913", ["orrick", "2913", "northern district of california", "mdl"], "parties"),
            ("San Francisco Unified bellwether; school districts", ["school district", "san francisco unified", "sfusd"], "parties"),
            ("FDA marketing denial order, June 2022, stayed", ["marketing denial", "denial order", "june 2022", "stay"], "events"),
            ("~$1.7bn global settlement (Dec 2022) with ~10,000 plaintiffs", ["1.7 billion", "$1.7", "1.2 billion", "10,000"], "outcome"),
            ("$462m settlement with six states incl. NY & CA (Apr 2023)", ["462", "six states"], "outcome"),
            ("$438.5m settlement with 34 states (Sept 2022)", ["438", "34 states", "33 states"], "outcome"),
            ("North Carolina $40m (2021), first state settlement", ["north carolina", "40 million"], "outcome"),
            ("Altria write-down / exit; later NJOY purchase", ["write-down", "writedown", "wrote down", "njoy", "impair"], "outcome"),
            ("JUUL documents in the UCSF Industry Documents Library", ["ucsf", "industry documents", "truth tobacco", "archive"], "outcome"),
            ("K.C. Crosthwaite (CEO from 2019, ex-Altria)", ["crosthwaite"], "people"),
        ],
    },
    # ------------------------------------------------------------------ e-mail and public records in public life
    "clinton_email": {
        "label": "Clinton e-mail server (2015-16)", "year": 2016, "family": "email", "expected": "high",
        "wiki": ["Hillary Clinton email controversy"],
        "sketch": (
            "A former U.S. Secretary of State was found in 2015 to have used a private e-mail server at her home for official business "
            "throughout her four-year tenure. About 30,000 work e-mails were turned over to the department and released under FOIA in "
            "monthly tranches; a similar number had been deleted as personal. The FBI investigated the handling of classified "
            "information; its director announced in July 2016 that no charges would be recommended while calling the conduct "
            "'extremely careless', then told Congress eleven days before a presidential election that the inquiry had been reopened "
            "after e-mails were found on a laptop belonging to an aide's husband, and closed it again two days before the vote."
        ),
        "answer_keys": ["clinton"],
        "name": "the Hillary Clinton private e-mail server controversy and FBI investigation (2015-2016)",
        "rubric": [
            ("James Comey (FBI director)", ["comey"], "people"),
            ("private server at Chappaqua home", ["chappaqua", "home server", "private server", "basement"], "allegations"),
            ("clintonemail.com domain", ["clintonemail"], "allegations"),
            ("Huma Abedin", ["abedin"], "people"),
            ("Anthony Weiner's laptop", ["weiner", "laptop"], "events"),
            ("Platte River Networks / Datto", ["platte river", "datto"], "parties"),
            ("Cheryl Mills / Bryan Pagliano", ["mills", "pagliano"], "people"),
            ("~30,000 e-mails deleted; BleachBit", ["30,000", "31,000", "33,000", "bleachbit"], "allegations"),
            ("'extremely careless', July 5 2016", ["extremely careless", "july 2016", "july 5"], "events"),
            ("October 28 2016 letter to Congress", ["october 28", "letter to congress", "oct. 28"], "events"),
            ("classified / Top Secret / SAP material", ["classified", "top secret", "special access"], "allegations"),
            ("Benghazi Committee discovered it", ["benghazi", "gowdy"], "events"),
            ("FOIA litigation (Judicial Watch) / monthly releases", ["foia", "judicial watch", "freedom of information"], "events"),
            ("State Dept inspector general report (May 2016)", ["inspector general", "oig"], "events"),
            ("no charges; 2016 election impact", ["no charges", "not recommend", "declin", "election"], "outcome"),
        ],
    },
    "bridgegate": {
        "label": "Bridgegate (2013)", "year": 2013, "family": "email", "expected": "mid",
        "wiki": ["Fort Lee lane closure scandal"],
        "sketch": (
            "For four days in September 2013, two of the three local access lanes from a New Jersey borough onto the world's busiest "
            "bridge were closed without notice, causing gridlock on the first day of school. Prosecutors alleged that the governor's "
            "deputy chief of staff and an executive of the bi-state bridge authority ordered the closures, under cover of a 'traffic "
            "study', to punish the borough's Democratic mayor for not endorsing the Republican governor's re-election. An e-mail "
            "reading 'Time for some traffic problems in [the borough]' was the key exhibit. Two officials were convicted in 2016; a third "
            "pleaded guilty and testified. The Supreme Court unanimously overturned the convictions in 2020, holding that political "
            "retaliation that does not aim to obtain money or property is not federal fraud."
        ),
        "answer_keys": ["bridgegate", "fort lee", "george washington bridge", "christie"],
        "name": "the Fort Lee lane closure scandal ('Bridgegate', 2013-2020)",
        "rubric": [
            ("Chris Christie (governor)", ["christie"], "people"),
            ("Bridget Anne Kelly (deputy chief of staff)", ["kelly"], "people"),
            ("Bill Baroni (Port Authority deputy executive director)", ["baroni"], "people"),
            ("David Wildstein (cooperating witness)", ["wildstein"], "people"),
            ("Port Authority of NY & NJ", ["port authority"], "parties"),
            ("Mayor Mark Sokolich of Fort Lee", ["sokolich", "fort lee"], "parties"),
            ("George Washington Bridge", ["george washington bridge", "gwb"], "events"),
            ("'time for some traffic problems' e-mail", ["traffic problems"], "allegations"),
            ("'traffic study' cover story", ["traffic study"], "allegations"),
            ("September 9-13, 2013", ["september 2013", "sept. 2013", "2013"], "events"),
            ("wire fraud / civil-rights charges; 'property' theory", ["wire fraud", "property", "civil rights"], "allegations"),
            ("Kelly v. United States (2020), Kagan, unanimous", ["kelly v", "supreme court", "kagan", "unanimous"], "outcome"),
            ("Judge Susan Wigenton, D.N.J.", ["wigenton", "newark"], "parties"),
            ("Mastro / Gibson Dunn internal report", ["mastro", "gibson dunn"], "events"),
            ("Christie's 2016 presidential bid damaged", ["presidential", "2016"], "outcome"),
        ],
    },
    "sony_hack": {
        "label": "Sony Pictures hack (2014)", "year": 2014, "family": "email", "expected": "mid",
        "wiki": ["2014 Sony Pictures hack"],
        "sketch": (
            "In November 2014 a Hollywood studio owned by a Japanese electronics group had its network wiped and tens of thousands of "
            "internal e-mails, unreleased films, employee medical records and salary data posted online by a group calling itself "
            "'Guardians of Peace'. The U.S. government attributed the attack to North Korea, which had threatened retaliation over a "
            "comedy depicting the assassination of its leader; the studio briefly cancelled the film's theatrical release and the "
            "President said publicly that it had made a mistake. Leaked e-mails between the studio's co-chair and a producer, including "
            "jokes about the President's taste in films, led to her departure. Employees sued over the exposure of their data and settled."
        ),
        "answer_keys": ["sony"],
        "name": "the 2014 Sony Pictures Entertainment hack and its aftermath",
        "rubric": [
            ("Amy Pascal (co-chair)", ["pascal"], "people"),
            ("Scott Rudin (producer) e-mails", ["rudin"], "people"),
            ("Michael Lynton (CEO)", ["lynton"], "people"),
            ("The Interview (Rogen / Franco)", ["the interview", "rogen", "franco"], "events"),
            ("Guardians of Peace", ["guardians of peace", "gop"], "parties"),
            ("North Korea / Lazarus Group attribution", ["north korea", "lazarus", "dprk", "pyongyang"], "parties"),
            ("Kim Jong-un", ["kim jong"], "people"),
            ("Obama: 'made a mistake'", ["obama", "president"], "events"),
            ("wiper malware (Destover)", ["wiper", "destover", "malware", "wiped"], "allegations"),
            ("Christmas Day limited / online release", ["christmas", "online", "limited release", "independent theat"], "outcome"),
            ("January 2015 sanctions on North Korea", ["sanction"], "outcome"),
            ("WikiLeaks published the archive (April 2015)", ["wikileaks"], "events"),
            ("employee class action settled (~$8m)", ["class action", "employees sued", "settle"], "outcome"),
            ("Park Jin Hyok indicted (2018)", ["park jin", "indict"], "outcome"),
            ("Spider-Man / Marvel, Jolie e-mails", ["spider", "marvel", "jolie"], "events"),
        ],
    },
    # ------------------------------------------------------------------ medical devices
    "depuy_asr": {
        "label": "DePuy ASR hip (2010)", "year": 2010, "family": "devices", "expected": "mid",
        "wiki": ["DePuy Synthes", "DePuy"],
        "sketch": (
            "In August 2010 the orthopaedics subsidiary of the world's largest healthcare company recalled a metal-on-metal hip "
            "resurfacing system and its total-hip version worldwide after a national joint registry reported revision rates of around "
            "12-13% at five years, several times the norm. Some 93,000 devices had been implanted. Thousands of suits were consolidated "
            "in federal court in Ohio; the first bellwether verdict, in Los Angeles in 2013, awarded $8.3 million. The company agreed in "
            "November 2013 to pay about $2.5 billion to resolve roughly 8,000 revision cases, later extended. Internal documents "
            "suggested the company had known of the design's problems well before the recall."
        ),
        "answer_keys": ["depuy", "asr", "johnson & johnson", "johnson and johnson", "j&j"],
        "name": "the DePuy ASR metal-on-metal hip recall and litigation (2010-2015)",
        "rubric": [
            ("Johnson & Johnson (parent)", ["johnson"], "parties"),
            ("ASR XL Acetabular / ASR Hip Resurfacing", ["asr"], "allegations"),
            ("metal-on-metal design; cobalt / chromium ions", ["metal-on-metal", "metal on metal", "cobalt", "chrom", "metallosis", "metal ion"], "allegations"),
            ("August 2010 worldwide recall", ["2010", "recall"], "events"),
            ("UK National Joint Registry 12-13% revision rate", ["national joint registry", "njr", "13%", "12%", "13 percent", "12 percent"], "events"),
            ("~93,000 implanted", ["93,000"], "allegations"),
            ("MDL 2197, Judge Katz, N.D. Ohio (Toledo)", ["katz", "toledo", "2197", "ohio"], "parties"),
            ("Kransky v. DePuy, LA, $8.3m (2013)", ["kransky", "8.3"], "events"),
            ("November 2013 settlement ~$2.5bn (later ~$4bn)", ["2.5 billion", "2.47", "4 billion", "settle"], "outcome"),
            ("Pinnacle sibling litigation (Dallas)", ["pinnacle", "dallas", "kinkeade"], "events"),
            ("Australian registry / 2009 withdrawal there", ["austral"], "events"),
            ("Warsaw, Indiana", ["warsaw"], "parties"),
            ("FDA 510(k) clearance route", ["510", "fda"], "allegations"),
            ("Andrew Ekdahl (DePuy president)", ["ekdahl"], "people"),
        ],
    },
    "earplugs": {
        "label": "3M Combat Arms earplugs (2019-23)", "year": 2023, "family": "devices", "expected": "mid",
        "wiki": ["3M Combat Arms earplugs", "3M earplug litigation", "Aearo Technologies"],
        "sketch": (
            "Dual-ended selective-attenuation earplugs issued to U.S. service members from about 2003 to 2015 were alleged to be too "
            "short to seal the ear canal and to loosen imperceptibly, after the manufacturer and the company it had acquired allegedly "
            "manipulated fit testing. A whistleblower suit under the False Claims Act, brought by a competitor, was settled with the "
            "government for $9.1 million in 2018 without admission. Veterans' claims then became the largest multidistrict litigation "
            "in U.S. history — roughly a quarter of a million plaintiffs in the Northern District of Florida. After bellwether verdicts "
            "of up to $77.5 million and a failed attempt to place the acquired subsidiary in bankruptcy, the manufacturer agreed in "
            "2023 to pay about $6 billion."
        ),
        "answer_keys": ["3m", "combat arms", "aearo"],
        "name": "the 3M Combat Arms Earplugs multidistrict litigation (2019-2023)",
        "rubric": [
            ("3M", ["3m"], "parties"),
            ("Aearo Technologies (acquired 2008)", ["aearo"], "parties"),
            ("Combat Arms Earplugs Version 2 (CAEv2)", ["combat arms", "caev2", "version 2"], "allegations"),
            ("Moldex-Metric qui tam / False Claims Act", ["moldex", "qui tam", "false claims"], "events"),
            ("$9.1 million 2018 settlement", ["9.1"], "events"),
            ("Judge M. Casey Rodgers, Pensacola", ["rodgers", "pensacola", "northern district of florida"], "parties"),
            ("~230,000-300,000 plaintiffs; largest MDL ever", ["largest", "300,000", "260,000", "250,000", "230,000", "240,000"], "events"),
            ("MDL 2885", ["2885"], "parties"),
            ("too short / flange fold / fit-test manipulation", ["flange", "too short", "loosen", "fit test", "fit-test"], "allegations"),
            ("hearing loss and tinnitus", ["tinnitus", "hearing loss"], "allegations"),
            ("bellwether verdicts up to $77.5m", ["77.5", "bellwether"], "events"),
            ("Aearo Chapter 11 (Indianapolis) dismissed 2023", ["chapter 11", "bankrupt", "graham", "indianapolis"], "events"),
            ("$6.01bn settlement, August 2023", ["6 billion", "6.01", "$6"], "outcome"),
            ("2003-2015 issue period", ["2003", "2015"], "events"),
        ],
    },
    "bair_hugger": {
        "label": "Bair Hugger warming MDL", "year": 2019, "family": "devices", "expected": "low",
        "wiki": ["Bair Hugger"],
        "sketch": (
            "A forced-air patient-warming system used in most U.S. operating rooms was alleged by hip- and knee-replacement patients "
            "to disrupt the operating room's laminar airflow and lift contaminated air from the floor into the surgical site, causing "
            "deep joint infections. The device's own inventor, having sold the business, had become its loudest critic and sold a "
            "competing conductive-fabric warmer; the manufacturer sued him for false advertising. About six thousand cases were "
            "consolidated in Minnesota federal court. The first bellwether ended in a defence verdict in 2018; the judge then excluded "
            "the plaintiffs' causation experts and dismissed the entire proceeding in 2019, the Eighth Circuit reinstated it in 2021, "
            "and the Supreme Court declined review."
        ),
        "answer_keys": ["bair hugger", "3m", "arizant", "augustine"],
        "name": "the Bair Hugger forced-air warming multidistrict litigation (MDL 2666, 2015-)",
        "rubric": [
            ("3M (owner since 2010)", ["3m"], "parties"),
            ("Arizant Healthcare (Eden Prairie, MN)", ["arizant", "eden prairie"], "parties"),
            ("Dr Scott Augustine (inventor turned critic)", ["augustine"], "people"),
            ("HotDog conductive warmer", ["hotdog", "hot dog"], "parties"),
            ("periprosthetic / deep joint infection", ["joint infection", "periprosthetic", "pji", "deep infection", "surgical site infection"], "allegations"),
            ("disrupted laminar airflow", ["laminar", "airflow", "air flow", "convection"], "allegations"),
            ("MDL 2666, Judge Joan Ericksen, D. Minn.", ["ericksen", "2666", "minnesota"], "parties"),
            ("Gareis bellwether defence verdict (May 2018)", ["gareis", "defense verdict", "defence verdict", "verdict for 3m"], "events"),
            ("experts excluded; MDL dismissed (2019)", ["daubert", "exclu", "dismiss", "summary judgment"], "events"),
            ("Eighth Circuit reinstated (Aug 2021)", ["eighth circuit", "8th circuit", "revers", "reinstat"], "outcome"),
            ("certiorari denied (2022)", ["certiorari", "cert", "supreme court"], "outcome"),
            ("FDA 2017 letter: continue using forced-air warming", ["fda"], "events"),
            ("3M v. Augustine false-advertising suit (Lanham Act)", ["false advertis", "lanham"], "events"),
            ("~5,000-6,000 cases", ["6,000", "5,000", "thousand"], "events"),
        ],
    },
    "dalkon": {
        "label": "Dalkon Shield (1970s-80s)", "year": 1985, "family": "devices", "expected": "mid",
        "wiki": ["Dalkon Shield"],
        "sketch": (
            "A crab-shaped intrauterine contraceptive device sold by a Virginia pharmaceutical company from 1971 to 1974 was linked to "
            "pelvic inflammatory disease, septic miscarriages and at least eighteen deaths, attributed to a multifilament tail string "
            "that wicked bacteria into the uterus. Hundreds of thousands of claims were filed. A federal judge in Minnesota rebuked the "
            "company's officers from the bench in 1984. The company sought Chapter 11 protection in 1985 and emerged in 1989 with a "
            "$2.5 billion trust for claimants, financed by its acquisition by a larger drug company. The episode helped produce the "
            "1976 law bringing medical devices under premarket regulation and became the model for mass-tort bankruptcies."
        ),
        "answer_keys": ["dalkon", "robins"],
        "name": "the Dalkon Shield litigation and the A.H. Robins bankruptcy (1974-1989)",
        "rubric": [
            ("A.H. Robins", ["robins"], "parties"),
            ("Richmond, Virginia", ["richmond", "virginia"], "parties"),
            ("IUD", ["iud", "intrauterine"], "allegations"),
            ("multifilament tail string wicking bacteria", ["multifilament", "string", "wick"], "allegations"),
            ("pelvic inflammatory disease", ["pelvic inflammatory", "pid"], "allegations"),
            ("septic spontaneous abortions / miscarriages", ["septic", "miscarriage", "abortion"], "allegations"),
            ("Hugh Davis (inventor, Johns Hopkins)", ["hugh davis", "davis", "johns hopkins"], "people"),
            ("Judge Miles Lord's 1984 rebuke", ["miles lord", "judge lord"], "people"),
            ("Chapter 11, August 1985, Judge Merhige", ["1985", "merhige", "chapter 11", "bankrupt"], "events"),
            ("$2.475bn Claimants Trust", ["2.4", "2.5 billion", "trust"], "outcome"),
            ("American Home Products acquisition (1989)", ["american home products", "ahp", "1989", "wyeth"], "outcome"),
            ("Medical Device Amendments of 1976", ["medical device amendments", "1976"], "outcome"),
            ("withdrawn from U.S. market 1974", ["1974"], "events"),
            ("18 deaths; ~200,000-300,000 claims", ["18 deaths", "eighteen", "300,000", "200,000", "327,000"], "allegations"),
            ("punitive damages / 'crab' shape", ["punitive", "crab"], "allegations"),
        ],
    },
    # ------------------------------------------------------------------ landmark events across the century
    "bhopal": {
        "label": "Bhopal (1984)", "year": 1984, "family": "landmark", "expected": "high",
        "wiki": ["Bhopal disaster"],
        "sketch": (
            "Shortly after midnight on 3 December 1984, about forty tonnes of a toxic intermediate gas leaked from a pesticide plant in "
            "central India majority-owned by a U.S. chemical company, killing thousands within days and injuring hundreds of thousands. "
            "Litigation filed in New York was dismissed in 1986 on forum non conveniens grounds; the Indian government, suing as the "
            "victims' sole representative under a special statute, settled in 1989 for $470 million. The U.S. company's chairman was "
            "arrested on arriving in India, released on bail and never returned; he died in 2014 with charges outstanding. Seven Indian "
            "managers were convicted of negligence in 2010 and sentenced to two years. The site remains contaminated."
        ),
        "answer_keys": ["bhopal", "union carbide"],
        "name": "the Bhopal gas disaster and the litigation against Union Carbide (1984-2010)",
        "rubric": [
            ("Union Carbide Corporation", ["union carbide", "ucc"], "parties"),
            ("Union Carbide India Ltd (UCIL)", ["ucil", "india ltd", "india limited", "indian subsidiary"], "parties"),
            ("methyl isocyanate (MIC)", ["methyl isocyanate", "mic"], "allegations"),
            ("Sevin (carbaryl) pesticide", ["sevin", "carbaryl"], "allegations"),
            ("Warren Anderson (chairman)", ["anderson"], "people"),
            ("tank E610; water ingress / runaway reaction", ["e610", "610", "water", "runaway", "exotherm"], "allegations"),
            ("safety systems off (scrubber, flare, refrigeration)", ["flare", "scrubber", "refriger", "safety system"], "allegations"),
            ("Judge Keenan; forum non conveniens (1986)", ["keenan", "forum non conveniens"], "events"),
            ("Bhopal Gas Leak Disaster Act 1985 (parens patriae)", ["gas leak disaster", "parens patriae", "sole representative", "1985"], "events"),
            ("$470 million settlement (Feb 1989)", ["470 million", "$470"], "outcome"),
            ("Supreme Court of India; curative petition", ["supreme court", "curative"], "outcome"),
            ("2010 convictions, two years (Keshub Mahindra)", ["2010", "two years", "two-year", "mahindra"], "outcome"),
            ("Dow Chemical acquired UCC (2001)", ["dow"], "outcome"),
            ("death toll (3,800 official; 15,000+ estimated)", ["3,800", "15,000", "2,259", "thousand"], "allegations"),
            ("Madhya Pradesh", ["madhya pradesh"], "parties"),
        ],
    },
    "texaco_pennzoil": {
        "label": "Texaco v. Pennzoil (1985-87)", "year": 1987, "family": "landmark", "expected": "mid",
        "wiki": ["Texaco, Inc. v. Pennzoil, Co.", "Pennzoil v. Texaco", "Texaco"],
        "sketch": (
            "In January 1984 an oil company reached an agreement in principle, announced in a press release and sealed with handshakes, "
            "to acquire three-sevenths of a California-based oil company controlled by a family trust and a museum. Days later a much "
            "larger oil major topped the bid and bought the whole target. The jilted bidder sued the acquirer in Texas state court for "
            "tortious interference with contract; a Houston jury in 1985 awarded $7.53 billion in compensatory and $3 billion in "
            "punitive damages, the largest civil verdict in history to that point. Unable to post a bond for the full amount, the "
            "acquirer filed for Chapter 11 in 1987 and settled for $3 billion. The trial judge was replaced mid-trial, and the "
            "plaintiff's famous lead lawyer had contributed to the first judge's campaign."
        ),
        "answer_keys": ["texaco", "pennzoil", "getty"],
        "name": "Pennzoil v. Texaco, the Getty Oil takeover litigation (1984-1988)",
        "rubric": [
            ("Texaco", ["texaco"], "parties"),
            ("Pennzoil", ["pennzoil"], "parties"),
            ("Getty Oil", ["getty"], "parties"),
            ("Gordon Getty / Sarah Getty Trust / Getty Museum", ["gordon getty", "trust", "museum"], "people"),
            ("Hugh Liedtke (Pennzoil chairman)", ["liedtke"], "people"),
            ("Joe Jamail (plaintiff's counsel)", ["jamail"], "people"),
            ("Judges Anthony Farris / Solomon Casseb", ["farris", "casseb"], "people"),
            ("tortious interference with contract", ["tortious interference"], "allegations"),
            ("agreement in principle / handshake / press release", ["agreement in principle", "handshake", "press release"], "allegations"),
            ("$7.53bn + $3bn punitive (Nov 1985)", ["7.53", "10.5", "10.3", "3 billion punitive", "$3 billion in punitive"], "outcome"),
            ("Harris County (Houston) jury", ["houston", "harris county"], "parties"),
            ("Texaco Chapter 11, April 1987", ["chapter 11", "1987", "bankrupt"], "events"),
            ("$3 billion settlement (Dec 1987 / 1988)", ["settle", "3 billion"], "outcome"),
            ("bond requirement; Pennzoil v. Texaco (U.S. 1987) abstention", ["bond", "supreme court", "abstention", "younger"], "events"),
            ("Carl Icahn's role", ["icahn"], "people"),
            ("Texas appeals court cut punitive award to $1bn", ["appeal", "1 billion", "reduced"], "outcome"),
        ],
    },
    "dieselgate": {
        "label": "Volkswagen Dieselgate (2015)", "year": 2015, "family": "landmark", "expected": "high",
        "wiki": ["Volkswagen emissions scandal"],
        "sketch": (
            "In September 2015 U.S. regulators announced that a German automaker had installed software in about eleven million diesel "
            "cars worldwide that detected emissions testing and enabled full pollution controls only then, allowing nitrogen-oxide "
            "emissions up to forty times the legal limit on the road. The chief executive resigned within days. The company pleaded "
            "guilty in the United States in 2017 and paid more than $25 billion in U.S. settlements, buybacks and fines; several "
            "executives were indicted, and one was arrested at Miami airport on his way home from holiday and sentenced to seven years. "
            "The discovery began with a small university laboratory's road tests, funded by a clean-transport nonprofit."
        ),
        "answer_keys": ["volkswagen", "vw", "dieselgate"],
        "name": "the Volkswagen diesel emissions scandal ('Dieselgate', 2015-)",
        "rubric": [
            ("Martin Winterkorn (CEO, resigned)", ["winterkorn"], "people"),
            ("defeat device software", ["defeat device"], "allegations"),
            ("EPA notice of violation, 18 September 2015", ["epa", "notice of violation", "september 2015"], "events"),
            ("CARB", ["carb", "california air resources"], "parties"),
            ("West Virginia University (CAFEE) road tests", ["west virginia", "wvu", "cafee"], "events"),
            ("ICCT funded the tests", ["icct", "international council on clean transportation"], "parties"),
            ("~11 million vehicles", ["11 million"], "allegations"),
            ("NOx up to 40x the limit", ["nox", "nitrogen oxide", "40 times", "forty times"], "allegations"),
            ("EA189 2.0 TDI engine", ["ea189", "2.0", "tdi"], "allegations"),
            ("Oliver Schmidt arrested in Miami, 7 years", ["schmidt", "seven years", "7 years"], "outcome"),
            ("Judge Charles Breyer, N.D. Cal. MDL", ["breyer", "san francisco", "mdl"], "parties"),
            ("$14.7bn consumer settlement / buybacks (2016)", ["14.7", "buyback", "buy-back", "buy back"], "outcome"),
            ("$4.3bn criminal / civil plea, January 2017", ["4.3", "guilty", "plea"], "outcome"),
            ("Audi / Porsche 3.0-litre; Rupert Stadler", ["audi", "porsche", "3.0", "stadler"], "events"),
            ("successors Matthias Müller / Herbert Diess", ["müller", "muller", "diess"], "people"),
            ("Braunschweig prosecutors / German trials", ["braunschweig", "brunswick", "german prosecutor", "munich"], "events"),
            ("Bosch supplied the engine software", ["bosch"], "parties"),
        ],
    },
    "theranos": {
        "label": "Theranos (2015-22)", "year": 2022, "family": "landmark", "expected": "high",
        "wiki": ["Theranos"],
        "sketch": (
            "A Silicon Valley blood-testing start-up founded by a university dropout claimed its proprietary device could run hundreds "
            "of tests on a finger-prick of blood, raised more than $700 million at a valuation near $9 billion, and operated testing "
            "centres inside a national pharmacy chain. A 2015 newspaper investigation, relying on whistle-blowers including a former "
            "laboratory employee and the grandson of a board member, showed that most tests ran on modified commercial analysers and "
            "that results were unreliable. Regulators banned the founder from the laboratory business; the SEC charged fraud in 2018; "
            "the founder was convicted on four counts in 2022 and sentenced to more than eleven years, and her former president and "
            "romantic partner to nearly thirteen."
        ),
        "answer_keys": ["theranos", "holmes"],
        "name": "the Theranos fraud and the trials of Elizabeth Holmes and Ramesh Balwani (2015-2022)",
        "rubric": [
            ("Elizabeth Holmes", ["holmes"], "people"),
            ("Ramesh 'Sunny' Balwani", ["balwani"], "people"),
            ("John Carreyrou / Wall Street Journal (Oct 2015)", ["carreyrou", "wall street journal", "wsj"], "events"),
            ("Tyler Shultz / Erika Cheung (whistle-blowers)", ["tyler shultz", "cheung"], "people"),
            ("Walgreens", ["walgreens"], "parties"),
            ("Safeway", ["safeway"], "parties"),
            ("Edison device / miniLab", ["edison", "minilab"], "allegations"),
            ("modified Siemens analysers", ["siemens", "commercial analyz", "commercial analys", "third-party"], "allegations"),
            ("CMS sanctions, Newark lab (2016)", ["cms", "newark", "sanction", "ban"], "events"),
            ("SEC fraud charges (March 2018)", ["sec", "securities and exchange"], "events"),
            ("Judge Edward Davila, San Jose", ["davila", "san jose"], "parties"),
            ("convicted on 4 counts, January 2022", ["four counts", "4 counts", "january 2022"], "outcome"),
            ("Holmes: 11 years 3 months", ["11 years", "135 months", "eleven years"], "outcome"),
            ("Balwani: ~13 years (155 months)", ["13 years", "155 months", "thirteen years", "12 years"], "outcome"),
            ("board: Shultz, Kissinger, Mattis", ["kissinger", "mattis", "george shultz"], "people"),
            ("$9bn valuation; ~$700m raised", ["9 billion", "700 million", "$9"], "allegations"),
            ("Bad Blood (2018)", ["bad blood"], "events"),
        ],
    },
    "ftx": {
        "label": "FTX (2022)", "year": 2022, "family": "landmark", "expected": "high",
        "wiki": ["Bankruptcy of FTX", "FTX"],
        "sketch": (
            "A Bahamas-based cryptocurrency exchange, among the largest in the world, collapsed in November 2022 within about ten days "
            "of a news report on the balance sheet of its founder's affiliated trading firm, revealing that roughly $8 billion of "
            "customer deposits had been lent to that firm and spent on venture bets, real estate, political donations and loans to "
            "insiders. The founder, a thirty-year-old MIT graduate and leading donor to a philanthropic movement, was extradited, "
            "convicted on seven counts in Manhattan in 2023 after three former lieutenants testified against him, and sentenced to "
            "25 years. The bankruptcy estate later proposed repaying customers in full at petition-date values."
        ),
        "answer_keys": ["ftx", "bankman", "sbf"],
        "name": "the collapse of FTX and the prosecution of Sam Bankman-Fried (2022-2024)",
        "rubric": [
            ("Sam Bankman-Fried", ["bankman", "sbf"], "people"),
            ("Alameda Research", ["alameda"], "parties"),
            ("Caroline Ellison", ["ellison"], "people"),
            ("Gary Wang / Nishad Singh", ["wang", "singh"], "people"),
            ("Binance / Changpeng Zhao", ["binance", "changpeng", "zhao", "cz"], "parties"),
            ("CoinDesk report, 2 November 2022", ["coindesk"], "events"),
            ("FTT token", ["ftt"], "allegations"),
            ("~$8 billion customer funds", ["8 billion", "$8"], "allegations"),
            ("John J. Ray III (restructuring CEO)", ["john ray", "ray iii", "john j. ray"], "people"),
            ("Chapter 11, Delaware, 11 November 2022", ["chapter 11", "delaware", "november 11", "nov. 11"], "events"),
            ("Judge Lewis Kaplan", ["kaplan"], "parties"),
            ("convicted on seven counts, November 2023", ["seven counts", "7 counts", "november 2023"], "outcome"),
            ("25 years (March 2024)", ["25 years", "25-year", "twenty-five"], "outcome"),
            ("Bahamas / Albany penthouse", ["bahamas", "nassau", "albany"], "parties"),
            ("political donations / straw donors; Ryan Salame", ["donation", "political contribution", "salame", "campaign finance"], "allegations"),
            ("effective altruism", ["effective altruism"], "people"),
            ("customers repaid in full at petition-date value", ["in full", "118", "petition date", "petition-date"], "outcome"),
            ("Michael Lewis, Going Infinite", ["michael lewis", "going infinite"], "events"),
        ],
    },
    # ------------------------------------------------------------------ post-cutoff controls
    "near": {
        "label": "Near Intelligence (2023 / SEC 2026)", "year": 2026, "family": "postcutoff", "expected": "none",
        "note": "straddles the cutoff: the company's December 2023 collapse was reported at the time; the SEC's complaint and its particulars are from 2026",
        "wiki": ["Near Intelligence"],
        "sketch": (
            "A location-data analytics company headquartered in Southern California, with operations in Singapore and India, went "
            "public in March 2023 by merging with a special-purpose acquisition company at a valuation near $1 billion, and filed for "
            "Chapter 11 nine months later after announcing that its financial statements could not be relied upon and that its chief "
            "executive and chief financial officer had been fired for cause. Securities regulators later alleged a round-trip scheme "
            "with the company's largest customer, an advertising-technology firm, in which the company wired money to the customer "
            "and the customer paid it back against fictitious invoices, inflating revenue by about 27 percent; and that the chief "
            "executive billed the rent of a luxury house to the company as 'professional services'."
        ),
        "answer_keys": ["near intelligence", "near inc", "mathews", "kludein", "mobilefuse"],
        "name": "the SEC's 2026 accounting-fraud case against the former CEO and CFO of Near Intelligence, Inc. (Anil Mathews and Rahul Agarwal)",
        "rubric": [
            ("Anil Mathews (CEO)", ["mathews"], "people"),
            ("Rahul Agarwal (CFO)", ["agarwal"], "people"),
            ("MobileFuse / Kenneth Harlan", ["mobilefuse", "harlan"], "parties"),
            ("round-trip revenue scheme", ["round-trip", "round trip", "roundtrip", "circular"], "allegations"),
            ("~27% revenue overstatement; $37.3m of $138.3m", ["27", "37.3", "138.3"], "allegations"),
            ("KludeIn I SPAC merger, March 2023", ["kludein", "spac", "special purpose acquisition"], "events"),
            ("Nasdaq ticker NIR", ["nasdaq", "nir"], "parties"),
            ("Pasadena, California", ["pasadena"], "parties"),
            ("Chapter 11, 8 December 2023", ["chapter 11", "bankrupt", "december 2023"], "events"),
            ("luxury residence billed as professional services", ["residence", "rental", "house", "professional services"], "allegations"),
            ("UberMedia acquisition (2021)", ["ubermedia"], "events"),
            ("SDNY complaint (2026)", ["southern district", "2026"], "events"),
        ],
    },
    "meyer": {
        "label": "Meyer Global Mgmt (SEC, Sept 2026)", "year": 2026, "family": "postcutoff", "expected": "none",
        "wiki": ["Meyer Global Management"],
        "sketch": (
            "On the last day of September 2026 securities regulators sued a private-fund adviser and its chief executive in Manhattan "
            "federal court, alleging that since late 2021 he had misappropriated assets of funds that held pre-IPO interests in a "
            "well-known private rocket and satellite company and other late-stage start-ups, used fund money for personal expenses, "
            "sent investors statements inflating their account values, required investors to sign releases to receive distributions "
            "smaller than they were owed, and let a fund forfeit a nearly $3 million position by failing to meet a capital call. The "
            "regulator seeks injunctions, disgorgement and penalties under the investment-adviser antifraud provisions."
        ),
        "answer_keys": ["meyer"],
        "name": "the SEC's September 2026 case against Meyer Global Management LLC and its CEO Owen Meyer",
        "rubric": [
            ("Owen E.H. Meyer", ["owen", "meyer"], "people"),
            ("Meyer Global Management LLC", ["meyer global", "mgm"], "parties"),
            ("SpaceX pre-IPO interests", ["spacex", "pre-ipo", "pre ipo"], "allegations"),
            ("misappropriation for personal expenses", ["misappropriat", "personal expense"], "allegations"),
            ("inflated account statements", ["inflat", "account value", "statements"], "allegations"),
            ("releases for reduced distributions", ["sign releases", "signed releases", "sign a release", "release accepting", "releases in exchange", "releases to receive", "general release"], "allegations"),
            ("forfeited ~$3m capital call", ["capital call", "forfeit", "3 million", "$3"], "allegations"),
            ("Investment Advisers Act antifraud", ["advisers act", "adviser"], "allegations"),
            ("S.D.N.Y., 30 September 2026", ["southern district", "manhattan", "september 2026", "2026"], "events"),
            ("conduct since December 2021", ["2021"], "events"),
        ],
    },
}

LADDER_ORDER = list(LADDER)

# where no article exists for the *matter*, the footprint falls back to the company's or person's page, which is broader than the case
FOOTPRINT_PROXY = {"texaco_pennzoil": "company article (Texaco)", "depuy_asr": "company article (DePuy Synthes)",
                   "healthsouth": "company article (Encompass Health)", "jebbush": "biography, not the governorship", "mnk": "company article",
                   "endo": "company article", "teva": "company article (Teva)", "juul": "company article (Juul)"}


# ------------------------------------------------------------------------------------------------ items

def ladder_items() -> list[dict]:
    """M0 + M1 items for every rung; same prompts and gold format as matter.py so they are scored by the same functions."""
    from .matter import MATTER_ID_SYSTEM, MATTER_RECALL_SYSTEM  # noqa: PLC0415
    out = []
    for key, r in LADDER.items():
        out.append({
            "item_id": f"matter_id:{key}",
            "probe": "matter_id",
            "corpus": "ladder",
            "system": MATTER_ID_SYSTEM,
            "user": f"{r['sketch']}\n\nWhich real company, person or case is this modelled on? Name it first, then give your reasons in a few sentences.",
            "gold": {"answer_keys": r["answer_keys"], "control": r["expected"] == "none", "template_keys": []},
            "meta": {"sketch": key, "kind": f"de-identified sketch (ladder: {FAMILY_LABEL[r['family']]})"},
        })
        out.append({
            "item_id": f"matter_recall:{key}",
            "probe": "matter_recall",
            "corpus": "ladder",
            "system": MATTER_RECALL_SYSTEM,
            "user": f"Describe {r['name']}: the parties, the key allegations or issues, the key people, the main events with dates, and the outcome.",
            "gold": {"rubric": [{"label": a, "keys": b, "cat": c, "in_context": False} for a, b, c in r["rubric"]],
                     "control": r["expected"] == "none", "template_keys": []},
            "meta": {"matter": key},
        })
    return out


# ------------------------------------------------------------------------------------------------ public footprint (Wikipedia)

UA = {"User-Agent": "jev-eval-contamination-probe/0.1 (research tool; local use)"}
# the study's own matters, so they appear on the same scale
STUDY_WIKI = {"enron": ["Enron scandal"], "mnk": ["Mallinckrodt"], "jebbush": ["Jeb Bush"], "microsoft": ["United States v. Microsoft Corp."],
              "veridian": [], "endo": ["Endo International", "Endo Pharmaceuticals", "Endo, Inc."]}


def _get(url: str, tries: int = 6):
    """GET JSON with patient backoff: Wikimedia rate-limits unauthenticated clients aggressively (HTTP 429)."""
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:  # 429 / 404
            if e.code == 404:
                return None
            time.sleep(10.0 * (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(5.0 * (i + 1))
    raise RuntimeError(f"gave up on {url}")


def _resolve(cands: list[str]) -> dict | None:
    if not cands:
        return None
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "titles": "|".join(cands), "prop": "info|langlinks", "lllimit": "500", "redirects": "1", "format": "json"})
    r = _get(url)
    if not r:
        return None
    pages = [p for p in r["query"]["pages"].values() if "missing" not in p]
    if not pages:
        return None
    # resolve each candidate to its page in candidate order; take the first that exists
    redirects = {x["from"]: x["to"] for x in r["query"].get("redirects", [])}
    by_title = {p["title"]: p for p in pages}
    for c in cands:
        t = redirects.get(c, c)
        if t in by_title:
            p = by_title[t]
            return {"title": p["title"], "length": p.get("length", 0), "langs": len(p.get("langlinks", []))}
    p = pages[0]
    return {"title": p["title"], "length": p.get("length", 0), "langs": len(p.get("langlinks", []))}


def _pageviews(title: str, start: str, end: str) -> int | None:
    t = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{t}/monthly/{start}/{end}"
    r = _get(url)
    if not r or "items" not in r:
        return None
    return int(sum(x["views"] for x in r["items"]))


def footprint(refresh: bool = False, fill_missing: bool = False, log=print) -> dict[str, dict]:
    """{key: {title, length, langs, views_12m}} for every rung and the study's matters; cached in data/contam/raw.
    fill_missing re-queries only the keys whose lookup failed (rate-limited) last time; genuinely absent articles stay absent."""
    cached = json.loads(FOOTPRINT_CACHE.read_text()) if FOOTPRINT_CACHE.exists() else {}
    if cached and not refresh and not fill_missing:
        return cached
    import datetime as dt  # noqa: PLC0415
    today = dt.date.today()
    first_this = today.replace(day=1)
    end_month = (first_this - dt.timedelta(days=1))  # last complete month
    start_month = (first_this - dt.timedelta(days=365)).replace(day=1)
    start, end = start_month.strftime("%Y%m01"), end_month.strftime("%Y%m01")
    out: dict[str, dict] = dict(cached) if fill_missing else {}
    allk = {**{k: v["wiki"] for k, v in LADDER.items()}, **STUDY_WIKI}
    for key, cands in allk.items():
        if fill_missing and out.get(key, {}).get("title"):
            continue
        if not cands:
            out[key] = {"title": None, "length": 0, "langs": 0, "views_12m": 0, "window": [start, end], "absent": True}
            continue
        try:
            res = _resolve(cands)
        except RuntimeError as e:
            log(f"  footprint {key}: {e}")
            out.setdefault(key, {"title": None, "length": 0, "langs": 0, "views_12m": 0, "window": [start, end], "failed": True})
            continue
        time.sleep(4.0)
        if res is None:
            out[key] = {"title": None, "length": 0, "langs": 0, "views_12m": 0, "window": [start, end], "absent": True}
            log(f"  footprint {key}: no article")
            continue
        try:
            pv = _pageviews(res["title"], start, end)
        except RuntimeError:
            pv = None
        time.sleep(4.0)
        out[key] = {**res, "views_12m": pv or 0, "window": [start, end]}
        log(f"  footprint {key}: {res['title']!r} {res['length']:,} bytes, {res['langs']} langs, {pv or 0:,} views")
        FOOTPRINT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        FOOTPRINT_CACHE.write_text(json.dumps(out, indent=1))
    FOOTPRINT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    FOOTPRINT_CACHE.write_text(json.dumps(out, indent=1))
    return out
