import yfinance as yf
import pandas as pd
import json
import logging
from sqlalchemy import create_engine, text

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg2://postgres:12345678@host.docker.internal:5432/de-stocks"
engine = create_engine(DB_URL, pool_size=10, max_overflow=20)

def ingest_bronze(ticker):
    logger.info(f"🚀 Ingesting: {ticker}")
    try:
        data = yf.download(ticker, period="1d", interval="1m", auto_adjust=True)
        if data.empty:
            logger.warning(f"⚠️ No data for {ticker}")
            return

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        df = data.reset_index()
        df['Ticker'] = ticker
        json_data = df.to_json(date_format='iso', orient='records')
        
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO bronze.stock_prices (ticker, raw_data) VALUES (:t, :d)"),
                {"t": ticker, "d": json_data}
            )
        logger.info(f"✅ {ticker} Ingested: {len(df)} rows")
    except Exception as e:
        logger.error(f"❌ Ingest Error {ticker}: {e}")

def transform_silver():
    logger.info("🎬 Starting Silver Transformation")
    with engine.connect() as conn:
        df_raw = pd.read_sql("SELECT id, ticker, raw_data FROM bronze.stock_prices WHERE is_processed = FALSE", conn)
    
    if df_raw.empty:
        logger.info("☕ Nothing to process.")
        return 0

    rows_counter = 0
    cols_map = {
        'Open': 'open_price', 'High': 'high_price', 'Low': 'low_price',
        'Close': 'close_price', 'Volume': 'volume', 
        'Dividends': 'dividends', 'Stock Splits': 'stock_splits'
    }

    for _, row in df_raw.iterrows():
        try:
            data = row['raw_data']
            df = pd.DataFrame(json.loads(data) if isinstance(data, str) else data)
            if df.empty: continue

            df.columns = [str(c).title() for c in df.columns]
            df_silver = pd.DataFrame()
            
            # Metadata mapping
            df_silver['ticker'] = df.get('Ticker', row['ticker'])
            time_col = next((c for c in df.columns if c in ['Datetime', 'Date', 'Timestamp', 'Index']), None)
            df_silver['price_timestamp'] = pd.to_datetime(df[time_col] if time_col else df.index)

            # Metrics mapping
            for yf_col, db_col in cols_map.items():
                if yf_col in df.columns:
                    val = pd.to_numeric(df[yf_col], errors='coerce').fillna(0)
                    df_silver[db_col] = val if db_col in ['dividends', 'stock_splits'] else val.astype(int)
                else:
                    df_silver[db_col] = 0.0

            df_silver = df_silver.dropna(subset=['ticker', 'price_timestamp'])
            
            if not df_silver.empty:
                # Upsert Logic
                df_silver.to_sql('stg_silver', engine, schema='silver', if_exists='replace', index=False)
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO silver.stock_prices 
                        (ticker, price_timestamp, open_price, high_price, low_price, close_price, volume, dividends, stock_splits)
                        SELECT ticker, price_timestamp, open_price, high_price, low_price, close_price, volume, dividends, stock_splits 
                        FROM silver.stg_silver
                        ON CONFLICT (ticker, price_timestamp) DO UPDATE SET
                        close_price = EXCLUDED.close_price, volume = EXCLUDED.volume;
                    """))
                    conn.execute(text("UPDATE bronze.stock_prices SET is_processed = TRUE WHERE id = :id"), {"id": row['id']})
                
                rows_counter += len(df_silver)
                logger.info(f"✨ Processed {row['ticker']} (ID: {row['id']})")
        except Exception as e:
            logger.error(f"❌ Transform Error ID {row['id']}: {e}")

    return rows_counter

def log_task_execution(dag_id, task_id, run_id, execution_date, start_time, end_time, status, rows_processed=0, error_message=None):
    duration = (end_time - start_time).total_seconds()
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO management.airflow_task_logs 
                (dag_id, task_id, run_id, execution_date, start_time, end_time, duration_seconds, status, rows_processed, error_message)
                VALUES (:d, :t, :r, :ed, :st, :et, :dur, :s, :rp, :em)
            """), {
                "d": dag_id, "t": task_id, "r": run_id, "ed": str(execution_date),
                "st": start_time, "et": end_time, "dur": duration, "s": status,
                "rp": rows_processed, "em": error_message
            })
    except Exception as e:
        logger.error(f"❌ Logging Error: {e}")