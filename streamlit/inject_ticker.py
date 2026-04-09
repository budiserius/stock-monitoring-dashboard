import yfinance as yf
import pandas as pd
import json
import logging
from sqlalchemy import create_engine, text
from datetime import datetime

# --- KONFIGURASI ---
DB_URL = "postgresql+psycopg2://postgres:12345678@103.67.78.244:5432/stock_monitoring"
LIST_SAHAM = ['UNTR.JK', 'MTDL.JK', 'ASII.JK', 'BBCA.JK', 'TLKM.JK']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
engine = create_engine(DB_URL)

def run_full_import():
    for ticker in LIST_SAHAM:
        logger.info(f"--- Memulai Proses Historis untuk {ticker} ---")
        
        try:
            # 1. BRONZE STEP
            df_raw = yf.download(ticker, period="max", interval="1d", auto_adjust=True)
            if df_raw.empty:
                continue

            if isinstance(df_raw.columns, pd.MultiIndex):
                df_raw.columns = df_raw.columns.get_level_values(0)

            df_reset = df_raw.reset_index()
            df_reset['Ticker'] = ticker # Pastikan ticker masuk di sini
            
            json_payload = df_reset.to_json(date_format='iso', orient='records')
            
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO bronze.stock_prices (ticker, raw_data, is_processed, extracted_at) VALUES (:t, :d, FALSE, CURRENT_TIMESTAMP)"),
                    {"t": ticker, "d": json_payload}
                )
            logger.info(f"✅ Bronze: {ticker} saved.")

            # 2. SILVER STEP
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, raw_data FROM bronze.stock_prices WHERE ticker = :t AND is_processed = FALSE ORDER BY extracted_at DESC LIMIT 1"),
                    {"t": ticker}
                ).fetchone()

            if result:
                bronze_id, raw_data = result
                data_list = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                df = pd.DataFrame(data_list)
                df.columns = [str(c).title() for c in df.columns]
                
                df_silver = pd.DataFrame()
                
                # DETEKSI WAKTU
                time_col = next((c for c in df.columns if c in ['Date', 'Datetime', 'Timestamp']), 'Index')
                
                # RE-FIX: Pastikan ticker diisi untuk SETIAP baris
                df_silver['ticker'] = [ticker] * len(df) 
                df_silver['price_timestamp'] = pd.to_datetime(df[time_col])
                
                # MAPPING HARGA
                df_silver['open_price'] = pd.to_numeric(pd.Series(df.get('Open', 0)), errors='coerce').fillna(0).astype(float)
                df_silver['high_price'] = pd.to_numeric(pd.Series(df.get('High', 0)), errors='coerce').fillna(0).astype(float)
                df_silver['low_price'] = pd.to_numeric(pd.Series(df.get('Low', 0)), errors='coerce').fillna(0).astype(float)
                df_silver['close_price'] = pd.to_numeric(pd.Series(df.get('Close', 0)), errors='coerce').fillna(0).astype(float)
                df_silver['volume'] = pd.to_numeric(pd.Series(df.get('Volume', 0)), errors='coerce').fillna(0).astype(int)
                
                # DIVIDENDS & SPLITS
                div_val = df.get('Dividends', df.get('Dividend', 0))
                split_val = df.get('Stock Splits', df.get('Stock_Splits', 0))
                df_silver['dividends'] = pd.to_numeric(pd.Series(div_val), errors='coerce').fillna(0).astype(float)
                df_silver['stock_splits'] = pd.to_numeric(pd.Series(split_val), errors='coerce').fillna(0).astype(float)

                # UPSERT
                df_silver.to_sql('stg_silver_temp', engine, schema='silver', if_exists='replace', index=False)

                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO silver.stock_prices 
                        (ticker, price_timestamp, open_price, high_price, low_price, close_price, volume, dividends, stock_splits)
                        SELECT ticker, price_timestamp, open_price, high_price, low_price, close_price, volume, dividends, stock_splits 
                        FROM silver.stg_silver_temp
                        ON CONFLICT (ticker, price_timestamp) DO UPDATE SET
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price, 
                            volume = EXCLUDED.volume,
                            dividends = EXCLUDED.dividends,
                            stock_splits = EXCLUDED.stock_splits;
                    """))
                    conn.execute(text("UPDATE bronze.stock_prices SET is_processed = TRUE WHERE id = :id"), {"id": bronze_id})
                
                logger.info(f"✨ Silver: {len(df_silver)} rows processed for {ticker}")

        except Exception as e:
            logger.error(f"❌ Error {ticker}: {str(e)}")

    # 3. GOLD STEP
    try:
        with engine.begin() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mvw_daily_stock_trends"))
        logger.info("🏆 Gold: Materialized View refreshed.")
    except Exception as e:
        logger.error(f"⚠️ Gold Refresh Failed: {e}")

if __name__ == "__main__":
    run_full_import()