#!/usr/bin/env python3
"""
Match healthy control subjects with their volume data.
Show which subjects have volumes and which are missing.
"""

import pandas as pd
import numpy as np
from pathlib import Path

data_dir = Path('/home/mario/Repository/Normal_Alzeihmer/data')
volumes_dir = data_dir / 'volumes'

print('='*80)
print('Matching Subjects with Volumes')
print('='*80)

# Load subjects
subjects_file = data_dir / 'combined' / 'all_healthy_controls_age45plus.csv'
subjects_df = pd.read_csv(subjects_file)
print(f'\n✓ Loaded {len(subjects_df)} healthy control subjects')

# Load volumes
volumes_files = {
    'ADNI': volumes_dir / 'adni.csv',
    'IXI': volumes_dir / 'ixi.csv',
    'OASIS2': volumes_dir / 'oasis2.csv',
    'OASIS3': volumes_dir / 'oasis3.csv',
    'PPMI': volumes_dir / 'ppmi.csv',
    'SRPBS': volumes_dir / 'srpb.csv'
}

print('\nLoading volumes...')
volumes_dfs = {}
for dataset, file_path in volumes_files.items():
    if file_path.exists():
        df = pd.read_csv(file_path)
        volumes_dfs[dataset] = df
        print(f'  ✓ {dataset}: {len(df)} subjects with volumes')
    else:
        print(f'  ✗ {dataset}: File not found')

# Match subjects with volumes
print('\n' + '='*80)
print('Matching by dataset...')
print('='*80)

matched_data = []
missing_by_dataset = {}

for dataset in subjects_df['dataset'].unique():
    dataset_subjects = subjects_df[subjects_df['dataset'] == dataset].copy()
    n_subjects = len(dataset_subjects)

    print(f'\n{dataset}:')
    print(f'  Subjects: {n_subjects}')

    if dataset not in volumes_dfs:
        print(f'  ✗ No volumes available')
        missing_by_dataset[dataset] = n_subjects
        continue

    vol_df = volumes_dfs[dataset].copy()

    # Normalize subject_id formats (remove BIDS "sub-" prefix if present)
    def normalize_subject_id(sid):
        sid = str(sid)
        if sid.startswith('sub-'):
            return sid[4:]  # Remove "sub-" prefix
        return sid

    dataset_subjects['subject_id_normalized'] = dataset_subjects['subject_id'].apply(normalize_subject_id)
    vol_df['subject_id_normalized'] = vol_df['subject_id'].apply(normalize_subject_id)

    # Merge on normalized IDs
    merged = dataset_subjects.merge(
        vol_df,
        left_on='subject_id_normalized',
        right_on='subject_id_normalized',
        how='left',
        suffixes=('', '_vol'),
        indicator=True
    )

    n_matched = (merged['_merge'] == 'both').sum()
    n_missing = (merged['_merge'] == 'left_only').sum()

    print(f'  ✓ Matched: {n_matched}/{n_subjects} ({n_matched/n_subjects*100:.1f}%)')
    if n_missing > 0:
        print(f'  ✗ Missing volumes: {n_missing}')
        missing_by_dataset[dataset] = n_missing

    # Keep only matched subjects
    matched = merged[merged['_merge'] == 'both'].copy()
    matched = matched.drop(columns=['_merge'])
    matched_data.append(matched)

# Combine all matched data
if len(matched_data) > 0:
    combined_df = pd.concat(matched_data, ignore_index=True)

    print('\n' + '='*80)
    print('COMBINED RESULTS')
    print('='*80)

    print(f'\nTotal subjects: {len(subjects_df)}')
    print(f'Matched with volumes: {len(combined_df)}')
    print(f'Missing volumes: {len(subjects_df) - len(combined_df)}')
    print(f'Match rate: {len(combined_df)/len(subjects_df)*100:.1f}%')

    print('\n Dataset distribution (with volumes):')
    print(combined_df['dataset'].value_counts().to_string())

    # Show available volume columns
    vol_cols = [col for col in combined_df.columns if col.startswith('vol_')]
    qc_cols = [col for col in combined_df.columns if col.startswith('qc_')]

    print(f'\nAvailable metrics:')
    print(f'  Volume columns: {len(vol_cols)}')
    print(f'  QC columns: {len(qc_cols)}')

    print(f'\nFirst 10 volume columns:')
    for col in vol_cols[:10]:
        print(f'    - {col}')

    print(f'\nQC columns:')
    for col in qc_cols:
        print(f'    - {col}')

    # Save matched data
    output_file = data_dir / 'combined' / 'subjects_with_volumes_age45plus.csv'
    combined_df.to_csv(output_file, index=False)
    print(f'\n✓ Saved matched data: {output_file}')
    print(f'✓ Shape: {combined_df.shape}')

    # Summary of missing volumes
    if missing_by_dataset:
        print('\n' + '='*80)
        print('MISSING VOLUMES SUMMARY')
        print('='*80)
        for dataset, count in missing_by_dataset.items():
            print(f'  {dataset}: {count} subjects')
else:
    print('\n✗ No matches found!')

print('\n' + '='*80)
