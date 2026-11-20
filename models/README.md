# Models

The 18 pretrained DeepPurpose models (~500 MB) are **not committed to git** (the folder is git-ignored). Download them with

```bash
python scripts/00_download_models.py                  # everything that is missing
python scripts/00_download_models.py --verify-only    # check what is on disk
python scripts/00_download_models.py --models MPNN_CNN_DAVIS CNN_CNN_DAVIS   # a subset
```

Source: the DeepPurpose authors' Harvard Dataverse dataset, [doi:10.7910/DVN/CNQV69](https://doi.org/10.7910/DVN/CNQV69)
(file IDs from DeepPurpose 0.1.5, listed in `scripts/00_download_models.py`). Each model is installed as
`models/pretrained_models/<name>/{config.pkl,model.pt}` under the canonical names below – DeepPurpose itself
unpacks some of them under different folder names (e.g. `CNN_CNN_DAVIS` → `model_DeepDTA_DAVIS`), which the
script handles.

**Using models that already exist on your machine.** Copy `config/config.local.example.yaml` to
`config/config.local.yaml` (git-ignored) and set `paths.models_dir` to the folder that contains the 18
`<model_name>/{config.pkl,model.pt}` folders; all scripts then use it instead of `models/pretrained_models/`
(an explicit `--config` bypasses the override).

The model folders are excluded from git by `.gitignore`, so a fresh clone downloads them with
`scripts/00_download_models.py`; after that no override is needed.

`checksums.sha256` holds the SHA-256 of `config.pkl` and `model.pt` of the models that produced
`results/`; the script verifies downloads against it and warns on any mismatch.

| Model | Drug encoder | Protein encoder | Training data |
|---|---|---|---|
| CNN_CNN_BindingDB, CNN_CNN_BindingDB_IC50, CNN_CNN_DAVIS | CNN | CNN | BindingDB (Kd), BindingDB IC50, DAVIS |
| Morgan_CNN_BindingDB, Morgan_CNN_BindingDB_IC50, Morgan_CNN_DAVIS | Morgan fingerprint | CNN | BindingDB, BindingDB IC50, DAVIS |
| Morgan_AAC_BindingDB, Morgan_AAC_BindingDB_IC50, Morgan_AAC_DAVIS, Morgan_AAC_KIBA | Morgan fingerprint | AAC | BindingDB, BindingDB IC50, DAVIS, KIBA |
| Daylight_AAC_BindingDB, Daylight_AAC_BindingDB_IC50, Daylight_AAC_DAVIS, Daylight_AAC_KIBA | Daylight fingerprint | AAC | BindingDB, BindingDB IC50, DAVIS, KIBA |
| MPNN_CNN_BindingDB, MPNN_CNN_DAVIS, MPNN_CNN_KIBA | message-passing NN | CNN | BindingDB, DAVIS, KIBA |
| Transformer_CNN_BindingDB | Transformer | CNN | BindingDB |

(AAC = amino-acid composition.) Please also cite DeepPurpose: Huang et al., *Bioinformatics* 2020.
The live Dataverse download path has not been exercised in this environment; run `--verify-only` after downloading.
