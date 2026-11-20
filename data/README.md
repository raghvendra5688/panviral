# Data

| Path | What | Used by |
|---|---|---|
| `proteins/protein_info.csv` | The 9 viral protein sequences that were screened (`UniProtId, Sequence, Virus`). | step 02 |
| `compounds/compound_info.csv` | The 2,216 drugs that were screened (`InchiKey, Canonical_SMILES`). | step 02 |
| `compounds/drug_names.csv` | Names for the 2,216 drugs (`InchiKey, DrugName, PubChem_CID, Match, MatchedInchiKey, NameNote`), looked up in PubChem with `scripts/04_fetch_drug_names.py`; see below. | annotation |
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

## Drug names (`compounds/drug_names.csv`)

The compound table has no names, so they were looked up in PubChem (public domain) by InChIKey with
`python scripts/04_fetch_drug_names.py` (needs internet access, takes a few minutes). Every one of the 2,216 compounds has a
name. How much to trust it is given by two columns:

| `Match` | Compounds | Meaning |
|---|---|---|
| `inchikey` | 2,193 | PubChem record with exactly this InChIKey – reliable |
| `smiles_same_skeleton` | 14 | not found by key; found via SMILES, same connectivity (differs in stereo/protonation) – probably the same drug |
| `smiles_different_structure` | 9 | found via SMILES but connectivity differs (e.g. salt/tautomer form) – check `MatchedInchiKey` before relying on the name |

| `NameNote` | Compounds | Meaning |
|---|---|---|
| (empty) | 1,794 | PubChem's preferred title |
| `systematic or multi-component name` | 409 | long chemical description (378) or a mixture of several components (31, separated by `;`), not a familiar drug name |
| `IUPAC name (no PubChem title or synonym)` | 13 | PubChem has the structure but no common name |

As a plausibility check, for the 700 compounds that an independent DrugBank table also covers (exact InChIKey), 613 names are
identical and the remainder are synonyms of the same drug (e.g. Mithramycin / Plicamycin, Mavorixafor / AMD-070).
PubChem names can change over time; re-run the script to refresh.
Whether the SMILES may be redistributed depends on that library (e.g. DrugBank has restrictive terms); check this
before publishing the repository.
