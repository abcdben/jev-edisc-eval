# Endo request sources

The eight requests in `tasks/endo.yaml` are grounded in two public complaints that plead the Endo opioid allegations
in detail. Both were fetched 2026-10-03 and converted with `pdftotext -layout`.

| File | Source | Used for |
|---|---|---|
| `Ohio_AG_complaint_2017.pdf` / `.txt` | State of Ohio ex rel. DeWine v. Purdue Pharma L.P. et al., Ross County C.P., filed 31 May 2017 — https://www.ohioattorneygeneral.gov/Files/Briefing-Room/News-Releases/Consumer-Protection/2017-05-31-Final-Complaint-with-Sig-Page.aspx | ¶106–107 (reformulated Opana ER "designed to be crush resistant"; undisclosed studies showing it could be ground and chewed; FDA 2013 letter), ¶123 (failure to set up a system for identifying and reporting suspicious prescribing; bonuses to reps for detailing later-arrested prescribers), ¶¶ on KOL-edited pamphlets, speakers bureau and APF/AAPM funding |
| `NYAG_opioid_complaint_2019.pdf` / `.txt` | People of the State of New York v. Purdue Pharma L.P. et al., Suffolk County Index No. 400016/2018, complaint filed 28 Mar 2019 — https://ag.ny.gov/sites/default/files/oag_opioid_lawsuit.pdf | ¶543–559: Endo's Opana ER revenue and promotional spend, ~164,000 New York detailing visits 2009–2013, 2011 training ("addiction to opioids is not common"), American Pain Foundation / National Initiative on Pain Control / painknowledge.com funding and editorial control, FDA's 2017 withdrawal request, the 2016 New York Assurance of Discontinuance (crush-resistance claims, "usually do not become addicted", "pseudoaddiction", detailing of suspect prescribers) |

Request pairs → allegation:

| Pair | Broad | Narrow | Complaint anchor |
|---|---|---|---|
| `opana` | Opana ER marketing / promotion / sales | abuse-deterrence and crush-resistance claims for the 2012 reformulation | Ohio ¶106–107; NY ¶559, ¶9199–9205 (Actavis suit) |
| `som` | controlled-substance order monitoring and DEA compliance (Endo / Par / Qualitest) | decisions to release, supply or not report a specific flagged order or customer | Ohio ¶123; NY ¶543 (generic opioids via Par / Qualitest); MDL 2804 distributor/manufacturer SOM claims |
| `promo` | sales training, messaging and speaker programmes on opioid risk (addiction, pseudoaddiction, dosing) | reps' observation / reporting of abuse or diversion signs and the decision to keep detailing a prescriber | NY ¶545, ¶559; Ohio ¶123, ¶1816 |
| `thirdparty` | funding of / work with pain-advocacy groups, KOLs and CME (APF, NIPC, painknowledge.com, AAPM) | editorial control over, or disclosure of Endo's role in, third-party pain content | NY ¶546; Ohio ¶1148, ¶1418, ¶1937 |

Also consulted (not stored): DOJ W.D. Va. press release on Endo Health Solutions' 2024 guilty plea for Opana ER
misbranding (https://www.justice.gov/usao-wdva/pr/endo-health-solutions-pleads-guilty-misbranding-opana-er); the FTC's
2016 Opana ER pay-for-delay complaint (https://www.ftc.gov/system/files/documents/cases/160331endocmpt.pdf) — the
latter concerns antitrust, not the opioid-marketing matter, and was not used for request drafting.

Corpus: UCSF/JHU Opioid Industry Documents Archive, collection "Endo Documents" (Endo International plc chapter 11,
Case No. 22-22549 (JLG), S.D.N.Y. Bankr.; production published to the archive 2024–2026). Emails only; text from the
archive's S3 OCR bucket. Sampling: `ediscovery_bench/endo/sample.py`.
