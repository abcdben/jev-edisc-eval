"""Generalisation checks on the contamination study's central claim (design/06_contamination_probe.md, 'Generalisation checks').

  A  knowledge-dependence error analysis on Enron J     (knowdep.py;  Luna tags, no new classification calls)
  B  ranking stability across known / unknown matters  (ranking.py;  existing results only)
  C  counterfactual conflict documents                   (conflict.py; ~30 pairs per matter, four systems)
  D  knowledge injection on Veridian                     (inject.py;   fictional case brief prepended, four systems)

CLI: `bench verify build | run | report`. Results in results/verify/. Jev is a system under test throughout.
"""
