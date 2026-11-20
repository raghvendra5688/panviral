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
(`convert_y=False`: scores stay on the model's native scale: pKd / pIC50 for the BindingDB and DAVIS models, where higher =
stronger binding, and KIBA score for the KIBA models; see the caveat below).
The models differ in drug encoder (CNN, Morgan fingerprint, Daylight fingerprint, MPNN, Transformer) × protein
encoder (CNN, AAC) × training set (BindingDB Kd, BindingDB IC50, DAVIS, KIBA), so they capture complementary signal.

### 3. Rank aggregation (`03_aggregate_ranks.py`)
Raw scores from different models are not comparable, so ranks are used:
1. per model and protein: rank all drugs by score (1 = best, ties get the minimum rank);
2. per drug and protein: median of the 18 model ranks (Borda aggregation, robust to one outlying model);
3. per protein: re-rank drugs by that median → consensus rank (1 … 2,216);
4. `Mean_Rank` = mean consensus rank over the 9 proteins; `Aggregate_Rank` = rank of `Mean_Rank`.

Drugs with the same `Aggregate_Rank` are ordered alphabetically by InChIKey so the output file is deterministic.

<!-- #### Caveat: score direction of the three KIBA models
The published ranking ranks all 18 models by *descending* score. That is right for pKd / pIC50, but DeepPurpose's KIBA
loader labels a drug–target pair as binding when the KIBA score is **below** a threshold, i.e. for KIBA a *lower* score
means stronger binding. If the KIBA models' outputs follow the same convention, MPNN_CNN_KIBA, Daylight_AAC_KIBA and
Morgan_AAC_KIBA were ranked in the wrong direction. The shipped screenings cannot settle this (all models correlate only
weakly with each other on these out-of-domain viral proteins; the KIBA models' correlation with the other models is
+0.04, +0.18 and -0.01). The effect on the result is substantial: with those three models flipped
(`python scripts/03_aggregate_ranks.py --lower-is-better MPNN_CNN_KIBA Daylight_AAC_KIBA Morgan_AAC_KIBA`), the
Spearman correlation between the two `Aggregate_Rank` columns is 0.86 and only 6 of the top-10 and 31 of the top-50
drugs are shared. **Decision:** the published convention is kept (all 18 models ranked by descending score), so
`results/panviral_drug_protein_ranks.csv` is unchanged and reproducible with the default settings. The KIBA direction is
a known limitation of the published ranking; the `--lower-is-better` run above gives the alternative if it is needed
for a sensitivity analysis.
-->

## Reproducibility notes
* `scripts/03_aggregate_ranks.py` reproduces the shipped ranking exactly (all 2,216 × 11 values; checked with
  `--compare-with`).
* `scripts/00_download_models.py --verify-only` compares model files with `models/checksums.sha256`, taken from
  the model files used to generate the shipped results.
