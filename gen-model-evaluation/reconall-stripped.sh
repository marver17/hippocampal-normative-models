#!/bin/bash
set -e # Interrompe lo script immediatamente se un comando fallisce


if [ "$#" -ne 3 ]; then
    echo "ERRORE: Numero di argomenti non corretto."
    echo "Uso: $0 <subject_id> <percorso_immagine_input> <cartella_output>"
    echo "Esempio: $0 sub-01 /data/input/sub-01_brain.nii.gz /data/output"
    exit 1
fi

if [ -z "$SUBJECTS_DIR" ] || [ -z "$FREESURFER_HOME" ]; then
    echo "ERRORE: Le variabili SUBJECTS_DIR e/o FREESURFER_HOME non sono impostate."
    echo "Assicurati di aver caricato la configurazione di FreeSurfer prima di lanciare questo script."
    exit 1
fi


SUBJECT_ID="$1"
INPUT_IMAGE_PATH="$2"
OUTPUT_DIR="$3"


SUBJ_DIR=${SUBJECTS_DIR}/${SUBJECT_ID}
MRI_DIR=${SUBJ_DIR}/mri
TRANSFORMS_DIR=${MRI_DIR}/transforms
ORIG_DIR=${MRI_DIR}/orig
FS_ATLAS="${FREESURFER_HOME}/average/RB_all_2016-05-10.vc700.gca"   # Atlante di riferimento per la registrazione


# --- Inizio del protocollo di preparazione ---
echo "======================================================"
echo "Inizio preparazione per soggetto: ${SUBJECT_ID}"
echo "Input: ${INPUT_IMAGE_PATH}"
echo "Workspace: ${SUBJECTS_DIR}"
echo "Output Finale: ${OUTPUT_DIR}"
echo "======================================================"

echo -e "\n--> PASSO 1: Creazione della struttura delle cartelle..."
mkdir -p ${ORIG_DIR}
mkdir -p ${TRANSFORMS_DIR}
echo "OK: Struttura creata."

echo -e "\n--> PASSO 2: Conversione input e creazione file di base..."
mri_convert ${INPUT_IMAGE_PATH} ${ORIG_DIR}/001.mgz --scale 1000
cp ${ORIG_DIR}/001.mgz ${MRI_DIR}/T1.mgz
cp ${MRI_DIR}/T1.mgz ${MRI_DIR}/brainmask.mgz
cp ${ORIG_DIR}/001.mgz ${MRI_DIR}/rawavg.mgz
cp ${ORIG_DIR}/001.mgz ${MRI_DIR}/orig.mgz
cp ${MRI_DIR}/brainmask.mgz ${MRI_DIR}/brain.mgz
echo "OK: File di base (T1, brainmask, rawavg, orig, brain) creati."

echo -e "\n--> PASSO 3: Correzione Non-Uniformità (creazione di nu.mgz)..."
mri_normalize -g 1 ${MRI_DIR}/T1.mgz ${MRI_DIR}/nu.mgz 
echo "OK: nu.mgz creato."

echo -e "\n--> PASSO 4: Registrazione Talairach (creazione di talairach.lta e .xfm)..."
mri_em_register -mask ${MRI_DIR}/brainmask.mgz \
                ${MRI_DIR}/nu.mgz \
                ${FS_ATLAS} \
                ${TRANSFORMS_DIR}/talairach.lta -openmp 8
echo "OK: talairach.lta creato."

lta_convert --inlta ${TRANSFORMS_DIR}/talairach.lta \
            --outmni ${TRANSFORMS_DIR}/talairach.xfm
echo "OK: talairach.xfm creato."

echo -e "\n--> PASSO 5: PREPARAZIONE COMPLETATA. Avvio di recon-all..."
echo "Questo processo richiederà molte ore."
echo "Al termine, la cartella del soggetto verrà spostata automaticamente in: ${OUTPUT_DIR}"

recon-all -s ${SUBJECT_ID} -autorecon2 -autorecon3 -openmp 4 -parallel

echo -e "\n--> PASSO 6: Analisi di recon-all completata."
echo "Spostamento della cartella dei risultati..."

mkdir -p ${OUTPUT_DIR}

# Sposta l'intera cartella del soggetto
mv ${SUBJ_DIR} ${OUTPUT_DIR}/

echo "Spostamento completato."
echo "La cartella ${SUBJECT_ID} si trova ora in ${OUTPUT_DIR}"

echo -e "\n\nPROCESSO COMPLETATO CON SUCCESSO per ${SUBJECT_ID}!"