#!/bin/bash
# filepath: /home/mario/Repository/Normal_Alzeihmer/scripts/fastsurfer_run.sh
set -e

if [ "$#" -ne 4 ]; then
    echo "ERRORE: Numero di argomenti non corretto."
    echo "Uso: $0 <subject_id> <percorso_immagine_input> <cartella_output_base> <numero_thread>"
    echo "Esempio: $0 sub-01 /data/input/sub-01_T1w.nii.gz /data/output 8"
    exit 1
fi

# Verifica che FastSurfer sia disponibile
if ! command -v run_fastsurfer.sh &> /dev/null; then
    echo "ERRORE: run_fastsurfer.sh non trovato. Assicurati di usare l'immagine deepmi/fastsurfer."
    exit 1
fi

SUBJECT_ID=$1
INPUT_IMAGE=$2
OUTPUT_BASE=$3
NUM_THREADS=$4

# Percorso licenza (override con FS_LICENSE se serve)
FS_LICENSE_PATH=${FS_LICENSE:-/mnt/NAS-Progetti/BrainAtrophy/code/license.txt}

if [ ! -f "$FS_LICENSE_PATH" ]; then
    echo "ERRORE: license.txt non trovato: $FS_LICENSE_PATH"
    exit 1
fi

# Verifica che il file di input esista
if [ ! -f "$INPUT_IMAGE" ]; then
    echo "ERRORE: Il file di input non esiste: $INPUT_IMAGE"
    exit 1
fi

# Crea la directory di output base se non esiste
mkdir -p "$OUTPUT_BASE"

echo "Inizio elaborazione FastSurfer per il soggetto: ${SUBJECT_ID}"
echo "Input: ${INPUT_IMAGE}"
echo "Output base: ${OUTPUT_BASE}"
echo "Threads: ${NUM_THREADS}"
echo "License: ${FS_LICENSE_PATH}"

# Se OUTPUT_BASE contiene già il subject_id, evita di creare un doppio livello
SID="$SUBJECT_ID"
SD="$OUTPUT_BASE"
MOVE_UP=false
if [[ "$OUTPUT_BASE" == *"/${SUBJECT_ID}/"* || "$OUTPUT_BASE" == *"/${SUBJECT_ID}" ]]; then
    SID="fastsurfer"
    MOVE_UP=true
fi

# Esegui FastSurfer (solo segmentazione)
run_fastsurfer.sh \
    --fs_license "$FS_LICENSE_PATH" \
    --t1 "$INPUT_IMAGE" \
    --sid "$SID" \
    --sd "$SD" \
    --threads "$NUM_THREADS" \
    --seg_only

# Se abbiamo usato SID temporaneo, sposta i risultati nella cartella desiderata
if [ "$MOVE_UP" = true ]; then
    TEMP_DIR="${SD}/${SID}"
    if [ -d "$TEMP_DIR" ]; then
        shopt -s dotglob
        mv "$TEMP_DIR"/* "$SD"/
        rmdir "$TEMP_DIR"
        shopt -u dotglob
    fi
fi

echo "Elaborazione completata per il soggetto: ${SUBJECT_ID}"
