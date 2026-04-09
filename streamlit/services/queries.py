import pandas as pd
import streamlit as st
from sqlalchemy import text
from services.database import engine

@st.cache_data(ttl=60)
def get_gold_data():
    query = """
        SELECT ticker, trade_date, open_daily, high_daily, low_daily, 
               close_daily, total_volume_daily, sma_1_day, sma_5_day
        FROM gold.mvw_daily_stock_trends
        ORDER BY trade_date;
    """
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except Exception as e:
        st.error(f"Error Gold Layer: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_silver_data(ticker: str):
    query = """
        SELECT ticker, price_timestamp, open_price, close_price, 
               high_price, low_price, volume
        FROM silver.stock_prices
        WHERE ticker = :ticker
        ORDER BY price_timestamp;
    """
    try:
        with engine.connect() as conn:
            # Gunakan parameter mapping :ticker untuk keamanan
            df = pd.read_sql(text(query), conn, params={"ticker": ticker})
            
        if not df.empty:
            df["price_timestamp"] = pd.to_datetime(df["price_timestamp"], utc=True)
            df["price_timestamp"] = df["price_timestamp"].dt.tz_convert("Asia/Jakarta")
        return df
    except Exception as e:
        st.error(f"Error Silver Layer: {e}")
        return pd.DataFrame()
    
@st.cache_data(ttl=10)
def get_pipeline_logs():
    query = """
        SELECT 
            dag_id, 
            task_id, 
            status, 
            execution_date, 
            start_time, 
            end_time, 
            duration_seconds, 
            rows_processed, 
            error_message
        FROM management.airflow_task_logs
        ORDER BY start_time DESC
        LIMIT 100;
    """
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except Exception as e:
        st.error(f"Error Pipeline Logs: {e}")
        return pd.DataFrame()