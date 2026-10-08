# Results site

Interactive page over `results/findings.json` (written by `bench export-findings`) and `results/sweep.json` (`bench export-sweep`: the same predictions re-cut at every threshold 0.01 … 0.99, behind the threshold slider and the Trade-off page).

```sh
# from the repo root, refresh the data first
.venv/bin/bench export-findings
.venv/bin/bench export-sweep     # reads every multi-arm result jsonl; a few minutes

cd site
npm install
npm run dev        # http://127.0.0.1:5173
npm run build      # static bundle in site/dist (host anywhere; open dist/index.html for the landing page, dist/compare.html for the app)
```

## Pages

- `index.html` (`/`, `src/landing.tsx` → `src/LandingPage.tsx`): the landing page, a card per page below. It also forwards the comparison app's old hash links (`/#compare`, `/#configurations`, `/#tradeoff`; the app used to be the root) to `compare.html` with the hash intact.
- `compare.html` (`src/main.tsx` → `src/App.tsx`): the comparison app, three views in the hash (below). Its masthead links Home.
- `study.html` (`src/study.tsx` → `src/StudyPage.tsx`): the human-anchored study, `results/study.json`.
- `explore.html` (`src/explore.tsx` → `src/ExplorePage.tsx`): the population explorer, `public/explore/`.
- `contamination/` (`public/contamination/index.html` and `gallery.html`): the contamination study's technical write-up and figure gallery, static pages staged from `results/contam/` by `scripts/publish_writeup.sh` (run by `deploy_site.sh`; the staging directory is git-ignored because the figures under `results/` are not tracked).
- `b.html` (`src/b.tsx` → `src/AppB.tsx`): variant B of the app for an A/B comparison, links back to A; not linked from the landing page, `noindex`.
- `studio.html` (`src/studio.tsx` → `src/StudioPage.tsx`): the screenshot studio; unlinked, `noindex`.

The comparison app has three sections, all driven by the sticky control bar (corpus, TREC criteria, prompting arm, scope, gold labels):

- **Compare models**: pick any subset of the headline roster. Recall against precision with 95% interval boxes (or ranked rows with whiskers), plus review time and cost per 100,000 documents for the same selection.
- **Configurations of one model**: pick Jev or a Laya checkpoint and compare its ablation variants the same way. The optimized configuration (the one selected on the Veridian dev split and carried into the headline comparison) is starred.
- **Trade-off** (`#tradeoff`, `src/Tradeoff.tsx`, `src/components/PRCurves.tsx`): recall against precision as a full curve per model, swept over the probability threshold, with a draggable operating point on each (arrow keys work too), the published 0.50 cut as an open ring, iso-F1 contours behind, and a readout of threshold, recall, precision, F1 and the share of the corpus flagged. "Match recall" moves every marker to the cheapest cut that reaches a target; the point being that every model outputs a probability, so the comparison is curve against curve, not label against label.

Every mark carries a hover tooltip with the counts and intervals behind it; every panel title has an (i) explaining the measurement.

**Consistency** (third card under each section): run-to-run disagreement from the determinism study, `bench determinism` → `results/determinism.json`, merged into `findings.json` by `bench export-findings`. Repeat runs are produced by `scripts/det_run.sh <arm>` (API models, this machine) and `scripts/gpu_box.sh det` (Laya, Gemma on a GPU box).

## Publishing

`scripts/deploy_site.sh` stages the contamination write-up (`scripts/publish_writeup.sh`), builds, and force-pushes `site/dist` to [github.com/abcdben/tarcalc](https://github.com/abcdben/tarcalc), which GitHub Pages serves at https://decider.tarcalc.com (the script writes that `CNAME`; also at https://abcdben.github.io/tarcalc/). The apex, tarcalc.com, is not served from this repository. If results changed, run `.venv/bin/bench export-findings` first. DNS at Namecheap: CNAME `decider` → `abcdben.github.io`.
