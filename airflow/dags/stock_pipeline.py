from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
import functools
import logging

sys.path.append('/opt/airflow/scripts')
from etl_logic import ingest_bronze, transform_silver, log_task_execution, engine

LIST_SAHAM = ['UNTR.JK', 'MTDL.JK', 'ASII.JK', 'BBCA.JK', 'TLKM.JK']
logger = logging.getLogger("airflow.task")

def task_logger(func):
    @functools.wraps(func)
    def wrapper(**kwargs):
        dag_id = kwargs['dag'].dag_id
        task_id = kwargs['task'].task_id
        run_id = kwargs['run_id']
        logical_date = kwargs['logical_date']
        
        start_time = datetime.now()
        try:
            result = func(**kwargs)
            log_task_execution(dag_id, task_id, run_id, logical_date, start_time, datetime.now(), 'SUCCESS', result)
            return result
        except Exception as e:
            log_task_execution(dag_id, task_id, run_id, logical_date, start_time, datetime.now(), 'FAILED', error_message=str(e))
            raise e
    return wrapper

@task_logger
def run_ingest_bronze(ticker, **kwargs):
    ingest_bronze(ticker)
    return 1

@task_logger
def run_transform_silver(**kwargs):
    return transform_silver()

@task_logger
def refresh_gold(**kwargs):
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mvw_daily_stock_trends"))
    return 1

default_args = {
    'owner': 'budi',
    'start_date': datetime(2026, 4, 7),
    'retries': 1
}

with DAG(
    'idx_medallion_pipeline',
    default_args=default_args,
    schedule_interval='0 17 * * 1-5',
    catchup=False,
    max_active_runs=1
) as dag:

    t_silver = PythonOperator(
        task_id='transform_to_silver',
        python_callable=run_transform_silver
    )

    t_gold = PythonOperator(
        task_id='refresh_gold_layer',
        python_callable=refresh_gold
    )

    for ticker in LIST_SAHAM:
        t_ingest = PythonOperator(
            task_id=f'ingest_bronze_{ticker.replace(".", "_")}',
            python_callable=run_ingest_bronze,
            op_kwargs={'ticker': ticker}
        )
        t_ingest >> t_silver

    t_silver >> t_gold