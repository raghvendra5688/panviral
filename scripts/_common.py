"""Shared helpers for the panviral pipeline scripts."""
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"


def load_config(path=None):
    """Load the YAML config and resolve every entry under `paths` against the repo root."""
    import yaml

    path = Path(path) if path else DEFAULT_CONFIG
    with open(path) as fh:
        cfg = yaml.safe_load(fh)
    # Optional machine-specific overrides (git-ignored), applied next to the default config only.
    # Typical use: point `paths.models_dir` at models that already exist on this machine.
    local = DEFAULT_CONFIG.with_name("config.local.yaml")
    if path == DEFAULT_CONFIG and local.is_file():
        with open(local) as fh:
            override = yaml.safe_load(fh) or {}
        for section, values in override.items():
            if isinstance(values, dict) and isinstance(cfg.get(section), dict):
                cfg[section].update(values)
            else:
                cfg[section] = values
        print(f"[config] applied local overrides from {local.name}", file=sys.stderr)
    # relative paths are resolved against the repo root; absolute paths are kept as they are
    cfg["paths"] = {k: (REPO_ROOT / v) for k, v in cfg["paths"].items()}
    return cfg


def parse_deeppurpose_table(path):
    """Parse the ASCII (PrettyTable) file written by DeepPurpose's virtual_screening().

    The file has "+---+" border lines and "| Rank | Drug Name | Target Name | Binding Score |" rows.
    Returns a DataFrame with columns: Drug Name, Target Name, Binding Score (float).
    """
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("|"):
                continue  # border line
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != 4 or cells[0] == "Rank":
                continue  # header or malformed row
            rows.append(cells[1:])
    df = pd.DataFrame(rows, columns=["Drug Name", "Target Name", "Binding Score"])
    df["Binding Score"] = df["Binding Score"].astype(float)
    return df
