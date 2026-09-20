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
  if ! command -v python3.12 >/dev/null && ! command -v python3.11 >/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y -qq python3-venv python3-pip >/dev/null
  fi
  PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
  $PY -m venv .venv
  .venv/bin/pip install -q -U pip
  .venv/bin/pip install -q -e '.[laya]' httpx
  .venv/bin/python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
  if ! command -v ollama >/dev/null; then curl -fsSL https://ollama.com/install.sh | sh; fi
  (pgrep -x ollama >/dev/null || (OLLAMA_NUM_PARALLEL=4 nohup ollama serve >ollama.log 2>&1 &)); sleep 4
  ollama pull gemma3:12b
  .venv/bin/bench doctor -m lexical -m laya@base -m gemma3-12b
}

# One job = "task data corpus model arm [concurrency]". Laya calls are ~30 ms of CPU
# overhead each with the GPU nearly idle, so we run several jobs at once (POOL).
job() { .venv/bin/bench run -t "$1" -d "$2" --corpus "$3" -m "$4" -a "$5" -c "${6:-1}" -y 2>&1 | grep "new rows" || true; }
export -f job

run() {
  (pgrep -x ollama >/dev/null || (OLLAMA_NUM_PARALLEL=4 nohup ollama serve >ollama.log 2>&1 &)); sleep 3
  POOL=${POOL:-6}
  V=tasks/veridian.yaml; VD=data/veridian/veridian.jsonl
  M=tasks/mallinckrodt.yaml; MD=data/mallinckrodt/mnk.jsonl
  LAYA="laya@base laya@choice laya@score laya@compact laya@chunk laya@recipe laya@recipe_choice laya@literal laya@gate laya@ensemble laya@decompose laya-typed@base laya-typed@recipe laya-multilingual@base laya-multilingual@recipe"

  echo "== Laya zero-shot, both corpora, pool=$POOL"
  { for v in $LAYA; do for a in single multi; do echo "$V $VD veridian $v $a"; done; done
    for v in $LAYA; do for a in single multi; do echo "$M $MD mnk $v $a"; done; done
  } | xargs -P "$POOL" -L 1 bash -c 'job "$@"' _

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

# Gemma 3 12B floor via Ollama. It saturates the GPU (~6 docs/min even on an A100 for the
# 10-question multi-arm prompt), so it runs alone, after the Laya grid, on the 400-doc subsamples.
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
  *) echo "usage: $0 setup|run|gemma"; exit 1 ;;
esac
