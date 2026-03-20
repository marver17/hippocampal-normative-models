#!/usr/bin/env bash
set -euo pipefail

# Transfer full-coverage processing lists to HPC.
# Usage:
#   scripts/transfer_coverage_files_to_hpc.sh <user@host> [remote_dir]
# Example:
#   scripts/transfer_coverage_files_to_hpc.sh mverdic1@login.leonardo.cineca.it ~/hpc_processing

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <user@host> [remote_dir]"
  exit 1
fi

REMOTE_HOST="$1"
REMOTE_DIR="${2:-~/hpc_processing}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_COMBINED="$REPO_ROOT/data/combined"

SRC_MAIN="$LOCAL_COMBINED/hpc_to_process_fastsurfer_full_coverage.csv"
SRC_PRIORITY="$LOCAL_COMBINED/hpc_to_process_priority_missing_both.csv"
SRC_SUMMARY="$LOCAL_COMBINED/coverage_gap_summary_by_dataset.csv"

for f in "$SRC_MAIN" "$SRC_PRIORITY" "$SRC_SUMMARY"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing required file: $f"
    exit 1
  fi
done

echo "[1/4] Ensuring remote directory exists: $REMOTE_DIR"
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR"

echo "[2/4] Transferring files with rsync"
rsync -av "$SRC_MAIN" "$REMOTE_HOST:$REMOTE_DIR/to_process_fastsurfer_unprocessed.csv"
rsync -av "$SRC_PRIORITY" "$REMOTE_HOST:$REMOTE_DIR/to_process_priority_missing_both.csv"
rsync -av "$SRC_SUMMARY" "$REMOTE_HOST:$REMOTE_DIR/coverage_gap_summary_by_dataset.csv"

echo "[3/4] Verifying remote files"
ssh "$REMOTE_HOST" "ls -lh $REMOTE_DIR/to_process_fastsurfer_unprocessed.csv $REMOTE_DIR/to_process_priority_missing_both.csv $REMOTE_DIR/coverage_gap_summary_by_dataset.csv"

echo "[4/4] Showing row counts (excluding header)"
ssh "$REMOTE_HOST" "echo -n 'to_process_fastsurfer_unprocessed: '; expr \$(wc -l < $REMOTE_DIR/to_process_fastsurfer_unprocessed.csv) - 1"
ssh "$REMOTE_HOST" "echo -n 'to_process_priority_missing_both: '; expr \$(wc -l < $REMOTE_DIR/to_process_priority_missing_both.csv) - 1"

echo "Done. On HPC, launch your array job with:"
echo "  sbatch $REMOTE_DIR/fastsurfer_array.sh"
