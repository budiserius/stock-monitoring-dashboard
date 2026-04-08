import plotly.express as px
import streamlit as st
import pandas as pd

def price_chart(df):
    fig = px.line(
        df,
        x="trade_date",
        y=["close_daily", "sma_5_day", "sma_20_day"]
    )
    st.plotly_chart(fig, width='stretch')

def volume_chart(df):
    fig = px.bar(df, x="trade_date", y="total_volume_daily")
    st.plotly_chart(fig, width='stretch')

import plotly.graph_objects as go
import streamlit as st

def intraday_price_chart(df, interval="1m"):
    pdf = df.copy()
    pdf['price_timestamp'] = pd.to_datetime(pdf['price_timestamp'])
    pdf = pdf.set_index('price_timestamp')

    resample_map = {
        "1m": "1min",
        "5m": "5min",
        "1h": "1h",
        "1d": "1D",
        "1M": "1ME"
    }
    
    rule = resample_map.get(interval, "1min")

    resampled_df = pdf.resample(rule).agg({
        'open_price': 'first',
        'high_price': 'max',
        'low_price': 'min',
        'close_price': 'last',
        'volume': 'sum'
    }).dropna()

    fig = go.Figure(data=[go.Candlestick(
        x=resampled_df.index,
        open=resampled_df['open_price'],
        high=resampled_df['high_price'],
        low=resampled_df['low_price'],
        close=resampled_df['close_price'],
        name=interval
    )])

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=20, b=20),
        height=450
    )

    st.plotly_chart(fig, width='stretch')