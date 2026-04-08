import streamlit as st
from services.queries import get_gold_data

df = get_gold_data()

st.title("🚀 Top Movers")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Gainers")
    st.dataframe(df.sort_values("daily_return_pct", ascending=False).head(10))

with col2:
    st.subheader("Top Losers")
    st.dataframe(df.sort_values("daily_return_pct").head(10))