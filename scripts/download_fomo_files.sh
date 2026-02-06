#!/bin/bash

# Script to download FOMO-300K MRI files for subjects listed in a CSV file
# Usage: ./download_fomo_files.sh <csv_file> [local_dir]

set -e  # Exit on any error

# Default values
CSV_FILE="$1"
LOCAL_DIR="${2:-./fomo_downloads}"

if [ -z "$CSV_FILE" ]; then
    echo "Usage: $0 <csv_file> [local_dir]"
    echo "Example: $0 data/FOMO-300K/fomo_healthy_controls_age45plus.csv /path/to/downloads"
    exit 1
fi

if [ ! -f "$CSV_FILE" ]; then
    echo "Error: CSV file not found: $CSV_FILE"
    exit 1
fi

# Create local directory
mkdir -p "$LOCAL_DIR"

echo "Reading CSV file: $CSV_FILE"
echo "Download directory: $LOCAL_DIR"

# Get total subjects and unique sites
TOTAL_SUBJECTS=$(tail -n +2 "$CSV_FILE" | wc -l)
UNIQUE_SITES=$(tail -n +2 "$CSV_FILE" | awk -F',' '{print $5}' | sort | uniq | wc -l)

echo "Found $TOTAL_SUBJECTS subjects across $UNIQUE_SITES sites"

# Read CSV and process in batches grouped by dataset to reuse a single connection
patterns=()
current_dataset=""

download_batch() {
    local dataset_name="$1"

    if [ ${#patterns[@]} -eq 0 ]; then
        return 0
    fi

    echo ""
    echo "Processing dataset: ${dataset_name} (${#patterns[@]} subjects)"

    cmd=(hf download FOMO-MRI/FOMO300K --repo-type dataset --local-dir "$LOCAL_DIR")
    for p in "${patterns[@]}"; do
        cmd+=(--include "$p")
    done

    echo "  Executing: ${cmd[*]}"
    if "${cmd[@]}"; then
        echo "  ✓ Successfully downloaded dataset batch"
    else
        echo "  ✗ Error downloading dataset batch"
        # Continue with next dataset instead of exiting
    fi

    patterns=()
}

while IFS=',' read -r subject_id session_id age sex site dataset_code dataset field_strength; do
    if [ -z "$current_dataset" ]; then
        current_dataset="$dataset"
    fi

    if [ "$dataset" != "$current_dataset" ]; then
        download_batch "$current_dataset"
        current_dataset="$dataset"
    fi

    PATTERN="${site}/${subject_id}/*"
    patterns+=("$PATTERN")
done < <(tail -n +2 "$CSV_FILE" | sort -t',' -k7,7)

# Download any remaining subjects
download_batch "$current_dataset"

echo ""
echo "Download process completed!"
echo "Files saved to: $LOCAL_DIR"

# Count downloaded files
if [ -d "$LOCAL_DIR" ]; then
    FILE_COUNT=$(find "$LOCAL_DIR" -type f 2>/dev/null | wc -l)
    echo "Total files downloaded: $FILE_COUNT"
fi