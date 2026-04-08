import streamlit as st

def safe_format(value, fmt="{:,.2f}", default="-"):
    try:
        if value is None:
            return default
        return fmt.format(value)
    except:
        return default

def render_kpi(latest, prev):
    # Baris Pertama: Harga Utama & Volume
    col1, col2, col3 = st.columns(3)

    close_latest = latest.get("close_daily")
    close_prev = prev.get("close_daily")

    # Hitung Delta Harga & Persentase manual untuk Metric
    delta_val = None
    delta_pct = None
    if close_latest and close_prev:
        delta_val = close_latest - close_prev
        delta_pct = (delta_val / close_prev) * 100

    col1.metric(
        label="Latest Close",
        value=f"Rp {safe_format(close_latest, '{:,.0f}')}",
        delta=f"{safe_format(delta_val, '{:,.0f}')} ({safe_format(delta_pct, '{:.2f}')}%)"
    )

    col2.metric(
        label="Daily High / Low",
        value=f"{safe_format(latest.get('high_daily'), '{:,.0f}')}",
        delta=f"Low: {safe_format(latest.get('low_daily'), '{:,.0f}')}",
        delta_color="off" # Warna netral untuk high/low
    )

    col3.metric(
        label="Total Volume",
        value=safe_format(latest.get("total_volume_daily"), "{:,.0f}")
    )

    st.markdown("---")
    
    # Baris Kedua: Trend Indicators (SMA)
    st.caption("🛠️ Trend Indicators (SMA)")
    c1, c2, c3 = st.columns(3)

    sma5 = latest.get("sma_5_day")
    sma20 = latest.get("sma_20_day")

    # Logic Sederhana untuk Trend
    trend = "Neutral"
    if sma5 and sma20:
        if sma5 > sma20:
            trend = "Bullish 📈"
        elif sma5 < sma20:
            trend = "Bearish 📉"

    c1.metric("SMA 5-Day", f"Rp {safe_format(sma5, '{:,.0f}')}")
    c2.metric("SMA 20-Day", f"Rp {safe_format(sma20, '{:,.0f}')}")
    c3.metric("Signal", trend)