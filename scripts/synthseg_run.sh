#!/bin/bash
# filepath: /home/mario/Repository/Normal_Alzeihmer/synthseg_run.sh
set -e # Interrompe lo script immediatamente se un comando fallisce

if [ "$#" -ne 4 ]; then
    echo "ERRORE: Numero di argomenti non corretto."
    echo "Uso: $0 <subject_id> <percorso_immagine_input> <cartella_output> <numero_thread>"
    echo "Esempio: $0 sub-01 /data/input/sub-01_brain.nii.gz /data/output 4"
    exit 1
fi

# Verifica che SynthSeg sia disponibile
if ! command -v mri_synthseg &> /dev/null; then
    echo "ERRORE: mri_synthseg non trovato. Assicurati che FreeSurfer sia configurato correttamente."
    exit 1
fi

SUBJECT_ID=$1
INPUT_IMAGE=$2
OUTPUT_DIR=$3
NUM_THREADS=$4

# Verifica che il file di input esista
if [ ! -f "$INPUT_IMAGE" ]; then
    echo "ERRORE: Il file di input non esiste: $INPUT_IMAGE"
    exit 1
fi

# Crea la directory di output se non esiste
mkdir -p ${OUTPUT_DIR}/${SUBJECT_ID}

# Definisci i percorsi di output
SEGMENTATION_OUTPUT="${OUTPUT_DIR}/${SUBJECT_ID}/segmentation.nii.gz"
VOLUMES_OUTPUT="${OUTPUT_DIR}/${SUBJECT_ID}/volumes.csv"
QC_OUTPUT="${OUTPUT_DIR}/${SUBJECT_ID}/qc_scores.csv"
POSTERIORS_OUTPUT="${OUTPUT_DIR}/${SUBJECT_ID}/posteriors"
RESAMPLED_OUTPUT="${OUTPUT_DIR}/${SUBJECT_ID}/resampled.nii.gz"

echo "Inizio elaborazione SynthSeg per il soggetto: ${SUBJECT_ID}"
echo "Input: ${INPUT_IMAGE}"
echo "Output dir: ${OUTPUT_DIR}/${SUBJECT_ID}"
echo "Threads: ${NUM_THREADS}"

# Crea directory per posteriors
mkdir -p ${POSTERIORS_OUTPUT}

# Esegui SynthSeg con parametri ottimizzati per ADNI
mri_synthseg \
    --i ${INPUT_IMAGE} \
    --o ${SEGMENTATION_OUTPUT} \
    --parc \
    --robust \
    --vol ${VOLUMES_OUTPUT} \
    --qc ${QC_OUTPUT} \
    --post ${POSTERIORS_OUTPUT} \
    --resample ${RESAMPLED_OUTPUT} \
    --threads ${NUM_THREADS} \
    --cpu \
    --addctab

# Verifica che l'output sia stato creato
if [ ! -f "$SEGMENTATION_OUTPUT" ]; then
    echo "ERRORE: La segmentazione non è stata generata"
    exit 1
fi

echo "Segmentazione salvata in: ${SEGMENTATION_OUTPUT}"
echo "Volumi salvati in: ${VOLUMES_OUTPUT}"
echo "QC scores salvati in: ${QC_OUTPUT}"
echo "Posteriors salvati in: ${POSTERIORS_OUTPUT}"
echo "Immagine ricampionata salvata in: ${RESAMPLED_OUTPUT}"
echo "Elaborazione completata per il soggetto: ${SUBJECT_ID}"

