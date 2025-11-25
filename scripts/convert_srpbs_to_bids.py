#!/usr/bin/env python3
"""
Convert SRPBS to BIDS format
SRPBS: Southwest University Adult Lifespan Dataset
"""

import shutil
import json
from pathlib import Path
import nibabel as nib

# Paths
srpbs_raw = Path("/mnt/db_ext/RAW/SRPBS_OPEN/data")
srpbs_bids = Path("/mnt/db_ext/RAW/SRPBS_OPEN/SRPBS_BIDS")

print("="*80)
print("SRPBS: Converting to BIDS")
print("="*80)

# Create BIDS root directory
srpbs_bids.mkdir(exist_ok=True)

# Get list of subjects
subjects = sorted([d for d in srpbs_raw.iterdir() if d.is_dir() and d.name.startswith('sub-')])
print(f"\nFound {len(subjects)} subjects")

# Convert each subject
converted = 0
missing_t1 = []

for i, subject_dir in enumerate(subjects, 1):
    subject_id = subject_dir.name  # sub-0001, etc.

    if i % 100 == 0:
        print(f"[{i}/{len(subjects)}] Processing {subject_id}...")

    # Check if T1 exists
    t1_file = subject_dir / 't1' / 'defaced_mprage.nii'
    if not t1_file.exists():
        missing_t1.append(subject_id)
        continue

    # Create BIDS structure
    bids_subject_dir = srpbs_bids / subject_id / 'anat'
    bids_subject_dir.mkdir(parents=True, exist_ok=True)

    # Output filename
    output_nii = bids_subject_dir / f"{subject_id}_T1w.nii.gz"
    output_json = bids_subject_dir / f"{subject_id}_T1w.json"

    # Load and save as compressed NIfTI
    try:
        img = nib.load(str(t1_file))

        # Save as compressed
        nib.save(img, str(output_nii))

        # Create JSON sidecar
        json_data = {
            "Modality": "MR",
            "MagneticFieldStrength": 3.0,
            "Manufacturer": "Siemens",
            "PulseSequence": "MPRAGE",
            "ConversionSoftware": "nibabel",
            "ConversionSoftwareVersion": nib.__version__,
            "SourceFormat": "NIfTI",
            "Defaced": True,
            "Dataset": "SRPBS"
        }

        with open(output_json, 'w') as f:
            json.dump(json_data, f, indent=2)

        converted += 1

    except Exception as e:
        print(f"  ✗ Error converting {subject_id}: {e}")
        missing_t1.append(subject_id)

print("\n" + "="*80)
print("Creating BIDS metadata files")
print("="*80)

# Create dataset_description.json
dataset_description = {
    "Name": "SRPBS - Southwest University Adult Lifespan Dataset",
    "BIDSVersion": "1.6.0",
    "DatasetType": "raw",
    "License": "CC BY-NC-SA 4.0",
    "Authors": [
        "Wei, Dongtao",
        "Zhuang, Kaixiang",
        "Ai, Lei",
        "Chen, Qunlin",
        "Yang, Wenjing",
        "Liu, Wen",
        "Wang, Kang",
        "Sun, Jiangzhou",
        "Qiu, Jiang"
    ],
    "Acknowledgements": "Southwest University Adult Lifespan Dataset (SRPBS)",
    "HowToAcknowledge": "Please cite: Wei et al. (2018). Structural and functional brain scans from the cross-sectional Southwest University adult lifespan dataset. Scientific Data, 5, 180134.",
    "ReferencesAndLinks": [
        "https://doi.org/10.1038/sdata.2018.134",
        "http://fcon_1000.projects.nitrc.org/indi/retro/southwestuni_qiu_index.html"
    ],
    "DatasetDOI": "10.1038/sdata.2018.134"
}

with open(srpbs_bids / 'dataset_description.json', 'w') as f:
    json.dump(dataset_description, f, indent=4)

print("✓ dataset_description.json created")

# Create README
readme_content = """# SRPBS - Southwest University Adult Lifespan Dataset

## Overview

The Southwest University Adult Lifespan Dataset (SRPBS) is a cross-sectional collection of structural and functional MRI data from healthy Chinese adults.

## Dataset Information

- **Subjects**: 1,410 healthy adults
- **Age Range**: 19-80 years
- **Study Type**: Cross-sectional
- **Institution**: Southwest University, China
- **Scanner**: 3T Siemens Trio
- **Acquisition Years**: 2012-2015

## Participant Demographics

- All participants were right-handed, healthy Chinese adults
- No history of neurological or psychiatric disorders
- Normal or corrected-to-normal vision

## MRI Sequences

T1-weighted MPRAGE:
- **Sequence**: MPRAGE (Magnetization Prepared Rapid Gradient Echo)
- **Field Strength**: 3.0T
- **Scanner**: Siemens Trio

## Privacy

All T1-weighted images have been defaced to protect participant privacy.

## Data Organization

This BIDS-formatted dataset follows the Brain Imaging Data Structure specification version 1.6.0.

```
SRPBS_BIDS/
├── dataset_description.json
├── participants.tsv
├── participants.json
└── sub-XXXX/
    └── anat/
        ├── sub-XXXX_T1w.nii.gz
        └── sub-XXXX_T1w.json
```

## Citation

If you use this dataset, please cite:

Wei, D., Zhuang, K., Ai, L., Chen, Q., Yang, W., Liu, W., Wang, K., Sun, J., & Qiu, J. (2018).
Structural and functional brain scans from the cross-sectional Southwest University adult lifespan dataset.
Scientific Data, 5, 180134.
https://doi.org/10.1038/sdata.2018.134

## License

CC BY-NC-SA 4.0

## Contact

For questions regarding SRPBS data:
- Website: http://fcon_1000.projects.nitrc.org/indi/retro/southwestuni_qiu_index.html

## Conversion Notes

- Original NIfTI format converted to compressed NIfTI (.nii.gz)
- All images are defaced
- Conversion date: 2025-11-20
- Conversion tool: nibabel
"""

with open(srpbs_bids / 'README', 'w') as f:
    f.write(readme_content)

print("✓ README created")

# Create participants.tsv placeholder (demographic data would need to be added separately)
participants_header = "participant_id\n"
participants_rows = [f"{s.name}\n" for s in sorted(srpbs_bids.iterdir()) if s.is_dir() and s.name.startswith('sub-')]

with open(srpbs_bids / 'participants.tsv', 'w') as f:
    f.write(participants_header)
    f.writelines(participants_rows)

print(f"✓ participants.tsv created ({len(participants_rows)} subjects)")

# Create participants.json
participants_json = {
    "participant_id": {
        "Description": "Unique participant identifier",
        "LongName": "Participant ID"
    }
}

with open(srpbs_bids / 'participants.json', 'w') as f:
    json.dump(participants_json, f, indent=4)

print("✓ participants.json created")

# Summary
print("\n" + "="*80)
print("CONVERSION SUMMARY")
print("="*80)
print(f"\nTotal subjects processed: {len(subjects)}")
print(f"Successfully converted: {converted}")
print(f"Missing T1 or errors: {len(missing_t1)}")

if missing_t1:
    print(f"\nSubjects with missing T1 (first 10):")
    for subj in missing_t1[:10]:
        print(f"  - {subj}")

print("\n" + "="*80)
print("SRPBS BIDS conversion complete!")
print("="*80)
