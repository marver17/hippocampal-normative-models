# OASIS-3 T1w Scans Download

## File Creato

**File**: `oasis3_t1w_scans_to_download.csv`

## Statistiche

- **Totale scansioni T1w**: 4,116
- **Soggetti unici**: 1,376
- **Sessioni uniche**: 2,832 (media ~2.06 sessioni per soggetto)

## Formato CSV

Il file contiene le seguenti colonne:

| Colonna    | Descrizione                                      | Esempio                |
|------------|--------------------------------------------------|------------------------|
| subject    | ID soggetto OASIS                                | OAS30001               |
| session    | ID sessione (giorni dallo studio)                | d0129                  |
| mr_id      | ID completo della sessione MRI                   | OAS30001_MR_d0129      |
| scan_type  | Tipo di scansione (sempre T1w)                   | T1w                    |
| filename   | Nome file BIDS originale                         | sub-OAS30001_ses-d0129_run-01_T1w.json |

## Note

### Multiple Run per Sessione
Alcune sessioni hanno multiple acquisizioni T1w (run-01, run-02):
- Questo è normale e indica acquisizioni ripetute nella stessa sessione
- Utili per quality control o averaging

### Formato Session ID
- `dXXXX`: giorni dalla baseline (es. d0129 = 129 giorni dopo la baseline)
- Sessioni con numeri più alti sono follow-up più tardivi

### Confronto con Dati Attuali

**Dati già scaricati in OASIS3_BIDS**:
- 874 soggetti
- 1,280 sessioni

**Dati disponibili totali (questo CSV)**:
- 1,376 soggetti
- 2,832 sessioni
- 4,116 scansioni T1w

**Soggetti mancanti**: ~502 soggetti (1,376 - 874)

## Utilizzo con download_scans

Lo script di download richiede tipicamente un CSV con queste colonne.
Verifica la documentazione dello script in `~/Repository/oasis-scripts/download_scans/` per il formato esatto richiesto.

### Possibili Formati Richiesti

Se lo script richiede un formato diverso, potrebbe servire:
1. Solo `mr_id` (una colonna)
2. `subject,session` (due colonne)
3. `subject,mr_id,scan_type` (tre colonne)

## Filtri Utili

### Solo Baseline (prima visita per soggetto)
```python
import pandas as pd
df = pd.read_csv('oasis3_t1w_scans_to_download.csv')
baseline = df.sort_values('session').groupby('subject').first().reset_index()
# 1,376 soggetti, solo prima visita
```

### Solo Healthy Controls (CDR=0, age≥50)
Per questo serve incrociare con i dati clinici. Dal notebook sappiamo che sono 918 soggetti.

### Solo 1 Run per Sessione
```python
# Prendi solo il primo run se ce ne sono multipli
unique_sessions = df.groupby(['subject', 'session']).first().reset_index()
# 2,832 sessioni uniche
```

## Download Completo

Per scaricare tutte le 4,116 scansioni T1w:
```bash
cd ~/Repository/oasis-scripts/download_scans/
# Verifica il comando esatto dello script
./download_oasis_scans.sh oasis3_t1w_scans_to_download.csv
```

## Spazio Disco Richiesto

Stima approssimativa:
- ~5-6 MB per scan T1w compressa (NIfTI .nii.gz)
- 4,116 scans × 6 MB ≈ **24.7 GB**
- Con JSON sidecar e file aggiuntivi: **~30 GB**

Se scarichi solo baseline (1,376 scans): **~8 GB**
