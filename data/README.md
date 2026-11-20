# Data

| Path | What | Used by |
|---|---|---|
| `proteins/protein_info.csv` | The 9 viral protein sequences that were screened (`UniProtId, Sequence, Virus`). | step 02 |
| `compounds/compound_info.csv` | The 2,216 drugs that were screened (`InchiKey, Canonical_SMILES`). | step 02 |
| `proteins/uniprot_downloads/` | Raw UniProt FASTA downloads (2026-03-14) collected while selecting proteins; see its README. | provenance |
| `reference_sequences/SARS-CoV-2_spike_sequences.fa.gz` | 10,074 SARS-CoV-2 surface-glycoprotein sequences (NCBI-style headers), gzip of the original `SARS-CoV-2_seq_update.fa`. | provenance / spike variant analysis |
| `legacy_pilot/` | One earlier pilot results file, **not** an input of the published results; see its README. | – |

## Provenance and checks

`protein_info.csv` and `compound_info.csv` are the tables read by the screening run that produced `results/`.
They were checked against the published results:

* **Compounds:** the 2,216 InChIKeys are unique and are exactly the 2,216 drugs of
  `results/panviral_drug_protein_ranks.csv` (no missing or extra drug). All SMILES parse with RDKit and reproduce their
  InChIKey's connectivity layer (2,215 of 2,216 reproduce the full key; one differs only in the stereo layer).
* **Proteins:** the 9 sequences are identical to the current UniProt entries
  (`python scripts/01_fetch_viral_proteins.py --check`).

The compound table contains no drug names. Names, if needed, must be mapped from InChIKey using the source library.
Whether the SMILES may be redistributed depends on that library (e.g. DrugBank has restrictive terms); check this
before publishing the repository.
