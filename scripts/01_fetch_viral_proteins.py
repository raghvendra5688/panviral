#!/usr/bin/env python3
"""Rebuild the viral protein table (UniProtId, Sequence, Virus) from UniProt.

Reads the accession -> label mapping from `viral_proteins` in config/config.yaml and downloads the
canonical sequences from the UniProt REST API.

Usage:
    python scripts/01_fetch_viral_proteins.py                  # write data/proteins/protein_info.csv
    python scripts/01_fetch_viral_proteins.py --check          # compare UniProt with the shipped table
    python scripts/01_fetch_viral_proteins.py --out my.csv
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_config  # noqa: E402

UNIPROT_FASTA = "https://rest.uniprot.org/uniprotkb/{}.fasta"


def fetch_sequence(accession):
    r = requests.get(UNIPROT_FASTA.format(accession), timeout=60)
    r.raise_for_status()
    lines = r.text.strip().splitlines()
    header, seq = lines[0], "".join(lines[1:])
    return header, seq


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default=None, help="output CSV (default: paths.protein_table from config)")
    ap.add_argument("--check", action="store_true", help="do not write; compare with the existing table")
    args = ap.parse_args()

    cfg = load_config(args.config)
    out = Path(args.out) if args.out else cfg["paths"]["protein_table"]

    rows = []
    for acc, label in cfg["viral_proteins"].items():
        header, seq = fetch_sequence(acc)
        print(f"{acc:8s} {label:15s} {len(seq):5d} aa  {header[:90]}")
        rows.append({"UniProtId": acc, "Sequence": seq, "Virus": label})
    fetched = pd.DataFrame(rows)

    if args.check:
        shipped = pd.read_csv(cfg["paths"]["protein_table"]).set_index("UniProtId")
        n_diff = 0
        for _, r in fetched.iterrows():
            if r.UniProtId not in shipped.index:
                print(f"[DIFF] {r.UniProtId}: not in shipped table")
                n_diff += 1
            elif shipped.loc[r.UniProtId, "Sequence"] != r.Sequence:
                print(f"[DIFF] {r.UniProtId}: sequence differs from the shipped table "
                      f"(UniProt may have released a new version)")
                n_diff += 1
        print("shipped table matches UniProt" if n_diff == 0 else f"{n_diff} difference(s)")
        sys.exit(1 if n_diff else 0)

    out.parent.mkdir(parents=True, exist_ok=True)
    fetched.to_csv(out, index=False)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
