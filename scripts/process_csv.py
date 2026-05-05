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
import csv as csvmod

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas --break-system-packages")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PRODUCT    = "IGN2932M75"
SPEC_LIMIT = 8
TARGET_MACHINES = {"B21", "B24", "B25", "B27"}

# ---------------------------------------------------------------------------
# Wire-type normalisation — all variants found in the CSV
# ---------------------------------------------------------------------------
TYPE_RULES = [
    # Type 1
    (r"^(type\s*[-#]?\s*1|type1|type\s*i|output-?1|input1|type\s*-\s*1|type\s*-\s*1)$", "t1"),
    # Type 2
    (r"^(type\s*[-#]?\s*2|type2|type\s*ii|output-?2|input2|type\s*-\s*2)$", "t2"),
    # Type 3 Short — many misspellings
    (r"^type[\s_-]*3[\s_-]*(s[hc]?o?r?t?|chort|schort|schot|shot)$", "t3s"),
    (r"^(type3\s*shor?t?|type3short|type3\s*chort)$", "t3s"),
    (r"^t[\s_]*3[\s_]*(shor?t?|chort|schort|ype3\s*shor?t?)$", "t3s"),
    (r"^tipe[\s_-]*3[\s_-]*shor?t?$", "t3s"),
    (r"^3\s*shor?t?$", "t3s"),
    # Type 3 Long
    (r"^type[\s_-]*3[\s_-]*(lon?g?|lng)$", "t3l"),
    (r"^(type3\s*lon?g?|type3long|type[\s_-]*3[\s_-]*long[\s_]*3)$", "t3l"),
    (r"^t[\s_]*3[\s_]*lon?g?$", "t3l"),
    (r"^tipe[\s_-]*3[\s_-]*lon?g?$", "t3l"),
    (r"^3\s*lon?g?$", "t3l"),
    # Loose numeric labels (old Layout-A records)
    (r"^2$", "t2"),
    (r"^1$", "t1"),
]


def normalise_wire_type(raw):
    if pd.isna(raw) or str(raw).strip().lower() in ("nan", ""):
        return None
    s = re.sub(r"\s+", " ", str(raw).strip().lower())
    for pattern, key in TYPE_RULES:
        if re.match(pattern, s):
            return key
    return None


def normalise_machine(raw):
    if pd.isna(raw):
        return None
    s = re.sub(r"[\s\-]+", "", str(raw).strip().upper())
    m = re.match(r"B(\d{2})", s)
    return "B" + m.group(1) if m else None


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def load_raw(csv_path):
    return pd.read_csv(csv_path, sep="\t", header=None, dtype=str)


def csv_split(line):
    yield list(csvmod.reader([line]))[0]


def safe_col(row, idx, default=""):
    try:
        v = str(row.iloc[idx]).strip()
        return v if v != "nan" else default
    except IndexError:
        return default


# ---------------------------------------------------------------------------
# Layout-A: rows with no Test ID (col-0 is NaN)
# col-3=date  col-5=Machine  col-6=Part  col-8=WireType
# ctrl in col-10 OR col-11    peak in col-18
# ---------------------------------------------------------------------------
def parse_layout_a(df_raw):
    records = []
    for _, row in df_raw.iterrows():
        if str(row.iloc[0]).strip() not in ("nan", ""):
            continue
        date_str = safe_col(row, 3)
        machine  = safe_col(row, 5)
        part     = safe_col(row, 6)
        wtype    = safe_col(row, 8)
        peak     = safe_col(row, 18)
        ctrl10   = safe_col(row, 10)
        ctrl11   = safe_col(row, 11)
        ctrl = ctrl10 if "CRTL" in ctrl10.upper() or ctrl10.upper() == "YES" else ctrl11

        if PRODUCT.upper() not in machine.upper() and PRODUCT.upper() not in part.upper():
            continue
        records.append({"date_str": date_str, "machine": machine, "part": part,
                         "wtype": wtype, "ctrl": ctrl, "peak": peak})

    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["date_str", "machine", "part", "wtype", "ctrl", "peak"])


# ---------------------------------------------------------------------------
# Layout-B: rows where col-0 is a numeric Test ID
#
# Two sub-layouts exist inside Layout-B:
#
#   Sub-layout B1 (most rows):
#     col-4=Machine  col-5=Part(product)  col-6=LotNo  col-7=WireType
#     col-10=ctrl    col-17=peak(rounded)
#
#   Sub-layout B2 (B24/B25 older rows — no lot number):
#     col-4=Machine  col-5=Part(product)  col-7=<empty>  col-8=WireType
#     col-10=ctrl    col-17=peak(rounded)
#
# We detect which sub-layout by checking whether col-7 looks like a wire type.
# If col-7 is empty/numeric and col-8 has content, use col-8.
#
# Comma-embedded rows (later exports) use col indices directly in the CSV string.
# ---------------------------------------------------------------------------
def parse_layout_b(df_raw):
    records = []

    for _, row in df_raw.iterrows():
        cell0 = str(row.iloc[0]).strip()

        # ---- comma-embedded full record ----
        if "," in cell0 and re.match(r"^\d+,", cell0):
            parts = next(iter(csv_split(cell0)))
            if len(parts) < 9:
                continue
            try:
                date_str = parts[3].strip().strip('"')
                machine  = parts[4].strip().strip('"')
                part     = parts[5].strip().strip('"')
                wtype    = parts[7].strip().strip('"')   # always col-7 in embedded format
                ctrl     = parts[10].strip().strip('"') if len(parts) > 10 else ""
                peak     = parts[17].strip().strip('"') if len(parts) > 17 else ""
                if not peak:
                    peak = parts[14].strip().strip('"') if len(parts) > 14 else ""
            except (IndexError, ValueError):
                continue

        # ---- standard tab-separated row ----
        elif re.match(r"^\d+$", cell0):
            date_str = safe_col(row, 3)
            machine  = safe_col(row, 4)
            part     = safe_col(row, 5)
            ctrl     = safe_col(row, 10)
            peak     = safe_col(row, 17)
            if not peak:
                peak = safe_col(row, 18)

            # Detect wire-type column: col-7 if it looks like a type label,
            # otherwise col-8 (older B24/B25 format where col-6=LotNo is missing)
            col7 = safe_col(row, 7)
            col8 = safe_col(row, 8)
            # col-7 is the wire type when it contains alphabetic characters
            # (excludes pure numbers which are lot/sample numbers)
            if col7 and re.search(r"[a-zA-Z]", col7):
                wtype = col7
            elif col8 and re.search(r"[a-zA-Z]", col8):
                wtype = col8
            else:
                wtype = col7 or col8  # fallback
        else:
            continue

        records.append({"date_str": date_str, "machine": machine, "part": part,
                         "wtype": wtype, "ctrl": ctrl, "peak": peak})

    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["date_str", "machine", "part", "wtype", "ctrl", "peak"])


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_dataset(csv_path):
    print(f"[1/4] Loading {csv_path} ...")
    df_raw = load_raw(csv_path)

    print("[2/4] Parsing rows ...")
    dfA = parse_layout_a(df_raw)
    dfB = parse_layout_b(df_raw)
    print(f"      Layout-A rows: {len(dfA)}")
    print(f"      Layout-B rows: {len(dfB)}")

    df = pd.concat([dfA, dfB], ignore_index=True)

    # filter product
    product_up = PRODUCT.upper()
    mask = (
        df["machine"].str.upper().str.contains(product_up, na=False) |
        df["part"].str.upper().str.contains(product_up, na=False)
    )
    df = df[mask].copy()
    print(f"      Rows matching {PRODUCT}: {len(df)}")

    # filter ctrl chart flag
    df = df[
        df["ctrl"].str.upper().str.contains("CRTL", na=False) |
        df["ctrl"].str.upper().str.strip().eq("YES")
    ].copy()
    print(f"      Rows with CRTL/YES flag: {len(df)}")

    # resolve swapped machine/part (some rows have product in machine column)
    def resolve_machine(row):
        return row["part"] if PRODUCT.upper() in str(row["machine"]).upper() else row["machine"]

    df["machine_raw"] = df.apply(resolve_machine, axis=1)
    df["machine_id"]  = df["machine_raw"].apply(normalise_machine)
    df["wire_key"]    = df["wtype"].apply(normalise_wire_type)
    df["force"]       = pd.to_numeric(df["peak"], errors="coerce")
    df["date"]        = pd.to_datetime(df["date_str"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["machine_id", "wire_key", "force", "date"])
    df = df[df["machine_id"].isin(TARGET_MACHINES)]
    df = df[df["force"] > 0]
    print(f"      Clean rows: {len(df)} (dropped {before - len(df)})")
    print(f"      Per machine: {df.groupby('machine_id').size().to_dict()}")

    return df


def group_by_machine_date(df):
    print("[3/4] Grouping by machine + date ...")
    result = {}
    for machine_id in sorted(TARGET_MACHINES):
        mdf = df[df["machine_id"] == machine_id].copy()
        mdf["date_only"] = mdf["date"].dt.date

        pivot = (
            mdf.groupby(["date_only", "wire_key"])["force"]
            .mean()
            .unstack("wire_key")
            .reset_index()
            .sort_values("date_only")
        )

        for col in ["t1", "t2", "t3s", "t3l"]:
            if col not in pivot.columns:
                pivot[col] = float("nan")

        pivot = pivot.dropna(subset=["t1", "t2", "t3s", "t3l"], how="all")

        dates = [str(d) for d in pivot["date_only"]]
        t1    = [round(v, 2) if pd.notna(v) else None for v in pivot["t1"]]
        t2    = [round(v, 2) if pd.notna(v) else None for v in pivot["t2"]]
        t3s   = [round(v, 2) if pd.notna(v) else None for v in pivot["t3s"]]
        t3l   = [round(v, 2) if pd.notna(v) else None for v in pivot["t3l"]]

        num_id = machine_id.replace("B", "")
        result[num_id] = {
            "label":     machine_id + " Machine",
            "title":     machine_id,
            "date":      dates[-1] if dates else "—",
            "specLimit": SPEC_LIMIT,
            "excel":     f"data/BOND PULL DATA IGN2932M75 {machine_id} bonder.xlsx",
            "dates":     dates,
            "t1":        t1,
            "t2":        t2,
            "t3s":       t3s,
            "t3l":       t3l,
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
    parser.add_argument("--csv", default="/home/integra/RoyceData.csv")
    parser.add_argument("--out", default="/var/www/integra-royce/dashboard/data/machine-data.json")
    args = parser.parse_args()

    df   = build_dataset(args.csv)
    data = group_by_machine_date(df)
    write_json(data, args.out)
    print("\nSummary:")
    for mid, d in data.items():
        print(f"  B{mid}: {len(d['dates'])} dates, last={d['date']}")


if __name__ == "__main__":
    main()
