# Data and results licence

The code in this repository is MIT-licensed (see `../LICENSE`). The data files and results are covered by the terms below, per corpus. Where a licence is granted by the author it is **Creative Commons Attribution 4.0 International (CC BY 4.0)**, <https://creativecommons.org/licenses/by/4.0/>; attribute as "Ben Sexton, *Jev vs the LLMs: an eDiscovery relevance-review benchmark*, 2026" (see `../CITATION.cff`).

## 1. Veridian (`data/veridian/`, `veridian/`, `tasks/veridian.yaml`) — CC BY 4.0

A fully synthetic matter. Every company, product and person is fictional (`veridian/bible.md`). The documents were generated with Google's Gemini API from the author's manifests (`veridian/manifest*.jsonl`, `ediscovery_bench/synth/`); under the Gemini API terms the output belongs to the user. The author licenses the corpus, manifests, criteria and gold labels under CC BY 4.0. Generation is not reproducible (LLM sampling), so the corpus is shipped as-is.

## 2. Results and manifests — CC BY 4.0

`results/**` (aggregates in the repository; per-decision records in the GitHub Release, see `../results/README.md`), `site/public/cutoffs.json`, `data/trec/*_ids.jsonl`, `data/trec/{dev,seen}_ids.txt`, the criteria text in `tasks/*.yaml`, and the design notes' data tables are the author's work and are licensed under CC BY 4.0. Results files contain document ids, model labels, probabilities, latencies, token counts and costs; they contain no document text and no model prompts or completions (`raw` is empty in every row).

Model outputs were obtained from Anthropic, OpenAI, Google, TypeSafe AI and ConvAI (Laya) APIs/weights under each provider's terms. The Mallinckrodt gold labels are themselves the output of a three-model LLM panel (`meta.panel`); the Veridian gold labels were LLM-planned and LLM-audited. This is disclosed here and on the results site.

## 3. CUAD-derived files (`data/cuad/*.jsonl`, `data/cuad/ft_split.json`) — CC BY 4.0

Derived from the Contract Understanding Atticus Dataset (CUAD) v1, © The Atticus Project, licensed CC BY 4.0. Attribution:

> Dan Hendrycks, Collin Burns, Anya Chen, Spencer Ball. *CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review.* NeurIPS 2021 Datasets and Benchmarks. <https://www.atticusprojectai.org/cuad>, <https://github.com/TheAtticusProject/cuad>.

The upstream files (`data/cuad/raw/`) are not tracked; `bench cuad-build` downloads them from the Atticus Project repository and rebuilds the paragraph corpora. The derived files are redistributed under the same licence (CC BY 4.0) with the attribution above; the author's paragraph segmentation, clause mapping and splits are also CC BY 4.0.

## 4. TREC 2016 Total Recall / Jeb Bush e-mails (`data/trec/`) — not redistributed

The document collection is distributed by NIST under the TREC Total Recall usage agreement and is **not redistributed** with this repository; see `data/trec/README.md` for how to obtain it and regenerate the corpus files. The NIST topics and relevance judgments in `data/trec/raw/` are redistributed as-is from <https://trec.nist.gov/data/total-recall/> (US-government research data; NIST is the source of record, no licence is asserted by the author). The id manifests (`*_ids.jsonl`) are the author's sampling record and are CC BY 4.0.

## 5. Mallinckrodt opioid-litigation e-mails (`data/mallinckrodt/`) — reproduced for non-commercial research; rights remain with the original creators

Source: the **Opioid Industry Documents Archive** (UCSF Industry Documents Library and Johns Hopkins University), <https://www.industrydocuments.ucsf.edu/opioids/>. Each record's `meta.url` and `meta.bates` point to the archive copy. The documents were produced in *In re National Prescription Opiate Litigation* (MDL 2804) and related state actions and made public through court-approved agreements.

The e-mail text is reproduced here for non-commercial research (benchmarking document-review systems) in reliance on fair use and the archive's public access terms (<https://www.industrydocuments.ucsf.edu/copyright/>). **No licence is granted by the author for the document text**; copyright and other rights remain with the original creators and rights holders, and users must comply with the archive's terms, including its take-down policy. The author's contributions (sampling, stratification, panel-derived gold labels, gray flags, splits, `det300.jsonl` sample selection) are CC BY 4.0.

If you are a rights holder and object to the inclusion of a document, open an issue or contact the author and it will be removed.

## 6. Trademarks

Anthropic, Claude, OpenAI, GPT, Google, Gemini, Gemma, TypeSafe, Jev, ConvAI and Laya are trademarks or trade names of their respective owners. They, and the logo marks in `site/src/logos.tsx` and `site/src/logos/`, are used nominatively, to identify the systems evaluated, and no affiliation with or endorsement by any of these companies is implied.
