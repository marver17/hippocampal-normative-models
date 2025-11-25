#!/usr/bin/env python3
"""
Create participants.tsv for OASIS-3 BIDS dataset
Integrates demographic and clinical data
"""

import pandas as pd
import os
from pathlib import Path

# Paths
oasis3_data = "/mnt/db_ext/RAW/oasis/OASIS 3/OASIS3_data_files"
oasis3_bids = "/mnt/db_ext/RAW/oasis/OASIS3_BIDS"

print("="*80)
print("Creating OASIS-3 participants.tsv")
print("="*80)

# Load demographics
demographics_file = f"{oasis3_data}/demo-demographics/resources/csv/files/OASIS3_demographics.csv"
demographics = pd.read_csv(demographics_file)

print(f"\nLoaded demographics: {len(demographics)} records")
print(f"Columns: {list(demographics.columns)}")

# Get list of subjects in BIDS dataset
bids_subjects = sorted([d.name for d in Path(oasis3_bids).iterdir()
                       if d.is_dir() and d.name.startswith('sub-')])

print(f"\nBIDS subjects found: {len(bids_subjects)}")

# Map subject IDs (sub-OAS3XXXX -> OAS3XXXX)
bids_subject_ids = [s.replace('sub-', '') for s in bids_subjects]

# Filter demographics for subjects in BIDS
demo_filtered = demographics[demographics['OASISID'].isin(bids_subject_ids)]

print(f"Matched demographics: {len(demo_filtered)} subjects")

# Get one record per subject (use first record)
demo_unique = demo_filtered.groupby('OASISID').first().reset_index()

print(f"Unique subjects: {len(demo_unique)}")

# Create participants dataframe
participants = pd.DataFrame({
    'participant_id': ['sub-' + s for s in demo_unique['OASISID']],
    'age_at_entry': demo_unique['AgeatEntry'],
    'age_at_death': demo_unique['AgeatDeath'].fillna('n/a'),
    'sex': demo_unique['GENDER'].map({1: 'M', 2: 'F'}),
    'hand': demo_unique['HAND'].fillna('n/a'),
    'race': demo_unique['race'].fillna('n/a'),
    'ethnicity': demo_unique['ETHNIC'].fillna('n/a'),
    'education_years': demo_unique['EDUC'].fillna('n/a'),
    'apoe': demo_unique['APOE'].fillna('n/a')
})

# Load CDR (Clinical Dementia Rating) data
try:
    cdr_file = f"{oasis3_data}/UDSb4-Form_B4__Global_Staging__CDR__Standard_and_Supplemental/resources/csv/files/OASIS3_UDSb4_cdr.csv"
    cdr = pd.read_csv(cdr_file)

    # Get baseline CDR for each subject
    # CDR file uses 'Subject' column
    cdr_baseline = cdr.groupby('Subject').first().reset_index()
    cdr_dict = dict(zip(['sub-' + s for s in cdr_baseline['Subject']],
                       cdr_baseline['cdr_global']))

    participants['cdr'] = participants['participant_id'].map(cdr_dict).fillna('n/a')
    print(f"\nAdded CDR data: {cdr['Subject'].nunique()} subjects")
except Exception as e:
    print(f"\nWarning: Could not load CDR data: {e}")
    participants['cdr'] = 'n/a'

# Sort by participant_id
participants = participants.sort_values('participant_id').reset_index(drop=True)

# Save participants.tsv
output_file = f"{oasis3_bids}/participants.tsv"
participants.to_csv(output_file, sep='\t', index=False)

print(f"\n✓ Saved participants.tsv: {len(participants)} subjects")
print(f"  File: {output_file}")

# Display summary statistics
print("\n" + "="*80)
print("PARTICIPANTS SUMMARY")
print("="*80)
print(f"\nTotal subjects: {len(participants)}")
print(f"\nAge at entry statistics:")
age_data = pd.to_numeric(participants['age_at_entry'], errors='coerce')
print(f"  Range: {age_data.min():.0f} - {age_data.max():.0f} years")
print(f"  Mean: {age_data.mean():.1f} ± {age_data.std():.1f}")
print(f"  Median: {age_data.median():.0f}")

print(f"\nSex distribution:")
for sex in ['M', 'F']:
    count = (participants['sex'] == sex).sum()
    print(f"  {sex}: {count} ({count/len(participants)*100:.1f}%)")

print(f"\nCDR distribution (Clinical Dementia Rating):")
cdr_counts = participants['cdr'].value_counts().sort_index()
for cdr, count in cdr_counts.items():
    if cdr != 'n/a':
        print(f"  CDR {cdr}: {count} ({count/len(participants)*100:.1f}%)")

print(f"\nFirst 10 rows:")
print(participants.head(10).to_string())
