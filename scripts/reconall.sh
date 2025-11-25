#!/bin/bash
set -e # Interrompe lo script immediatamente se un comando fallisce

if [ "$#" -ne 4 ]; then
    echo "ERRORE: Numero di argomenti non corretto."
    echo "Uso: $0 <subject_id> <percorso_immagine_input> <cartella_output> <numero_thread>"
    echo "Esempio: $0 sub-01 /data/input/sub-01_brain.nii.gz /data/output 4"
    exit 1
fi

if [ -z "$SUBJECTS_DIR" ] || [ -z "$FREESURFER_HOME" ]; then
    echo "ERRORE: Le variabili SUBJECTS_DIR e/o FREESURFER_HOME non sono impostate."
    echo "Assicurati di aver caricato la configurazione di FreeSurfer prima di lanciare questo script."
    exit 1
fi


SUBJECT_ID=$1
INPUT_IMAGE=$2
OUTPUT_DIR=$3
OMP_NUM_THREADS=$4
### copiare il file in modo che freesurfer lo possa leggere
WORK_DIR=${SUBJECTS_DIR}/${SUBJECT_ID}
mkdir -p ${WORK_DIR}/mri/orig
mri_convert ${INPUT_IMAGE} ${WORK_DIR}/mri/orig/001.mgz
### eseguire recon-all
recon-all -s ${SUBJECT_ID} -all -openmp $OMP_NUM_THREADS -parallel
### copiare i risultati nella cartella di output
mkdir -p ${OUTPUT_DIR}
cp -r ${WORK_DIR} ${OUTPUT_DIR}/
echo "Elaborazione completata per il soggetto: ${SUBJECT_ID}"
