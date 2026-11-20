#!/usr/bin/env python3
"""Aggregate the per-model screenings into one consensus drug ranking per viral protein.

This step needs only pandas / numpy / scipy (no DeepPurpose, no GPU), so the published ranking can
be reproduced from the shipped results/ml_screenings/ tables.

Method (Borda / median-rank aggregation)
  1. For each model and each protein, rank all drugs by predicted binding score (1 = strongest binder).
  2. For each (drug, protein) take the MEDIAN of the 18 model ranks.
  3. Re-rank drugs inside each protein by that median  -> consensus rank per protein (1..N_drugs).
  4. Mean_Rank      = mean of the consensus ranks over all viral proteins (pan-viral score).
     Aggregate_Rank = rank of Mean_Rank (1 = best candidate across all viruses).

Usage:
    python scripts/03_aggregate_ranks.py
    python scripts/03_aggregate_ranks.py --out /tmp/ranks.csv --compare-with results/panviral_drug_protein_ranks.csv
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as ss

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_config, parse_deeppurpose_table  # noqa: E402


def per_model_ranks(path):
    """Protein x drug matrix of ranks (1 = highest predicted binding score) for one model."""
    df = parse_deeppurpose_table(path)
    scores = df.pivot(index="Target Name", columns="Drug Name", values="Binding Score")
    return scores.rank(axis=1, ascending=False, method="min")


def aggregate(model_ranks):
    """model_ranks: dict model -> (protein x drug) rank DataFrame. Returns the drug x protein result table."""
    names = list(model_ranks)
    ref = model_ranks[names[0]]
    proteins, drugs = ref.index.tolist(), ref.columns.tolist()
    cube = np.stack([model_ranks[n].reindex(index=proteins, columns=drugs).to_numpy() for n in names])  # model x prot x drug

    median_rank = pd.DataFrame(np.nanmedian(cube, axis=0).T, index=drugs, columns=proteins)  # drug x protein
    consensus = median_rank.apply(lambda col: ss.rankdata(col, method="min", nan_policy="omit")).astype(int)
    consensus.index.name, consensus.columns.name = "Drug_InchiKey", "UniProtId"

    consensus["Mean_Rank"] = consensus[proteins].mean(axis=1)
    consensus["Aggregate_Rank"] = ss.rankdata(consensus["Mean_Rank"], method="min").astype(int)
    # stable sort: drugs tied on Aggregate_Rank stay in InChIKey order, so the output file is deterministic
    return consensus.sort_index().sort_values("Aggregate_Rank", kind="stable")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--screenings-dir", default=None, help="default: paths.screenings_dir from config")
    ap.add_argument("--out", default=None, help="default: paths.ranks_out from config")
    ap.add_argument("--compare-with", default=None, help="existing ranking CSV to compare against (exit 1 if different)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    sdir = Path(args.screenings_dir) if args.screenings_dir else cfg["paths"]["screenings_dir"]
    out = Path(args.out) if args.out else cfg["paths"]["ranks_out"]

    model_ranks = {}
    for name in cfg["models"]:
        f = sdir / name / f"{name}_virtual_screening.csv"
        if not f.exists():
            print(f"[missing] {name} ({f})")
            continue
        model_ranks[name] = per_model_ranks(f)
        print(f"loaded {name}: {model_ranks[name].shape[0]} proteins x {model_ranks[name].shape[1]} drugs")
    if not model_ranks:
        sys.exit("No screening results found. Run scripts/02_run_virtual_screening.py first.")
    if len(model_ranks) < len(cfg["models"]):
        print(f"WARNING: aggregating {len(model_ranks)} of {len(cfg['models'])} models")

    result = aggregate(model_ranks)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out)
    print(f"\nsaved {result.shape} -> {out}")
    print(result.head(10).to_string())

    if args.compare_with:
        ref = pd.read_csv(args.compare_with, index_col=0)
        new = pd.read_csv(out, index_col=0)
        # compare drug by drug: row order among drugs tied on Aggregate_Rank is not meaningful
        same = (set(ref.index) == set(new.index) and list(ref.columns) == list(new.columns)
                and np.allclose(ref.loc[new.index].to_numpy(float), new.to_numpy(float)))
        print("\nidentical to reference ranking (all values, matched by drug)" if same
              else "\nDIFFERS from reference ranking")
        sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
