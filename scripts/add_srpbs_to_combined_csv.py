#!/usr/bin/env python3
"""
Add SRPBS subjects to combined synthseg processing CSV
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("Adding SRPBS to Combined SynthSeg Processing CSV")
print("="*80)

# Paths
srpbs_bids = Path("/mnt/db_ext/RAW/SRPBS_OPEN/SRPBS_BIDS")
oasis_csv = Path("/mnt/db_ext/RAW/oasis/oasis_combined_synthseg_processing.csv")
output_csv = Path("/mnt/db_ext/RAW/oasis/oasis_srpbs_combined_synthseg_processing.csv")

# Load existing OASIS CSV
oasis_df = pd.read_csv(oasis_csv)
print(f"\nOASIS CSV loaded: {len(oasis_df)} subjects")

# Find all SRPBS subjects
subjects = sorted([d for d in srpbs_bids.iterdir() if d.is_dir() and d.name.startswith('sub-')])
print(f"SRPBS subjects found: {len(subjects)}")

# Create SRPBS entries
srpbs_entries = []

for subject_dir in subjects:
    subject_id = subject_dir.name
    anat_dir = subject_dir / 'anat'

    # Find T1w file
    t1w_file = anat_dir / f"{subject_id}_T1w.nii.gz"

    if t1w_file.exists():
        srpbs_entries.append({
            'subject_id': subject_id,
            'input_image': str(t1w_file.absolute()),
            'output_dir': str(srpbs_bids / 'derivatives' / 'synthseg'),
            'num_threads': 4
        })

print(f"SRPBS entries created: {len(srpbs_entries)}")

# Create SRPBS DataFrame
srpbs_df = pd.DataFrame(srpbs_entries)

# Combine with OASIS
combined_df = pd.concat([oasis_df, srpbs_df], ignore_index=True)

# Save combined CSV
combined_df.to_csv(output_csv, index=False)

print(f"\n✓ Combined CSV saved: {output_csv}")
print(f"\nTotal subjects in combined CSV: {len(combined_df)}")
print(f"  OASIS: {len(oasis_df)}")
print(f"  SRPBS: {len(srpbs_df)}")

print(f"\nFirst 3 SRPBS entries:")
print(srpbs_df.head(3).to_string(index=False))

print(f"\nLast 3 SRPBS entries:")
print(srpbs_df.tail(3).to_string(index=False))

# Create derivatives directory
derivatives_dir = srpbs_bids / 'derivatives' / 'synthseg'
derivatives_dir.mkdir(parents=True, exist_ok=True)
print(f"\n✓ Created: {derivatives_dir}")

# Create dataset_description.json for derivatives
import json

dataset_desc = {
    "Name": "SynthSeg Segmentation",
    "BIDSVersion": "1.6.0",
    "DatasetType": "derivative",
    "GeneratedBy": [
        {
            "Name": "SynthSeg",
            "Version": "2.0",
            "Description": "Robust Segmentation of brain MRI in the wild"
        }
    ],
    "SourceDatasets": [
        {
            "DatasetName": "SRPBS"
        }
    ]
}

desc_file = derivatives_dir / 'dataset_description.json'
with open(desc_file, 'w') as f:
    json.dump(dataset_desc, f, indent=4)

print(f"✓ Created: {desc_file}")

print("\n" + "="*80)
print("Done!")
print("="*80)
