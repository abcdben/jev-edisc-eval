#!/bin/bash
# Determinism study: repeat runs over data/mallinckrodt/det300.jsonl. Usage: det_run.sh <arm>
# arms: api_multi | api_single | t0_multi | t0_single | laya | gemma
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
B=.venv/bin/bench
T=tasks/mallinckrodt.yaml; D=data/mallinckrodt/det300.jsonl; C=mnk_det
NARROW=som_narrow,dea_narrow
API="-m jev@base -m jev@choice -m jev@score -m jev@state_string -m claude-haiku-4.5 -m claude-sonnet-5 -m gpt-5.6-luna -m gpt-5.6-terra -m gemini-3.5-flash-lite -m gemini-3.8-flash -m lexical"
T0="-m claude-haiku-4.5 -m gpt-5.6-luna -m gpt-5.6-terra -m gemini-3.5-flash-lite -m gemini-3.8-flash"
case "$1" in
  api_multi)  for k in 2 3 4 5; do $B run -t $T -d $D --corpus $C $API -a multi --tag rep$k -y; done ;;
  api_single) for k in 2 3 4 5; do $B run -t $T -d $D --corpus $C $API -a single -q $NARROW --tag rep$k -y; done ;;
  t0_multi)   for k in 1 2 3 4 5; do $B run -t $T -d $D --corpus $C $T0 -a multi --temperature 0 --tag t0_rep$k -y; done ;;
  t0_single)  for k in 1 2 3 4 5; do $B run -t $T -d $D --corpus $C $T0 -a single -q $NARROW --temperature 0 --tag t0_rep$k -y; done ;;
  laya)       for k in 2 3 4 5; do $B run -t $T -d $D --corpus $C -m laya@base -m laya@recipe -a multi --tag rep$k -y
                                 $B run -t $T -d $D --corpus $C -m laya@base -m laya@recipe -a single -q $NARROW --tag rep$k -y; done ;;
  gemma)      for k in 2 3 4 5; do $B run -t $T -d $D --corpus $C -m gemma3-12b -a multi --tag rep$k -y
                                 $B run -t $T -d $D --corpus $C -m gemma3-12b -a single -q $NARROW --tag rep$k -y; done ;;
esac
echo "DET_DONE $1"
