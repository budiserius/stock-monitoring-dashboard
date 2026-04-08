import yfinance as yf
import pandas as pd
import json
import psycopg2
import logging
from sqlalchemy import create_engine, text

# Konfigurasi Logging agar muncul di Airflow Task Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg2://postgres:12345678@host.docker.internal:5432/de-stocks"

def get_connection():
    return psycopg2.connect("host=host.docker.internal dbname=de-stocks user=postgres password=12345678")

def ingest_bronze(ticker):
    logger.info(f"🚀 Starting ingestion for ticker: {ticker}")
    
    data = yf.download(ticker, period="1d", interval="1m", auto_adjust=True)
    if data.empty:
        logger.warning(f"⚠️ No data found for {ticker} from yfinance.")
        return
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    df_to_save = data.reset_index()
    df_to_save['Ticker'] = ticker
    
    json_data = df_to_save.to_json(date_format='iso', orient='records')
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO bronze.stock_prices (ticker, raw_data) VALUES (%s, %s)", (ticker, json_data))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"✅ Successfully ingested {len(df_to_save)} rows into Bronze for {ticker}")

def transform_silver():
    logger.info("Starting Silver transformation...")
    engine = create_engine(DB_URL)
    df_raw = pd.read_sql("SELECT id, ticker as bronze_ticker, raw_data FROM bronze.stock_prices WHERE is_processed = FALSE", engine)
    
    if df_raw.empty:
        logger.info("Nothin to process. All Bronze records are already processed.")
        return 0

    logger.info(f"Found {len(df_raw)} records in Bronze to process.")
    rows_counter = 0
    
    for _, row in df_raw.iterrows():
        raw_json = row['raw_data']
        bronze_id = row['id']
        ticker_name = row['bronze_ticker']
        
        logger.info(f"Processing Bronze ID: {bronze_id} ({ticker_name})")
        
        try:
            data_list = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
            df = pd.DataFrame(data_list)
            
            if df.empty:
                logger.warning(f"Empty JSON data for Bronze ID: {bronze_id}")
                continue

            df.columns = [str(c).title() for c in df.columns] 
            df_silver = pd.DataFrame()
            
            df_silver['ticker'] = df['Ticker'] if 'Ticker' in df.columns else ticker_name
            
            time_col = next((c for c in df.columns if c in ['Datetime', 'Date', 'Timestamp', 'Index']), None)
            if time_col:
                df_silver['price_timestamp'] = pd.to_datetime(df[time_col])
            else:
                df_silver['price_timestamp'] = pd.to_datetime(df.index)

            cols_map = {
                'Open': 'open_price', 'High': 'high_price', 'Low': 'low_price',
                'Close': 'close_price', 'Volume': 'volume', 
                'Dividends': 'dividends', 'Stock Splits': 'stock_splits'
            }

            for yf_col, db_col in cols_map.items():
                if yf_col in df.columns:
                    series = pd.to_numeric(df[yf_col], errors='coerce').fillna(0)
                    df_silver[db_col] = series if db_col in ['dividends', 'stock_splits'] else series.astype(int)
                else:
                    df_silver[db_col] = 0.0 if db_col in ['dividends', 'stock_splits'] else 0

            df_silver = df_silver.dropna(subset=['ticker', 'price_timestamp'])
            
            if not df_silver.empty:
                df_silver.to_sql('stg_silver', engine, schema='silver', if_exists='replace', index=False)
                
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO silver.stock_prices 
                        (ticker, price_timestamp, open_price, high_price, low_price, close_price, volume, dividends, stock_splits)
                        SELECT ticker, price_timestamp, open_price, high_price, low_price, close_price, volume, dividends, stock_splits 
                        FROM silver.stg_silver
                        ON CONFLICT (ticker, price_timestamp) DO UPDATE SET
                        close_price = EXCLUDED.close_price, 
                        volume = EXCLUDED.volume;
                    """))
                    conn.execute(text("UPDATE bronze.stock_prices SET is_processed = TRUE WHERE id = :id"), {"id": bronze_id})
                
                rows_counter += len(df_silver)
                logger.info(f"✨ Successfully transformed {len(df_silver)} rows for {ticker_name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing Bronze ID {bronze_id}: {str(e)}")
            continue
            
    logger.info(f"Transformation complete. Total rows moved to Silver: {rows_counter}")
    return rows_counter

def log_task_execution(dag_id, task_id, run_id, execution_date, start_time, end_time, status, rows_processed=0, error_message=None):
    logger.info(f"Logging task execution: {task_id} with status {status}")
    conn = get_connection()
    cur = conn.cursor()
    duration = (end_time - start_time).total_seconds()
    cur.execute("""
        INSERT INTO management.airflow_task_logs 
        (dag_id, task_id, run_id, execution_date, start_time, end_time, duration_seconds, status, rows_processed, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (dag_id, task_id, run_id, str(execution_date), start_time, end_time, duration, status, rows_processed, error_message))
    conn.commit()
    cur.close()
    conn.close()