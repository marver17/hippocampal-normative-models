#!/bin/bash
docker run  -v /mnt/NAS-Progetti/BrainAtrophy/DATASET/RF/sub-183791/processed/MR/:/data \
            -v /mnt/NAS-Progetti/BrainAtrophy/DATASET/RF-Generated/fastsurfer_output/original:/output/ \
            -v /home/mario/Repository/Normal_Alzeihmer/gen-model-evaluation/license.txt:/fs_license/license.txt \
            --rm --user $(id -u):$(id -g) deepmi/fastsurfer:latest \
            --fs_license /fs_license/license.txt \
            --t1 /data/sub-183791mrNormalized.nii.gz \
            --sid subjectX --sd /output \
            --threads 8 \
            --seg_only 

