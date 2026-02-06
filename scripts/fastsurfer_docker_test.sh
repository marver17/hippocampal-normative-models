#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Uso: $0 <subject_id> <input_image> <output_dir> [threads=4] [cpus=6] [memory_limit] [image=deepmi/fastsurfer:latest]" >&2
  exit 1
fi

SUBJECT_ID=$1
INPUT_IMAGE=$2
OUTPUT_DIR=$3
THREADS=${4:-4}
CPUS=${5:-6}
MEMORY_LIMIT=${6:-}
IMAGE=${7:-deepmi/fastsurfer:latest}

FS_LICENSE_PATH=${FS_LICENSE_PATH:-/mnt/NAS-Progetti/BrainAtrophy/code/license.txt}

mkdir -p "$OUTPUT_DIR"

NAME="fastsurfer-test-${SUBJECT_ID//[^a-zA-Z0-9]/}"

DOCKER_ARGS=(
  --rm
  --name "$NAME"
  --cpus "$CPUS"
  --rm
  --user $(id -u):$(id -g)
  -v "/mnt/NAS-Progetti:/mnt/NAS-Progetti"
  -e "FS_LICENSE=$FS_LICENSE_PATH"
)

if [ -n "$MEMORY_LIMIT" ]; then
  DOCKER_ARGS+=(--memory "$MEMORY_LIMIT")
fi

set +e

docker run "${DOCKER_ARGS[@]}" "$IMAGE" --t1  " /mnt/NAS-Progetti/BrainAtrophy/code/fastsurfer_run.sh \"$SUBJECT_ID\" \"$INPUT_IMAGE\" \"$OUTPUT_DIR\" \"$THREADS\"" &

PID=$!
MAX_MIB=0

while docker ps -q -f "name=$NAME" | grep -q .; do
  MEM_RAW=$(docker stats --no-stream --format "{{.MemUsage}}" "$NAME" | awk '{print $1}')
  NUM=$(echo "$MEM_RAW" | sed -E 's/([0-9.]+).*/\1/')
  UNIT=$(echo "$MEM_RAW" | sed -E 's/[0-9.]+(.*)/\1/')

  case "$UNIT" in
    KiB|KB)
      MEM_MIB=$(awk "BEGIN{printf \"%.2f\", $NUM/1024}")
      ;;
    MiB|MB)
      MEM_MIB=$NUM
      ;;
    GiB|GB)
      MEM_MIB=$(awk "BEGIN{printf \"%.2f\", $NUM*1024}")
      ;;
    TiB|TB)
      MEM_MIB=$(awk "BEGIN{printf \"%.2f\", $NUM*1024*1024}")
      ;;
    *)
      MEM_MIB=$NUM
      ;;
  esac

  if awk "BEGIN{exit !($MEM_MIB>$MAX_MIB)}"; then
    MAX_MIB=$MEM_MIB
  fi

  sleep 5
done
wait "$PID"
EXIT_CODE=$?

set -e

echo "Max RAM stimata: ${MAX_MIB} MiB"
exit "$EXIT_CODE"
