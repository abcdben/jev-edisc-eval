"""Classifier-native contamination tests for Jev (design/06_contamination_probe.md, "Classifier-native tests").

Jev is a decision model: it takes a document and a request and returns a call (and a Noul probability). The generative
contamination probes in `ediscovery_bench/contam/` cannot be posed to it. The tests here can be posed through that
interface, with the GPT-5.6 models as a comparison arm where cheap:

  T1  code-name swap          same document, real matter token vs fictional token of the same shape; nameless request
  T2  minimal-edit label flip public-qrels documents whose true relevance is flipped by a 1-2 sentence edit
  T3  paraphrase sensitivity  |delta p| between an original and a meaning-preserving paraphrase, by corpus (Jev returns p)
  T4  published vs unpublished labels  accuracy on judged vs matched unjudged documents of the same collection
  BT  bare-token check        header + one sentence naming Raptor / LJM2 / Chewco vs the fictional mapping, FAS 140

Jev is a system under test throughout. Results are reported as evidence consistent / inconsistent with the vendor's
statement that it is trained on synthetic data; nothing here proves it.

CLI: `bench jev-probe build | run | report`.  Data: data/jev_probe/.  Results: results/jev_probe/.
"""
