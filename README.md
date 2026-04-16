# AI's Energy Constraint Is Showing Up in Tech Hiring

A Streamlit dashboard version of a labor-economics piece I wrote in
February 2026, reproducing the full written analysis and four charts that
show how Big Tech's North American workforce is shifting toward energy
and environmental roles as AI data-center buildout accelerates.

**Author:** Hannah Kamen · [hmkamen6@gmail.com](mailto:hmkamen6@gmail.com) · [github.com/hmkamen](https://github.com/hmkamen)

---

## What's in the dashboard

Four charts, reproduced from the original piece, with the full accompanying
narrative:

1. **Energy role share of Big Tech headcount (2016 – Aug 2025)** — a monthly
   time series showing the share rising from roughly 0.08% to 0.15%.
2. **Top 7 fastest-growing Big Tech roles, Jan 2023 → Aug 2025** — a horizontal
   bar chart where Environmental Engineer (+34.6%) and Renewable Energy
   Engineer (+23.3%) lead.
3. **12-month rolling churn, energy vs. other top-7 growth roles** — a line
   chart showing energy role churn overtaking peer growth roles in 2025.
4. **Cumulative in/outflow rates by seniority within energy roles** — a grouped
   bar chart showing senior-level reshuffling dominates.

## A note on data

The underlying source is a proprietary role-level workforce-flows dataset that
was shared with me in February 2026 for an analytical writing piece. To avoid
republishing a data provider's licensed raw data on public infrastructure,
**this repo only contains small pre-aggregated summary files** — the exact
chart-level numbers under `data/`. No raw, row-level, or company-level data is
committed.

If you have the original raw CSVs locally, `preprocess.py` regenerates those
aggregates from them.

## Project structure

```
.
├── app.py                    # Streamlit dashboard
├── preprocess.py             # Reproduces data/ from the raw workforce CSVs
├── data/                     # Pre-aggregated chart data (tiny; safe to commit)
│   ├── energy_share_ts.csv
│   ├── top_roles_growth.csv
│   ├── churn_timeseries.csv
│   └── seniority_churn.csv
├── requirements.txt
├── .gitignore                # Keeps any raw data folder out of git
└── README.md
```

## Run it locally

Requires Python 3.10+.

```bash
git clone https://github.com/hmkamen/tech_hiring_labor_trends.git
cd tech_hiring_labor_trends

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

The dashboard then opens at [http://localhost:8501](http://localhost:8501).

## Regenerating the aggregates

If you have access to the original raw data layout:

```
<raw_dir>/wf_dynam_role_breakdown/wf_dynam_role_breakdown_*_*_*.csv
```

run:

```bash
python preprocess.py --raw-dir /path/to/raw-data-folder --out-dir data
```

The script streams each CSV, filters to Northern America / the relevant time
windows, and accumulates only chart-level sums, so it runs in modest memory
even on the full ~10M-row dataset.

## Methodology in brief

- **Energy role** definition: `role_k150` title matches any of
  `renewable, energy, grid, environmental, environment` (case-insensitive).
- **Big Tech / Northern America scope**: region = "Northern America",
  `role_k50 != "unknown"`.
- **Headcount window for growth** (chart 2): Jan 2023 → Aug 2025 snapshots.
- **Churn** (chart 3): 12-month rolling sum of outflows divided by 12-month
  rolling mean headcount, within the top-7 fastest-growing roles.
- **Seniority churn** (chart 4): cumulative inflows/outflows for energy roles
  from Feb 2023 → Aug 2025, scaled by the window's average monthly headcount.

See `preprocess.py` for the exact aggregation code.

## License

Code is released under License. The underlying proprietary data is
**not** licensed for redistribution and is not included in this repository.
