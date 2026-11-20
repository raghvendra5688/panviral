#!/usr/bin/env python3
"""Run every drug x viral-protein pair through the 18 DeepPurpose pretrained models.

For each model, DeepPurpose predicts a binding score (pKd / pIC50-like, higher = stronger) for all
(drug, protein) pairs and the result table is written to
    results/ml_screenings/<model>/<model>_virtual_screening.csv
(DeepPurpose writes a PrettyTable-formatted text file; the `.csv` name is kept for backwards
compatibility with the published results and is parsed by scripts/03_aggregate_ranks.py).

Models that already have an output file are skipped, so an interrupted run can simply be restarted.
A CUDA GPU is strongly recommended (2,216 drugs x 9 proteins x 18 models).

Usage:
    python scripts/02_run_virtual_screening.py --dry-run     # validate inputs/models, build pairs, run nothing
    python scripts/02_run_virtual_screening.py
    python scripts/02_run_virtual_screening.py --models MPNN_CNN_DAVIS --force
"""
import argparse
import gc
import itertools
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_config  # noqa: E402


def load_pairs(cfg):
    compounds_path = cfg["paths"]["compound_table"]
    if not compounds_path.exists():
        sys.exit(f"Compound table not found: {compounds_path}")
    compounds = pd.read_csv(compounds_path)
    proteins = pd.read_csv(cfg["paths"]["protein_table"])

    for col in ("InchiKey", "Canonical_SMILES"):
        if col not in compounds:
            sys.exit(f"{compounds_path} needs a '{col}' column (found {list(compounds.columns)})")
    for col in ("UniProtId", "Sequence"):
        if col not in proteins:
            sys.exit(f"{cfg['paths']['protein_table']} needs a '{col}' column")
    if compounds["InchiKey"].duplicated().any() or proteins["UniProtId"].duplicated().any():
        sys.exit("Duplicate InchiKey / UniProtId entries found in the input tables.")
    if compounds["Canonical_SMILES"].isna().any() or proteins["Sequence"].isna().any():
        sys.exit("Empty SMILES / sequence entries found in the input tables.")

    # drug-major all-pairs lists (identical ordering to the published run)
    pairs = list(itertools.product(range(len(compounds)), range(len(proteins))))
    smiles = [compounds["Canonical_SMILES"].iloc[i] for i, _ in pairs]
    drug_ids = [compounds["InchiKey"].iloc[i] for i, _ in pairs]
    seqs = [proteins["Sequence"].iloc[j] for _, j in pairs]
    prot_ids = [proteins["UniProtId"].iloc[j] for _, j in pairs]
    print(f"{len(compounds)} drugs x {len(proteins)} proteins = {len(pairs)} pairs")
    return smiles, drug_ids, seqs, prot_ids


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--models", nargs="+", default=None, help="subset of models (default: all in config)")
    ap.add_argument("--force", action="store_true", help="recompute models that already have an output file")
    ap.add_argument("--dry-run", action="store_true", help="check inputs and model files, then exit")
    args = ap.parse_args()

    cfg = load_config(args.config)
    models_dir, out_dir = cfg["paths"]["models_dir"], cfg["paths"]["screenings_dir"]
    names = args.models or cfg["models"]

    smiles, drug_ids, seqs, prot_ids = load_pairs(cfg)

    missing = [n for n in names if not (models_dir / n / "model.pt").is_file()]
    if missing:
        sys.exit(f"Model files missing in {models_dir}: {missing}\nRun: python scripts/00_download_models.py")
    if args.dry_run:
        print(f"dry run OK: inputs valid and all {len(names)} model(s) present.")
        return

    # heavy imports only when actually screening
    import torch
    from DeepPurpose import DTI as models

    out_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        final_csv = out_dir / name / f"{name}_virtual_screening.csv"
        if final_csv.exists() and not args.force:
            print(f"[skip] {name}")
            continue

        print(f"\n>>> {name}")
        t0 = time.time()
        result_folder = out_dir / name
        result_folder.mkdir(parents=True, exist_ok=True)

        model = models.model_pretrained(str(models_dir / name))
        model.config["batch_size"] = cfg["screening"]["batch_size"]
        models.virtual_screening(
            smiles, seqs, model,
            drug_names=drug_ids, target_names=prot_ids,
            result_folder=str(result_folder) + "/", convert_y=False,
            output_num_max=len(smiles), verbose=True,
        )

        # release GPU memory before the next model
        del model
        torch.cuda.empty_cache()
        gc.collect()

        raw = result_folder / "virtual_screening.txt"
        if raw.exists():
            raw.replace(final_csv)
        print(f"    done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
