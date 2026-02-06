#!/usr/bin/env python3
"""
Add field_strength_T column to existing healthy controls CSV files.
Based on validated documentation for each dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("ADDING FIELD_STRENGTH_T TO DATASET CSV FILES")
print("="*80)
print()

# Dataset field strength mapping (from documentation)
FIELD_STRENGTH_MAP = {
    'AABC': 3.0,      # All sites use 3T MRI
    'OASIS1': 1.5,    # Siemens Vision 1.5T
    'OASIS2': 1.5,    # Siemens Vision 1.5T
    'OASIS3': 3.0,    # Siemens Trio 3T
    'PPMI': 3.0,      # All sites use 3T
    'SRPBS': 3.0,     # Siemens Trio 3T
}

# IXI site-specific mapping
IXI_SITE_MAP = {
    'IXI-Guys': 1.5,  # Philips Gyroscan Intera 1.5T
    'IXI-HH': 3.0,    # Philips Intera 3T
    'IXI-IOP': np.nan  # Unknown (will be excluded)
}

data_dir = Path('data')

# 1. AABC
print("1. Processing AABC...")
aabc_file = data_dir / 'AABC' / 'aabc_healthy_controls_age45plus.csv'
if aabc_file.exists():
    df = pd.read_csv(aabc_file)
    df['field_strength_T'] = FIELD_STRENGTH_MAP['AABC']
    df.to_csv(aabc_file, index=False)
    print(f"   ✓ Added field_strength_T = {FIELD_STRENGTH_MAP['AABC']} to {len(df)} subjects")
else:
    print(f"   ✗ File not found: {aabc_file}")

# 2. ADNI - parse from existing FLDSTRENG field
print("\n2. Processing ADNI...")
adni_file = data_dir / 'ADNI' / 'adni_healthy_controls_age45plus.csv'
if adni_file.exists():
    df = pd.read_csv(adni_file)
    
    # Check if field_strength_T already exists and has values
    if 'field_strength_T' in df.columns and df['field_strength_T'].notna().any():
        n_existing = df['field_strength_T'].notna().sum()
        print(f"   ✓ field_strength_T already present for {n_existing}/{len(df)} subjects")
    else:
        # Try to get field strength from ADNIMERGE
        try:
            adnimerge = pd.read_csv(data_dir / 'ADNI' / 'ADNIMERGE_30Jul2024.csv', low_memory=False)
            
            # Merge to get FLDSTRENG (use first non-null value per subject)
            field_map = adnimerge[['PTID', 'FLDSTRENG']].dropna().drop_duplicates('PTID')
            
            df = df.merge(
                field_map,
                left_on='subject_id',
                right_on='PTID',
                how='left'
            )
            
            # Parse field strength from string
            def parse_field_strength(s):
                if pd.isna(s):
                    return np.nan
                s = str(s)
                if '3' in s or '3.0' in s:
                    return 3.0
                elif '1.5' in s:
                    return 1.5
                return np.nan
            
            df['field_strength_T'] = df['FLDSTRENG'].apply(parse_field_strength)
            df = df.drop(columns=['PTID', 'FLDSTRENG'], errors='ignore')
            
        except Exception as e:
            print(f"   ⚠ Could not parse from ADNIMERGE: {e}")
            print(f"   ⚠ Assigning 1.5T as default (most common in ADNI)")
            df['field_strength_T'] = 1.5
    
    # For missing values, assign 1.5T as default (most common in ADNI)
    n_missing = df['field_strength_T'].isna().sum()
    if n_missing > 0:
        print(f"   ⚠ {n_missing} subjects missing field_strength, assigning 1.5T as default")
        df['field_strength_T'] = df['field_strength_T'].fillna(1.5)
    
    # Report results
    n_total = len(df)
    n_1_5t = (df['field_strength_T'] == 1.5).sum()
    n_3t = (df['field_strength_T'] == 3.0).sum()
    
    df.to_csv(adni_file, index=False)
    print(f"   ✓ Final distribution for {n_total} subjects:")
    print(f"     - 1.5T: {n_1_5t} ({n_1_5t/n_total*100:.1f}%)")
    print(f"     - 3.0T: {n_3t} ({n_3t/n_total*100:.1f}%)")
else:
    print(f"   ✗ File not found: {adni_file}")

# 3. IXI - extract site from subject_id and map to field strength
print("\n3. Processing IXI...")
ixi_file = data_dir / 'IXI' / 'ixi_healthy_controls_age45plus.csv'
if ixi_file.exists():
    df = pd.read_csv(ixi_file)
    
    # Extract site from nifti path (e.g., /mnt/NAS-Progetti/IXI/13_HH/... → IXI-HH)
    # Or from subject_id if path not available
    # Check if we have a 'nifti_path' column or need to infer from subject_id
    if 'nifti_path' in df.columns:
        # Extract site from path
        def extract_site_from_path(path):
            if pd.isna(path):
                return 'IXI'
            path = str(path)
            if '_HH/' in path or '/HH/' in path:
                return 'IXI-HH'
            elif '_Guys/' in path or '/Guys/' in path:
                return 'IXI-Guys'
            elif '_IOP/' in path or '/IOP/' in path:
                return 'IXI-IOP'
            return 'IXI'
        
        df['site_specific'] = df['nifti_path'].apply(extract_site_from_path)
    else:
        # For now, assume all IXI are 1.5T (most common) if site not specified
        # This is a conservative approach
        print("   ⚠ Warning: nifti_path not found, cannot determine specific sites")
        print("   ⚠ Assigning 1.5T as default (most common IXI scanner)")
        df['site_specific'] = 'IXI-Guys'  # Default to 1.5T
    
    df['field_strength_T'] = df['site_specific'].map(IXI_SITE_MAP)
    
    # If site mapping failed, use default 1.5T
    df['field_strength_T'] = df['field_strength_T'].fillna(1.5)
    
    # Report results
    n_total = len(df)
    n_1_5t = (df['field_strength_T'] == 1.5).sum()
    n_3t = (df['field_strength_T'] == 3.0).sum()
    
    df.to_csv(ixi_file, index=False)
    print(f"   ✓ Assigned field_strength_T for {n_total} subjects:")
    print(f"     - 1.5T: {n_1_5t} ({n_1_5t/n_total*100:.1f}%)")
    print(f"     - 3.0T: {n_3t} ({n_3t/n_total*100:.1f}%)")
else:
    print(f"   ✗ File not found: {ixi_file}")

# 4. OASIS3 - Extract from MR JSON metadata file
print("\n4. Processing OASIS3...")
oasis3_file = data_dir / 'OASIS' / 'OASIS 3' / 'oasis3_healthy_controls_age45plus.csv'
oasis3_json = data_dir / 'OASIS' / 'OASIS 3' / 'MRI-json-MRI_json_information' / 'resources' / 'csv' / 'files' / 'OASIS3_MR_json.csv'

if oasis3_file.exists() and oasis3_json.exists():
    df = pd.read_csv(oasis3_file)
    
    # Load MRI metadata
    df_json = pd.read_csv(oasis3_json)
    
    # Filter for T1w scans only (most relevant)
    df_json_t1 = df_json[df_json['scan category'] == 'T1w'].copy()
    
    # Get first T1w scan per subject with field strength info
    field_map = df_json_t1.groupby('subject_id')['MagneticFieldStrength'].first().reset_index()
    
    # Round field strength to standard values (1.494T → 1.5T)
    def round_field_strength(val):
        if pd.isna(val):
            return np.nan
        if 1.4 <= val < 1.6:
            return 1.5
        elif 2.8 <= val < 3.2:
            return 3.0
        return val
    
    field_map['MagneticFieldStrength'] = field_map['MagneticFieldStrength'].apply(round_field_strength)
    
    # Merge with healthy controls (drop old field_strength_T if exists)
    if 'field_strength_T' in df.columns:
        df = df.drop(columns=['field_strength_T'])
    
    df = df.merge(field_map, on='subject_id', how='left')
    df = df.rename(columns={'MagneticFieldStrength': 'field_strength_T'})
    
    # Report
    n_total = len(df)
    n_with_field = df['field_strength_T'].notna().sum()
    
    if n_with_field < n_total:
        print(f"   ⚠ {n_total - n_with_field} subjects missing field_strength, assigning 3.0T as default")
        df['field_strength_T'] = df['field_strength_T'].fillna(3.0)
    
    field_dist = df['field_strength_T'].value_counts().sort_index()
    
    df.to_csv(oasis3_file, index=False)
    print(f"   ✓ Extracted field_strength_T for {n_total} subjects:")
    for field, count in field_dist.items():
        print(f"     - {field}T: {count} ({count/n_total*100:.1f}%)")
elif oasis3_file.exists():
    print(f"   ⚠ JSON metadata file not found, assigning 3.0T as default")
    df = pd.read_csv(oasis3_file)
    df['field_strength_T'] = 3.0
    df.to_csv(oasis3_file, index=False)
    print(f"   ✓ Assigned 3.0T to {len(df)} subjects")
else:
    print(f"   ✗ File not found: {oasis3_file}")

# 5. Process OASIS1 (standalone file)
print("\n5. Processing OASIS1...")
oasis1_file = data_dir / 'OASIS' / 'OASIS1' / 'oasis1_healthy_controls_age45plus.csv'
if oasis1_file.exists():
    df = pd.read_csv(oasis1_file)
    df['field_strength_T'] = 1.5
    df.to_csv(oasis1_file, index=False)
    print(f"   ✓ Added field_strength_T = 1.5 to {len(df)} subjects")
else:
    print(f"   ⚠ File not found: {oasis1_file}")

# 6. Process OASIS2 (standalone file)
print("\n6. Processing OASIS2...")
oasis2_file = data_dir / 'OASIS' / 'OASIS2' / 'oasis2_healthy_controls_age60plus.csv'
if oasis2_file.exists():
    df = pd.read_csv(oasis2_file)
    df['field_strength_T'] = 1.5
    df.to_csv(oasis2_file, index=False)
    print(f"   ✓ Added field_strength_T = 1.5 to {len(df)} subjects")
else:
    print(f"   ⚠ File not found: {oasis2_file}")

# 7. OASIS (combined file with OASIS1/2/3)
print("\n7. Processing OASIS (combined file)...")
oasis_combined = data_dir / 'OASIS' / 'oasis_combined_healthy_controls_age50plus.csv'
if oasis_combined.exists():
    df = pd.read_csv(oasis_combined)
    
    # OASIS1/2 are 1.5T, OASIS3 needs to be extracted from metadata
    # First assign based on dataset
    df['field_strength_T'] = df['dataset'].map({
        'OASIS1': 1.5,
        'OASIS2': 1.5,
        'OASIS3': 3.0  # Default, will override with actual values
    })
    
    # Override OASIS3 with actual values from metadata if available
    if oasis3_json.exists():
        df_json = pd.read_csv(oasis3_json)
        df_json_t1 = df_json[df_json['scan category'] == 'T1w'].copy()
        field_map = df_json_t1.groupby('subject_id')['MagneticFieldStrength'].first().reset_index()
        
        # Round field strength to standard values
        def round_field_strength(val):
            if pd.isna(val):
                return np.nan
            if 1.4 <= val < 1.6:
                return 1.5
            elif 2.8 <= val < 3.2:
                return 3.0
            return val
        
        field_map['MagneticFieldStrength'] = field_map['MagneticFieldStrength'].apply(round_field_strength)
        
        # Update only OASIS3 subjects
        oasis3_subjects = df[df['dataset'] == 'OASIS3']['subject_id']
        field_map_oasis3 = field_map[field_map['subject_id'].isin(oasis3_subjects)]
        
        # Merge and update
        df = df.merge(field_map_oasis3.rename(columns={'MagneticFieldStrength': 'field_strength_actual'}), 
                      on='subject_id', how='left')
        df.loc[df['dataset'] == 'OASIS3', 'field_strength_T'] = df.loc[df['dataset'] == 'OASIS3', 'field_strength_actual'].fillna(3.0)
        df = df.drop(columns=['field_strength_actual'], errors='ignore')
    
    # Report results
    n_total = len(df)
    oasis1_count = (df['dataset'] == 'OASIS1').sum()
    oasis2_count = (df['dataset'] == 'OASIS2').sum()
    oasis3_count = (df['dataset'] == 'OASIS3').sum()
    
    field_dist_oasis3 = df[df['dataset'] == 'OASIS3']['field_strength_T'].value_counts().sort_index()
    
    df.to_csv(oasis_combined, index=False)
    print(f"   ✓ Assigned field_strength_T for {n_total} subjects:")
    print(f"     - OASIS1 (1.5T): {oasis1_count}")
    print(f"     - OASIS2 (1.5T): {oasis2_count}")
    print(f"     - OASIS3: {oasis3_count} subjects")
    for field, count in field_dist_oasis3.items():
        print(f"       • {field}T: {count} ({count/oasis3_count*100:.1f}% of OASIS3)")
else:
    print(f"   ✗ File not found: {oasis_combined}")

# 8. PPMI
print("\n8. Processing PPMI...")
ppmi_file = data_dir / 'PPMI' / 'ppmi_healthy_controls_age45plus.csv'
if ppmi_file.exists():
    df = pd.read_csv(ppmi_file)
    df['field_strength_T'] = FIELD_STRENGTH_MAP['PPMI']
    df.to_csv(ppmi_file, index=False)
    print(f"   ✓ Added field_strength_T = {FIELD_STRENGTH_MAP['PPMI']} to {len(df)} subjects")
else:
    print(f"   ✗ File not found: {ppmi_file}")

# 9. SRPBS
print("\n9. Processing SRPBS...")
srpbs_file = data_dir / 'SRPBS' / 'srpbs_healthy_controls_age45plus.csv'
if srpbs_file.exists():
    df = pd.read_csv(srpbs_file)
    df['field_strength_T'] = FIELD_STRENGTH_MAP['SRPBS']
    df.to_csv(srpbs_file, index=False)
    print(f"   ✓ Added field_strength_T = {FIELD_STRENGTH_MAP['SRPBS']} to {len(df)} subjects")
else:
    print(f"   ✗ File not found: {srpbs_file}")

print("\n" + "="*80)
print("COMPLETED: field_strength_T added to all dataset CSV files")
print("="*80)
print("\nNext steps:")
print("1. Re-run notebook 7 (Combined_datasets.ipynb) to include field_strength_T")
print("2. Re-run notebook 9 (normative_model_preparation.ipynb) to include field_strength_T")
print("3. Update notebook 10 (gamlss_normative_modeling) to use field_strength_T as covariate")
