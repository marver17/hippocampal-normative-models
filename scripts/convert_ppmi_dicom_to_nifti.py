#!/usr/bin/env python3
"""
PPMI DICOM to NIfTI Conversion Script
Converts T1-weighted DICOM images from healthy control subjects to NIfTI format
following BIDS (Brain Imaging Data Structure) standard.

Author: Generated with Claude Code
Date: 2025-11-17
"""

import os
import subprocess
import pandas as pd
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re
from tqdm import tqdm

# Configuration
DICOM_ROOT = Path("/mnt/db_ext/RAW/PPMI/PPMI")
METADATA_FILE = Path("/mnt/db_ext/RAW/PPMI/Participant_Status_06Nov2025.csv")
DEMOGRAPHICS_FILE = Path("/mnt/db_ext/RAW/PPMI/Demographics_06Nov2025.csv")
OUTPUT_ROOT = Path("/mnt/db_ext/RAW/PPMI/nifti")
LOG_FILE = Path("/home/mario/Repository/Normal_Alzeihmer/logs/ppmi_conversion.log")

# T1 sequence patterns (case-insensitive matching)
T1_PATTERNS = [
    r".*T1.*",
    r".*MPRAGE.*",
    r".*FSPGR.*",
    r".*SPGR.*",
]

# Exclude patterns (ND = non-diagnostic, localizer, scout)
EXCLUDE_PATTERNS = [
    r".*localizer.*",
    r".*scout.*",
    r".*calibration.*",
]

# Priority order for selecting best T1 sequence when multiple are available
SEQUENCE_PRIORITY = [
    "3D_T1-weighted",
    "3D_T1_weighted",
    "MPRAGE_GRAPPA",
    "MPRAGE",
    "SAG_3D_MPRAGE",
    "SAG_3D_T1_MPRAGE",
    "3D_T1_MPRAGE",
    "SAG_3D_FSPGR",
    "SAG_3D_T1_FSPGR",
    "FSPGR",
]


def setup_logging():
    """Setup logging configuration"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def load_healthy_controls() -> pd.DataFrame:
    """Load healthy control subjects from metadata"""
    logger = logging.getLogger(__name__)
    logger.info(f"Loading metadata from {METADATA_FILE}")

    df = pd.read_csv(METADATA_FILE)

    # Filter for healthy controls (COHORT=2) and enrolled status
    healthy = df[
        ((df['COHORT'] == 2) | (df['COHORT_DEFINITION'] == 'Healthy Control')) &
        (df['ENROLL_STATUS'] == 'Enrolled')
    ]

    logger.info(f"Found {len(healthy)} healthy control subjects")
    return healthy


def load_demographics() -> pd.DataFrame:
    """Load demographics data"""
    logger = logging.getLogger(__name__)
    logger.info(f"Loading demographics from {DEMOGRAPHICS_FILE}")

    try:
        df = pd.read_csv(DEMOGRAPHICS_FILE)
        logger.info(f"Loaded demographics for {len(df)} subjects")
        return df
    except Exception as e:
        logger.warning(f"Could not load demographics: {e}")
        return pd.DataFrame()


def is_t1_sequence(sequence_name: str) -> bool:
    """Check if sequence name matches T1 patterns"""
    sequence_lower = sequence_name.lower()

    # Check exclude patterns first
    for pattern in EXCLUDE_PATTERNS:
        if re.match(pattern, sequence_lower):
            return False

    # Check T1 patterns
    for pattern in T1_PATTERNS:
        if re.match(pattern, sequence_lower, re.IGNORECASE):
            return True

    return False


def get_sequence_priority(sequence_name: str) -> int:
    """Get priority score for sequence (lower is better)"""
    for idx, priority_seq in enumerate(SEQUENCE_PRIORITY):
        if priority_seq.lower() in sequence_name.lower():
            return idx
    return len(SEQUENCE_PRIORITY)  # Lowest priority for unknown sequences


def find_t1_sequences(subject_id: str) -> List[Dict[str, any]]:
    """Find all T1 sequences for a subject"""
    logger = logging.getLogger(__name__)
    subject_dir = DICOM_ROOT / str(subject_id)

    if not subject_dir.exists():
        logger.warning(f"Subject directory not found: {subject_dir}")
        return []

    t1_sequences = []

    # Iterate through sequence directories
    for seq_dir in subject_dir.iterdir():
        if not seq_dir.is_dir():
            continue

        seq_name = seq_dir.name
        if not is_t1_sequence(seq_name):
            continue

        # Find timestamp directories (sessions)
        for timestamp_dir in seq_dir.iterdir():
            if not timestamp_dir.is_dir():
                continue

            # Extract session date from timestamp
            timestamp_name = timestamp_dir.name
            session_date = extract_session_date(timestamp_name)

            # Find image directory (contains DICOM files)
            dicom_dirs = list(timestamp_dir.iterdir())
            if not dicom_dirs:
                continue

            # Usually there's one subdirectory with the actual DICOM files
            dicom_dir = dicom_dirs[0] if len(dicom_dirs) == 1 else timestamp_dir

            # Check if DICOM files exist
            dicom_files = list(dicom_dir.glob("*.dcm"))
            if not dicom_files:
                continue

            t1_sequences.append({
                'subject_id': subject_id,
                'sequence_name': seq_name,
                'session_date': session_date,
                'timestamp': timestamp_name,
                'dicom_path': dicom_dir,
                'num_files': len(dicom_files),
                'priority': get_sequence_priority(seq_name)
            })

    return t1_sequences


def extract_session_date(timestamp_str: str) -> str:
    """Extract session date from timestamp directory name

    Examples:
        '2011-04-05_14_45_45.0' -> '20110405'
        '2021-05-17_10_47_24.0' -> '20210517'
    """
    # Try to extract date pattern YYYY-MM-DD
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})', timestamp_str)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"

    # Fallback: use full timestamp as session identifier
    return timestamp_str.replace('-', '').replace('_', '').replace('.', '')[:8]


def select_best_sequences(sequences: List[Dict]) -> List[Dict]:
    """Select best T1 sequence per session

    If multiple T1 sequences exist for the same session, select based on priority.
    If they have same priority, keep all as separate runs.
    """
    if not sequences:
        return []

    # Group by session
    sessions = {}
    for seq in sequences:
        session_key = seq['session_date']
        if session_key not in sessions:
            sessions[session_key] = []
        sessions[session_key].append(seq)

    selected = []
    for session_date, session_seqs in sessions.items():
        # Sort by priority
        session_seqs.sort(key=lambda x: x['priority'])

        # Take the best one (lowest priority number)
        best_priority = session_seqs[0]['priority']

        # If multiple sequences have same priority, keep all as runs
        best_seqs = [s for s in session_seqs if s['priority'] == best_priority]

        # Add run number if multiple sequences
        for run_idx, seq in enumerate(best_seqs, start=1):
            seq['run'] = run_idx if len(best_seqs) > 1 else None
            selected.append(seq)

    return selected


def convert_to_nifti(sequence_info: Dict, output_dir: Path) -> bool:
    """Convert DICOM sequence to NIfTI using dcm2niix"""
    logger = logging.getLogger(__name__)

    subject_id = sequence_info['subject_id']
    session_date = sequence_info['session_date']
    run = sequence_info['run']
    dicom_path = sequence_info['dicom_path']

    # Create BIDS-compliant filename
    if run:
        filename = f"sub-{subject_id}_ses-{session_date}_run-{run:02d}_T1w"
    else:
        filename = f"sub-{subject_id}_ses-{session_date}_T1w"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run dcm2niix
    cmd = [
        'dcm2niix',
        '-o', str(output_dir),      # Output directory
        '-f', filename,              # Output filename
        '-z', 'y',                   # Compress (gzip)
        '-b', 'y',                   # Save BIDS sidecar JSON
        '-ba', 'n',                  # Don't anonymize
        '-v', '0',                   # Quiet mode (only errors)
        str(dicom_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Check if output files were created
        nifti_file = output_dir / f"{filename}.nii.gz"
        json_file = output_dir / f"{filename}.json"

        if nifti_file.exists():
            logger.info(f"✓ Converted: {filename}")
            return True
        else:
            logger.error(f"✗ Conversion failed (no output): {filename}")
            logger.error(f"  STDOUT: {result.stdout}")
            logger.error(f"  STDERR: {result.stderr}")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Conversion failed: {filename}")
        logger.error(f"  Error: {e}")
        logger.error(f"  STDOUT: {e.stdout}")
        logger.error(f"  STDERR: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error converting {filename}: {e}")
        return False


def create_bids_metadata(healthy_subjects: pd.DataFrame, demographics: pd.DataFrame):
    """Create BIDS metadata files"""
    logger = logging.getLogger(__name__)
    logger.info("Creating BIDS metadata files")

    # Create dataset_description.json
    dataset_desc = {
        "Name": "PPMI Healthy Controls T1w",
        "BIDSVersion": "1.8.0",
        "DatasetType": "raw",
        "License": "PPMI Data Use Agreement",
        "Authors": ["Parkinson's Progression Markers Initiative"],
        "Acknowledgements": "Data used in the preparation of this dataset were obtained from the Parkinson's Progression Markers Initiative (PPMI) database (www.ppmi-info.org/data).",
        "HowToAcknowledge": "Data used in this publication were obtained from the Parkinson's Progression Markers Initiative (PPMI) database (www.ppmi-info.org/data).",
        "DatasetDOI": "10.1038/sdata.2016.102",
        "GeneratedBy": [{
            "Name": "PPMI DICOM to NIfTI Conversion",
            "Version": "1.0",
            "CodeURL": "https://github.com/anthropics/claude-code",
            "Description": "Automated conversion of PPMI DICOM images to NIfTI format using dcm2niix"
        }],
        "SourceDatasets": [{
            "DOI": "10.1038/sdata.2016.102",
            "URL": "https://www.ppmi-info.org/",
            "Version": "November 2025"
        }]
    }

    dataset_desc_file = OUTPUT_ROOT / "dataset_description.json"
    with open(dataset_desc_file, 'w') as f:
        json.dump(dataset_desc, f, indent=2)
    logger.info(f"Created {dataset_desc_file}")

    # Create participants.tsv
    participants_data = []

    for _, subject in healthy_subjects.iterrows():
        patno = subject['PATNO']

        # Get demographics if available
        demo = demographics[demographics['PATNO'] == patno]

        participant = {
            'participant_id': f"sub-{patno}",
            'cohort': 'Healthy Control',
            'enroll_status': subject.get('ENROLL_STATUS', 'N/A'),
            'enroll_age': subject.get('ENROLL_AGE', 'N/A'),
        }

        if not demo.empty:
            demo_row = demo.iloc[0]
            participant['sex'] = demo_row.get('SEX', 'N/A')
            participant['age'] = demo_row.get('BIRTHDT', 'N/A')  # Will need calculation
            participant['race'] = demo_row.get('RACE', 'N/A')
            participant['ethnicity'] = demo_row.get('HISPLAT', 'N/A')
            participant['handedness'] = demo_row.get('HANDED', 'N/A')

        participants_data.append(participant)

    participants_df = pd.DataFrame(participants_data)
    participants_file = OUTPUT_ROOT / "participants.tsv"
    participants_df.to_csv(participants_file, sep='\t', index=False)
    logger.info(f"Created {participants_file}")

    # Create participants.json (data dictionary)
    participants_dict = {
        "participant_id": {
            "Description": "Unique participant identifier",
            "LongName": "Participant ID"
        },
        "cohort": {
            "Description": "Study cohort",
            "Levels": {
                "Healthy Control": "Healthy control subject with no signs of Parkinson's disease"
            }
        },
        "enroll_status": {
            "Description": "Enrollment status in PPMI study",
            "Levels": {
                "Enrolled": "Currently enrolled in study"
            }
        },
        "enroll_age": {
            "Description": "Age at enrollment in years",
            "Units": "years"
        },
        "sex": {
            "Description": "Biological sex",
            "Levels": {
                "0": "Female",
                "1": "Male"
            }
        },
        "race": {
            "Description": "Self-reported race"
        },
        "ethnicity": {
            "Description": "Self-reported ethnicity (Hispanic/Latino)"
        },
        "handedness": {
            "Description": "Hand dominance",
            "Levels": {
                "1": "Right",
                "2": "Left",
                "3": "Mixed"
            }
        }
    }

    participants_json = OUTPUT_ROOT / "participants.json"
    with open(participants_json, 'w') as f:
        json.dump(participants_dict, f, indent=2)
    logger.info(f"Created {participants_json}")


def main():
    """Main conversion workflow"""
    logger = setup_logging()
    logger.info("="*80)
    logger.info("PPMI DICOM to NIfTI Conversion - Starting")
    logger.info("="*80)

    # Create output directory
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    # Load healthy control subjects
    healthy_subjects = load_healthy_controls()
    demographics = load_demographics()

    # Create BIDS metadata
    create_bids_metadata(healthy_subjects, demographics)

    # Statistics
    stats = {
        'total_subjects': len(healthy_subjects),
        'subjects_with_dicom': 0,
        'subjects_without_dicom': 0,
        'total_sequences': 0,
        'successful_conversions': 0,
        'failed_conversions': 0,
        'total_sessions': 0,
    }

    # Process each subject
    logger.info(f"\nProcessing {stats['total_subjects']} healthy control subjects...")

    subjects_to_process = healthy_subjects['PATNO'].tolist()

    for subject_id in tqdm(subjects_to_process, desc="Converting subjects"):
        # Find T1 sequences
        t1_sequences = find_t1_sequences(subject_id)

        if not t1_sequences:
            stats['subjects_without_dicom'] += 1
            logger.debug(f"No T1 sequences found for subject {subject_id}")
            continue

        stats['subjects_with_dicom'] += 1

        # Select best sequences
        selected = select_best_sequences(t1_sequences)
        stats['total_sequences'] += len(selected)

        # Count unique sessions
        unique_sessions = len(set(seq['session_date'] for seq in selected))
        stats['total_sessions'] += unique_sessions

        # Convert each sequence
        for seq in selected:
            session_date = seq['session_date']

            # Create output directory: sub-{PATNO}/ses-{date}/anat/
            output_dir = OUTPUT_ROOT / f"sub-{subject_id}" / f"ses-{session_date}" / "anat"

            # Convert
            success = convert_to_nifti(seq, output_dir)

            if success:
                stats['successful_conversions'] += 1
            else:
                stats['failed_conversions'] += 1

    # Print final statistics
    logger.info("\n" + "="*80)
    logger.info("CONVERSION COMPLETE - STATISTICS")
    logger.info("="*80)
    logger.info(f"Total subjects in cohort:        {stats['total_subjects']}")
    logger.info(f"Subjects with DICOM data:        {stats['subjects_with_dicom']}")
    logger.info(f"Subjects without DICOM data:     {stats['subjects_without_dicom']}")
    logger.info(f"Total sessions:                  {stats['total_sessions']}")
    logger.info(f"Total sequences found:           {stats['total_sequences']}")
    logger.info(f"Successful conversions:          {stats['successful_conversions']}")
    logger.info(f"Failed conversions:              {stats['failed_conversions']}")
    logger.info(f"\nOutput directory: {OUTPUT_ROOT}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("="*80)

    # Save statistics to JSON
    stats_file = OUTPUT_ROOT / "conversion_statistics.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Statistics saved to: {stats_file}")


if __name__ == "__main__":
    main()
