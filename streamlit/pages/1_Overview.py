import streamlit as st
from services.queries import get_gold_data, get_silver_data
from components.charts import intraday_price_chart
from components.kpi import render_kpi

# 1. Fetch Data
df = get_gold_data()

st.title("📊 Stock Dashboard")

if df.empty:
    st.info("Database is empty. Please run Airflow pipeline first.")
    st.stop()

# 2. Sidebar/Filter
ticker = st.selectbox("Choose Ticker", df["ticker"].unique())

# 3. Process Gold Data (KPI)
filtered_gold = df[df["ticker"] == ticker].sort_values("trade_date")

if filtered_gold.empty:
    st.warning(f"No gold data for {ticker}")
    st.stop()

# Ambil data terbaru dan sebelumnya untuk delta calculation
latest = filtered_gold.iloc[-1]
prev = filtered_gold.iloc[-2] if len(filtered_gold) > 1 else latest

# Render KPI Component
render_kpi(latest, prev)

st.divider()

# 4. Process Silver Data (Charts)
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader(f"📈 Price of {ticker}")
with col2:
    interval = st.radio(
        "Interval", ["1m", "5m", "1h", "1d", "1M"],
        horizontal=True, index=0
    )

silver_df = get_silver_data(ticker)

if silver_df.empty:
    st.warning(f"Intraday data for {ticker} is not available in Silver layer.")
else:
    intraday_price_chart(silver_df, interval)