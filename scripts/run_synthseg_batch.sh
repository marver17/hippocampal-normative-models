#!/bin/bash
# Batch processing script for SynthSeg on PPMI and IXI datasets
# Author: Generated with Claude Code
# Date: 2025-11-17

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_JOBS=4
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNTHSEG_SCRIPT="${SCRIPT_DIR}/synthseg_run.sh"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --dataset DATASET    Dataset to process (ppmi|ixi|combined) [required]"
    echo "  -j, --jobs NUM           Number of parallel jobs (default: ${DEFAULT_JOBS})"
    echo "  -t, --test               Test mode: process only first 5 subjects"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --dataset ppmi                  # Process all PPMI subjects"
    echo "  $0 --dataset ixi --jobs 8          # Process IXI with 8 parallel jobs"
    echo "  $0 --dataset combined --test       # Test with first 5 subjects"
    exit 1
}

# Function to check dependencies
check_dependencies() {
    echo -e "${BLUE}Checking dependencies...${NC}"

    # Check GNU parallel
    if ! command -v parallel &> /dev/null; then
        echo -e "${RED}ERROR: GNU parallel not found${NC}"
        echo "Install with: sudo apt-get install parallel"
        exit 1
    fi

    # Check SynthSeg script
    if [ ! -f "$SYNTHSEG_SCRIPT" ]; then
        echo -e "${RED}ERROR: SynthSeg script not found: $SYNTHSEG_SCRIPT${NC}"
        exit 1
    fi

    # Check if script is executable
    if [ ! -x "$SYNTHSEG_SCRIPT" ]; then
        echo -e "${YELLOW}Making synthseg_run.sh executable...${NC}"
        chmod +x "$SYNTHSEG_SCRIPT"
    fi

    echo -e "${GREEN}✓ All dependencies OK${NC}"
}

# Function to process dataset
process_dataset() {
    local dataset=$1
    local jobs=$2
    local test_mode=$3

    # Determine CSV file
    case $dataset in
        ppmi)
            CSV_FILE="${SCRIPT_DIR}/data/PPMI/ppmi_synthseg_processing.csv"
            DATASET_NAME="PPMI"
            ;;
        ixi)
            CSV_FILE="${SCRIPT_DIR}/data/IXI/ixi_synthseg_processing.csv"
            DATASET_NAME="IXI"
            ;;
        combined)
            CSV_FILE="${SCRIPT_DIR}/data/combined/combined_ppmi_ixi_synthseg_processing.csv"
            DATASET_NAME="PPMI + IXI Combined"
            ;;
        *)
            echo -e "${RED}ERROR: Invalid dataset: $dataset${NC}"
            usage
            ;;
    esac

    # Check if CSV file exists
    if [ ! -f "$CSV_FILE" ]; then
        echo -e "${RED}ERROR: CSV file not found: $CSV_FILE${NC}"
        exit 1
    fi

    # Count total subjects
    TOTAL_SUBJECTS=$(($(wc -l < "$CSV_FILE") - 1))

    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}SYNTHSEG BATCH PROCESSING${NC}"
    echo -e "${BLUE}================================${NC}"
    echo -e "Dataset:          ${GREEN}${DATASET_NAME}${NC}"
    echo -e "CSV file:         ${CSV_FILE}"
    echo -e "Total subjects:   ${TOTAL_SUBJECTS}"
    echo -e "Parallel jobs:    ${jobs}"
    echo -e "Test mode:        ${test_mode}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Prepare command
    if [ "$test_mode" = "true" ]; then
        echo -e "${YELLOW}Running in TEST MODE (first 5 subjects only)${NC}"
        PROCESS_CMD="head -n 6 \"$CSV_FILE\" | tail -n +2"
    else
        PROCESS_CMD="tail -n +2 \"$CSV_FILE\""
    fi

    # Confirmation prompt
    echo -e "${YELLOW}Press ENTER to start processing or Ctrl+C to cancel...${NC}"
    read

    # Start processing
    echo -e "${GREEN}Starting SynthSeg processing...${NC}"
    START_TIME=$(date +%s)

    # Run parallel processing with progress bar
    eval $PROCESS_CMD | parallel --colsep ',' --jobs "$jobs" --bar --eta \
        "$SYNTHSEG_SCRIPT" {1} {2} {3} {4}

    EXIT_CODE=$?
    END_TIME=$(date +%s)
    ELAPSED_TIME=$((END_TIME - START_TIME))

    echo ""
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}================================${NC}"
        echo -e "${GREEN}✓ PROCESSING COMPLETE${NC}"
        echo -e "${GREEN}================================${NC}"
        echo -e "Total time: $(($ELAPSED_TIME / 3600))h $(($ELAPSED_TIME % 3600 / 60))m $(($ELAPSED_TIME % 60))s"
        echo ""

        # Show output directories
        echo "Output locations:"
        if [ "$dataset" = "ppmi" ] || [ "$dataset" = "combined" ]; then
            echo "  PPMI: /mnt/db_ext/RAW/PPMI/synthseg_output"
        fi
        if [ "$dataset" = "ixi" ] || [ "$dataset" = "combined" ]; then
            echo "  IXI: /mnt/NAS-Progetti/IXI_synthseg_output"
        fi
    else
        echo -e "${RED}================================${NC}"
        echo -e "${RED}✗ PROCESSING FAILED${NC}"
        echo -e "${RED}================================${NC}"
        echo -e "Exit code: $EXIT_CODE"
        exit $EXIT_CODE
    fi
}

# Parse command line arguments
DATASET=""
JOBS=$DEFAULT_JOBS
TEST_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dataset)
            DATASET="$2"
            shift 2
            ;;
        -j|--jobs)
            JOBS="$2"
            shift 2
            ;;
        -t|--test)
            TEST_MODE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate required arguments
if [ -z "$DATASET" ]; then
    echo -e "${RED}ERROR: Dataset not specified${NC}"
    usage
fi

# Run processing
check_dependencies
process_dataset "$DATASET" "$JOBS" "$TEST_MODE"
