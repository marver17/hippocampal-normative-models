#!/usr/bin/env python3
"""
Create a comprehensive CSV of all healthy control subjects aged ≥45 years
from all available datasets.

Inclusion criteria:
- Cognitively normal/healthy controls
- Age ≥ 45 years
- One timepoint per subject (baseline or first available)
"""

import pandas as pd
import numpy as np
from pathlib import Path

data_dir = Path('/home/mario/Repository/Normal_Alzeihmer/data')
output_file = data_dir / 'combined' / 'all_healthy_controls_age45plus.csv'

print('='*80)
print('Creating comprehensive list of healthy controls aged ≥45')
print('='*80)

all_subjects = []

# ============================================================================
# ADNI - Alzheimer's Disease Neuroimaging Initiative
# ============================================================================
print('\n1. ADNI:')
adni_file = data_dir / 'ADNI' / 'adni_healthy_controls_age45plus.csv'
if adni_file.exists():
    adni_df = pd.read_csv(adni_file)
    print(f'   Loaded: {len(adni_df)} subjects')
    # Standardize columns
    adni_std = pd.DataFrame({
        'subject_id': adni_df['subject_id'],
        'dataset': 'ADNI',
        'age': adni_df['age'],
        'sex': adni_df['sex'],
        'site': adni_df.get('site', np.nan),
        'field_strength': adni_df.get('field_strength', np.nan),
        'nifti_path': adni_df.get('nifti_path', np.nan),
        'visit_code': adni_df.get('visit_code', 'bl'),
        'exam_date': adni_df.get('exam_date', np.nan)
    })
    all_subjects.append(adni_std)
    print(f'   ✓ Added {len(adni_std)} ADNI subjects')
else:
    print(f'   ✗ File not found: {adni_file}')

# ============================================================================
# IXI - Information eXtraction from Images
# ============================================================================
print('\n2. IXI:')
ixi_file = data_dir / 'IXI' / 'ixi_healthy_controls_age45plus.csv'
if ixi_file.exists():
    ixi_df = pd.read_csv(ixi_file)
    print(f'   Loaded: {len(ixi_df)} subjects')
    ixi_std = pd.DataFrame({
        'subject_id': ixi_df['subject_id'],
        'dataset': 'IXI',
        'age': ixi_df['age'],
        'sex': ixi_df['sex'],
        'site': ixi_df.get('site', np.nan),
        'field_strength': ixi_df.get('field_strength', np.nan),
        'nifti_path': ixi_df.get('nifti_path', np.nan),
        'visit_code': ixi_df.get('visit_code', 'baseline'),
        'exam_date': ixi_df.get('exam_date', np.nan)
    })
    all_subjects.append(ixi_std)
    print(f'   ✓ Added {len(ixi_std)} IXI subjects')
else:
    print(f'   ✗ File not found: {ixi_file}')

# ============================================================================
# PPMI - Parkinson's Progression Markers Initiative
# ============================================================================
print('\n3. PPMI:')
ppmi_file = data_dir / 'PPMI' / 'ppmi_healthy_controls_age45plus.csv'
if ppmi_file.exists():
    ppmi_df = pd.read_csv(ppmi_file)
    print(f'   Loaded: {len(ppmi_df)} subjects')
    ppmi_std = pd.DataFrame({
        'subject_id': ppmi_df['subject_id'],
        'dataset': 'PPMI',
        'age': ppmi_df['age'],
        'sex': ppmi_df['sex'],
        'site': ppmi_df.get('site', np.nan),
        'field_strength': ppmi_df.get('field_strength', np.nan),
        'nifti_path': ppmi_df.get('nifti_path', np.nan),
        'visit_code': ppmi_df.get('visit_code', 'baseline'),
        'exam_date': ppmi_df.get('exam_date', np.nan)
    })
    all_subjects.append(ppmi_std)
    print(f'   ✓ Added {len(ppmi_std)} PPMI subjects')
else:
    print(f'   ✗ File not found: {ppmi_file}')

# ============================================================================
# OASIS-1 - Open Access Series of Imaging Studies
# ============================================================================
print('\n4. OASIS-1:')
oasis1_file = data_dir / 'OASIS' / 'OASIS1' / 'oasis1_healthy_controls_age45plus.csv'
if oasis1_file.exists():
    oasis1_df = pd.read_csv(oasis1_file)
    print(f'   Loaded: {len(oasis1_df)} subjects')
    oasis1_std = pd.DataFrame({
        'subject_id': oasis1_df['subject_id'],
        'dataset': 'OASIS1',
        'age': oasis1_df['age'],
        'sex': oasis1_df['sex'],
        'site': oasis1_df.get('site', 'Washington University'),
        'field_strength': oasis1_df.get('field_strength', '1.5T'),
        'nifti_path': oasis1_df.get('nifti_path', np.nan),
        'visit_code': oasis1_df.get('visit_code', 'baseline'),
        'exam_date': oasis1_df.get('exam_date', np.nan)
    })
    all_subjects.append(oasis1_std)
    print(f'   ✓ Added {len(oasis1_std)} OASIS-1 subjects')
else:
    print(f'   ✗ File not found: {oasis1_file}')

# ============================================================================
# OASIS-2 - Cross-sectional MRI Data in Young, Middle Aged, Nondemented and Demented Older Adults
# ============================================================================
print('\n5. OASIS-2:')
oasis2_file = data_dir / 'OASIS' / 'OASIS2' / 'oasis2_healthy_controls_age60plus.csv'
if oasis2_file.exists():
    oasis2_df = pd.read_csv(oasis2_file)
    # Filter for age >= 45
    oasis2_df = oasis2_df[oasis2_df['age'] >= 45]
    print(f'   Loaded: {len(oasis2_df)} subjects (age ≥45)')
    oasis2_std = pd.DataFrame({
        'subject_id': oasis2_df['subject_id'],
        'dataset': 'OASIS2',
        'age': oasis2_df['age'],
        'sex': oasis2_df['sex'],
        'site': oasis2_df.get('site', 'Washington University'),
        'field_strength': oasis2_df.get('field_strength', '1.5T'),
        'nifti_path': oasis2_df.get('nifti_path', np.nan),
        'visit_code': oasis2_df.get('visit_code', 'ses-01'),
        'exam_date': oasis2_df.get('exam_date', np.nan)
    })
    all_subjects.append(oasis2_std)
    print(f'   ✓ Added {len(oasis2_std)} OASIS-2 subjects')
else:
    print(f'   ✗ File not found: {oasis2_file}')

# ============================================================================
# OASIS-3 - Longitudinal Neuroimaging, Clinical, and Cognitive Dataset
# ============================================================================
print('\n6. OASIS-3:')
oasis3_file = data_dir / 'OASIS' / 'OASIS 3' / 'oasis3_healthy_controls_age45plus.csv'
if oasis3_file.exists():
    oasis3_df = pd.read_csv(oasis3_file)
    print(f'   Loaded: {len(oasis3_df)} subjects')
    oasis3_std = pd.DataFrame({
        'subject_id': oasis3_df['subject_id'],
        'dataset': 'OASIS3',
        'age': oasis3_df['age'],
        'sex': oasis3_df['sex'],
        'site': oasis3_df.get('site', 'Washington University'),
        'field_strength': oasis3_df.get('field_strength', '3T'),
        'nifti_path': oasis3_df.get('nifti_path', np.nan),
        'visit_code': oasis3_df.get('visit_code', 'ses-01'),
        'exam_date': oasis3_df.get('exam_date', np.nan)
    })
    all_subjects.append(oasis3_std)
    print(f'   ✓ Added {len(oasis3_std)} OASIS-3 subjects')
else:
    print(f'   ✗ File not found: {oasis3_file}')

# ============================================================================
# SRPBS - Southwest University Adult Lifespan Dataset
# ============================================================================
print('\n7. SRPBS:')
srpbs_file = data_dir / 'SRPBS' / 'srpbs_healthy_controls_age45plus.csv'
if srpbs_file.exists():
    srpbs_df = pd.read_csv(srpbs_file)
    print(f'   Loaded: {len(srpbs_df)} subjects')
    srpbs_std = pd.DataFrame({
        'subject_id': srpbs_df['subject_id'],
        'dataset': 'SRPBS',
        'age': srpbs_df['age'],
        'sex': srpbs_df['sex'],
        'site': srpbs_df.get('site', 'Southwest University'),
        'field_strength': srpbs_df.get('field_strength', '3T'),
        'nifti_path': srpbs_df.get('nifti_path', np.nan),
        'visit_code': srpbs_df.get('visit_code', 'baseline'),
        'exam_date': srpbs_df.get('exam_date', np.nan)
    })
    all_subjects.append(srpbs_std)
    print(f'   ✓ Added {len(srpbs_std)} SRPBS subjects')
else:
    print(f'   ✗ File not found: {srpbs_file}')

# ============================================================================
# Combine all datasets
# ============================================================================
print('\n' + '='*80)
print('Combining all datasets...')
print('='*80)

if len(all_subjects) == 0:
    print('✗ No subjects found!')
    exit(1)

combined_df = pd.concat(all_subjects, ignore_index=True)
print(f'\n✓ Total subjects: {len(combined_df)}')

# Summary statistics
print('\n' + '='*80)
print('SUMMARY')
print('='*80)

print('\nDataset distribution:')
print(combined_df['dataset'].value_counts().to_string())

print(f'\nAge statistics:')
print(f'  Mean: {combined_df["age"].mean():.1f} ± {combined_df["age"].std():.1f}')
print(f'  Range: {combined_df["age"].min():.1f} - {combined_df["age"].max():.1f}')

print(f'\nSex distribution:')
print(combined_df['sex'].value_counts().to_string())

# Save combined file
output_file.parent.mkdir(parents=True, exist_ok=True)
combined_df.to_csv(output_file, index=False)
print(f'\n✓ Saved: {output_file}')
print(f'✓ Shape: {combined_df.shape}')
print('='*80)
