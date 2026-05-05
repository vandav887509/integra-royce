#!/usr/bin/env python3
"""
process_csv.py
==============
Converts RoyceData.csv → dashboard/data/machine-data.json

Rules (confirmed):
  1. Skip rows 1-3746 (old manual records, different format)
  2. Column D (index 3)  = Date
  3. Column E (index 4)  = Machine  → keep B21, B24, B25, B27 only
  4. Column F (index 5)  = Product  → keep IGN2932M75 only
  5. Column H (index 7)  = Wire/Bond Type
  6. Column R (index 17) = Peak Force g (Y-axis)
  7. Normalise all wire-type spelling variants → TYPE 1 / TYPE 2 / TYPE 3 SHORT / TYPE 3 LONG
  8. Duplicates: keep LAST value per (Date, Machine, Wire_Type)

Usage:
    python3 scripts/process_csv.py \
        --csv /home/integra/RoyceData.csv \
        --out /var/www/integra-royce/dashboard/data/machine-data.json

Cron (daily 06:00):
    0 6 * * * python3 /var/www/integra-royce/scripts/process_csv.py \
        --csv /home/integra/RoyceData.csv \
        --out /var/www/integra-royce/dashboard/data/machine-data.json
"""

import re
import csv
import json
import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required:  pip install pandas --break-system-packages")


# ── configuration ────────────────────────────────────────────────────────────

SKIP_ROWS       = 3746                          # rows 1-3746 are skipped
TARGET_PRODUCT  = "IGN2932M75"
TARGET_MACHINES = {"B21", "B24", "B25", "B27"}
SPEC_LIMIT      = 8                             # lower spec limit (g)

# column indices inside the comma-separated data rows
COL_DATE    = 3   # D
COL_MACHINE = 4   # E
COL_PRODUCT = 5   # F
COL_WTYPE   = 7   # H
COL_PEAK    = 17  # R


# ── wire-type normalisation ───────────────────────────────────────────────────
# Maps every spelling variant found in the CSV to one of four canonical labels.

_WIRE_RULES = [
    # TYPE 1
    (r"^(type\s*[-#i]?\s*1|type1|type\s*-\s*1|output-?1|input1)$",   "TYPE 1"),
    # TYPE 2
    (r"^(type\s*[-#]?\s*2|type2|type\s*-\s*2|output-?2|input2)$",    "TYPE 2"),
    # TYPE 3 SHORT  (chort / schort / schot / shot / shor variants)
    (r"^type[\s_-]*3[\s_-]*(s[hc]?o?r?t?|chort|schort|schot|shot)$", "TYPE 3 SHORT"),
    (r"^(type3\s*shor?t?|type3short|type3\s*chort)$",                 "TYPE 3 SHORT"),
    (r"^t[\s_]*3[\s_]*(shor?t?|chort|schort|ype3\s*shor?t?)$",       "TYPE 3 SHORT"),
    (r"^tipe[\s_-]*3[\s_-]*shor?t?$",                                 "TYPE 3 SHORT"),
    (r"^type[\s_-]*3[\s_-]*schort$",                                  "TYPE 3 SHORT"),
    (r"^type-3\s*sch?o[rt]+$",                                        "TYPE 3 SHORT"),
    (r"^3\s*shor?t?$",                                                "TYPE 3 SHORT"),
    # TYPE 3 LONG
    (r"^type[\s_-]*3[\s_-]*(lon?g?|lng)$",                            "TYPE 3 LONG"),
    (r"^(type3\s*lon?g?|type3long|type[\s_-]*3[\s_-]*long[\s_]*3?)$", "TYPE 3 LONG"),
    (r"^t[\s_]*3[\s_]*lon?g?$",                                       "TYPE 3 LONG"),
    (r"^tipe[\s_-]*3[\s_-]*lon?g?$",                                  "TYPE 3 LONG"),
    (r"^type-3\s*lon?g?$",                                            "TYPE 3 LONG"),
    (r"^3\s*lon?g?$",                                                 "TYPE 3 LONG"),
    # TYPE 3 ambiguous (no short/long) → SHORT (conservative default)
    (r"^(type\s*[-#]?\s*3|type3|type-3|type#3)$",                    "TYPE 3 SHORT"),
]


def normalise_wire_type(raw: str):
    """Return canonical wire-type label or None if unrecognisable."""
    if not raw or raw.lower() == "nan":
        return None
    s = re.sub(r"\s+", " ", raw.strip().lower())
    for pattern, label in _WIRE_RULES:
        if re.match(pattern, s):
            return label
    return None


def normalise_machine(raw: str):
    """Return 'B21' / 'B24' / 'B25' / 'B27' or None."""
    if not raw:
        return None
    s = re.sub(r"[\s\-]+", "", raw.strip().upper())
    m = re.match(r"B(\d{2})", s)
    return "B" + m.group(1) if m else None


# ── CSV parsing ───────────────────────────────────────────────────────────────

def load_data(csv_path: str) -> pd.DataFrame:
    """
    Read all lines, skip the first SKIP_ROWS, parse each remaining line as
    a standard comma-separated row (values may be quoted), extract the five
    columns we need, filter, normalise, deduplicate, and return a clean DataFrame.
    """
    print(f"[1/4] Loading {csv_path} ...")
    with open(csv_path, encoding="utf-8", errors="replace") as fh:
        all_lines = fh.readlines()

    data_lines = all_lines[SKIP_ROWS:]
    print(f"      Total lines after skip: {len(data_lines)}")

    records = []
    for line in data_lines:
        line = line.strip()
        if not line:
            continue
        try:
            fields = list(csv.reader([line]))[0]
        except Exception:
            continue

        # guard against short rows
        if len(fields) <= max(COL_DATE, COL_MACHINE, COL_PRODUCT, COL_WTYPE, COL_PEAK):
            continue

        date_raw    = fields[COL_DATE].strip()
        machine_raw = fields[COL_MACHINE].strip()
        product_raw = fields[COL_PRODUCT].strip()
        wtype_raw   = fields[COL_WTYPE].strip()
        peak_raw    = fields[COL_PEAK].strip()

        records.append({
            "date_raw":    date_raw,
            "machine_raw": machine_raw,
            "product_raw": product_raw,
            "wtype_raw":   wtype_raw,
            "peak_raw":    peak_raw,
        })

    print(f"      Parsed rows: {len(records)}")

    df = pd.DataFrame(records)

    # ── filter product ──────────────────────────────────────────────────────
    df = df[df["product_raw"].str.upper().str.strip() == TARGET_PRODUCT].copy()
    print(f"      After product filter ({TARGET_PRODUCT}): {len(df)}")

    # ── normalise machine ───────────────────────────────────────────────────
    df["Machine"] = df["machine_raw"].apply(normalise_machine)
    df = df[df["Machine"].isin(TARGET_MACHINES)].copy()
    print(f"      After machine filter {sorted(TARGET_MACHINES)}: {len(df)}")

    # ── normalise wire type ─────────────────────────────────────────────────
    df["Wire_Type"] = df["wtype_raw"].apply(normalise_wire_type)
    df = df[df["Wire_Type"].notna()].copy()
    print(f"      After wire-type normalisation: {len(df)}")

    # ── parse date & peak force ─────────────────────────────────────────────
    df["Date"]       = pd.to_datetime(df["date_raw"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["Peak_Force"] = pd.to_numeric(df["peak_raw"], errors="coerce")
    df = df[df["Date"].notna() & df["Peak_Force"].notna() & (df["Peak_Force"] > 0)].copy()

    # ── deduplicate: keep LAST row per (Date, Machine, Wire_Type) ───────────
    df = df.drop_duplicates(subset=["Date", "Machine", "Wire_Type"], keep="last")
    print(f"      After deduplication (keep last): {len(df)}")

    # ── summary ─────────────────────────────────────────────────────────────
    print()
    for mid in sorted(TARGET_MACHINES):
        sub = df[df["Machine"] == mid]
        dates = sorted(sub["Date"].unique())
        print(f"      {mid}: {len(dates)} dates  "
              f"({dates[0] if dates else '—'} → {dates[-1] if dates else '—'})")

    return df[["Date", "Machine", "Wire_Type", "Peak_Force"]].sort_values(
        ["Machine", "Date", "Wire_Type"]
    ).reset_index(drop=True)


# ── pivot to JSON structure ───────────────────────────────────────────────────

_WIRE_KEY = {
    "TYPE 1":       "t1",
    "TYPE 2":       "t2",
    "TYPE 3 SHORT": "t3s",
    "TYPE 3 LONG":  "t3l",
}


def build_json(df: pd.DataFrame) -> dict:
    print("[3/4] Building JSON ...")
    result = {}

    for machine_id in sorted(TARGET_MACHINES):
        mdf = df[df["Machine"] == machine_id].copy()

        # pivot so each date is one row and columns are t1/t2/t3s/t3l
        mdf["wire_key"] = mdf["Wire_Type"].map(_WIRE_KEY)
        pivot = (
            mdf.groupby(["Date", "wire_key"])["Peak_Force"]
            .last()                           # keep last (already deduped, but safe)
            .unstack("wire_key")
            .reset_index()
            .sort_values("Date")
        )

        for col in ["t1", "t2", "t3s", "t3l"]:
            if col not in pivot.columns:
                pivot[col] = float("nan")

        # drop dates where ALL four types are missing
        pivot = pivot.dropna(subset=["t1", "t2", "t3s", "t3l"], how="all")

        def fmt(series):
            return [round(v, 2) if pd.notna(v) else None for v in series]

        dates  = list(pivot["Date"])
        num_id = machine_id.replace("B", "")

        result[num_id] = {
            "label":     f"{machine_id} Machine",
            "title":     machine_id,
            "date":      dates[-1] if dates else "—",
            "specLimit": SPEC_LIMIT,
            "excel":     f"data/BOND PULL DATA IGN2932M75 {machine_id} bonder.xlsx",
            "dates":     dates,
            "t1":        fmt(pivot["t1"]),
            "t2":        fmt(pivot["t2"]),
            "t3s":       fmt(pivot["t3s"]),
            "t3l":       fmt(pivot["t3l"]),
        }
        print(f"      {machine_id}: {len(dates)} date points, last={result[num_id]['date']}")

    return result


# ── write JSON ────────────────────────────────────────────────────────────────

def write_json(data: dict, out_path: str):
    print(f"[4/4] Writing {out_path} ...")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print("      Done.")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RoyceData.csv → machine-data.json"
    )
    parser.add_argument(
        "--csv", default="/home/integra/RoyceData.csv",
        help="Path to RoyceData.csv"
    )
    parser.add_argument(
        "--out", default="/var/www/integra-royce/dashboard/data/machine-data.json",
        help="Output JSON path"
    )
    args = parser.parse_args()

    print()
    df   = load_data(args.csv)
    print()
    print("[2/4] Loaded clean dataset — building JSON ...")
    data = build_json(df)
    write_json(data, args.out)

    print()
    print("Summary:")
    for mid, d in data.items():
        print(f"  B{mid}: {len(d['dates'])} dates, last={d['date']}")


if __name__ == "__main__":
    main()
