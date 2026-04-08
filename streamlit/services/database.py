import psycopg2
from config.settings import DB_CONFIG
import streamlit as st

@st.cache_resource
def get_connection():
    return psycopg2.connect(**DB_CONFIG)