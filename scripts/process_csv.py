#!/usr/bin/env python3
"""
process_csv.py
==============
Reads RoyceData.csv, filters CRTL CHART rows for IGN2932M75,
normalises machine names and wire-type labels, groups by machine
and date, averages the peak force per (date, wire-type) group,
then writes dashboard/data/machine-data.json.

Usage:
    python3 scripts/process_csv.py \
        --csv  /home/integra/RoyceData.csv \
        --out  /var/www/integra-royce/dashboard/data/machine-data.json

Schedule with cron (runs at 06:00 every day):
    0 6 * * * python3 /var/www/integra-royce/scripts/process_csv.py \
        --csv /home/integra/RoyceData.csv \
        --out /var/www/integra-royce/dashboard/data/machine-data.json
"""

import re
import json
import argparse
import sys
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas --break-system-packages")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PRODUCT   = "IGN2932M75"   # string that must appear in col-5 or col-6
CTRL_FLAG = "CRTL CHART"   # value in the CTRL_CHART column (col-10)
SPEC_LIMIT = 8             # lower spec limit in grams

# Machines to include — canonical upper-case IDs
TARGET_MACHINES = {"B21", "B24", "B25", "B27"}

# Wire-type normalisation: raw → canonical key
# Handles the many spelling variants found in the CSV
TYPE_MAP = {
    # --- Type 1 ---
    r"^(type\s*[-#]?\s*1|type1|type\s*i|output-?1|input1)$": "t1",
    # --- Type 2 ---
    r"^(type\s*[-#]?\s*2|type2|type\s*ii|output-?2|input2)$": "t2",
    # --- Type 3 Short ---
    r"^(type[\s_-]*3[\s_-]*(s(h(o(r(t?)?)?)?)?|chort|shor?t?|shot|schort|schot|3short|3\s*shor?t?))$": "t3s",
    # --- Type 3 Long ---
    r"^(type[\s_-]*3[\s_-]*(l(o(n(g?)?)?)?|lng|3long|3\s*lon?g?))$": "t3l",
    # --- Legacy loose labels (B25 old records) ---
    r"^(3\s*shor?t?|3short)$":  "t3s",
    r"^(3\s*lon?g?|3long)$":   "t3l",
    r"^(2|type\s*2)$":          "t2",
    r"^(1|type\s*1)$":          "t1",
}


def normalise_wire_type(raw):
    """Return canonical wire-type key or None if unrecognised."""
    if pd.isna(raw):
        return None
    s = str(raw).strip().lower()
    # remove extra spaces
    s = re.sub(r"\s+", " ", s)
    for pattern, key in TYPE_MAP.items():
        if re.match(pattern, s):
            return key
    return None


def normalise_machine(raw):
    """Return canonical machine ID (B21, B24, B25, B27) or None."""
    if pd.isna(raw):
        return None
    s = str(raw).strip().upper().replace(" ", "").replace("-", "")
    # match B followed by 2 digits
    m = re.match(r"B(\d{2})", s)
    if m:
        return "B" + m.group(1)
    return None


def load_raw(csv_path):
    """
    The CSV has two distinct layouts that can appear interleaved:

    Layout A (rows 0-14): header metadata rows, no Test ID
        col-3 = date string, col-5 = Machine, col-6 = Part,
        col-8 = Wire Type, col-10 = Ctrl flag, col-18 = Peak Force

    Layout B (rows 15+): full Royce-instrument export
        col-0 = Test ID, col-3 = DateTime, col-4 = Machine,
        col-5 = Part, col-8 = Wire Type, col-10 = Ctrl flag,
        col-17 or col-18 = Peak Force

    Additionally the CSV periodically repeats its own header row
    and some later rows were exported with comma-delimited values
    embedded inside a single tab-separated cell.
    """
    df_raw = pd.read_csv(csv_path, sep="\t", header=None, dtype=str)
    return df_raw


def parse_layout_b(df_raw):
    """
    Parse Layout-B rows: col-0 is numeric Test ID, col-3 is full timestamp.
    Handles both the normal multi-column format and rows where the whole
    record was embedded as a comma-separated string in col-0.
    """
    records = []

    for _, row in df_raw.iterrows():
        # ---- detect comma-embedded rows ----
        cell0 = str(row.iloc[0]).strip()
        if "," in cell0 and re.match(r"^\d+,", cell0):
            # the entire record is in col-0 as CSV; split it
            parts = next(iter(csv_split(cell0)))
            if len(parts) < 9:
                continue
            try:
                date_str = parts[3].strip().strip('"')
                machine  = parts[4].strip().strip('"')
                part     = parts[5].strip().strip('"')
                wtype    = parts[7].strip().strip('"')
                ctrl     = parts[10].strip().strip('"') if len(parts) > 10 else ""
                peak     = parts[14].strip().strip('"') if len(parts) > 14 else ""
            except (IndexError, ValueError):
                continue
        else:
            # standard tab-separated Layout-B row
            if not re.match(r"^\d+$", cell0):
                continue   # not a data row
            try:
                date_str = str(row.iloc[3]).strip()
                machine  = str(row.iloc[4]).strip()
                part     = str(row.iloc[5]).strip()
                wtype    = str(row.iloc[8]).strip()
                ctrl     = str(row.iloc[10]).strip() if len(row) > 10 else ""
                # peak force: prefer col-17 (rounded), fall back to col-18 (raw)
                peak_col = 17
                peak = str(row.iloc[peak_col]).strip() if len(row) > peak_col else ""
                if not peak or peak == "nan":
                    peak = str(row.iloc[18]).strip() if len(row) > 18 else ""
            except (IndexError, ValueError):
                continue

        records.append({
            "date_str": date_str,
            "machine":  machine,
            "part":     part,
            "wtype":    wtype,
            "ctrl":     ctrl,
            "peak":     peak,
        })

    return pd.DataFrame(records)


def parse_layout_a(df_raw):
    """
    Parse Layout-A rows: col-3 = date, col-5 = Machine, col-6 = Part,
    col-8 = Wire Type, col-10 = Ctrl flag, col-18 = Peak Force.
    These rows have NaN in col-0 (no Test ID).
    """
    records = []
    for _, row in df_raw.iterrows():
        cell0 = str(row.iloc[0]).strip()
        if cell0 not in ("nan", ""):
            continue   # not a Layout-A row
        try:
            date_str = str(row.iloc[3]).strip()
            machine  = str(row.iloc[5]).strip()
            part     = str(row.iloc[6]).strip()
            wtype    = str(row.iloc[8]).strip()
            ctrl     = str(row.iloc[10]).strip() if len(row) > 10 else ""
            peak     = str(row.iloc[18]).strip() if len(row) > 18 else ""
        except IndexError:
            continue
        records.append({
            "date_str": date_str,
            "machine":  machine,
            "part":     part,
            "wtype":    wtype,
            "ctrl":     ctrl,
            "peak":     peak,
        })
    return pd.DataFrame(records)


def csv_split(line):
    """Yield lists of fields split on commas, respecting double-quoted fields."""
    import csv
    yield list(csv.reader([line]))[0]


def build_dataset(csv_path):
    print(f"[1/4] Loading {csv_path} ...")
    df_raw = load_raw(csv_path)

    print("[2/4] Parsing rows ...")
    dfA = parse_layout_a(df_raw)
    dfB = parse_layout_b(df_raw)
    df  = pd.concat([dfA, dfB], ignore_index=True)
    print(f"      Total candidate rows: {len(df)}")

    # ---- filter on product string ----
    product_up = PRODUCT.upper()
    mask_product = (
        df["machine"].str.upper().str.contains(product_up, na=False) |
        df["part"].str.upper().str.contains(product_up, na=False)
    )
    df = df[mask_product].copy()
    print(f"      Rows matching {PRODUCT}: {len(df)}")

    # ---- filter on CRTL CHART flag ----
    df = df[df["ctrl"].str.upper().str.contains("CRTL", na=False)].copy()
    print(f"      Rows with CRTL flag: {len(df)}")

    # ---- normalise machine / wire type ----
    # When the product string is IN the machine column, the actual machine
    # is in the part column and vice-versa (swapped in some later records)
    def resolve_machine(row):
        if PRODUCT.upper() in str(row["machine"]).upper():
            return row["part"]
        return row["machine"]

    def resolve_part(row):
        if PRODUCT.upper() in str(row["machine"]).upper():
            return row["machine"]
        return row["part"]

    df["machine_raw"] = df.apply(resolve_machine, axis=1)
    df["machine_id"]  = df["machine_raw"].apply(normalise_machine)
    df["wire_key"]    = df["wtype"].apply(normalise_wire_type)

    # ---- parse peak force ----
    df["force"] = pd.to_numeric(df["peak"], errors="coerce")

    # ---- parse date ----
    df["date"] = pd.to_datetime(df["date_str"], errors="coerce", infer_datetime_format=True)

    # ---- drop unusable rows ----
    before = len(df)
    df = df.dropna(subset=["machine_id", "wire_key", "force", "date"])
    df = df[df["machine_id"].isin(TARGET_MACHINES)]
    df = df[df["force"] > 0]   # drop zero / negative readings
    print(f"      Clean rows after normalisation: {len(df)} (dropped {before - len(df)})")

    return df


def group_by_machine_date(df):
    """
    For each machine, produce a sorted list of {date, t1, t2, t3s, t3l}
    where each value is the AVERAGE peak force of all readings on that date
    for that wire type.
    """
    print("[3/4] Grouping by machine + date ...")

    result = {}
    for machine_id in sorted(TARGET_MACHINES):
        mdf = df[df["machine_id"] == machine_id].copy()
        mdf["date_only"] = mdf["date"].dt.date

        # pivot: rows = date, columns = wire_key, values = mean force
        pivot = (
            mdf.groupby(["date_only", "wire_key"])["force"]
            .mean()
            .unstack("wire_key")
            .reset_index()
            .sort_values("date_only")
        )

        # ensure all 4 columns exist
        for col in ["t1", "t2", "t3s", "t3l"]:
            if col not in pivot.columns:
                pivot[col] = float("nan")

        # drop rows where ALL four types are NaN
        pivot = pivot.dropna(subset=["t1", "t2", "t3s", "t3l"], how="all")

        dates = [str(d) for d in pivot["date_only"]]
        t1    = [round(v, 2) if pd.notna(v) else None for v in pivot["t1"]]
        t2    = [round(v, 2) if pd.notna(v) else None for v in pivot["t2"]]
        t3s   = [round(v, 2) if pd.notna(v) else None for v in pivot["t3s"]]
        t3l   = [round(v, 2) if pd.notna(v) else None for v in pivot["t3l"]]

        num_id = machine_id.replace("B", "")   # "21", "24" etc.
        result[num_id] = {
            "label":      machine_id + " Machine",
            "title":      machine_id,
            "date":       dates[-1] if dates else "—",
            "specLimit":  SPEC_LIMIT,
            "excel":      f"data/BOND PULL DATA IGN2932M75 {machine_id} bonder.xlsx",
            "dates":      dates,
            "t1":         t1,
            "t2":         t2,
            "t3s":        t3s,
            "t3l":        t3l,
        }
        print(f"      {machine_id}: {len(dates)} date points")

    return result


def write_json(data, out_path):
    print(f"[4/4] Writing {out_path} ...")
    import pathlib
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print("      Done.")


def main():
    parser = argparse.ArgumentParser(description="Process RoyceData.csv → machine-data.json")
    parser.add_argument("--csv", default="/home/integra/RoyceData.csv",
                        help="Path to RoyceData.csv")
    parser.add_argument("--out", default="/var/www/integra-royce/dashboard/data/machine-data.json",
                        help="Output JSON path")
    args = parser.parse_args()

    df   = build_dataset(args.csv)
    data = group_by_machine_date(df)
    write_json(data, args.out)
    print("\nSummary:")
    for mid, d in data.items():
        print(f"  B{mid}: {len(d['dates'])} dates, last={d['date']}")


if __name__ == "__main__":
    main()
