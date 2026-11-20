# Results

## `panviral_drug_protein_ranks.csv`
2,216 rows (drugs) × 11 columns, sorted by `Aggregate_Rank`.

| Column | Meaning |
|---|---|
| `Drug_InchiKey` | InChIKey of the drug |
| `P03254`, `P03322`, `P08668`, `P0DTC2`, `Q6WB98`, `Q6YMS1`, `Q710U6`, `Q86825`, `Q9IH62` | Consensus rank of the drug for that viral protein (1 = most promising of the 2,216; median over 18 models, re-ranked) |
| `Mean_Rank` | Mean of the 9 per-protein ranks (pan-viral score, lower = better) |
| `Aggregate_Rank` | Rank of `Mean_Rank` (1 = best across all viruses; ties share the minimum rank) |

See `docs/WORKFLOW.md` for the method and `data/proteins/protein_info.csv` for the accession → virus map
(note the labelling caveat for P03322 in the top-level README).

## `ml_screenings/<model>/<model>_virtual_screening.csv`
Raw output of each of the 18 models: 19,944 drug–protein pairs, sorted by predicted binding score. Despite the
`.csv` extension this is the ASCII table written by DeepPurpose (`+---+` borders, `| Rank | Drug Name | Target Name |
Binding Score |` rows); `scripts/_common.py::parse_deeppurpose_table` reads it. `Drug Name` holds the InChIKey,
`Target Name` the UniProt accession; a higher `Binding Score` means stronger predicted binding.

The ranking file is reproducible from these tables with `bash scripts/run_pipeline.sh aggregate`.
