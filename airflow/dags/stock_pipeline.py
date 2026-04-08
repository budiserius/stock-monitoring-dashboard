from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
import functools

sys.path.append('/opt/airflow/scripts')
from etl_logic import ingest_bronze, transform_silver, log_task_execution

# Konfigurasi list ticker yang ingin dipantau
LIST_SAHAM = ['UNTR.JK', 'MTDL.JK', 'ASII.JK', 'BBCA.JK', 'TLKM.JK']

def task_logger(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        dag_id = kwargs.get('dag').dag_id
        task_id = kwargs.get('task').task_id
        run_id = kwargs.get('run_id')
        execution_date = kwargs.get('logical_date')
        
        start_time = datetime.now()
        try:
            # Teruskan semua kwargs ke fungsi asli
            rows_affected = func(**kwargs) 
            end_time = datetime.now()
            log_task_execution(dag_id, task_id, run_id, execution_date, start_time, end_time, 'SUCCESS', rows_processed=rows_affected)
            return rows_affected
        except Exception as e:
            end_time = datetime.now()
            log_task_execution(dag_id, task_id, run_id, execution_date, start_time, end_time, 'FAILED', error_message=str(e))
            raise e
    return wrapper

@task_logger
def run_ingest_bronze(ticker, **kwargs):
    # Sekarang menerima argumen 'ticker' langsung dari loop
    ingest_bronze(ticker)
    return 1

@task_logger
def run_transform_silver(**kwargs):
    return transform_silver()

@task_logger
def refresh_gold(**kwargs):
    from sqlalchemy import create_engine, text
    engine = create_engine("postgresql+psycopg2://postgres:12345678@host.docker.internal:5432/de-stocks")
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW gold.mvw_daily_stock_trends"))
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
    catchup=False
) as dag:

    # 1. Task Transform dan Refresh (tetap satu task untuk memproses semua data di antrian)
    t_silver = PythonOperator(
        task_id='transform_to_silver',
        python_callable=run_transform_silver
    )

    t_gold = PythonOperator(
        task_id='refresh_gold_layer',
        python_callable=refresh_gold
    )

    # 2. Looping Ingestion untuk setiap ticker
    for ticker in LIST_SAHAM:
        # Buat task ID unik per ticker, misal: ingest_UNTR_JK
        clean_id = ticker.replace('.', '_')
        
        t_ingest = PythonOperator(
            task_id=f'ingest_bronze_{clean_id}',
            python_callable=run_ingest_bronze,
            op_kwargs={'ticker': ticker} # Kirim ticker spesifik ke fungsi
        )

        # Set dependency: Tiap task ingest harus selesai sebelum masuk ke Silver
        t_ingest >> t_silver

    # Terakhir, Silver harus selesai sebelum Refresh Gold
    t_silver >> t_gold