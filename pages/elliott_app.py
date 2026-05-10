import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# Konfigurasi Halaman
st.set_page_config(page_title="IDX Elliott Wave Analyzer", layout="wide")

st.title("📈 IDX Elliott Wave Analyzer")
st.write("Analisis otomatis gelombang Elliott untuk saham IDX.")

# Input Ticker
ticker_input = st.text_input("Masukkan Kode Saham (contoh: BBCA, ASII, ANTM):", "BBCA").upper()
ticker = f"{ticker_input}.JK"

# Sidebar untuk parameter
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
order = st.sidebar.slider("Sensitivitas Wave (Semakin besar semakin selektif)", 5, 50, 15)

@st.cache_data
def load_data(symbol, period):
    # Mengambil data harga
    df = yf.download(symbol, period=period, interval="1d")
    # Menghapus MultiIndex pada kolom jika ada (versi yfinance terbaru)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

try:
    data = load_data(ticker, period)
    
    if data.empty:
        st.error("Data tidak ditemukan. Pastikan kode ticker benar.")
    else:
        # Cari titik ekstrim (puncak dan lembah)
        # Menggunakan harga Close
        close_prices = data['Close'].values
        
        ilocs_max = argrelextrema(close_prices, np.greater, order=order)[0]
        ilocs_min = argrelextrema(close_prices, np.less, order=order)[0]
        
        # Gabungkan titik puncak dan lembah
        extrema_indices = np.sort(np.concatenate((ilocs_max, ilocs_min)))
        extrema = data.iloc[extrema_indices].copy()
        
        # Ambil 5 titik terakhir
        if len(extrema) >= 5:
            last_5_waves = extrema.tail(5).copy()
            last_5_waves['Wave_Label'] = ['Wave 1', 'Wave 2', 'Wave 3', 'Wave 4', 'Wave 5']
            
            # --- FORMATTING HARGA (Hapus Nol di Belakang Koma) ---
            # Kita bulatkan ke integer untuk tampilan tabel
            display_table = last_5_waves[['Close']].copy()
            display_table['Harga'] = display_table['Close'].astype(int)
            
            st.subheader(f"Tabel Harga Elliott Wave - {ticker_input}")
            st.table(display_table[['Harga']].T) # Transpose agar hemat ruang

            # --- VISUALISASI ---
            fig = go.Figure()
            # Garis Harga Utama
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Harga', line=dict(color='lightgray', width=1)))
            # Garis Elliott Wave
            fig.add_trace(go.Scatter(x=last_5_waves.index, y=last_5_waves['Close'], 
                                     mode='lines+markers+text',
                                     name='Elliott Wave Path',
                                     text=last_5_waves['Wave_Label'],
                                     textposition="top center",
                                     line=dict(color='orange', width=3)))
            
            st.plotly_chart(fig, use_container_width=True)

            # --- LOGIKA KESIMPULAN ---
            prices = last_5_waves['Close'].values
            p1, p2, p3, p4, p5 = prices[0], prices[1], prices[2], prices[3], prices[4]
            
            st.subheader("📌 Kesimpulan Status & Proyeksi")
            
            # Aturan dasar Elliott: Wave 3 biasanya bukan yang terpendek 
            # dan Wave 4 tidak boleh masuk ke area Wave 1 (dalam teori dasar)
            is_bullish_impulse = (p3 > p1) and (p5 > p3) and (p4 > p2)
            
            if is_bullish_impulse:
                status = "🚀 FASE BULLISH IMPULSIF"
                detail = "Saham telah menyelesaikan atau sedang di ujung Wave 5."
                arah = "Akan menuju Fase Koreksi ABC (Penurunan Sementara)."
                color = "green"
            else:
                status = "📉 FASE KOREKTIF / CONSOLIDATION"
                detail = "Pola 5 gelombang naik tidak sempurna. Saat ini harga cenderung membentuk struktur ABC atau Sideways."
                arah = "Mencari titik support (Bottom) untuk membentuk siklus baru."
                color = "orange"

            st.markdown(f"**Status:** <span style='color:{color}'>{status}</span>", unsafe_allow_html=True)
            st.write(f"**Detail:** {detail}")
            st.write(f"**Arah Selanjutnya:** {arah}")
            
        else:
            st.warning(f"Titik balik tidak cukup terdeteksi dengan sensitivitas {order}. Coba kecilkan angka 'Sensitivitas' di sidebar.")

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
