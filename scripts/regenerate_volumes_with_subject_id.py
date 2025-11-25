#!/usr/bin/env python3
"""
Regenerate volumes CSV files with subject_id as a column (not index)
"""

import os
import pandas as pd
from pathlib import Path

# Paths
oasis2_path = "/mnt/db_ext/RAW/oasis/OASIS2_BIDS/derivatives/synthseg/"
oasis3_path = "/mnt/db_ext/RAW/oasis/OASIS3_BIDS/derivatives/synthseg/"
adni_path = "/mnt/db_ext/ADNI_DB/derivatives/synthseg/"
ixi_path = "/mnt/db_ext/RAW/IXI/derivatives/synthseg/"
ppmi_path = "/mnt/db_ext/RAW/PPMI/nifti/derivatives/synthseg/"
srpb_path = "/mnt/db_ext/RAW/SRPBS_OPEN/SRPBS_BIDS/derivatives/synthseg"

output_dir = Path('/home/mario/Repository/Normal_Alzeihmer/data/volumes')

print('='*80)
print('Regenerating Volumes CSV with subject_id column')
print('='*80)

def find_volumes_and_qc(path):
    """Find all volumes.csv and qc_scores.csv files"""
    volumes_list = []
    for root, dirs, files in os.walk(path):
        if 'volumes.csv' in files and 'qc_scores.csv' in files:
            subject_id = os.path.basename(root)
            volumes_list.append({
                'subject_id': subject_id,
                'volumes': os.path.join(root, 'volumes.csv'),
                'qc': os.path.join(root, 'qc_scores.csv')
            })
    return pd.DataFrame(volumes_list)

def aggregate_volumes_and_qc(volumes_df):
    """Aggregate volumes and QC for all subjects"""
    aggregated_data = []
    for idx, row in volumes_df.iterrows():
        vol_df = pd.read_csv(row['volumes'])
        qc_df = pd.read_csv(row['qc'])
        vol_df = vol_df.add_prefix('vol_')
        qc_df = qc_df.add_prefix('qc_')
        subject_id = row['subject_id']

        # Merge volumes and QC
        merged_df = pd.merge(vol_df, qc_df, left_on='vol_subject', right_on='qc_subject')

        # Add subject_id as a column (NOT as index!)
        merged_df['subject_id'] = subject_id

        # Drop redundant subject columns
        merged_df = merged_df.drop(columns=['vol_subject', 'qc_subject'])

        aggregated_data.append(merged_df)

    return pd.concat(aggregated_data, ignore_index=True)

# Process each dataset
datasets = {
    'oasis2': oasis2_path,
    'oasis3': oasis3_path,
    'adni': adni_path,
    'ixi': ixi_path,
    'ppmi': ppmi_path,
    'srpb': srpb_path
}

for dataset_name, path in datasets.items():
    print(f'\n{dataset_name.upper()}:')

    if not os.path.exists(path):
        print(f'  ✗ Path not found: {path}')
        continue

    # Find volumes
    volumes_df = find_volumes_and_qc(path)
    print(f'  Found {len(volumes_df)} subjects')

    if len(volumes_df) == 0:
        print(f'  ✗ No volumes found')
        continue

    # Aggregate
    try:
        aggregated = aggregate_volumes_and_qc(volumes_df)
        print(f'  Aggregated {len(aggregated)} subjects')

        # Verify subject_id is a column
        if 'subject_id' not in aggregated.columns:
            print(f'  ✗ ERROR: subject_id not found in columns!')
            continue

        print(f'  Columns: {len(aggregated.columns)}')
        print(f'  First few columns: {list(aggregated.columns[:5])}')

        # Save with subject_id as a regular column
        output_file = output_dir / f'{dataset_name}.csv'
        aggregated.to_csv(output_file, index=False)
        print(f'  ✓ Saved: {output_file}')

    except Exception as e:
        print(f'  ✗ Error: {e}')

print('\n' + '='*80)
print('Done!')
print('='*80)
