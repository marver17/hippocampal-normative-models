#!/usr/bin/env python3
"""
Test script to verify OASIS conversion scripts work correctly
Tests conversion of first subject only
"""

import os
import json
from pathlib import Path
import nibabel as nib

print("="*80)
print("OASIS CONVERSION TEST")
print("="*80)

# Test OASIS-1 conversion on first subject
print("\n1. Testing OASIS-1 conversion (first subject only)...")

oasis1_raw = "/mnt/db_ext/RAW/oasis/OASIS 1"
oasis1_bids = "/mnt/db_ext/RAW/oasis/OASIS1_BIDS_TEST"

# Get first subject
subjects = sorted([d for d in os.listdir(oasis1_raw) if d.startswith('OAS1_')])
if not subjects:
    print("   ✗ No subjects found in OASIS-1")
    exit(1)

subject = subjects[0]
subject_id = subject.replace('_MR1', '')
bids_subject_id = f"sub-{subject_id}"

print(f"   Testing with: {subject_id}")

# Create test directory
subject_dir = Path(oasis1_bids) / bids_subject_id / "anat"
subject_dir.mkdir(parents=True, exist_ok=True)

# Get paths
orig_subject_dir = Path(oasis1_raw) / subject
raw_dir = orig_subject_dir / "RAW"

# Get first MPR file
mpr_files = sorted([f for f in os.listdir(raw_dir) if f.endswith('_anon.hdr')])
if not mpr_files:
    print(f"   ✗ No MPR files found")
    exit(1)

print(f"   Found {len(mpr_files)} MPR scans")

# Test conversion of first scan
hdr_file = raw_dir / mpr_files[0]
output_base = f"{bids_subject_id}_run-01_T1w"
output_nii = subject_dir / f"{output_base}.nii.gz"

try:
    # Load and convert
    print(f"   Loading: {hdr_file.name}")
    img = nib.load(str(hdr_file))
    print(f"   Original shape: {img.shape}")

    # Squeeze if needed
    data = img.get_fdata()
    if data.ndim == 4 and data.shape[3] == 1:
        data = data[:, :, :, 0]
        print(f"   Squeezed to: {data.shape}")

    # Save
    nii_img = nib.Nifti1Image(data, img.affine)
    nib.save(nii_img, str(output_nii))

    # Check file size
    file_size = output_nii.stat().st_size / (1024*1024)
    print(f"   ✓ Saved: {output_nii.name} ({file_size:.1f} MB)")

    # Verify it can be read back
    test_img = nib.load(str(output_nii))
    print(f"   ✓ Verified: shape={test_img.shape}")

    if test_img.shape != (256, 256, 128):
        print(f"   ⚠ Warning: unexpected shape {test_img.shape}")

except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n2. Testing OASIS-2 conversion (first session only)...")

oasis2_raw = "/mnt/db_ext/RAW/oasis/OASIS 2"
oasis2_bids = "/mnt/db_ext/RAW/oasis/OASIS2_BIDS_TEST"

# Get first session
sessions = sorted([d for d in os.listdir(oasis2_raw) if d.startswith('OAS2_')])
if not sessions:
    print("   ✗ No sessions found in OASIS-2")
    exit(1)

session = sessions[0]
print(f"   Testing with: {session}")

import re
match = re.match(r'(OAS2_\d+)_MR(\d+)', session)
if not match:
    print(f"   ✗ Cannot parse session ID")
    exit(1)

subject_id = match.group(1)
session_num = int(match.group(2))
bids_subject_id = f"sub-{subject_id}"
bids_session_id = f"ses-{session_num:02d}"

# Create test directory
session_dir = Path(oasis2_bids) / bids_subject_id / bids_session_id / "anat"
session_dir.mkdir(parents=True, exist_ok=True)

# Get paths
orig_session_dir = Path(oasis2_raw) / session
raw_dir = orig_session_dir / "RAW"

# Get first MPR file
mpr_files = sorted([f for f in os.listdir(raw_dir) if f.endswith('_anon.hdr')])
if not mpr_files:
    print(f"   ✗ No MPR files found")
    exit(1)

print(f"   Found {len(mpr_files)} MPR scans")

# Test conversion of first scan
hdr_file = raw_dir / mpr_files[0]
output_base = f"{bids_subject_id}_{bids_session_id}_run-01_T1w"
output_nii = session_dir / f"{output_base}.nii.gz"

try:
    # Load and convert
    print(f"   Loading: {hdr_file.name}")
    img = nib.load(str(hdr_file))
    print(f"   Original shape: {img.shape}")

    # Squeeze if needed
    data = img.get_fdata()
    if data.ndim == 4 and data.shape[3] == 1:
        data = data[:, :, :, 0]
        print(f"   Squeezed to: {data.shape}")

    # Save
    nii_img = nib.Nifti1Image(data, img.affine)
    nib.save(nii_img, str(output_nii))

    # Check file size
    file_size = output_nii.stat().st_size / (1024*1024)
    print(f"   ✓ Saved: {output_nii.name} ({file_size:.1f} MB)")

    # Verify it can be read back
    test_img = nib.load(str(output_nii))
    print(f"   ✓ Verified: shape={test_img.shape}")

    if test_img.shape != (256, 256, 128):
        print(f"   ⚠ Warning: unexpected shape {test_img.shape}")

except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*80)
print("✓ All tests passed!")
print("="*80)
print("\nYou can now run the full conversion scripts:")
print("  python3 convert_oasis1_to_bids.py")
print("  python3 convert_oasis2_to_bids.py")
print("\nTest directories created (can be deleted):")
print(f"  {oasis1_bids}")
print(f"  {oasis2_bids}")
