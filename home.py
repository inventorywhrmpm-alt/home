import streamlit as st

# 1. Konfigurasi Halaman (Harus di paling atas)
st.set_page_config(
    page_title="Dashboard Analytics",
    page_icon="📊",
    layout="wide"
)

# 2. Custom CSS untuk mempercantik font & warna
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        color: #1E1E1E;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #5E5E5E;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Header Area

# 4. Fitur Utama (Layout Kolom)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("### 📱 App")
    st.write("Visualisasi data interaktif menggunakan Plotly untuk insight yang lebih tajam.")
    # PERBAIKAN: Gunakan path file lokal, bukan URL website
    st.page_link("pages/app.py", label="Buka Aplikasi", icon="🔥")

with col2:
    st.warning("### 📈 Wyckoff")
    st.write("Analisis pergerakan market dengan metode Wyckoff secara otomatis.")
    st.page_link("pages/wyckoffstreamlit.py", label="Cek Strategi", icon="📊")

with col3:
    st.success("### 📥 Download")
    st.write("Ekspor hasil analisis kamu ke berbagai format seperti CSV atau Excel.")
    st.page_link("pages/downloadsaham.py", label="Ke Unduhan", icon="📁")

with col4:
    st.success("### 💡 AI Predict")
    st.write("analisis harga saham sesuai model yang telah di latih.")
    st.page_link("pages/app_streamlit.py", label="AI prediksi", icon="📈")
st.divider()
# 5. Fitur Utama (Layout Kolom)
col5, col6, col7, col8 = st.columns(4)
with col5:
    st.success("### 🚀 Predict MA")
    st.write("analisis harga saham Berdasrkan MA 5, 20, 50 dan 100 + RSI.")
    st.page_link("pages/prediksibyma.py", label="MA Predict", icon="📈")
st.divider()
# 5. Tambahkan Informasi Tambahan di Bawah
with st.expander("ℹ️ Tentang Sistem Ini"):
    st.write("""
        Dashboard ini dibangun menggunakan **Streamlit** dan **Python**. 
        Didesain &  Dibuat 💡 oleh Yonz Suharyono
    """)

# 6. Sidebar (Opsional: Tambahkan foto atau info)
st.sidebar.markdown("### 👤 User Profile")
st.sidebar.info("Selamat Datang, **Admin**!")
