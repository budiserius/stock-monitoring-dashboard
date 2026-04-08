import streamlit as st
from services.queries import get_gold_data

df = get_gold_data()

st.title("🔍 Stock Detail")

ticker = st.selectbox("Select Ticker", df["ticker"].unique())

filtered = df[df["ticker"] == ticker]

st.dataframe(filtered.sort_values("trade_date", ascending=False))