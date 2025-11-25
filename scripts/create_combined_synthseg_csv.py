#!/usr/bin/env python3
"""
Create combined synthseg processing CSV for OASIS + SRPBS
Following the same logic used for OASIS datasets
"""

from pathlib import Path
import pandas as pd

print('='*80)
print('CREATING COMBINED SYNTHSEG PROCESSING CSV (OASIS + SRPBS)')
print('='*80)

processing_list = []

# ============================================================================
# OASIS-1: Cross-sectional (1 sessione per soggetto, prendi primo run)
# ============================================================================
print('\n### OASIS-1 ###')
oasis1_bids = Path('/mnt/db_ext/RAW/oasis/OASIS1_BIDS')
subjects_o1 = sorted([d for d in oasis1_bids.iterdir() if d.is_dir() and d.name.startswith('sub-')])

for subject_dir in subjects_o1:
    anat_dir = subject_dir / 'anat'
    if not anat_dir.exists():
        continue

    # Trova tutti i T1w, prendi il primo run
    t1w_files = sorted(anat_dir.glob('*_T1w.nii.gz'))
    if t1w_files:
        first_t1w = t1w_files[0]
        processing_list.append({
            'subject_id': subject_dir.name,
            'input_image': str(first_t1w.absolute()),
            'output_dir': str(oasis1_bids / 'derivatives' / 'synthseg'),
            'num_threads': 4,
            'dataset': 'OASIS1'
        })

print(f'Soggetti OASIS-1: {len([x for x in processing_list if x["dataset"]=="OASIS1"])}')

# ============================================================================
# OASIS-2: Longitudinal (prendi baseline/ses-01, primo run)
# ============================================================================
print('\n### OASIS-2 ###')
oasis2_bids = Path('/mnt/db_ext/RAW/oasis/OASIS2_BIDS')
subjects_o2 = sorted([d for d in oasis2_bids.iterdir() if d.is_dir() and d.name.startswith('sub-')])

for subject_dir in subjects_o2:
    # Trova tutte le sessioni, ordina e prendi la prima (ses-01)
    sessions = sorted([d for d in subject_dir.iterdir() if d.is_dir() and d.name.startswith('ses-')])
    if not sessions:
        continue

    first_session = sessions[0]  # Prima sessione
    anat_dir = first_session / 'anat'

    if not anat_dir.exists():
        continue

    # Prendi il primo run
    t1w_files = sorted(anat_dir.glob('*_T1w.nii.gz'))
    if t1w_files:
        first_t1w = t1w_files[0]
        processing_list.append({
            'subject_id': subject_dir.name,
            'input_image': str(first_t1w.absolute()),
            'output_dir': str(oasis2_bids / 'derivatives' / 'synthseg'),
            'num_threads': 4,
            'dataset': 'OASIS2'
        })

print(f'Soggetti OASIS-2 (baseline): {len([x for x in processing_list if x["dataset"]=="OASIS2"])}')

# ============================================================================
# OASIS-3: Longitudinal (prendi prima sessione, primo run)
# ============================================================================
print('\n### OASIS-3 ###')
oasis3_bids = Path('/mnt/db_ext/RAW/oasis/OASIS3_BIDS')
subjects_o3 = sorted([d for d in oasis3_bids.iterdir() if d.is_dir() and d.name.startswith('sub-')])

for subject_dir in subjects_o3:
    # Trova tutte le sessioni, ordina e prendi la prima
    sessions = sorted([d for d in subject_dir.iterdir() if d.is_dir() and d.name.startswith('ses-')])
    if not sessions:
        continue

    first_session = sessions[0]  # Prima sessione
    anat_dir = first_session / 'anat'

    if not anat_dir.exists():
        continue

    # Prendi il primo run
    t1w_files = sorted(anat_dir.glob('*_T1w.nii.gz'))
    if t1w_files:
        first_t1w = t1w_files[0]
        processing_list.append({
            'subject_id': subject_dir.name,
            'input_image': str(first_t1w.absolute()),
            'output_dir': str(oasis3_bids / 'derivatives' / 'synthseg'),
            'num_threads': 4,
            'dataset': 'OASIS3'
        })

print(f'Soggetti OASIS-3 (baseline): {len([x for x in processing_list if x["dataset"]=="OASIS3"])}')

# ============================================================================
# SRPBS: Cross-sectional (1 sessione per soggetto, no multiple run)
# ============================================================================
print('\n### SRPBS ###')
srpbs_bids = Path('/mnt/db_ext/RAW/SRPBS_OPEN/SRPBS_BIDS')
subjects_srpbs = sorted([d for d in srpbs_bids.iterdir() if d.is_dir() and d.name.startswith('sub-')])

for subject_dir in subjects_srpbs:
    anat_dir = subject_dir / 'anat'
    if not anat_dir.exists():
        continue

    # SRPBS ha un solo T1w per soggetto
    t1w_file = anat_dir / f"{subject_dir.name}_T1w.nii.gz"

    if t1w_file.exists():
        processing_list.append({
            'subject_id': subject_dir.name,
            'input_image': str(t1w_file.absolute()),
            'output_dir': str(srpbs_bids / 'derivatives' / 'synthseg'),
            'num_threads': 4,
            'dataset': 'SRPBS'
        })

print(f'Soggetti SRPBS: {len([x for x in processing_list if x["dataset"]=="SRPBS"])}')

# ============================================================================
# Create DataFrame and Save
# ============================================================================
df = pd.DataFrame(processing_list)

# Rimuovi colonna dataset (era solo per debug)
df_final = df[['subject_id', 'input_image', 'output_dir', 'num_threads']]

# Salva
output_file = '/mnt/db_ext/RAW/combined_oasis_srpbs_synthseg_processing.csv'
df_final.to_csv(output_file, index=False)

print('\n' + '='*80)
print('RIEPILOGO')
print('='*80)
print(f'\nFile creato: {output_file}')
print(f'\nTotale soggetti: {len(df_final)}')
print(f'  OASIS-1: {(df["dataset"]=="OASIS1").sum()}')
print(f'  OASIS-2: {(df["dataset"]=="OASIS2").sum()}')
print(f'  OASIS-3: {(df["dataset"]=="OASIS3").sum()}')
print(f'  SRPBS:   {(df["dataset"]=="SRPBS").sum()}')

print(f'\nPrime 5 righe (OASIS-1):')
print(df_final.head(5).to_string(index=False))

print(f'\nUltime 5 righe (SRPBS):')
print(df_final.tail(5).to_string(index=False))

# Verifica che tutte le immagini esistano
print(f'\nVerifica esistenza file...')
missing = 0
for _, row in df_final.iterrows():
    if not Path(row['input_image']).exists():
        missing += 1

if missing == 0:
    print(f'✓ Tutti i {len(df_final)} file input esistono')
else:
    print(f'⚠ {missing} file input mancanti')

# Create derivatives directories if they don't exist
print(f'\nCreazione directory derivatives...')
for output_dir in df['output_dir'].unique():
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f'  ✓ {output_path}')

# Create dataset_description.json for SRPBS derivatives
import json

srpbs_derivatives = srpbs_bids / 'derivatives' / 'synthseg'
desc_file = srpbs_derivatives / 'dataset_description.json'

if not desc_file.exists():
    dataset_desc = {
        "Name": "SynthSeg Segmentation",
        "BIDSVersion": "1.6.0",
        "DatasetType": "derivative",
        "GeneratedBy": [
            {
                "Name": "SynthSeg",
                "Version": "2.0",
                "Description": "Robust Segmentation of brain MRI in the wild",
                "CodeURL": "https://github.com/BBillot/SynthSeg"
            }
        ],
        "HowToAcknowledge": "Please cite: Billot et al., SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining. Medical Image Analysis (2023)",
        "SourceDatasets": [
            {
                "DatasetName": "SRPBS"
            }
        ]
    }

    with open(desc_file, 'w') as f:
        json.dump(dataset_desc, f, indent=4)
    print(f'\n✓ Created: {desc_file}')

print('\n' + '='*80)
print('✓ COMBINED CSV CREATED SUCCESSFULLY!')
print('='*80)
print(f'\nTotal: {len(df_final)} subjects ready for SynthSeg segmentation')
print(f'\nDataset breakdown:')
print(f'  OASIS (1+2+3): {(df["dataset"].str.startswith("OASIS")).sum()} subjects')
print(f'  SRPBS:         {(df["dataset"]=="SRPBS").sum()} subjects')
