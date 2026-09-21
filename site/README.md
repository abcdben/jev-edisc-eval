# Results site

Interactive page over `results/findings.json` (written by `bench export-findings`).

```sh
# from the repo root, refresh the data first
.venv/bin/bench export-findings

cd site
npm install
npm run dev        # http://127.0.0.1:5173
npm run build      # static bundle in site/dist (open dist/index.html or host anywhere)
```

Two sections, both driven by the sticky control bar (corpus, TREC criteria, prompting arm, scope, gold labels):

- **Compare models**: pick any subset of the headline roster. Recall against precision with 95% interval boxes (or ranked rows with whiskers), plus review time and cost per 100,000 documents for the same selection.
- **Configurations of one model**: pick Jev or a Laya checkpoint and compare its ablation variants the same way. The recipe carried into the headline comparison is starred.

Every mark carries a hover tooltip with the counts and intervals behind it; every panel title has an (i) explaining the measurement.

**Consistency** (third card under each section): run-to-run disagreement from the determinism study, `bench determinism` → `results/determinism.json`, merged into `findings.json` by `bench export-findings`. Repeat runs are produced by `scripts/det_run.sh <arm>` (API models, this machine) and `scripts/gpu_box.sh det` (Laya, Gemma on a GPU box).

## Publishing

`scripts/deploy_site.sh` builds and force-pushes `site/dist` to [github.com/abcdben/tarcalc](https://github.com/abcdben/tarcalc), which GitHub Pages serves at https://tarcalc.com. If results changed, run `.venv/bin/bench export-findings` first. DNS at Namecheap: A records for `@` → 185.199.108.153 / .109.153 / .110.153 / .111.153, CNAME `www` → `abcdben.github.io`.
