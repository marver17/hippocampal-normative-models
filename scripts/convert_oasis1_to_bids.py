#!/usr/bin/env python3
"""
Convert OASIS-1 from Analyze 7.5 format to BIDS using nibabel
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
print("OASIS-1: Converting Analyze 7.5 to BIDS")
print("="*80)

# Get list of subjects
subjects = sorted([d for d in os.listdir(oasis1_raw) if d.startswith('OAS1_')])
print(f"\nFound {len(subjects)} subjects")

# Storage for participants data
participants_data = []
conversion_errors = []

# Process each subject
for i, subject in enumerate(subjects, 1):
    subject_id = subject.replace('_MR1', '')  # OAS1_0001_MR1 -> OAS1_0001
    bids_subject_id = f"sub-{subject_id}"

    if i % 50 == 0 or i == 1:
        print(f"\n[{i}/{len(subjects)}] Processing {subject_id}...")

    # Create BIDS subject directory
    subject_dir = Path(oasis1_bids) / bids_subject_id / "anat"
    subject_dir.mkdir(parents=True, exist_ok=True)

    # Path to original subject data
    orig_subject_dir = Path(oasis1_raw) / subject
    raw_dir = orig_subject_dir / "RAW"

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

    # Find MPR scans (usually 3-4 per subject)
    if not raw_dir.exists():
        conversion_errors.append(f"{subject_id}: RAW directory not found")
        continue

    mpr_files = sorted([f for f in os.listdir(raw_dir) if f.endswith('_anon.hdr')])

    # Convert each MPR scan using nibabel
    for run_idx, mpr_file in enumerate(mpr_files, 1):
        mpr_base = mpr_file.replace('.hdr', '')
        hdr_file = raw_dir / mpr_file

        # Output filename with run number
        if len(mpr_files) > 1:
            output_base = f"{bids_subject_id}_run-{run_idx:02d}_T1w"
        else:
            output_base = f"{bids_subject_id}_T1w"

        output_nii = subject_dir / f"{output_base}.nii.gz"
        output_json = subject_dir / f"{output_base}.json"

        try:
            # Load Analyze format image
            img = nib.load(str(hdr_file))

            # Get data and squeeze extra dimensions if needed
            data = img.get_fdata()
            if data.ndim == 4 and data.shape[3] == 1:
                data = data[:, :, :, 0]

            # Convert to NIfTI and save as compressed
            nii_img = nib.Nifti1Image(data, img.affine)
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
                "SourceFormat": "Analyze7.5"
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
            error_msg = f"{bids_subject_id} run {run_idx}: {type(e).__name__}: {e}"
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

# Create participants.json descriptor
participants_json = {
    "participant_id": {
        "Description": "Unique participant identifier",
        "LongName": "Participant ID"
    },
    "age": {
        "Description": "Age of participant at time of scan",
        "Units": "years",
        "LongName": "Age"
    },
    "sex": {
        "Description": "Biological sex of the participant",
        "Levels": {
            "M": "Male",
            "F": "Female"
        },
        "LongName": "Sex"
    },
    "hand": {
        "Description": "Handedness of participant",
        "Levels": {
            "R": "Right-handed",
            "L": "Left-handed"
        },
        "LongName": "Handedness"
    },
    "education": {
        "Description": "Years of education completed",
        "Units": "years",
        "LongName": "Years of Education"
    },
    "ses": {
        "Description": "Socioeconomic status (Hollingshead Index of Social Position)",
        "LongName": "Socioeconomic Status"
    },
    "cdr": {
        "Description": "Clinical Dementia Rating (CDR) global score",
        "Levels": {
            "0": "No dementia",
            "0.5": "Very mild dementia",
            "1": "Mild dementia",
            "2": "Moderate dementia"
        },
        "LongName": "Clinical Dementia Rating"
    },
    "mmse": {
        "Description": "Mini-Mental State Examination score",
        "LongName": "MMSE"
    },
    "etiv": {
        "Description": "Estimated Total Intracranial Volume",
        "Units": "mm³",
        "LongName": "Estimated Total Intracranial Volume"
    },
    "asf": {
        "Description": "Atlas Scaling Factor (volume scaling factor required to match each subject to the atlas)",
        "LongName": "Atlas Scaling Factor"
    },
    "nwbv": {
        "Description": "Normalized Whole Brain Volume (ratio of brain volume to intracranial volume)",
        "LongName": "Normalized Whole Brain Volume"
    }
}

participants_json_file = Path(oasis1_bids) / "participants.json"
with open(participants_json_file, 'w') as f:
    json.dump(participants_json, f, indent=4)

print(f"✓ Saved participants.json")

# Print summary
print("\n" + "="*80)
print("OASIS-1 conversion complete!")
print("="*80)
