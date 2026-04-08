import pandas as pd
from services.database import get_connection
import streamlit as st

@st.cache_data
def get_gold_data():
    conn = get_connection()
    query = """
        SELECT ticker, trade_date, open_daily, high_daily, low_daily, close_daily, total_volume_daily, sma_5_day, sma_20_day
        FROM gold.mvw_daily_stock_trends
        ORDER BY trade_date;
    """
    return pd.read_sql(query, conn)

@st.cache_data
def get_silver_data(ticker: str):
    conn = get_connection()
    query = """
        SELECT 
            ticker,
            price_timestamp,
            open_price,
            close_price,
            high_price,
            low_price,
            volume
        FROM silver.stock_prices
        WHERE ticker = %s
        ORDER BY price_timestamp;
    """
    df = pd.read_sql(query, conn, params=(ticker,))
    df["price_timestamp"] = pd.to_datetime(df["price_timestamp"], utc=True)
    df["price_timestamp"] = df["price_timestamp"].dt.tz_convert("Asia/Jakarta")
    return df