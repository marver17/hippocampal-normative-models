#!/usr/bin/env python3
"""
Convert OASIS-2 from Analyze 7.5 format to BIDS using nibabel
OASIS-2 is longitudinal: 373 imaging sessions from 150 subjects (2-5 sessions each)
"""

import os
import json
import pandas as pd
from pathlib import Path
import nibabel as nib
import numpy as np
import re

# Paths
oasis2_raw = "/mnt/db_ext/RAW/oasis/OASIS 2"
oasis2_bids = "/mnt/db_ext/RAW/oasis/OASIS2_BIDS"

print("="*80)
print("OASIS-2: Converting Analyze 7.5 to BIDS (Longitudinal)")
print("="*80)

# Get list of sessions
if not Path(oasis2_raw).exists():
    print(f"\n✗ ERRORE: La directory di input non esiste: {oasis2_raw}")
    print("Verifica che il percorso sia corretto e che il disco sia montato.")
    exit(1)

sessions = sorted([d for d in os.listdir(oasis2_raw) if d.startswith('OAS2_')])
print(f"\nFound {len(sessions)} imaging sessions")

if not sessions:
    print("\n⚠ ATTENZIONE: Nessuna sessione di imaging trovata nella directory di input.")
    print(f"Controlla che la directory '{oasis2_raw}' contenga le cartelle delle sessioni (es. 'OAS2_0001_MR1').")

# Storage for participants and sessions data
participants_data = {}
sessions_data = []
conversion_errors = []

# Process each session
for i, session in enumerate(sessions, 1):
    # Parse subject and session ID
    # Format: OAS2_0001_MR1, OAS2_0001_MR2, etc.
    match = re.match(r'(OAS2_\d+)_MR(\d+)', session)
    if not match:
        conversion_errors.append(f"Cannot parse session ID: {session}")
        continue

    subject_id = match.group(1)  # OAS2_0001
    session_num = int(match.group(2))  # 1, 2, 3, etc.

    bids_subject_id = f"sub-{subject_id}"
    bids_session_id = f"ses-{session_num:02d}"

    if i % 50 == 0 or i == 1:
        print(f"\n[{i}/{len(sessions)}] Processing {subject_id} {bids_session_id}...")

    # Create BIDS directory structure
    session_dir = Path(oasis2_bids) / bids_subject_id / bids_session_id / "anat"
    session_dir.mkdir(parents=True, exist_ok=True)

    # Path to original session data
    orig_session_dir = Path(oasis2_raw) / session
    raw_dir = orig_session_dir / "RAW"

    # Parse metadata from TXT file
    txt_file = orig_session_dir / f"{session}.txt"
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
                    elif key in ['M/F', 'HAND', 'DELAY']:
                        metadata[key] = value

    # Add session data
    sessions_data.append({
        'participant_id': bids_subject_id,
        'session_id': bids_session_id,
        'age': metadata.get('AGE', 'n/a'),
        'cdr': metadata.get('CDR', 'n/a'),
        'mmse': metadata.get('MMSE', 'n/a'),
        'etiv': metadata.get('eTIV', 'n/a'),
        'asf': metadata.get('ASF', 'n/a'),
        'nwbv': metadata.get('nWBV', 'n/a'),
        'delay': metadata.get('DELAY', 'n/a')
    })

    # Add participant data (only once per subject)
    if bids_subject_id not in participants_data:
        participants_data[bids_subject_id] = {
            'participant_id': bids_subject_id,
            'sex': 'M' if metadata.get('M/F') == 'Male' else 'F' if metadata.get('M/F') == 'Female' else 'n/a',
            'hand': 'R' if metadata.get('HAND') == 'Right' else 'L' if metadata.get('HAND') == 'Left' else 'n/a',
            'education': metadata.get('EDUC', 'n/a'),
            'ses': metadata.get('SES', 'n/a'),
            'age_baseline': metadata.get('AGE', 'n/a') if session_num == 1 else participants_data.get(bids_subject_id, {}).get('age_baseline', 'n/a')
        }

    # We search recursively for .hdr files within the session directory to be more robust
    mpr_files_paths = sorted(list(orig_session_dir.glob('**/*nifti.hdr')))

    if not mpr_files_paths:
        error_msg = f"{bids_subject_id} {bids_session_id}: Nessun file '*.hdr' trovato in {orig_session_dir}"
        conversion_errors.append(error_msg)
        continue
    
    if i % 50 == 0 or i == 1:
        print(f"  ✓ Trovati {len(mpr_files_paths)} file .hdr da convertire.")

    for run_idx, hdr_file in enumerate(mpr_files_paths, 1):
        mpr_base = hdr_file.name.replace('.hdr', '')

        # Output filename with run number
        if len(mpr_files_paths) > 1:
            output_base = f"{bids_subject_id}_{bids_session_id}_run-{run_idx:02d}_T1w"
        else:
            output_base = f"{bids_subject_id}_{bids_session_id}_T1w"

        output_nii = session_dir / f"{output_base}.nii.gz"
        output_json = session_dir / f"{output_base}.json"

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

            # Add session metadata
            if metadata:
                json_data["SessionMetadata"] = {
                    "Age": metadata.get('AGE'),
                    "Sex": metadata.get('M/F'),
                    "CDR": metadata.get('CDR'),
                    "MMSE": metadata.get('MMSE'),
                    "eTIV": metadata.get('eTIV'),
                    "ASF": metadata.get('ASF'),
                    "nWBV": metadata.get('nWBV'),
                    "Delay": metadata.get('DELAY')
                }

            with open(output_json, 'w') as f:
                json.dump(json_data, f, indent=2)

        except Exception as e:
            error_msg = f"{bids_subject_id} {bids_session_id} run {run_idx}: {type(e).__name__}: {e}"
            conversion_errors.append(error_msg)
            print(f"  ✗ Error: {error_msg}")

print("\n" + "="*80)
print("Creating participants.tsv")
print("="*80)

# Create participants dataframe
participants_df = pd.DataFrame(list(participants_data.values()))
participants_df = participants_df.sort_values('participant_id').reset_index(drop=True)

# Save participants.tsv
participants_file = Path(oasis2_bids) / "participants.tsv"
participants_df.to_csv(participants_file, sep='\t', index=False)

print(f"\n✓ Saved participants.tsv: {len(participants_df)} subjects")

# Create participants.json descriptor
participants_json = {
    "participant_id": {
        "Description": "Unique participant identifier",
        "LongName": "Participant ID"
    },
    "age_baseline": {
        "Description": "Age of participant at baseline (first session)",
        "Units": "years",
        "LongName": "Age at Baseline"
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
    }
}

participants_json_file = Path(oasis2_bids) / "participants.json"
with open(participants_json_file, 'w') as f:
    json.dump(participants_json, f, indent=4)

print(f"✓ Saved participants.json")

print("\n" + "="*80)
print("Creating sessions.tsv files")
print("="*80)

# Group sessions by participant
sessions_df = pd.DataFrame(sessions_data)

# Create sessions.tsv for each subject
for subject_id in participants_df['participant_id']:
    subject_sessions = sessions_df[sessions_df['participant_id'] == subject_id].copy()
    subject_sessions = subject_sessions.drop('participant_id', axis=1)
    subject_sessions = subject_sessions.sort_values('session_id').reset_index(drop=True)

    sessions_file = Path(oasis2_bids) / subject_id / f"{subject_id}_sessions.tsv"
    subject_sessions.to_csv(sessions_file, sep='\t', index=False)

print(f"✓ Saved sessions.tsv for {len(participants_df)} subjects")

# Create sessions.json descriptor (applies to all sessions.tsv files)
sessions_json = {
    "session_id": {
        "Description": "Session identifier",
        "LongName": "Session ID"
    },
    "age": {
        "Description": "Age of participant at this session",
        "Units": "years",
        "LongName": "Age"
    },
    "cdr": {
        "Description": "Clinical Dementia Rating (CDR) global score at this session",
        "Levels": {
            "0": "No dementia",
            "0.5": "Very mild dementia",
            "1": "Mild dementia",
            "2": "Moderate dementia"
        },
        "LongName": "Clinical Dementia Rating"
    },
    "mmse": {
        "Description": "Mini-Mental State Examination score at this session",
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
    },
    "delay": {
        "Description": "Time delay from baseline scan (in days)",
        "Units": "days",
        "LongName": "Delay from Baseline"
    }
}

sessions_json_file = Path(oasis2_bids) / "sessions.json"
with open(sessions_json_file, 'w') as f:
    json.dump(sessions_json, f, indent=4)

print(f"✓ Saved sessions.json")

# Print summary
print("\n" + "="*80)
print("CONVERSION SUMMARY")
print("="*80)
print(f"\nTotal subjects: {len(participants_df)}")
print(f"Total sessions: {len(sessions_df)}")
print(f"Sessions per subject: {len(sessions_df)/len(participants_df):.1f} average")

if conversion_errors:
    print(f"\n⚠ Conversion errors: {len(conversion_errors)}")
    print("First 5 errors:")
    for err in conversion_errors[:5]:
        print(f"  - {err}")

print(f"\nAge at baseline:")
age_data = pd.to_numeric(participants_df['age_baseline'], errors='coerce')
print(f"  Range: {age_data.min():.0f} - {age_data.max():.0f} years")
print(f"  Mean: {age_data.mean():.1f} ± {age_data.std():.1f}")

print(f"\nSex distribution:")
for sex in ['M', 'F']:
    count = (participants_df['sex'] == sex).sum()
    print(f"  {sex}: {count} ({count/len(participants_df)*100:.1f}%)")

print(f"\nCDR distribution at baseline:")
baseline_sessions = sessions_df[sessions_df['session_id'] == 'ses-01']
cdr_counts = baseline_sessions['cdr'].value_counts().sort_index()
for cdr, count in cdr_counts.items():
    if cdr != 'n/a':
        print(f"  CDR {cdr}: {count} ({count/len(baseline_sessions)*100:.1f}%)")

print(f"\nMMSE at baseline:")
mmse_data = pd.to_numeric(baseline_sessions['mmse'], errors='coerce')
print(f"  Range: {mmse_data.min():.0f} - {mmse_data.max():.0f}")
print(f"  Mean: {mmse_data.mean():.1f} ± {mmse_data.std():.1f}")

# Count sessions per subject
sessions_per_subject = sessions_df.groupby('participant_id').size()
print(f"\nSessions per subject distribution:")
for n_sessions in sorted(sessions_per_subject.unique()):
    count = (sessions_per_subject == n_sessions).sum()
    print(f"  {n_sessions} sessions: {count} subjects ({count/len(participants_df)*100:.1f}%)")

print("\n" + "="*80)
print("OASIS-2 conversion complete!")
print("="*80)
