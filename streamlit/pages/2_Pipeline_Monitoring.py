import streamlit as st
import pandas as pd
from services.queries import get_pipeline_logs

st.set_page_config(page_title="Pipeline Monitoring", page_icon="⚙️", layout="wide")

st.title("⚙️ Pipeline Monitoring")
st.write("Real-time monitoring for Medallion ETL Pipeline health.")

df_logs = get_pipeline_logs()

if df_logs.empty:
    st.info("No execution logs found. Please run the Airflow DAG first.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
total_runs = len(df_logs)
success_rate = (len(df_logs[df_logs['status'] == 'SUCCESS']) / total_runs) * 100

col1.metric("Total Executions", total_runs)
col2.metric("Success Rate", f"{success_rate:.1f}%")
col3.metric("Failed Tasks", len(df_logs[df_logs['status'] == 'FAILED']))
col4.metric("Avg Duration", f"{df_logs['duration_seconds'].mean():.2f}s")

st.divider()

status_filter = st.multiselect("Filter Status", options=["SUCCESS", "FAILED"], default=["SUCCESS", "FAILED"])
filtered_logs = df_logs[df_logs['status'].isin(status_filter)]

st.subheader("Recent Task Executions")

def color_status(val):
    color = '#28a745' if val == 'SUCCESS' else '#dc3545'
    return f'background-color: {color}; color: white; font-weight: bold; border-radius: 5px;'

st.dataframe(
    filtered_logs.style.map(color_status, subset=['status']),
    width='stretch',
    hide_index=True
)

failed_tasks = filtered_logs[filtered_logs['status'] == 'FAILED']
if not failed_tasks.empty:
    with st.expander("⚠️ View Error Details"):
        for _, row in failed_tasks.iterrows():
            st.error(f"**Task:** {row['task_id']} | **Time:** {row['start_time']}")
            st.code(row['error_message'], language='python')