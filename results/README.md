# results/

Aggregates are tracked in git; per-decision records are attached to a GitHub Release.

## Tracked here

- `findings.json`: every number on the results site (imported by `site/src/data.ts`), written by `bench export-findings`.
- `examples.json`: worked examples for the site (`site/src/examples.ts`), written by `bench export-examples`.
- `determinism.json`: run-to-run flip rates from the repeat runs in `mnk_det/`, written by `bench determinism`.
- `<corpus>/summary*.json`, `<corpus>/REPORT.md`: per-corpus tables written by `bench report` / `bench run`.
- `trec_lat/sample_ids.json`: the 200 TREC e-mails used for the latency comparison.

## Per-decision records: Release `v1.0-results`

The `.jsonl` files under `results/<corpus>/<arm>/` (one row per model decision per document; about 11 GB uncompressed, no document text, no prompts or completions) are **not** in git. They are published as one `.tar.zst` per corpus on the GitHub Release
<https://github.com/abcdben/jev-edisc-eval/releases/tag/v1.0-results> (runs 2026-09-19 to 2026-09-25; licence CC BY 4.0, see `../data/LICENSE-DATA.md`).

- `trec`: TREC 2016 Total Recall / Jeb Bush eval sample (3,116 e-mails): all models, both arms, TAR baselines
- `trec_full`: TREC full-collection tier (~286k e-mails): Jev, Laya, lexical, TAR
- `cuad`: CUAD contract-clause corpus: all models, both arms, TAR baselines
- `mnk`: Mallinckrodt opioid-litigation e-mails: all models, both arms, TAR baselines
- `mnk_det`: Determinism study: repeat runs (rep2-5, t0_rep1-5) on det300
- `veridian`: Veridian synthetic matter: all models, both arms
- `trec_dev`: TREC dev split (criteria iteration v0/v1)
- `veridian_audit`: Veridian gold audit panel runs
- `veridian_gists`: Veridian spec-label (gist) pilot
- `veridian_literal`: Veridian literal-criteria pilot
- `veridian_pilot`: Veridian effort/pilot runs

| Corpus | Archive | Size | Uncompressed | `.jsonl` files | SHA-256 |
|---|---|---:|---:|---:|---|
| `trec` | `results-trec.tar.zst` | 60.4 MB | 1.5 GB | 106 | `4aa51708ec720503e848b6f433479436bcb8628cb5e2198d003920138c687bef` |
| `trec_full` | `results-trec_full.tar.zst` | 110.0 MB | 4.9 GB | 19 | `6d8d99f59ffee475447d287b4ba26a41ef1acb8c4d3fa30c47a9f3137dbaf706` |
| `cuad` | `results-cuad.tar.zst` | 107.1 MB | 2.8 GB | 95 | `5c599b1e0f46195a3b0a47593617552ae868167980277ed5e4310cfd4fca359d` |
| `mnk` | `results-mnk.tar.zst` | 25.3 MB | 554.2 MB | 99 | `18aa13a11da9baf474f931d953f2713a5d0a56284f233a441b1239e795c8e29f` |
| `mnk_det` | `results-mnk_det.tar.zst` | 3.8 MB | 104.4 MB | 162 | `fae2323645a231b00c908bbcb27f55f1c4290909960bc2b7efd2d0721ee20b78` |
| `veridian` | `results-veridian.tar.zst` | 29.3 MB | 625.4 MB | 80 | `ca8f1c236b419874bf9d57221c2ecb43e06561aaf87a5a318950fc3084321bdb` |
| `trec_dev` | `results-trec_dev.tar.zst` | 775.6 KB | 21.4 MB | 6 | `f444d59f97ed14f6e29318826fcd2bc3d2ac0e87dfb3b1c2abc9305bea84f778` |
| `veridian_audit` | `results-veridian_audit.tar.zst` | 605.7 KB | 24.8 MB | 3 | `74ef2e43aa6e62d1a6366105d18542a73e009bc6ab9362c5d8493e3f041b62a1` |
| `veridian_gists` | `results-veridian_gists.tar.zst` | 365.1 KB | 16.5 MB | 2 | `999c92e0d0097d71c4476622b6e8d55e4887526cf9b7c81a256cf57ac25d21d5` |
| `veridian_literal` | `results-veridian_literal.tar.zst` | 523.8 KB | 8.5 MB | 3 | `44b07c130c962da508bb71b70df59239caa32027f308d8448cecb5686d23a966` |
| `veridian_pilot` | `results-veridian_pilot.tar.zst` | 596.3 KB | 8.3 MB | 14 | `fb8cb86a7f05a891ffe87cff7198fede8444af952b71ee4228b6d73837d7a0a5` |

A `SHA256SUMS` file with the same digests is attached to the release.

### Extracting into `results/`

Each archive was created from the repository root with `tar --zstd -cf results-<corpus>.tar.zst results/<corpus>/`, so extracting from the repository root restores the original layout (the tracked `summary*.json` / `REPORT.md` inside the archives are identical to the tracked copies):

```bash
# needs zstd: brew install zstd  |  apt install zstd
cd <repo root>
gh release download v1.0-results --repo abcdben/jev-edisc-eval --dir /tmp/jev-results      # or download from the release page
(cd /tmp/jev-results && shasum -a 256 -c SHA256SUMS)
for f in /tmp/jev-results/results-*.tar.zst; do tar --zstd -xf "$f"; done
```

Everything under `results/` other than the aggregates listed above is git-ignored, so the extracted files will not show up in `git status`. Once extracted, `bench report --corpus <corpus> -t tasks/<task>.yaml`, `bench determinism` and `bench export-findings` re-derive the tracked aggregates (see `README.md`, "Reproducing the study").
