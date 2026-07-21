"""
fred_pipeline_dag.py

Orchestrates the FRED data extraction and transformation pipeline.
Runs extract/fetch_fred_data.py, then runs dbt to transform the raw
data into analysis-ready marts - daily, inside the Aireflow container.

The project root is mounted into the container as /opt/airflow/project
(see docker-compose.yaml), so the script, dbt project, and output
database are all reachable from here.
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
    description="Pull economic indicators from FRED into DuckDB, transform with dbt",
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

    run_dbt = BashOperator(
        task_id="run_dbt",
        bash_command="cd /opt/airflow/project/econ_dbt && dbt run --profiles-dir .",
    )

    fetch_fred_data >> run_dbt