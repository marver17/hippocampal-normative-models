#!/usr/bin/env python3
"""
Combine volumes from all datasets with selected subjects.
Apply QC filters and select relevant volume columns.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Paths
data_dir = Path('/home/mario/Repository/Normal_Alzeihmer/data')
volumes_dir = data_dir / 'volumes'
output_file = data_dir / 'combined' / 'combined_volumes_with_subjects.csv'

print('='*80)
print('Combining Volumes with Selected Subjects')
print('='*80)

# Load volumes CSV files
print('\n1. Loading volumes CSV files...')
volumes_files = {
    'ADNI': volumes_dir / 'adni.csv',
    'IXI': volumes_dir / 'ixi.csv',
    'OASIS2': volumes_dir / 'oasis2.csv',
    'OASIS3': volumes_dir / 'oasis3.csv',
    'PPMI': volumes_dir / 'ppmi.csv',
    'SRPBS': volumes_dir / 'srpb.csv'
}

volumes_dfs = {}
for dataset, file_path in volumes_files.items():
    if file_path.exists():
        df = pd.read_csv(file_path)
        volumes_dfs[dataset] = df
        print(f'  ✓ {dataset}: {len(df)} subjects')
    else:
        print(f'  ✗ {dataset}: File not found - {file_path}')

# Load selected subjects
print('\n2. Loading selected subjects...')
selected_subjects_file = data_dir / 'combined' / 'combined_datasets_age50plus_with_oasis.csv'

if not selected_subjects_file.exists():
    print(f'  ✗ Selected subjects file not found: {selected_subjects_file}')
    print('  Available combined files:')
    for f in (data_dir / 'combined').glob('*.csv'):
        print(f'    - {f.name}')
    exit(1)

selected_df = pd.read_csv(selected_subjects_file)
print(f'  ✓ Loaded {len(selected_df)} selected subjects')
print(f'  Columns: {list(selected_df.columns)}')

# Check which column contains subject IDs
if 'subject_id' in selected_df.columns:
    subject_col = 'subject_id'
elif 'Subject' in selected_df.columns:
    subject_col = 'Subject'
else:
    print(f'  Available columns: {list(selected_df.columns)}')
    raise ValueError('Cannot find subject ID column')

print(f'  Using subject ID column: {subject_col}')

# Add dataset column if not present
if 'dataset' not in selected_df.columns:
    print('  Adding dataset column based on subject_id patterns...')
    # Infer dataset from subject_id patterns
    def infer_dataset(subject_id):
        subject_id = str(subject_id)
        if subject_id.startswith('sub-'):
            if 'OASIS' in subject_id or 'OAS' in subject_id:
                return 'OASIS3'
            elif 'IXI' in subject_id:
                return 'IXI'
            elif 'PPMI' in subject_id:
                return 'PPMI'
            elif 'SRPBS' in subject_id or 'SRPB' in subject_id:
                return 'SRPBS'
        elif '_S_' in subject_id:
            return 'ADNI'
        elif subject_id.startswith('OAS2_'):
            return 'OASIS2'
        elif subject_id.startswith('OAS1_'):
            return 'OASIS1'
        return 'UNKNOWN'

    selected_df['dataset'] = selected_df[subject_col].apply(infer_dataset)
    print(f'  Dataset distribution:')
    print(selected_df['dataset'].value_counts())

# Match subjects with volumes
print('\n3. Matching subjects with volumes...')
matched_data = []

for dataset, vol_df in volumes_dfs.items():
    # Get subjects from this dataset
    dataset_subjects = selected_df[selected_df['dataset'] == dataset].copy()

    if len(dataset_subjects) == 0:
        print(f'  {dataset}: No subjects selected')
        continue

    # Match on subject_id
    # Volumes CSV should have a subject identifier column
    vol_subject_cols = [col for col in vol_df.columns if 'subject' in col.lower()]

    if len(vol_subject_cols) == 0:
        print(f'  ✗ {dataset}: Cannot find subject column in volumes CSV')
        print(f'    Available columns: {list(vol_df.columns)[:10]}...')
        continue

    # Use first subject column found
    vol_subject_col = vol_subject_cols[0]
    print(f'  {dataset}: Using volume subject column: {vol_subject_col}')

    # Merge
    merged = dataset_subjects.merge(
        vol_df,
        left_on=subject_col,
        right_on=vol_subject_col,
        how='inner'
    )

    print(f'  {dataset}: Matched {len(merged)}/{len(dataset_subjects)} subjects')
    matched_data.append(merged)

if len(matched_data) == 0:
    print('\n✗ No subjects matched with volumes!')
    exit(1)

# Combine all datasets
print('\n4. Combining all datasets...')
combined_df = pd.concat(matched_data, ignore_index=True)
print(f'  ✓ Combined: {len(combined_df)} subjects')

# Apply QC filters
print('\n5. Applying QC filters...')
print('  QC columns available:')
qc_cols = [col for col in combined_df.columns if col.startswith('qc_')]
for col in qc_cols:
    if col in combined_df.columns:
        print(f'    - {col}: mean={combined_df[col].mean():.3f}, min={combined_df[col].min():.3f}')

# Define QC thresholds (adjust based on your needs)
qc_thresholds = {
    'qc_hippocampus+amygdala': 0.75,  # Example threshold
    'qc_general white matter': 0.75,
    'qc_general grey matter': 0.70,
}

# Apply filters
filtered_df = combined_df.copy()
n_before = len(filtered_df)

for qc_col, threshold in qc_thresholds.items():
    if qc_col in filtered_df.columns:
        n_filtered = len(filtered_df[filtered_df[qc_col] < threshold])
        filtered_df = filtered_df[filtered_df[qc_col] >= threshold]
        print(f'  {qc_col} >= {threshold}: removed {n_filtered} subjects')

n_after = len(filtered_df)
print(f'  ✓ QC filtering: {n_before} → {n_after} subjects ({n_before - n_after} removed)')

# Select relevant columns
print('\n6. Selecting relevant columns...')

# Demographic columns
demo_cols = ['subject_id', 'dataset', 'age', 'sex', 'site', 'field_strength']
demo_cols = [col for col in demo_cols if col in filtered_df.columns]

# Volume columns of interest (adjust based on your needs)
volume_cols_of_interest = [
    'vol_left hippocampus',
    'vol_right hippocampus',
    'vol_left cerebral white matter',
    'vol_right cerebral white matter',
    'vol_left cerebral cortex',
    'vol_right cerebral cortex',
    'vol_left thalamus',
    'vol_right thalamus',
    'vol_total intracranial',
    'vol_brain-stem'
]

# Filter to columns that exist
volume_cols = [col for col in volume_cols_of_interest if col in filtered_df.columns]
print(f'  Volume columns selected: {len(volume_cols)}')

# QC columns to keep
qc_cols_to_keep = [col for col in qc_cols if col in filtered_df.columns]
print(f'  QC columns kept: {len(qc_cols_to_keep)}')

# Select final columns
final_cols = demo_cols + volume_cols + qc_cols_to_keep
final_df = filtered_df[final_cols].copy()

# Calculate derived metrics
print('\n7. Calculating derived metrics...')
if 'vol_left hippocampus' in final_df.columns and 'vol_right hippocampus' in final_df.columns:
    final_df['vol_total_hippocampus'] = final_df['vol_left hippocampus'] + final_df['vol_right hippocampus']
    print('  ✓ Added vol_total_hippocampus')

if 'vol_total intracranial' in final_df.columns and 'vol_total_hippocampus' in final_df.columns:
    final_df['vol_hippocampus_normalized'] = (
        final_df['vol_total_hippocampus'] / final_df['vol_total intracranial']
    )
    print('  ✓ Added vol_hippocampus_normalized (normalized by TIV)')

# Save combined file
print('\n8. Saving combined volumes file...')
output_file.parent.mkdir(parents=True, exist_ok=True)
final_df.to_csv(output_file, index=False)
print(f'  ✓ Saved: {output_file}')
print(f'  ✓ Shape: {final_df.shape}')

# Summary statistics
print('\n' + '='*80)
print('SUMMARY')
print('='*80)
print(f'\nTotal subjects: {len(final_df)}')
print(f'\nDataset distribution:')
print(final_df['dataset'].value_counts())

if 'age' in final_df.columns:
    print(f'\nAge statistics:')
    print(f'  Mean: {final_df["age"].mean():.1f} ± {final_df["age"].std():.1f}')
    print(f'  Range: {final_df["age"].min():.1f} - {final_df["age"].max():.1f}')

if 'sex' in final_df.columns:
    print(f'\nSex distribution:')
    print(final_df['sex'].value_counts())

print(f'\nOutput file: {output_file}')
print('='*80)
