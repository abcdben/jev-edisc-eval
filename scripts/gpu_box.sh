#!/usr/bin/env bash
# Run the local-model grid (Laya zero-shot variants, Laya fine-tune, Gemma via Ollama)
# on a rented Linux GPU box. Usage on the box, from the synced repo dir:
#     bash scripts/gpu_box.sh setup     # python env, laya, ollama + gemma3:12b
#     bash scripts/gpu_box.sh run       # the full grid; resumable; logs to gpu_run.log
# Results land in results/ exactly as they do locally; rsync them back.
set -euo pipefail
cd "$(dirname "$0")/.."
export USE_TF=0 TOKENIZERS_PARALLELISM=false
# Several bench processes share the box; without this each spawns one torch thread per core and they thrash.
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} MKL_NUM_THREADS=${MKL_NUM_THREADS:-4}

setup() {
  if command -v python3.12 >/dev/null || command -v python3.11 >/dev/null; then
    PY=$(command -v python3.12 || command -v python3.11)
    $PY -m venv .venv
  else
    # image ships an older python: let uv fetch a standalone 3.12
    command -v uv >/dev/null || (curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1)
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    uv venv --python 3.12 .venv >/dev/null
    uv pip install --python .venv/bin/python -q pip
  fi
  .venv/bin/pip install -q -U pip
  .venv/bin/pip install -q -e '.[laya]' httpx
  .venv/bin/python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
  if [ -z "${SKIP_OLLAMA:-}" ]; then
    if ! command -v ollama >/dev/null; then curl -fsSL https://ollama.com/install.sh | sh; fi
    (pgrep -x ollama >/dev/null || (OLLAMA_NUM_PARALLEL=4 nohup ollama serve >ollama.log 2>&1 &)); sleep 4
    ollama pull gemma3:12b
    .venv/bin/bench doctor -m lexical -m laya@base -m gemma3-12b
  else
    .venv/bin/bench doctor -m lexical -m laya@base
  fi
}

# One job = "task data corpus model arm [concurrency] [tag]". The Laya provider micro-batches
# concurrent requests into single forward passes, so Laya jobs run at high concurrency (-c 64)
# and only a couple of jobs at a time (POOL) share the GPU.
job() {
  local extra=(); [ -n "${7:-}" ] && extra=(--tag "$7")
  .venv/bin/bench run -t "$1" -d "$2" --corpus "$3" -m "$4" -a "$5" -c "${6:-64}" "${extra[@]}" -y 2>&1 | grep "new rows" || true
}
export -f job

run() {
  (pgrep -x ollama >/dev/null || (OLLAMA_NUM_PARALLEL=4 nohup ollama serve >ollama.log 2>&1 &)); sleep 3
  POOL=${POOL:-2}
  V=tasks/veridian.yaml; VD=data/veridian/veridian.jsonl
  M=tasks/mallinckrodt.yaml; MD=data/mallinckrodt/mnk.jsonl
  LAYA="laya@base laya@choice laya@score laya@compact laya@chunk laya@recipe laya@recipe_choice laya@literal laya@gate laya@ensemble laya@decompose laya-typed@base laya-typed@recipe laya-multilingual@base laya-multilingual@recipe"

  echo "== Laya zero-shot, both corpora, pool=$POOL"
  { for v in $LAYA; do for a in single multi; do echo "$V $VD veridian $v $a"; done; done
    for v in $LAYA; do for a in single multi; do echo "$M $MD mnk $v $a"; done; done
  } | xargs -P "$POOL" -L 1 bash -c 'job "$@"' _

  echo "== Laya per-request latency sample (concurrency 1, unbatched; the speed table uses this, not the batched rows)"
  for v in laya@base laya@recipe laya-typed@base; do for a in single multi; do
    job $V data/veridian/local_subset.jsonl veridian $v $a 1 latency
    job $M data/mallinckrodt/local_subset.jsonl mnk $v $a 1 latency
  done; done

  echo "== Laya fine-tune (SUPERVISED), Veridian"
  .venv/bin/bench laya-ft -t $V -d $VD -o models/laya-ft-veridian 2>&1 | grep -E "laya-ft\]|split:" || true
  echo "== Laya fine-tune (SUPERVISED), Mallinckrodt"
  .venv/bin/bench laya-ft -t $M -d $MD -o models/laya-ft-mnk 2>&1 | grep -E "laya-ft\]|split:" || true
  echo "== Fine-tuned eval on held-out splits, pool=$POOL"
  { for v in laya-ft-veridian@compact laya-ft-veridian@recipe; do for a in single multi; do echo "$V data/veridian/ft_test.jsonl veridian $v $a"; done; done
    for v in laya-ft-mnk@compact laya-ft-mnk@recipe; do for a in single multi; do echo "$M data/mallinckrodt/ft_test.jsonl mnk $v $a"; done; done
  } | xargs -P "$POOL" -L 1 bash -c 'job "$@"' _

  echo GPU_GRID_DONE
}

# Same grid on the CUAD contract-paragraph corpus (added after the first two corpora).
cuad() {
  POOL=${POOL:-2}
  C=tasks/cuad.yaml; CD=data/cuad/cuad.jsonl
  LAYA="laya@base laya@choice laya@score laya@compact laya@chunk laya@recipe laya@recipe_choice laya@literal laya@gate laya@ensemble laya@decompose laya-typed@base laya-typed@recipe laya-multilingual@base laya-multilingual@recipe"
  echo "== Laya zero-shot, CUAD, pool=$POOL"
  { for v in $LAYA; do for a in single multi; do [ "$v$a" = "laya@decomposesingle" ] && continue; echo "$C $CD cuad $v $a"; done; done; } | xargs -P "$POOL" -L 1 bash -c 'job "$@"' _
  echo "== Laya latency sample, CUAD"
  for v in laya@base laya@recipe laya-typed@base; do for a in single multi; do job $C data/cuad/local_subset.jsonl cuad $v $a 1 latency; done; done
  echo "== Laya fine-tune (SUPERVISED), CUAD"
  .venv/bin/bench laya-ft -t $C -d $CD -o models/laya-ft-cuad 2>&1 | grep -E "laya-ft\]|split:" || true
  { for v in laya-ft-cuad@compact laya-ft-cuad@recipe; do for a in single multi; do echo "$C data/cuad/ft_test.jsonl cuad $v $a"; done; done; } | xargs -P "$POOL" -L 1 bash -c 'job "$@"' _
  echo "== Gemma, CUAD subsample"
  job $C data/cuad/local_subset.jsonl cuad gemma3-12b multi 4
  job $C data/cuad/local_subset.jsonl cuad gemma3-12b single 4
  echo CUAD_GRID_DONE
}

# Gemma 3 12B floor via Ollama. It saturates the GPU (~6 docs/min even on an A100 for the
# 10-question multi-arm prompt), so it runs alone, after the Laya grid, on the 400-doc subsamples.
trec() {
  # laya@decompose single-arm is skipped: on Veridian it ran 4.5 h at 0% GPU (batcher starvation); multi-arm decompose is kept.
  # TREC 2016 Total Recall. Zero-shot Laya on the 3,116 eval sample (both arms, v1 criteria) plus the
  # bare-sentence v0 criteria for base; supervised fine-tune on dev.jsonl (the calibration set, disjoint
  # from eval); then one multi-arm pass over the full 286k collection with the best zero-shot variant.
  POOL=${POOL:-2}
  C=tasks/trec.yaml; CD=data/trec/eval.jsonl
  LAYA="laya@base laya@choice laya@score laya@compact laya@chunk laya@recipe laya@recipe_choice laya@literal laya@gate laya@ensemble laya@decompose laya-typed@base laya-typed@recipe laya-multilingual@base laya-multilingual@recipe"
  echo "== Laya zero-shot, TREC eval, pool=$POOL"
  { for v in $LAYA; do for a in multi single; do [ "$v$a" = "laya@decomposesingle" ] && continue; echo "$C $CD trec $v $a"; done; done; } | xargs -P "$POOL" -L 1 bash -c 'job "$@"' _
  echo "== Laya v0 (bare sentence) criteria, TREC eval"
  for a in multi single; do job design/trec/criteria_v0.yaml $CD trec laya@base $a 64 v0; done
  echo "== Laya fine-tune (SUPERVISED) on TREC dev, eval on eval"
  .venv/bin/bench laya-ft -t $C -d $CD --train data/trec/dev.jsonl -o models/laya-ft-trec 2>&1 | grep -E "laya-ft\]|split:" || true
  for a in multi single; do job $C $CD trec laya-ft-trec@compact $a; job $C $CD trec laya-ft-trec@recipe $a; done
  echo TREC_GRID_DONE
}

trec_full() {
  # Sharded full-collection pass: trec_full K N runs shard K of N (1-based) of data/trec/full.jsonl.
  # Each box writes results/trec_full/multi/*.jsonl for its shard; shards are concatenated locally.
  K=${1:-1}; N=${2:-1}
  .venv/bin/python - "$K" "$N" <<'PY'
import sys, itertools
k, n = int(sys.argv[1]), int(sys.argv[2])
src = open("data/trec/full.jsonl"); out = open(f"data/trec/full_{k}of{n}.jsonl", "w")
for i, line in enumerate(src):
    if i % n == k - 1: out.write(line)
PY
  echo "== Laya full collection shard $K/$N, multi arm"
  job tasks/trec.yaml data/trec/full_${K}of${N}.jsonl trec_full laya@recipe multi 128
  job tasks/trec.yaml data/trec/full_${K}of${N}.jsonl trec_full lexical multi 128
  echo "TREC_FULL_DONE $K/$N"
}

trec_gemma() {
  (pgrep -x ollama >/dev/null || (OLLAMA_NUM_PARALLEL=4 nohup ollama serve >ollama.log 2>&1 &)); sleep 3
  job tasks/trec.yaml data/trec/local_subset.jsonl trec gemma3-12b multi 4
  job tasks/trec.yaml data/trec/local_subset.jsonl trec gemma3-12b single 4
  echo TREC_GEMMA_DONE
}

gemma() {
  V=tasks/veridian.yaml; M=tasks/mallinckrodt.yaml
  job $V data/veridian/local_subset.jsonl veridian gemma3-12b multi 4
  job $M data/mallinckrodt/local_subset.jsonl mnk gemma3-12b multi 4
  job $V data/veridian/local_subset.jsonl veridian gemma3-12b single 4
  job $M data/mallinckrodt/local_subset.jsonl mnk gemma3-12b single 4
  echo GEMMA_DONE
}

case "${1:-}" in
  setup) setup ;;
  run) run 2>&1 | tee -a gpu_run.log ;;
  gemma) gemma 2>&1 | tee -a gpu_run.log ;;
  cuad) cuad 2>&1 | tee -a gpu_run.log ;;
  trec) trec 2>&1 | tee -a gpu_run.log ;;
  trec_full) trec_full "${2:-1}" "${3:-1}" 2>&1 | tee -a gpu_run.log ;;
  trec_gemma) trec_gemma 2>&1 | tee -a gpu_run.log ;;
  *) echo "usage: $0 setup|run|gemma|cuad|trec|trec_full K N|trec_gemma"; exit 1 ;;
esac
