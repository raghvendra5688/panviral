# PanViral – ML-based drug repurposing across viral proteins

A reproducible pan-viral drug-repurposing screen. 2,216 drugs are scored against the key proteins of nine
viruses with 18 pretrained [DeepPurpose](https://github.com/kexinhuang12345/DeepPurpose) drug–target-interaction
models, and the 18 per-model rankings are combined (median rank / Borda) into one **consensus ranking per
protein** and one **pan-viral aggregate ranking**.

The approach follows the AI-driven repurposing strategy of Patel, Mall & Bensmail,
*"AI-driven drug repurposing and binding pose meta dynamics identifies novel targets for monkeypox virus"*,
J Infect Public Health 16(5):799–807 (2023), [doi:10.1016/j.jiph.2023.03.007](https://doi.org/10.1016/j.jiph.2023.03.007),
extended from a single virus to several viruses. This repository implements the **ML screening and
consensus-ranking stage**; the structure-based follow-up described in the paper (docking, dynamics,
binding free energy) is out of scope here. See [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Quick start

**1. Reproduce the published ranking (1 minute, no GPU, no DeepPurpose)**

```bash
pip install -r requirements-aggregation.txt
bash scripts/run_pipeline.sh aggregate
```
This re-aggregates the shipped per-model screenings in `results/ml_screenings/` and checks that the output
is identical to `results/panviral_drug_protein_ranks.csv`.

**2. Re-run the whole pipeline (GPU recommended)**

```bash
conda env create -f environment.yml && conda activate panviral   # see the note inside environment.yml
python scripts/00_download_models.py          # ~500 MB from Harvard Dataverse; verifies SHA-256 checksums
python scripts/01_fetch_viral_proteins.py --check   # optional: confirm sequences against UniProt
python scripts/02_run_virtual_screening.py --dry-run   # validate inputs and models first
python scripts/02_run_virtual_screening.py
python scripts/03_aggregate_ranks.py
python scripts/04_fetch_drug_names.py          # optional: refresh drug names from PubChem (internet)
```

All paths are repo-relative and set in `config/config.yaml`; machine-specific overrides (e.g. a models folder that
already exists locally) go in the git-ignored `config/config.local.yaml` (template:
`config/config.local.example.yaml`, see [models/README.md](models/README.md)).

The screening inputs are `data/proteins/protein_info.csv` (9 viral proteins) and
`data/compounds/compound_info.csv` (2,216 drugs, InChIKey + SMILES); see [data/README.md](data/README.md).

## Repository layout

```
panviral/
├── config/config.yaml          paths, the 9 viral proteins, the 18 models, batch size
├── scripts/
│   ├── 00_download_models.py       download + verify the 18 DeepPurpose models (not stored in git)
│   ├── 01_fetch_viral_proteins.py  rebuild/check the viral protein table from UniProt
│   ├── 02_run_virtual_screening.py drug × protein × model predictions (GPU)
│   ├── 03_aggregate_ranks.py       median-rank consensus + pan-viral ranking (CPU, seconds)
│   ├── 04_fetch_drug_names.py      look up drug names for the InChIKeys in PubChem (needs internet)
│   ├── run_pipeline.sh             wrapper: `all` or `aggregate`
│   └── _common.py                  shared helpers
├── data/
│   ├── proteins/                   protein_info.csv (screened sequences) + raw UniProt downloads
│   ├── compounds/                  compound_info.csv (2,216 drugs: InchiKey, Canonical_SMILES) + drug_names.csv
│   ├── reference_sequences/        SARS-CoV-2 spike sequence collection (gzip)
│   └── legacy_pilot/               one earlier pilot results file, kept for provenance only
├── models/                     checksums.sha256 + pretrained_models/ (18 models, git-ignored; see models/README.md)
├── results/
│   ├── ml_screenings/<model>/      raw predictions of each of the 18 models
│   └── panviral_drug_protein_ranks.csv   final consensus ranking
├── docs/WORKFLOW.md            method, stage mapping to the paper, rank-aggregation details
├── environment.yml · requirements-aggregation.txt
└── logs/
```

## Screened viral proteins

| UniProt | Label in table | UniProt entry |
|---|---|---|
| Q6WB98 | HMPV | Fusion glycoprotein F0, human metapneumovirus |
| P0DTC2 | SARS2-Spike | Spike glycoprotein, SARS-CoV-2 |
| P08668 | HANTA | Envelopment polyprotein (GP), Hantaan virus |
| P03254 | ADENOVIRUS-E1A | Early E1A protein, human adenovirus C serotype 2 |
| Q9IH62 | NIPAH | Glycoprotein G, Nipah virus |
| P03322 | **RSV** | **Gag polyprotein, Rous sarcoma virus** |
| Q710U6 | IAV | Neuraminidase, influenza A virus (A/Chicken/Scotland/1959) |
| Q6YMS1 | DENGUE | Genome polyprotein (fragment), dengue virus type 3 |
| Q86825 | PAMV | Capsid protein, potato aucuba mosaic virus (a plant virus) |

## Outputs

`results/panviral_drug_protein_ranks.csv` – one row per drug (InChIKey), sorted by `Aggregate_Rank`:
per-protein consensus rank (columns named by UniProt accession, 1 = most promising), `Mean_Rank` (average
over the 9 proteins) and `Aggregate_Rank`. Full column description in [results/README.md](results/README.md).

*Predictions are computational hypotheses from sequence-based models, not evidence of antiviral activity.*

## Licence and data provenance

The code in this repository is released under the MIT licence (see [LICENSE](LICENSE)). The licence covers the code,
not third-party material: DeepPurpose models are distributed by their authors (see [models/README.md](models/README.md));
protein sequences come from UniProt; the source library of the 2,216 drugs (`data/compounds/compound_info.csv`) may
carry its own redistribution terms.
