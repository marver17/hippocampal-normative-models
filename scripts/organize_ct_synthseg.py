#!/usr/bin/env python3
"""
Organize CT SynthSeg Results into BIDS-like Structure

This script reorganizes CT SynthSeg results from a flat structure into a
BIDS-like derivatives structure, matching the organization used for MR SynthSeg results.

Source structure:
    /mnt/NAS-Progetti/BrainAtrophy/ct_result/
    ├── volumes_results/
    ├── qc_results/
    └── segmentation_results/

Target structure:
    /mnt/NAS-Progetti/BrainAtrophy/DATASET/RF/derivatives/synthseg_ct/
    └── sub-{subject_id}/
        ├── volumes.csv
        ├── qc_scores.csv
        └── segmentation.nii.gz

Author: Claude Code
Date: 2025-12-12
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
CT_RESULT_DIR = Path("/mnt/NAS-Progetti/BrainAtrophy/ct_result")
TARGET_DIR = Path("/mnt/NAS-Progetti/BrainAtrophy/DATASET/RF/derivatives/synthseg_ct")

VOLUMES_DIR = CT_RESULT_DIR / "volumes_results"
QC_DIR = CT_RESULT_DIR / "qc_results"
SEGMENTATION_DIR = CT_RESULT_DIR / "segmentation_results"


def extract_subject_id(filename: str) -> str:
    """
    Extract subject ID from filename.

    Examples:
        sub-1027483.csv -> sub-1027483
        sub-1070908_ritorno.csv -> sub-1070908_ritorno

    Args:
        filename: Filename to extract subject ID from

    Returns:
        Subject ID string
    """
    return filename.replace('.csv', '').replace('ctTemplatespace_synthseg.nii.gz', '')


def find_subject_files(subject_id: str) -> Dict[str, Path]:
    """
    Find all three required files for a subject.

    Args:
        subject_id: Subject ID (e.g., 'sub-1027483')

    Returns:
        Dictionary with paths to volumes, qc, and segmentation files

    Raises:
        FileNotFoundError: If any required file is missing
    """
    files = {
        'volumes': VOLUMES_DIR / f"{subject_id}.csv",
        'qc': QC_DIR / f"{subject_id}.csv",
        'segmentation': SEGMENTATION_DIR / f"{subject_id}ctTemplatespace_synthseg.nii.gz"
    }

    # Check all files exist
    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing files for {subject_id}: {', '.join(missing)}")

    return files


def copy_subject_files(subject_id: str, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Copy and organize files for a single subject.

    Args:
        subject_id: Subject ID
        dry_run: If True, only simulate the operation

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Find source files
        source_files = find_subject_files(subject_id)

        # Create target directory
        target_subject_dir = TARGET_DIR / subject_id

        if not dry_run:
            target_subject_dir.mkdir(parents=True, exist_ok=True)

        # Copy and rename files
        operations = [
            (source_files['volumes'], target_subject_dir / 'volumes.csv'),
            (source_files['qc'], target_subject_dir / 'qc_scores.csv'),
            (source_files['segmentation'], target_subject_dir / 'segmentation.nii.gz')
        ]

        for src, dst in operations:
            if dry_run:
                print(f"  [DRY RUN] Would copy: {src.name} -> {dst}")
            else:
                shutil.copy2(src, dst)

        return True, f"✓ {subject_id}: Copied 3 files"

    except FileNotFoundError as e:
        return False, f"✗ {subject_id}: {str(e)}"
    except Exception as e:
        return False, f"✗ {subject_id}: Unexpected error - {str(e)}"


def verify_structure() -> Tuple[int, int, List[str]]:
    """
    Verify the integrity of the created structure.

    Returns:
        Tuple of (total_subjects, complete_subjects, incomplete_subjects)
    """
    if not TARGET_DIR.exists():
        return 0, 0, []

    subject_dirs = [d for d in TARGET_DIR.iterdir() if d.is_dir()]
    total = len(subject_dirs)

    incomplete = []
    complete = 0

    for subject_dir in subject_dirs:
        expected_files = ['volumes.csv', 'qc_scores.csv', 'segmentation.nii.gz']
        existing_files = [f.name for f in subject_dir.iterdir() if f.is_file()]

        if set(expected_files) == set(existing_files):
            complete += 1
        else:
            missing = set(expected_files) - set(existing_files)
            extra = set(existing_files) - set(expected_files)
            incomplete.append(f"{subject_dir.name}: missing={missing}, extra={extra}")

    return total, complete, incomplete


def main(dry_run: bool = False):
    """
    Main execution function.

    Args:
        dry_run: If True, simulate without making changes
    """
    print("="*70)
    print("CT SYNTHSEG RESULTS ORGANIZER")
    print("="*70)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No files will be modified\n")

    # Validate source directories
    print("\n📁 Validating source directories...")
    for name, path in [
        ("Volumes", VOLUMES_DIR),
        ("QC", QC_DIR),
        ("Segmentation", SEGMENTATION_DIR)
    ]:
        if not path.exists():
            print(f"✗ {name} directory not found: {path}")
            return 1
        print(f"✓ {name}: {path}")

    # Get list of subjects from volumes directory
    print("\n📋 Scanning for subjects...")
    volume_files = list(VOLUMES_DIR.glob("*.csv"))
    subject_ids = [extract_subject_id(f.name) for f in volume_files]
    print(f"✓ Found {len(subject_ids)} subjects")

    # Create target directory
    if not dry_run:
        print(f"\n📂 Creating target directory: {TARGET_DIR}")
        TARGET_DIR.mkdir(parents=True, exist_ok=True)
    else:
        print(f"\n📂 [DRY RUN] Would create: {TARGET_DIR}")

    # Process each subject
    print("\n🔄 Processing subjects...")
    print("-"*70)

    successes = []
    failures = []

    for i, subject_id in enumerate(subject_ids, 1):
        success, message = copy_subject_files(subject_id, dry_run=dry_run)

        if success:
            successes.append(subject_id)
        else:
            failures.append(message)

        # Print progress
        if i % 10 == 0 or i == len(subject_ids):
            print(f"Progress: {i}/{len(subject_ids)} subjects processed")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"✓ Successful: {len(successes)}/{len(subject_ids)}")
    print(f"✗ Failed:     {len(failures)}/{len(subject_ids)}")

    if failures:
        print("\n⚠️  Failed subjects:")
        for failure in failures:
            print(f"  {failure}")

    # Verify structure (only if not dry run)
    if not dry_run:
        print("\n🔍 Verifying structure...")
        total, complete, incomplete = verify_structure()
        print(f"✓ Total subject directories: {total}")
        print(f"✓ Complete (3 files):        {complete}")

        if incomplete:
            print(f"⚠️  Incomplete directories:     {len(incomplete)}")
            for item in incomplete[:5]:  # Show first 5
                print(f"  {item}")
            if len(incomplete) > 5:
                print(f"  ... and {len(incomplete) - 5} more")
        else:
            print("✓ All directories complete!")

    print("\n" + "="*70)
    print("ORGANIZATION COMPLETE" if not dry_run else "DRY RUN COMPLETE")
    print("="*70)

    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    import sys

    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    exit_code = main(dry_run=dry_run)
    sys.exit(exit_code)
