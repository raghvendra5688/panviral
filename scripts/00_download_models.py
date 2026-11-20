#!/usr/bin/env python3
"""Download the 18 DeepPurpose pretrained models used by the panviral pipeline.

The model weights (~500 MB in total) are NOT stored in this repository. They are published
by the DeepPurpose authors on Harvard Dataverse (doi:10.7910/DVN/CNQV69). This script downloads
each zip, unpacks it and stores it under the *canonical* folder name used by this pipeline, e.g.
`models/pretrained_models/CNN_CNN_DAVIS/{config.pkl,model.pt}` (DeepPurpose itself unpacks some
models under different folder names, such as `model_DeepDTA_DAVIS`).

The Dataverse file IDs below are taken from DeepPurpose 0.1.5 (`DeepPurpose/utils.py`, `name2ids`).

Usage:
    python scripts/00_download_models.py                 # download everything that is missing
    python scripts/00_download_models.py --verify-only   # only check what is on disk
    python scripts/00_download_models.py --models MPNN_CNN_DAVIS CNN_CNN_DAVIS
"""
import argparse
import hashlib
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_config  # noqa: E402

DATAVERSE_URL = "https://dataverse.harvard.edu/api/access/datafile/{}"

# canonical model name -> Harvard Dataverse file id
DATAVERSE_IDS = {
    "CNN_CNN_BindingDB_IC50": 4203606,
    "MPNN_CNN_DAVIS": 4159677,
    "Morgan_CNN_BindingDB_IC50": 4203603,
    "Morgan_AAC_BindingDB_IC50": 4203602,
    "Daylight_AAC_BindingDB_IC50": 4203604,
    "CNN_CNN_DAVIS": 4159673,
    "CNN_CNN_BindingDB": 4159715,
    "Morgan_CNN_BindingDB": 4159708,
    "Morgan_CNN_DAVIS": 4159705,
    "MPNN_CNN_BindingDB": 4204178,
    "MPNN_CNN_KIBA": 4159696,
    "Transformer_CNN_BindingDB": 4159655,
    "Daylight_AAC_DAVIS": 4159679,
    "Daylight_AAC_KIBA": 4159649,
    "Daylight_AAC_BindingDB": 4159667,
    "Morgan_AAC_BindingDB": 4159694,
    "Morgan_AAC_KIBA": 4159690,
    "Morgan_AAC_DAVIS": 4159706,
}


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_checksums(path):
    """Parse `sha256sum`-style lines: '<hash>  <model>/<file>'."""
    sums = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            if line.strip():
                digest, rel = line.split(None, 1)
                sums[rel.strip()] = digest
    return sums


def model_is_present(model_dir):
    return (model_dir / "config.pkl").is_file() and (model_dir / "model.pt").is_file()


def verify_model(name, model_dir, checksums):
    """Return a list of problems (empty list = model OK)."""
    problems = []
    for fname in ("config.pkl", "model.pt"):
        f = model_dir / fname
        if not f.is_file():
            problems.append(f"missing {name}/{fname}")
            continue
        expected = checksums.get(f"{name}/{fname}")
        if expected is None:
            problems.append(f"no reference checksum for {name}/{fname}")
        elif sha256(f) != expected:
            problems.append(f"checksum mismatch for {name}/{fname}")
    return problems


def safe_extract(zf, dest):
    """Extract a zip, refusing members that would land outside `dest` (zip-slip)."""
    dest = Path(dest).resolve()
    for member in zf.namelist():
        target = (dest / member).resolve()
        if dest != target and dest not in target.parents:
            raise RuntimeError(f"unsafe path in zip archive: {member}")
    zf.extractall(dest)


def download(url, out_path):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as fh:
            for block in r.iter_content(chunk_size=1 << 20):
                fh.write(block)


def fetch_model(name, models_dir):
    """Download one model zip and install it as models_dir/<name>/."""
    models_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=models_dir) as tmp:
        tmp = Path(tmp)
        zip_path = tmp / f"{name}.zip"
        print(f"  downloading {name} ...")
        download(DATAVERSE_URL.format(DATAVERSE_IDS[name]), zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            safe_extract(zf, tmp / "unpacked")
        # the folder inside the zip is named differently for some models -> find it by content
        candidates = [p.parent for p in (tmp / "unpacked").rglob("model.pt") if (p.parent / "config.pkl").is_file()]
        if len(candidates) != 1:
            raise RuntimeError(f"{name}: expected exactly one model folder in the zip, found {len(candidates)}")
        final = models_dir / name
        if final.exists():
            shutil.rmtree(final)
        shutil.move(str(candidates[0]), str(final))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None, help="path to config.yaml (default: config/config.yaml)")
    ap.add_argument("--models", nargs="+", default=None, help="subset of models (default: all in config)")
    ap.add_argument("--verify-only", action="store_true", help="do not download, only verify files on disk")
    ap.add_argument("--force", action="store_true", help="re-download even if the model is already present")
    ap.add_argument("--strict", action="store_true", help="treat a checksum mismatch as an error (exit code 1)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    models_dir = cfg["paths"]["models_dir"]
    checksums = load_checksums(cfg["paths"]["model_checksums"])
    names = args.models or cfg["models"]
    unknown = [n for n in names if n not in DATAVERSE_IDS]
    if unknown:
        sys.exit(f"Unknown model(s): {unknown}\nKnown: {sorted(DATAVERSE_IDS)}")

    failures, bad = [], []
    for name in names:
        mdir = models_dir / name
        if not args.verify_only and (args.force or not model_is_present(mdir)):
            try:
                fetch_model(name, models_dir)
            except Exception as exc:  # network / zip problems: keep going with the other models
                print(f"[FAIL] {name}: {exc}")
                failures.append(name)
                continue
        problems = verify_model(name, mdir, checksums)
        if problems:
            print(f"[WARN] {name}: " + "; ".join(problems))
            bad.append(name)
        else:
            print(f"[ ok ] {name}")

    print(f"\n{len(names) - len(failures) - len(bad)}/{len(names)} models verified in {models_dir}")
    if failures:
        print(f"download failures: {failures}")
    if bad:
        print("Models with checksum problems may still work but are not byte-identical to the ones used "
              "to produce results/ (see models/README.md).")
    sys.exit(1 if failures or (bad and args.strict) else 0)


if __name__ == "__main__":
    main()
