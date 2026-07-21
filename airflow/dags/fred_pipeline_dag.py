"""
fred_pipeline_dag.py

Orchestrates the FRED data extraction pipeline. Runs
extract/fetch_fred_data.py inside the Aireflow container on a daily
schedule.

The project root is mounted into the container as /opt/airflow/project
(see docker-compose.yaml), so the script and its output database are
both reachable from here.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "greg",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="fred_pipeline",
    description="Pull economic indicators from FRED into DuckDB",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["econ-pipeline"],
) as dag:

    fetch_fred_data = BashOperator(
        task_id="fetch_fred_data",
        bash_command="python /opt/airflow/project/extract/fetch_fred_data.py",
    )