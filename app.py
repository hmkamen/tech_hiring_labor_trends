"""
Streamlit dashboard for Hannah Kamen's labor-economics piece:
"AI's Energy Constraint Is Showing Up in Tech Hiring".

This app loads only pre-aggregated summary CSVs from data/ — it never touches
the raw workforce-flows source files, so the dashboard is safe to publish.
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

# --- Color palette (matches the PDF / notebook) ---
COLOR_SHARE = "#90D5FF"         # Chart 1 line
COLOR_GROWTH_BAR = "#5BE19A"    # Chart 2 bars
COLOR_ENERGY = "#f59e0b"        # Chart 3 energy line (orange)
COLOR_NON_ENERGY = "#3b82f6"    # Chart 3 non-energy line (blue)
COLOR_INFLOW = "#22c55e"        # Chart 4 inflow bars (green)
COLOR_OUTFLOW = "#f07c93"       # Chart 4 outflow bars (pink)
TITLE_COLOR = "#111827"
SUBTITLE_COLOR = "#6b7280"
GRID_COLOR = "#e5e7eb"
AXIS_COLOR = "#374151"

# Energy keywords that get bolded in role labels.
ENERGY_KWRDS = ["renewable", "energy", "grid", "environmental", "environment"]


# ---------- Page setup ----------
st.set_page_config(
    page_title="AI's Energy Constraint Is Showing Up in Tech Hiring",
    page_icon="⚡",
    layout="wide",
)

# Trim default Streamlit padding so the app feels more like a newsletter.
st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1100px; }
      h1 { margin-bottom: 0.25rem; }
      h2 { margin-top: 2rem; }
      .meta { color: #6b7280; margin-top: 0.25rem; margin-bottom: 1.25rem; }
      .takeaway { margin-left: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Data loading ----------
@st.cache_data
def load_data():
    share = pd.read_csv(DATA_DIR / "energy_share_ts.csv", parse_dates=["month"])
    growth = pd.read_csv(DATA_DIR / "top_roles_growth.csv")
    churn = pd.read_csv(DATA_DIR / "churn_timeseries.csv", parse_dates=["month"])
    seniority = pd.read_csv(DATA_DIR / "seniority_churn.csv")
    return share, growth, churn, seniority


share_df, growth_df, churn_df, seniority_df = load_data()


# ---------- Chart builders ----------
def _apply_base_layout(fig: go.Figure, title: str, subtitle: str) -> None:
    fig.update_layout(
        title=dict(
            text=(
                f"<b style='color:{TITLE_COLOR};font-size:18px'>{title}</b><br>"
                f"<span style='color:{SUBTITLE_COLOR};font-size:13px'>{subtitle}</span>"
            ),
            x=0, xanchor="left", y=0.95, yanchor="top",
            font=dict(family="Helvetica, Arial, sans-serif"),
        ),
        margin=dict(l=60, r=40, t=90, b=50),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Helvetica, Arial, sans-serif", color=AXIS_COLOR),
        hoverlabel=dict(bgcolor="white", font_size=12),
        xaxis=dict(showgrid=False, showline=False, ticks="",
                   tickfont=dict(color=AXIS_COLOR)),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, showline=False,
                   ticks="", tickfont=dict(color=AXIS_COLOR), zeroline=False),
    )


def chart_energy_share(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["month"], y=df["energy_share_pct"],
        mode="lines",
        line=dict(color=COLOR_SHARE, width=2.8),
        hovertemplate="%{x|%b %Y}<br>%{y:.3f}%<extra></extra>",
        name="Energy share",
    ))
    _apply_base_layout(
        fig,
        "Energy related roles are a growing share of Big Tech's North American workforce",
        "energy role share of total headcount by month",
    )
    fig.update_yaxes(title=dict(text="Share of headcount (%)",
                                font=dict(color=AXIS_COLOR, size=12)),
                     ticksuffix="")
    fig.update_xaxes(dtick="M12", tickformat="%Y")
    fig.update_layout(height=440, showlegend=False)
    return fig


def _bold_energy_words(label: str) -> str:
    """Wrap any energy keyword inside <b>...</b> for plotly tick labels."""
    out = label
    for kw in ENERGY_KWRDS:
        idx = out.lower().find(kw.lower())
        while idx != -1:
            matched = out[idx:idx + len(kw)]
            out = out[:idx] + f"<b>{matched}</b>" + out[idx + len(kw):]
            idx = out.lower().find(kw.lower(), idx + len(f"<b>{matched}</b>"))
    return out


def chart_top_roles(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("pct_change", ascending=True)  # plotly bars go bottom-up
    labels = [_bold_energy_words(r) for r in df["role"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=df["pct_change"],
        orientation="h",
        marker=dict(color=COLOR_GROWTH_BAR),
        text=[f"{v:+.1f}%" for v in df["pct_change"]],
        textposition="outside",
        textfont=dict(color=TITLE_COLOR, size=12),
        hovertemplate="%{y}<br>%{x:+.2f}%<extra></extra>",
    ))
    _apply_base_layout(
        fig,
        "Environmental/energy engineers comprise the fastest growing North American roles",
        "Percent change in headcount by role, Jan 2023 → Aug 2025",
    )
    fig.update_xaxes(
        range=[0, df["pct_change"].max() * 1.22],
        showgrid=True, gridcolor=GRID_COLOR,
    )
    fig.update_yaxes(showgrid=False, tickfont=dict(size=12, color=TITLE_COLOR))
    fig.update_layout(height=500, bargap=0.3, showlegend=False)
    return fig


def chart_churn_timeseries(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for group, color in [("Energy roles", COLOR_ENERGY),
                         ("Non-energy roles", COLOR_NON_ENERGY)]:
        sub = df[df["group"] == group].sort_values("month")
        fig.add_trace(go.Scatter(
            x=sub["month"], y=sub["churn_12m"],
            mode="lines",
            name=group,
            line=dict(color=color, width=3),
            hovertemplate="%{x|%b %Y}<br>%{y:.1%}<extra></extra>",
        ))
    _apply_base_layout(
        fig,
        "Churn in energy roles surpasses other growth roles in 2025",
        "12-month rolling churn within top-7 fastest-growing tech roles",
    )
    fig.update_yaxes(title=dict(text="12-month proportion churn (outflows / avg headcount)",
                                font=dict(color=TITLE_COLOR, size=12)),
                     tickformat=".2f")
    fig.update_xaxes(dtick="M6", tickformat="%b %Y")
    fig.update_layout(
        height=460,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0)", bordercolor="rgba(0,0,0,0)"),
    )
    return fig


def chart_seniority_churn(df: pd.DataFrame) -> go.Figure:
    order = ["Entry", "Mid", "Senior"]
    df = df.set_index("seniority_3").loc[order].reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["seniority_3"], y=df["inflow_rate_pct"],
        name="Cumulative inflow rate",
        marker=dict(color=COLOR_INFLOW),
        text=[f"{v:.1f}%" for v in df["inflow_rate_pct"]],
        textposition="outside",
        hovertemplate="%{x} – inflow<br>%{y:.1f}% of avg headcount<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["seniority_3"], y=df["outflow_rate_pct"],
        name="Cumulative outflow rate",
        marker=dict(color=COLOR_OUTFLOW),
        text=[f"{v:.1f}%" for v in df["outflow_rate_pct"]],
        textposition="outside",
        hovertemplate="%{x} – outflow<br>%{y:.1f}% of avg headcount<extra></extra>",
    ))
    _apply_base_layout(
        fig,
        "Churn intensity is the highest in senior roles",
        "Cumulative inflows/outflows from Feb 2023 to Aug 2025 scaled by "
        "average headcount over the same period",
    )
    fig.update_yaxes(
        title=dict(text="Cumulative flows (% of average headcount over period)",
                   font=dict(color=TITLE_COLOR, size=12)),
        ticksuffix="",
    )
    fig.update_layout(
        barmode="group", bargap=0.25, bargroupgap=0.05, height=480,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0)", bordercolor="rgba(0,0,0,0)"),
    )
    return fig


# ---------- Page content ----------
st.title("Tech: AI's Energy Constraint Is Showing Up in Tech Hiring")
st.markdown(
    "<div class='meta'>Hannah Kamen &middot; Labor-economics portfolio piece "
    "&middot; February 3, 2026</div>",
    unsafe_allow_html=True,
)

st.subheader("Key Takeaways")
st.markdown(
    """
- Energy and environment coded roles are a larger slice of Big Tech's North
  American workforce than they were a decade ago, rising from about **0.08%**
  in 2016 to about **0.15%** by August 2025, with the greatest increase
  occurring after 2020.
- From January 2023 to August 2025, **Environmental Engineer (+34.6%)** and
  **Renewable Energy Engineer (+23.3%)** represented the two fastest growing
  roles by headcount, ahead of several research and clinical roles.
- This growth is not purely additive. Energy roles show higher churn in 2025
  and the highest flow intensity is concentrated in **senior roles**, consistent
  with active reshuffling in addition to expansion.
""",
)

st.markdown(
    """
As large tech firms invest [enormous sums into data centers across the US](https://www.reuters.com/business/energy/us-data-center-power-use-could-triple-by-2028-doe-backed-report-says-2024-12-20/),
the hiring of talent who can help secure their success has followed suit. Data
centers are large physical facilities whose implementation relies on grid
interconnections, water and cooling systems, and lengthy environmental
permitting processes, skills historically housed in other industries. At the
same time, the sector has been moving through a post-boom labor reset, with
major layoffs beginning in mid 2022 and continuing through much of 2023. The
result is a natural question: as tech firms rebalance their workforces, which
roles are expanding to support new infrastructure bottlenecks?

Workforce-flows data shows that energy and environment coded
roles are becoming a larger share of Big Tech's North American workforce,
[even as overall tech employment has been under pressure](https://layoffs.fyi/).
Energy related roles, defined here using role title keywords (for example
*energy, renewable, environment, grid*), rose from roughly **0.08%** of total
headcount in 2016 to about **0.15%** by August 2025, with the slope of the
increase steepening after 2021, and continuing through the major layoff period
that occurred after.
"""
)

st.plotly_chart(chart_energy_share(share_df), width="stretch")

st.markdown(
    """
Zooming into the most recent cycle using granular role breakdowns reveals the
source of this increase. Between January 2023 and August 2025, **Environmental
Engineer (+34.6%)** and **Renewable Energy Engineer (+23.3%)** led headcount
growth relative to January 2023 among the seven fastest growing roles in Big
Tech's North American workforce, with Environmental Engineer hiring leading
role growth across firms in North America by a landslide. This pattern is
consistent with a world where big tech firms' constraints are increasingly
physical: site selection, environmental permitting, power procurement, grid
interconnection, and reliability planning. [Recent reporting](https://www.nerc.com/pa/RAPA/ra/Reliability%20Assessments%20DL/NERC_LTRA_2024.pdf)
from grid and energy institutions underscores that data centers and other large
loads are becoming a central planning challenge, with rapid load growth and
reliability concerns increasingly tied to data center expansion.
"""
)

st.plotly_chart(chart_top_roles(growth_df), width="stretch")

st.markdown(
    """
However, employee inflow and outflow data by role suggests that the growth
story has not simply been "hire and retain." Within the same top seven fastest
growing roles, 12 month rolling churn rises above peers for energy and
environmental roles in 2025. By mid 2025, energy role churn reaches **22%**
(outflows relative to average headcount), while the remaining fast growth
roles sit closer to **18%**. In other words, the energy roles are expanding,
but they are also turning over more quickly than other high growth roles. That
combination is consistent with a market where talent is both in demand and
being reallocated frequently, whether due to competition across firms,
project-based ramp ups, or internal reorganization. This pattern suggests that
hiring is not the only margin tech firms are adjusting that is impacting worker
movement in these roles.
"""
)

st.plotly_chart(chart_churn_timeseries(churn_df), width="stretch")

st.markdown(
    """
Digging into churn intensity across seniority levels and within energy and
environmental roles reveals that reallocations are happening most frequently at
the highest levels within companies. Scaling cumulative worker flows by average
headcount over the same period (Feb 2023 to Aug 2025), reveals that senior
roles show the highest churn intensity: cumulative inflows are **85.7%** of
average headcount and cumulative outflows are about **63.9%**. Entry and
mid-level churn levels are also high, but substantially lower for both.
"""
)

st.plotly_chart(chart_seniority_churn(seniority_df), width="stretch")

st.markdown(
    """
Taken together, this Workforce Dynamics analysis points to expansion in
physical infrastructure capabilities as well as retooling at the top. Big Tech
appears to be rebuilding energy and environment capability while simultaneously
cycling through senior leadership and specialist layers, a pattern that may
reflect a sector trying to operationalize very large infrastructure bets under
tight physical and regulatory constraints.
"""
)

# ---------- Footer ----------
st.divider()
st.markdown(
    """
<div style='color:#6b7280; font-size:0.85rem; line-height:1.5'>
<b>Data &amp; methodology.</b> Source data is a proprietary role-level
workforce-flows dataset shared with the author for a hiring assignment in
February 2026. To keep the provider's licensed raw data off of public
infrastructure, this repo ships only small <em>pre-aggregated</em> summary
files — the exact numbers driving the four charts above — under
<code>data/</code>. Re-running <code>preprocess.py</code> against the original
raw CSVs reproduces these aggregates. See README for details.<br><br>
<b>About.</b> Built by Hannah Kamen as part of a portfolio of applied labor
economics work. Original piece: <em>"AI's Energy Constraint Is Showing Up
in Tech Hiring."</em>
</div>
""",
    unsafe_allow_html=True,
)
