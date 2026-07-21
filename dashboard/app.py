"""
app.py

Streamlit dashboard for the econ-pipeline project. Reads from the
dbt-built fct_fred_indicators table in DuckDB and displays trend
charts, rolling averages, and period-over-period change for each
economic indicator.

Run from the project root:
    streamlit run dashboard/app.py
"""

import os

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "econ_pipeline.duckdb")

SERIES_LABELS = {
    "FEDFUNDS": "Federal Funds Effective Rate",
    "CPIAUCSL": "Consumer Price Index (All Urban Consumers)",
    "UNRATE": "Unemployment Rate",
}

st.set_page_config(page_title="Economic Indicators Dashboard", layout="wide")

@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("SELECT * FROM fct_fred_indicators ORDER BY series_id, observation_date").df()
    con.close()
    return df

st.title("Economic Indicators Dashboard")
st.caption("Data sourced from FRED, orchestrated with Airflow, transformed with dbt.")

try:
    data = load_data()
except Exception as e:
    st.error(f"Couldn't load data from DuckDB: {e}")
    st.info("Make sure the pipeline has run at lease once (via Airflow or `python extract/fetch_fred_data.py` + `dbt run`)")
    st.stop()

available_series = data["series_id"].unique().tolist()

selected_series = st.sidebar.selectbox(
    "Select an indicator",
    options=available_series,
    format_func=lambda s: SERIES_LABELS.get(s, s),
)

series_data = data[data["series_id"] == selected_series].copy()
series_data = series_data.sort_values("observation_date")

latest = series_data.iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("Latest value", f"{latest['value']:.2f}")
col2.metric(
    "Change vs. prior period",
    f"{latest['period_change']:.2f}" if pd.notna(latest["period_change"]) else "N/A",
)
col3.metric("As of", str(latest["observation_date"].date()))

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=series_data["observation_date"],
    y=series_data["value"],
    mode="lines",
    name="Value",
))
fig.add_trace(go.Scatter(
    x=series_data["observation_date"],
    y=series_data["rolling_3_period_avg"],
    mode="lines",
    name="3-period rolling avg",
    line=dict(dash="dash"),
))
fig.update_layout(
    title=SERIES_LABELS.get(selected_series, selected_series),
    xaxis_title="Date",
    yaxis_title="Value",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Period-over-period change")
change_fig = go.Figure()
change_fig.add_trace(go.Bar(
    x=series_data["observation_date"],
    y=series_data["period_change"],
    name="Change",
))
change_fig.update_layout(xaxis_title="Date", yaxis_title="Change")
st.plotly_chart(change_fig, use_container_width=True)

with st.expander("View raw data"):
    st.dataframe(series_data, use_container_width=True)