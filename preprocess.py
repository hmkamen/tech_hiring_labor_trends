"""
Preprocess raw workforce-flows CSVs into small, aggregated chart-level files
that the Streamlit dashboard can load.

Only chart-level aggregates are emitted — no company-level or monthly raw rows
are written out. This keeps the repo safe to publish while preserving the
exact numbers behind the published analysis.

Inputs (expected layout; NOT committed to the repo):
    <raw_dir>/wf_dynam_role_breakdown/wf_dynam_role_breakdown_*_*_*.csv

Outputs (committed; tiny):
    data/energy_share_ts.csv
    data/top_roles_growth.csv
    data/churn_timeseries.csv
    data/seniority_churn.csv

The raw files total ~2GB / ~10M rows, so this script streams each file,
keeps only the columns and rows needed, and accumulates small per-chart totals
in memory instead of holding the whole dataset.
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

ENERGY_KWRDS = ["renewable", "energy", "grid", "environmental", "environment"]
ENERGY_PATTERN = re.compile(
    "|".join(re.escape(k) for k in ENERGY_KWRDS), flags=re.IGNORECASE
)
TOP7_ROLES = {
    "Environmental Engineer",
    "Renewable Energy Engineer",
    "Clinical Research Coordinator",
    "Research Scientist",
    "Research Scholar",
    "Construction Engineer",
    "Technician",
}
CHART1_START = pd.Timestamp("2016-01-01")
WINDOW_START = pd.Timestamp("2023-01-01")
WINDOW_END = pd.Timestamp("2025-08-01")
SENIORITY_BUCKETS = {
    1: "Entry", 2: "Entry",
    3: "Mid", 4: "Mid",
    5: "Senior", 6: "Senior", 7: "Senior",
}

USECOLS = [
    "region", "seniority", "role_k50", "role_k150",
    "month", "count", "inflow", "outflow",
    "external_inflow", "external_outflow",
]


def _is_energy_series(role_k150: pd.Series) -> pd.Series:
    """Return a 0/1 energy indicator based on role_k150 keyword match."""
    return (role_k150.astype(str).str.contains(ENERGY_PATTERN, na=False)).astype(int)


def _add(accum: dict, key: str, new: pd.Series) -> None:
    """Add a newly-computed groupby Series into the accumulator."""
    if accum.get(key) is None:
        accum[key] = new
    else:
        accum[key] = accum[key].add(new, fill_value=0)


def process_file(path: Path, accum: dict) -> None:
    """Load one WFD CSV, filter, and add its contributions to the accumulators."""
    df = pd.read_csv(path, usecols=USECOLS)

    # Standardize types.
    df["month"] = pd.to_datetime(df["month"])
    df["region_str"] = df["region"].astype(str).str.strip()
    df["role_k50"] = df["role_k50"].astype(str).str.strip()
    df["role_k50_lower"] = df["role_k50"].str.lower()
    for c in ("count", "inflow", "outflow", "external_inflow",
              "external_outflow", "seniority"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop any rows with nulls, matching the notebook's QA step.
    df = df.dropna(
        subset=["region_str", "seniority", "role_k50", "role_k150",
                "month", "count"]
    )

    df["energy"] = _is_energy_series(df["role_k150"])

    # Pick which outflow / inflow columns to use (mirrors notebook fallback).
    if df["external_outflow"].notna().any():
        df["_outflow"] = df["external_outflow"].fillna(0)
    else:
        df["_outflow"] = df["outflow"].fillna(0)
    if df["external_inflow"].notna().any():
        df["_inflow"] = df["external_inflow"].fillna(0)
    else:
        df["_inflow"] = df["inflow"].fillna(0)

    na = df[df["region_str"] == "Northern America"].copy()
    na_no_unknown = na[na["role_k50_lower"] != "unknown"]

    # Chart 1: monthly total HC & energy HC (Northern America, excl. unknown, from 2016).
    c1 = na_no_unknown[na_no_unknown["month"] >= CHART1_START]
    _add(accum, "c1_total", c1.groupby("month")["count"].sum())
    _add(accum, "c1_energy",
         c1[c1["energy"] == 1].groupby("month")["count"].sum())

    # Chart 2: HC by role_k50 for Jan 2023 and Aug 2025 snapshots.
    c2 = na_no_unknown[na_no_unknown["month"].isin([WINDOW_START, WINDOW_END])]
    _add(accum, "c2", c2.groupby(["month", "role_k50"])["count"].sum())

    # Chart 3: monthly HC + outflows for the top-7 growth roles in Northern America
    # between Jan 2023 and Aug 2025.
    c3 = na[na["role_k50"].isin(TOP7_ROLES) &
            (na["month"] >= WINDOW_START) &
            (na["month"] <= WINDOW_END)].copy()
    c3["group"] = np.where(c3["energy"] == 1, "Energy roles", "Non-energy roles")
    _add(accum, "c3_hc", c3.groupby(["month", "group"])["count"].sum())
    _add(accum, "c3_out", c3.groupby(["month", "group"])["_outflow"].sum())

    # Chart 4: energy roles only; monthly HC + inflows + outflows by seniority bucket.
    # Matches notebook scope: Northern America (inherits the chart-1 region filter).
    c4 = na[(na["energy"] == 1) &
            (na["month"] >= WINDOW_START) &
            (na["month"] <= WINDOW_END)].copy()
    c4["seniority_3"] = c4["seniority"].astype(int).map(SENIORITY_BUCKETS)
    c4 = c4.dropna(subset=["seniority_3"])
    _add(accum, "c4_hc", c4.groupby(["month", "seniority_3"])["count"].sum())
    _add(accum, "c4_in", c4.groupby(["month", "seniority_3"])["_inflow"].sum())
    _add(accum, "c4_out", c4.groupby(["month", "seniority_3"])["_outflow"].sum())


def build_chart1(accum: dict) -> pd.DataFrame:
    total = accum["c1_total"].rename("total_hc")
    energy = accum["c1_energy"].rename("energy_hc")
    m = pd.concat([total, energy], axis=1).fillna({"energy_hc": 0}).sort_index()
    m["energy_share_pct"] = np.where(
        m["total_hc"] > 0, 100 * m["energy_hc"] / m["total_hc"], np.nan
    )
    return (m.reset_index()
              .rename(columns={"index": "month"})
              [["month", "energy_share_pct"]])


def build_chart2(accum: dict) -> pd.DataFrame:
    c2 = accum["c2"].reset_index(name="count")
    p = c2.pivot(index="role_k50", columns="month", values="count").fillna(0)
    p = p[p[WINDOW_START] > 0]
    p["pct_change"] = 100 * (p[WINDOW_END] - p[WINDOW_START]) / p[WINDOW_START]
    top = p.sort_values("pct_change", ascending=False).head(7).reset_index()
    return top[["role_k50", "pct_change"]].rename(columns={"role_k50": "role"})


def build_chart3(accum: dict) -> pd.DataFrame:
    hc = accum["c3_hc"].rename("headcount")
    out = accum["c3_out"].rename("outflows")
    monthly = pd.concat([hc, out], axis=1).fillna(0).reset_index()

    # Fill the full (month, group) grid.
    all_months = pd.date_range(WINDOW_START, WINDOW_END, freq="MS")
    idx = pd.MultiIndex.from_product(
        [all_months, ["Energy roles", "Non-energy roles"]],
        names=["month", "group"],
    )
    monthly = (monthly.set_index(["month", "group"])
                      .reindex(idx, fill_value=0)
                      .reset_index()
                      .sort_values(["group", "month"]))

    monthly["out_12m"] = monthly.groupby("group")["outflows"].transform(
        lambda s: s.rolling(12, min_periods=12).sum()
    )
    monthly["hc_12m"] = monthly.groupby("group")["headcount"].transform(
        lambda s: s.rolling(12, min_periods=12).mean()
    )
    monthly["churn_12m"] = np.where(
        monthly["hc_12m"] > 0, monthly["out_12m"] / monthly["hc_12m"], np.nan
    )
    return (monthly[["month", "group", "churn_12m"]]
              .dropna(subset=["churn_12m"])
              .reset_index(drop=True))


def build_chart4(accum: dict) -> pd.DataFrame:
    hc = accum["c4_hc"].rename("hc")
    inflow = accum["c4_in"].rename("inflow")
    out = accum["c4_out"].rename("outflow")
    monthly = pd.concat([hc, inflow, out], axis=1).fillna(0).reset_index()

    order = ["Entry", "Mid", "Senior"]
    all_months = pd.date_range(WINDOW_START, WINDOW_END, freq="MS")
    idx = pd.MultiIndex.from_product(
        [all_months, order], names=["month", "seniority_3"]
    )
    monthly = (monthly.set_index(["month", "seniority_3"])
                      .reindex(idx, fill_value=0)
                      .reset_index())

    # Cumulative flows occur AFTER the baseline month; exposure is window average.
    flows = (monthly[(monthly["month"] > WINDOW_START) &
                     (monthly["month"] <= WINDOW_END)]
             .groupby("seniority_3", as_index=False)
             .agg(cum_in=("inflow", "sum"), cum_out=("outflow", "sum")))
    avg_hc = (monthly.groupby("seniority_3", as_index=False)["hc"]
              .mean().rename(columns={"hc": "avg_hc"}))

    tab = (pd.DataFrame({"seniority_3": order})
             .merge(flows, on="seniority_3", how="left")
             .merge(avg_hc, on="seniority_3", how="left"))
    tab["inflow_rate_pct"] = np.where(
        tab["avg_hc"] > 0, 100 * tab["cum_in"] / tab["avg_hc"], np.nan
    )
    tab["outflow_rate_pct"] = np.where(
        tab["avg_hc"] > 0, 100 * tab["cum_out"] / tab["avg_hc"], np.nan
    )
    return tab[["seniority_3", "inflow_rate_pct", "outflow_rate_pct"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        required=True,
        help="Directory containing wf_dynam_role_breakdown/",
    )
    parser.add_argument(
        "--out-dir",
        default="data",
        help="Directory to write aggregated CSVs (default: data/)",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted((raw_dir / "wf_dynam_role_breakdown").glob(
        "wf_dynam_role_breakdown_*_*_*.csv"
    ))
    if not files:
        raise FileNotFoundError(
            f"No wf_dynam_role_breakdown_*.csv files found under {raw_dir}"
        )

    accum: dict = {
        "c1_total": None, "c1_energy": None,
        "c2": None,
        "c3_hc": None, "c3_out": None,
        "c4_hc": None, "c4_in": None, "c4_out": None,
    }
    for i, f in enumerate(files, 1):
        print(f"  [{i:2d}/{len(files)}] {f.name}")
        process_file(f, accum)

    print("Building chart 1 (energy share time series) ...")
    build_chart1(accum).to_csv(out_dir / "energy_share_ts.csv", index=False)

    print("Building chart 2 (top 7 fastest growing roles) ...")
    build_chart2(accum).to_csv(out_dir / "top_roles_growth.csv", index=False)

    print("Building chart 3 (churn time series) ...")
    build_chart3(accum).to_csv(out_dir / "churn_timeseries.csv", index=False)

    print("Building chart 4 (churn by seniority) ...")
    build_chart4(accum).to_csv(out_dir / "seniority_churn.csv", index=False)

    print(f"Done. Aggregated outputs written to {out_dir}")


if __name__ == "__main__":
    main()
