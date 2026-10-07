"""Pseudonymisation ablation: does case knowledge change classification?

The contamination probes (ediscovery_bench/contam) show that the models know the Enron *case* even though they have
not memorised the Enron *documents*. This package measures the effect of that knowledge on precision and recall by
classifying the same labelled documents twice: as they are (named) and with every knowledge-bearing name consistently
replaced (renamed). Baselines for the renaming cost (assumption-free): the Complaint K oil-spill requests on the same
mailbox (knowledge-poor) and the fictional Veridian corpus. Knowledge effect = Δ(J) − Δ(K) for every system. Four
systems are under test: GPT-5.6 Luna / Terra / Sol and Jev. Jev's vendor states it is not pre-trained on these corpora;
we treat that as a claim and test it with the same contrasts. A fourth arm adds knowledge instead of removing it:
Mallinckrodt with and without a one-page case brief.

  bench ablation-build   data/ablation/*.jsonl, mapping.json, mnk_brief.md
  bench ablation-leak    residual identification on renamed documents
  bench ablation-run     --pilot | full, per model
  bench ablation-report  results/ablation/summary.json, REPORT.md, ablation_report.html
"""
