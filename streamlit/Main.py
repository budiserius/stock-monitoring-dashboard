import streamlit as st

# Konfigurasi Halaman (Opsional tapi bagus untuk portofolio)
st.set_page_config(
    page_title="Stock Monitoring Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Stock Monitoring Dashboard")
st.markdown("""
Aplikasi ini adalah platform **End-to-End Data Pipeline** yang dirancang untuk memonitoring pergerakan harga saham secara *real-time* (intraday). 
Data ditarik menggunakan API, diolah melalui arsitektur **Medallion (Bronze, Silver, Gold)**, dan divisualisasikan untuk membantu analisis teknikal.

**Saham yang dimonitor saat ini:**
* 🚗 **ASII.JK** (Astra International)
* 🏦 **BBCA.JK** (Bank Central Asia)
* 💻 **MTDL.JK** (Metrodata Electronics)
* 📞 **TLKM.JK** (Telkom Indonesia)
* 🚜 **UNTR.JK** (United Tractors)
""")

st.info("💡 **Navigasi:** Gunakan sidebar di sebelah kiri untuk berpindah antar halaman (Overview, Analytics, dll).")

with st.sidebar:
    st.divider()
    st.subheader("About")
    st.write("🚀 **Developer:** Muhammad Budi Setiawan")
    st.write("🛠️ **Stack:** Airflow, PostgreSQL, Docker, Streamlit")
    st.markdown("[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/mbudis23)")
    st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/muhammad-budi-setiawan)")
    st.caption("Developed as a Data Engineering Portfolio Project.")

st.divider()
st.caption("© 2026 IDX Medallion Pipeline | Muhammad Budi Setiawan")