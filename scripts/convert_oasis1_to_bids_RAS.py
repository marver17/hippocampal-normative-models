#!/usr/bin/env python3
"""
Convert OASIS-1 from Analyze 7.5 format to BIDS using nibabel
IMPORTANT: Using PROCESSED files + REORIENTING to RAS (to match OASIS-3 and SRPBS)
"""

import os
import json
import pandas as pd
from pathlib import Path
import nibabel as nib
import numpy as np

# Paths
oasis1_raw = "/mnt/db_ext/RAW/oasis/OASIS 1"
oasis1_bids = "/mnt/db_ext/RAW/oasis/OASIS1_BIDS"

print("="*80)
print("OASIS-1: Converting PROCESSED Analyze 7.5 to BIDS with RAS orientation")
print("="*80)

# Get list of subjects
subjects = sorted([d for d in os.listdir(oasis1_raw) if d.startswith('OAS1_')])
print(f"\nFound {len(subjects)} subjects")
print("Reorienting from LAS to RAS to match OASIS-3 and SRPBS")

# Storage for participants data
participants_data = []
conversion_errors = []

# Process each subject
for i, subject in enumerate(subjects, 1):
    subject_id = subject.replace('_MR1', '')
    bids_subject_id = f"sub-{subject_id}"

    if i % 50 == 0 or i == 1:
        print(f"\n[{i}/{len(subjects)}] Processing {subject_id}...")

    # Create BIDS subject directory
    subject_dir = Path(oasis1_bids) / bids_subject_id / "anat"
    subject_dir.mkdir(parents=True, exist_ok=True)

    # Path to original subject data
    orig_subject_dir = Path(oasis1_raw) / subject

    # USE PROCESSED FILES
    processed_dir = orig_subject_dir / "PROCESSED" / "MPRAGE" / "SUBJ_111"

    # Parse metadata from TXT file
    txt_file = orig_subject_dir / f"{subject}.txt"
    metadata = {}

    if txt_file.exists():
        with open(txt_file, 'r') as f:
            for line in f:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    if key in ['AGE', 'EDUC', 'SES', 'CDR', 'MMSE', 'eTIV', 'ASF', 'nWBV']:
                        try:
                            metadata[key] = float(value) if '.' in value else int(value)
                        except:
                            metadata[key] = value
                    elif key in ['M/F', 'HAND']:
                        metadata[key] = value

    # Add to participants data
    participants_data.append({
        'participant_id': bids_subject_id,
        'age': metadata.get('AGE', 'n/a'),
        'sex': 'M' if metadata.get('M/F') == 'Male' else 'F' if metadata.get('M/F') == 'Female' else 'n/a',
        'hand': 'R' if metadata.get('HAND') == 'Right' else 'L' if metadata.get('HAND') == 'Left' else 'n/a',
        'education': metadata.get('EDUC', 'n/a'),
        'ses': metadata.get('SES', 'n/a'),
        'cdr': metadata.get('CDR', 'n/a'),
        'mmse': metadata.get('MMSE', 'n/a'),
        'etiv': metadata.get('eTIV', 'n/a'),
        'asf': metadata.get('ASF', 'n/a'),
        'nwbv': metadata.get('nWBV', 'n/a')
    })

    # Find PROCESSED file
    if not processed_dir.exists():
        conversion_errors.append(f"{subject_id}: PROCESSED directory not found")
        continue

    processed_files = sorted(list(processed_dir.glob('*_sbj_111.hdr')))

    if not processed_files:
        conversion_errors.append(f"{subject_id}: No processed .hdr file found")
        continue

    # Convert the processed file
    hdr_file = processed_files[0]
    output_base = f"{bids_subject_id}_T1w"
    output_nii = subject_dir / f"{output_base}.nii.gz"
    output_json = subject_dir / f"{output_base}.json"

    try:
        # Load Analyze format image (will be in LAS)
        img = nib.load(str(hdr_file))

        # Get data and squeeze extra dimensions if needed
        data = img.get_fdata()
        if data.ndim == 4 and data.shape[3] == 1:
            data = data[:, :, :, 0]

        # REORIENT from LAS to RAS
        # LAS has negative X (left is positive), RAS has positive X (right is positive)
        # We need to flip the X axis
        data_ras = np.flip(data, axis=0)  # Flip X axis: L->R

        # Create new affine for RAS orientation
        # Original LAS affine has -1 for X, we need +1
        affine_ras = img.affine.copy()
        affine_ras[0, 0] = 1.0  # Change from -1 to +1 (L to R)
        affine_ras[0, 3] = -affine_ras[0, 3]  # Adjust origin

        # Create NIfTI image with RAS orientation
        nii_img = nib.Nifti1Image(data_ras, affine_ras)

        # Verify orientation is now RAS
        assert nib.aff2axcodes(nii_img.affine) == ('R', 'A', 'S'), "Orientation conversion failed!"

        nib.save(nii_img, str(output_nii))

        # Create JSON sidecar
        json_data = {
            "Modality": "MR",
            "MagneticFieldStrength": 1.5,
            "Manufacturer": "Siemens",
            "ManufacturersModelName": "Vision",
            "PulseSequence": "MPRAGE",
            "ScanningSequence": "GR\\IR",
            "SequenceVariant": "SP\\MP",
            "EchoTime": 0.004,
            "RepetitionTime": 0.0095,
            "InversionTime": 0.02,
            "FlipAngle": 10,
            "PhaseEncodingDirection": "j-",
            "ConversionSoftware": "nibabel",
            "ConversionSoftwareVersion": nib.__version__,
            "SourceFormat": "Analyze7.5",
            "ProcessingNote": "PROCESSED/MPRAGE/SUBJ_111 - N4 corrected, reoriented from LAS to RAS"
        }

        # Add subject metadata
        if metadata:
            json_data["SubjectMetadata"] = {
                "Age": metadata.get('AGE'),
                "Sex": metadata.get('M/F'),
                "CDR": metadata.get('CDR'),
                "MMSE": metadata.get('MMSE'),
                "eTIV": metadata.get('eTIV'),
                "ASF": metadata.get('ASF'),
                "nWBV": metadata.get('nWBV')
            }

        with open(output_json, 'w') as f:
            json.dump(json_data, f, indent=2)

    except Exception as e:
        error_msg = f"{bids_subject_id}: {type(e).__name__}: {e}"
        conversion_errors.append(error_msg)
        print(f"  ✗ Error: {error_msg}")

print("\n" + "="*80)
print("Creating participants.tsv")
print("="*80)

# Create participants dataframe
participants_df = pd.DataFrame(participants_data)
participants_df = participants_df.sort_values('participant_id').reset_index(drop=True)

# Save participants.tsv
participants_file = Path(oasis1_bids) / "participants.tsv"
participants_df.to_csv(participants_file, sep='\t', index=False)

print(f"\n✓ Saved participants.tsv: {len(participants_df)} subjects")

# Create participants.json
participants_json = {
    "participant_id": {"Description": "Unique participant identifier"},
    "age": {"Description": "Age at time of scan", "Units": "years"},
    "sex": {"Description": "Biological sex", "Levels": {"M": "Male", "F": "Female"}},
    "hand": {"Description": "Handedness", "Levels": {"R": "Right", "L": "Left"}},
    "education": {"Description": "Years of education", "Units": "years"},
    "ses": {"Description": "Socioeconomic status"},
    "cdr": {"Description": "Clinical Dementia Rating", "Levels": {"0": "No dementia", "0.5": "Very mild", "1": "Mild", "2": "Moderate"}},
    "mmse": {"Description": "Mini-Mental State Examination"},
    "etiv": {"Description": "Estimated Total Intracranial Volume", "Units": "mm³"},
    "asf": {"Description": "Atlas Scaling Factor"},
    "nwbv": {"Description": "Normalized Whole Brain Volume"}
}

with open(Path(oasis1_bids) / "participants.json", 'w') as f:
    json.dump(participants_json, f, indent=4)

print(f"✓ Saved participants.json")

# Summary
print("\n" + "="*80)
print("CONVERSION SUMMARY")
print("="*80)
print(f"\nTotal subjects: {len(participants_df)}")
print(f"Successfully converted: {len(participants_df) - len(conversion_errors)}")

if conversion_errors:
    print(f"Errors: {len(conversion_errors)}")
    for err in conversion_errors[:3]:
        print(f"  - {err}")

print("\n✓ All images reoriented to RAS (matches OASIS-3, SRPBS)")
print("="*80)
