#!/bin/bash
#SBATCH --account=IscrC_PREVAIL
#SBATCH --partition=boost_usr_prod
#SBATCH --job-name=fastsurfer
#SBATCH --output=/leonardo_scratch/large/userexternal/mverdic1/fastsurfer_logs/%A_%a.out
#SBATCH --error=/leonardo_scratch/large/userexternal/mverdic1/fastsurfer_logs/%A_%a.err
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
# Array: un task per soggetto.
# %4 = max 4 task in parallelo (1 nodo x 4 GPU)
#SBATCH --array=1-      %4

# ============================================================
# MODULI
# ============================================================
module purge
module load hpcx-mpi/2.19
module load cuda/12.2

# ============================================================
# CONFIGURAZIONE
# ============================================================
NAS_PREFIX="$SCRATCH/mnt/NAS-Progetti"

CSV="$HOME/hpc_processing/to_process_fastsurfer_unprocessed.csv"
FASTSURFER_SIF="$HOME/hpc_processing/fastsurfer_gpu-latest.sif"

export FS_LICENSE="$HOME/hpc_processing/license.txt"

TMPSD="$SCRATCH/fastsurfer_tmp/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"

# ============================================================
# Leggi la riga del CSV corrispondente a questo task (skip header)
# ============================================================
line=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$CSV")

if [ -z "$line" ]; then
    echo "Nessuna riga per TASK_ID=$SLURM_ARRAY_TASK_ID — skip"
    exit 0
fi

IFS=',' read -r subject_id image_path output_path dataset_code session_id <<< "$line"

strip_quotes() { local v="$1"; v="${v#\"}"; v="${v%\"}"; echo "$v"; }
subject_id=$(strip_quotes "$subject_id")
image_path=$(strip_quotes "$image_path")
output_path=$(strip_quotes "$output_path")
dataset_code=$(strip_quotes "$dataset_code")
session_id=$(strip_quotes "$session_id")

image_path_local="${image_path/\/mnt\/NAS-Progetti/$NAS_PREFIX}"
output_path_local="${output_path/\/mnt\/NAS-Progetti/$NAS_PREFIX}"

# ============================================================
# Calcola output_path se vuoto (stessa logica del job Kubernetes)
# ============================================================
if [ -z "$output_path" ]; then
    BASE_ROOT="$NAS_PREFIX/BrainAtrophy/Normative_model"
    if [ -n "$dataset_code" ]; then
        OUTPUT_ROOT="$BASE_ROOT/$dataset_code/derivatives/fastsurfer"
    else
        OUTPUT_ROOT="$BASE_ROOT/derivatives/fastsurfer"
    fi
    if [ -n "$session_id" ]; then
        output_path_local="$OUTPUT_ROOT/$subject_id/$session_id"
    else
        output_path_local="$OUTPUT_ROOT/$subject_id"
    fi
fi

# ============================================================
# Flag di completamento
#   SEG:  segmentazione CNN completata  (--seg_only)
#   SURF: surface pipeline completata   (produce aseg.stats con eTIV)
# ============================================================
SEG_DONE=false
SURF_DONE=false

if [ -f "$output_path_local/mri/aparc.DKTatlas+aseg.deep.mgz" ] && \
   [ -f "$output_path_local/stats/aseg+DKT.stats" ] && \
   [ -f "$output_path_local/mri/orig.mgz" ]; then
    SEG_DONE=true
fi

if [ -f "$output_path_local/stats/aseg.stats" ] && \
   [ -f "$output_path_local/surf/lh.white" ] && \
   [ -f "$output_path_local/surf/rh.white" ]; then
    SURF_DONE=true
fi

# ============================================================
# Skip se già completamente processato
# ============================================================
if $SEG_DONE && $SURF_DONE; then
    echo "=== $subject_id ALREADY FULLY PROCESSED — skip ==="
    exit 0
fi

echo "=== Processing: $subject_id ==="
echo "Input:        $image_path_local"
echo "Output:       $output_path_local"
echo "GPU:          $CUDA_VISIBLE_DEVICES"
echo "SEG_DONE:     $SEG_DONE"
echo "SURF_DONE:    $SURF_DONE"

mkdir -p "$output_path_local" "$TMPSD/temp_fastsurfer"

# ============================================================
# Se la segmentazione esiste già, copiala nel TMPSD
# così FastSurfer con --surf_only la trova dove si aspetta
# ============================================================
if $SEG_DONE; then
    echo "=== Copio segmentazione esistente in TMPSD ==="
    cp -r "$output_path_local/." "$TMPSD/temp_fastsurfer/"
fi

# ============================================================
# Scegli la modalità di esecuzione
#
#   SEG_DONE=false  → pipeline completa (seg + surf)
#   SEG_DONE=true   → solo surface pipeline (--surf_only)
# ============================================================
if $SEG_DONE; then
    PIPELINE_FLAG="--surf_only"
    echo "=== Modalità: SURF_ONLY ==="
else
    PIPELINE_FLAG=""
    echo "=== Modalità: FULL PIPELINE (seg + surf) ==="
fi

# ============================================================
# Lancia FastSurfer dentro Singularity con GPU
# ============================================================
singularity exec \
    --nv \
    -B "$NAS_PREFIX:/mnt/NAS-Progetti" \
    -B "$TMPSD:/sd" \
    "$FASTSURFER_SIF" \
    run_fastsurfer.sh \
        --fs_license "$FS_LICENSE" \
        --t1 "$image_path" \
        --sid temp_fastsurfer \
        --sd /sd \
        --threads "$SLURM_CPUS_PER_TASK" \
        --no_hypothal \
        --no_skull_strip \
        --device cuda \
        $PIPELINE_FLAG

EXIT_CODE=$?

# ============================================================
# Sposta risultati e pulizia
# ============================================================
if [ $EXIT_CODE -eq 0 ] && [ -d "$TMPSD/temp_fastsurfer" ]; then
    cp -r "$TMPSD/temp_fastsurfer/." "$output_path_local/"
    rm -rf "$TMPSD"
    echo "=== Done: $subject_id ==="
else
    echo "=== FAILED: $subject_id (exit $EXIT_CODE) ==="
    rm -rf "$TMPSD"
    exit $EXIT_CODE
fi