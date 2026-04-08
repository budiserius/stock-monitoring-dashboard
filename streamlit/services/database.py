import streamlit as st
from sqlalchemy import create_engine
import psycopg2

db_conf = st.secrets["connections"]["postgresql"]
DB_URL = f"{db_conf['dialect']}+{db_conf['driver']}://{db_conf['username']}:{db_conf['password']}@{db_conf['host']}:{db_conf['port']}/{db_conf['database']}"

# 1. Definisikan Engine (Untuk SQLAlchemy/Pandas)
# Ini yang dipanggil oleh from services.database import engine
engine = create_engine(
    DB_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)