#!/usr/bin/env python3
"""Look up drug names for the screened compounds (InChIKey -> name) using PubChem.

The compound table (`data/compounds/compound_info.csv`) has InChIKeys and SMILES but no names. This script
queries the PubChem PUG REST service (public-domain data) and writes `data/compounds/drug_names.csv`:

    InchiKey, DrugName, PubChem_CID, Match, MatchedInchiKey, NameNote

Match is
  * `inchikey`            - PubChem record found with exactly this InChIKey (reliable);
  * `smiles_same_skeleton`- not found by InChIKey; found via the SMILES string and the returned compound has the
                            same connectivity (first 14 characters of the InChIKey), differing only in
                            stereochemistry/protonation (probably the same drug);
  * `smiles_different_structure` - found via SMILES but the connectivity differs (e.g. salt or tautomer form):
                            the name may refer to a related form, so check `MatchedInchiKey` before relying on it;
  * `none`                - no PubChem record found; DrugName is empty.
`DrugName` is PubChem's preferred title. If PubChem has no title, the first PubChem synonym is used
(NameNote = `first synonym`); if there is no synonym either, the IUPAC name is used
(NameNote = `IUPAC name (no PubChem title or synonym)`). NameNote = `systematic or multi-component name` marks names that are long
chemical descriptions (or mixtures of several components) rather than a familiar drug name.

Usage:
    python scripts/04_fetch_drug_names.py
    python scripts/04_fetch_drug_names.py --out my_names.csv --batch-size 100
Needs internet access. Roughly 25 batch requests plus one request per unresolved compound (a few minutes).
"""
import argparse
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import REPO_ROOT, load_config  # noqa: E402

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
PROPS = "Title,InChIKey"
PAUSE = 0.3  # seconds between requests (PubChem asks for at most 5 requests/second)


def pubchem_csv(url, data=None, retries=6):
    """POST/GET a PUG REST CSV query. Returns a DataFrame (empty if nothing was found)."""
    for attempt in range(retries):
        r = requests.post(url, data=data, timeout=60) if data is not None else requests.get(url, timeout=60)
        time.sleep(PAUSE)
        if r.status_code == 404:  # none of the queried compounds exist
            return pd.DataFrame(columns=["CID", "Title", "InChIKey"])
        if r.status_code in (429, 500, 502, 503, 504):  # busy -> back off and retry
            time.sleep(3 * (attempt + 1))
            continue
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text))
    r.raise_for_status()


def first_synonyms(cids, retries=6):
    """CID -> first PubChem synonym, for a list of CIDs (one batched request)."""
    url = f"{PUG}/cid/synonyms/JSON"
    for attempt in range(retries):
        r = requests.post(url, data={"cid": ",".join(str(c) for c in cids)}, timeout=60)
        time.sleep(PAUSE)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        info = r.json()["InformationList"]["Information"]
        return {i["CID"]: i["Synonym"][0] for i in info if i.get("Synonym")}
    r.raise_for_status()


def looks_systematic(name):
    return bool(name) and (len(name) > 80 or ";" in name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default=str(REPO_ROOT / "data" / "compounds" / "drug_names.csv"))
    ap.add_argument("--batch-size", type=int, default=100)
    args = ap.parse_args()

    cfg = load_config(args.config)
    comp = pd.read_csv(cfg["paths"]["compound_table"])
    keys = comp["InchiKey"].tolist()

    # 1) exact InChIKey lookup in batches
    found = {}
    for i in range(0, len(keys), args.batch_size):
        chunk = keys[i:i + args.batch_size]
        df = pubchem_csv(f"{PUG}/inchikey/property/{PROPS}/CSV", data={"inchikey": ",".join(chunk)})
        for _, r in df.iterrows():
            found[r["InChIKey"]] = (r["Title"], int(r["CID"]))
        print(f"inchikey lookup {min(i + args.batch_size, len(keys))}/{len(keys)}  (resolved {len(found)})", flush=True)

    rows, unresolved = {}, []
    for k in keys:
        if k in found:
            rows[k] = (found[k][0], found[k][1], "inchikey", k)
        else:
            unresolved.append(k)

    # 2) fallback: look the compound up by its SMILES
    smiles = dict(zip(comp["InchiKey"], comp["Canonical_SMILES"]))
    for n, k in enumerate(unresolved, 1):
        try:
            df = pubchem_csv(f"{PUG}/smiles/property/{PROPS}/CSV", data={"smiles": smiles[k]})
        except requests.HTTPError as exc:
            if exc.response is None or exc.response.status_code != 400:  # 400 = SMILES PubChem cannot parse
                raise  # transient/server problem: fail loudly instead of recording a false "none"
            df = pd.DataFrame()
        if len(df):
            r = df.iloc[0]
            same = str(r["InChIKey"])[:14] == k[:14]
            rows[k] = (r["Title"], int(r["CID"]),
                       "smiles_same_skeleton" if same else "smiles_different_structure", r["InChIKey"])
        else:
            rows[k] = ("", pd.NA, "none", "")
        if n % 25 == 0 or n == len(unresolved):
            print(f"smiles fallback {n}/{len(unresolved)}", flush=True)

    out = pd.DataFrame(
        [(k, *rows[k]) for k in keys],
        columns=["InchiKey", "DrugName", "PubChem_CID", "Match", "MatchedInchiKey"],
    )
    out["PubChem_CID"] = out["PubChem_CID"].astype("Int64")
    out["NameNote"] = ""

    # 3) records that exist but have no title -> first synonym
    notitle = out["DrugName"].isna() & out["PubChem_CID"].notna()
    cids = out.loc[notitle, "PubChem_CID"].astype(int).tolist()
    syn = {}
    for i in range(0, len(cids), args.batch_size):
        syn.update(first_synonyms(cids[i:i + args.batch_size]))
    for idx in out.index[notitle]:
        name = syn.get(int(out.at[idx, "PubChem_CID"]))
        if name:
            out.at[idx, "DrugName"], out.at[idx, "NameNote"] = name, "first synonym"
    # 4) still nothing -> IUPAC name (the compound has no common name in PubChem)
    still = out["DrugName"].isna() & out["PubChem_CID"].notna()
    cids = out.loc[still, "PubChem_CID"].astype(int).tolist()
    iupac = {}
    for i in range(0, len(cids), args.batch_size):
        df = pubchem_csv(f"{PUG}/cid/property/IUPACName/CSV", data={"cid": ",".join(map(str, cids[i:i + args.batch_size]))})
        iupac.update({int(r["CID"]): r["IUPACName"] for _, r in df.iterrows() if isinstance(r["IUPACName"], str)})
    for idx in out.index[still]:
        name = iupac.get(int(out.at[idx, "PubChem_CID"]))
        if name:
            out.at[idx, "DrugName"], out.at[idx, "NameNote"] = name, "IUPAC name (no PubChem title or synonym)"
    out["DrugName"] = out["DrugName"].fillna("")
    out.loc[out["Match"] == "none", "NameNote"] = "no PubChem record"
    sysname = out["DrugName"].map(looks_systematic)
    out.loc[sysname & (out["NameNote"] == ""), "NameNote"] = "systematic or multi-component name"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print("\n" + out["Match"].value_counts().to_string())
    print("\n" + out["NameNote"].replace("", "(plain PubChem title)").value_counts().to_string())
    print(f"names present for {(out['DrugName'].fillna('') != '').sum()}/{len(out)} compounds -> {args.out}")


if __name__ == "__main__":
    main()
