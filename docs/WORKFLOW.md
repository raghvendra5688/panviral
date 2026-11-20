# Workflow

## Relation to the reference paper

Patel, Mall & Bensmail (J Infect Public Health 2023, 16(5):799–807, doi:10.1016/j.jiph.2023.03.007)
screen FDA-approved and investigational drugs against monkeypox virus proteins with an AI compound–protein
interaction framework (DeepRepurpose, built on DeepPurpose) and then validate top hits with structure-based
methods (homology modelling, docking, molecular dynamics, binding free energy).
*This description is taken from the paper's abstract; the full text was not accessible when this repository
was assembled, so please check the stage mapping below against the paper.*

| Stage in the paper | This repository |
|---|---|
| Collect viral protein sequences | `data/proteins/protein_info.csv`, `scripts/01_fetch_viral_proteins.py` |
| Collect drug library (SMILES) | `data/compounds/compound_info.csv` |
| AI-based compound–protein interaction screening | `scripts/00_download_models.py`, `scripts/02_run_virtual_screening.py` |
| Rank drugs per protein | `scripts/03_aggregate_ranks.py` → `results/panviral_drug_protein_ranks.csv` |
| Homology modelling, docking, MD, binding free energy | **not included** (downstream, structure-based) |

The pan-viral version differs from the paper in three ways: nine viruses instead of one; 18 pretrained models
whose rankings are combined by median rank (instead of a single model); and an additional pan-viral score that
averages the per-protein consensus ranks.

## Pipeline

```
 UniProt ──► protein_info.csv ─┐
                               ├─► all drug×protein pairs ─► 18 DeepPurpose models ─► results/ml_screenings/<model>/
 drug library ► compound_info ─┘        (02_run_virtual_screening.py)                       (binding score per pair)
                                                                                                │
                                                                           03_aggregate_ranks.py │
                                                                                                ▼
                                                                      results/panviral_drug_protein_ranks.csv
```

### 1. Inputs
* **Proteins** – `data/proteins/protein_info.csv` (`UniProtId, Sequence, Virus`), 9 sequences.
* **Compounds** – `data/compounds/compound_info.csv` (`InchiKey, Canonical_SMILES`), 2,216 drugs.

### 2. Prediction (`02_run_virtual_screening.py`)
Every drug is paired with every protein (2,216 × 9 = 19,944 pairs). Each of the 18 pretrained models
(`config/config.yaml → models`) predicts a binding score for every pair with `DeepPurpose.DTI.virtual_screening`
(`convert_y=False`: scores stay on the model's native, log-scaled affinity axis; higher = stronger binding).
The models differ in drug encoder (CNN, Morgan fingerprint, Daylight fingerprint, MPNN, Transformer) × protein
encoder (CNN, AAC) × training set (BindingDB Kd, BindingDB IC50, DAVIS, KIBA), so they capture complementary signal.

### 3. Rank aggregation (`03_aggregate_ranks.py`)
Raw scores from different models are not comparable, so ranks are used:
1. per model and protein: rank all drugs by score (1 = best, ties get the minimum rank);
2. per drug and protein: median of the 18 model ranks (Borda aggregation, robust to one outlying model);
3. per protein: re-rank drugs by that median → consensus rank (1 … 2,216);
4. `Mean_Rank` = mean consensus rank over the 9 proteins; `Aggregate_Rank` = rank of `Mean_Rank`.

Drugs with the same `Aggregate_Rank` are ordered alphabetically by InChIKey so the output file is deterministic.

## Reproducibility notes
* `scripts/03_aggregate_ranks.py` reproduces the shipped ranking exactly (all 2,216 × 11 values; checked with
  `--compare-with`).
* `scripts/00_download_models.py --verify-only` compares model files with `models/checksums.sha256`, taken from
  the model files used to generate the shipped results.
