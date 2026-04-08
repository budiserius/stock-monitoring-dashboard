from sqlalchemy import create_engine
import psycopg2

# URL Koneksi Database
DB_URL = "postgresql+psycopg2://postgres:12345678@localhost:5432/de-stocks"

# 1. Definisikan Engine (Untuk SQLAlchemy/Pandas)
# Ini yang dipanggil oleh from services.database import engine
engine = create_engine(
    DB_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

# 2. Fungsi get_connection (Optional, jika masih ada script lama yang butuh psycopg2 mentah)
def get_connection():
    return psycopg2.connect("host=host.docker.internal dbname=de-stocks user=postgres password=12345678")