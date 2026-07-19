"""
fetch_fred_data.py

Pulls economic time series from the FRED API and lands them as raw
data in local DuckDB database. This is the "extract" step of the
pipeline - no transformation happens here (that happends later using DBT).

Run standalone:
    python extract/fetch_fred_data.py

Requires a .env file in the project root with:
    FRED_API_KEY=your_key_here
"""

import os
import sys
import logging
from datetime import datetime, timezone

import requests
import pandas as pd
import duckdb
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

SERIES_IDS = {
    "FEDFUNDS": "Federal Funds Effective Rate",
    "CPIAUCSL": "Consumer Price Index (All Urban Consumers)",
    "UNRATE": "Unemployment Rate",
}

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "econ_pipeline.duckdb")
RAW_TABLE_NAME = "raw_fred_observations"

def get_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        logger.error("FRED_API_KEY not found. Check your .env file.")
        sys.exit(1)
    return api_key

def fetch_series(series_id: str, api_key: str) -> pd.DataFrame:
    """Fetch all overservations for a single FRED series."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }

    logger.info("Fetching series: %s", series_id)
    response = requests.get(FRED_BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    observations = response.json().get("observations", [])
    if not observations:
        logger.warning("No observations returned for %s", series_id)
        return pd.DataFrame()

    df = pd.DataFrame(observations)[["date", "value"]]
    df["series_id"] = series_id
    df["fetched_at"] = datetime.now(timezone.utc)

    # FRED uses "." for missing values - drop those rather than
    # silently casting them to NaN and letting bad rows through
    df = df[df["value"] != "."]
    df["value"] = df["value"].astype(float)
    df["date"] = pd.to_datetime(df["date"])

    return df[["series_id", "date", "value", "fetched_at"]]

def load_to_duckdb(df: pd.DataFrame) -> None:
    """Append fetched observations into the raw DuckDb table."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = duckdb.connect(DB_PATH)

    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {RAW_TABLE_NAME} (
            "series_id" VARCHAR,
            "observation_date" DATE,
            "value" DOUBLE,
            "fetched_at" TIMESTAMP
        )
    """)

    con.register("df_view", df)
    con.execute(f"INSERT INTO {RAW_TABLE_NAME} SELECT * FROM df_view")
    con.close()
    logger.info("Loaded %d rows into %s", len(df), RAW_TABLE_NAME)

def main():
    api_key = get_api_key()
    all_data = []

    for series_id in SERIES_IDS:
        try:
            df = fetch_series(series_id, api_key)
            if not df.empty:
                all_data.append(df)
        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch %s: %s", series_id, e)

    if not all_data:
        logger.warning("No data fetched - nothing to load.")
        return

    combined = pd.concat(all_data, ignore_index=True)
    load_to_duckdb(combined)

if __name__ == "__main__":
    main()