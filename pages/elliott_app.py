import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# Konfigurasi Halaman
st.set_page_config(page_title="IDX Elliott Wave Analyzer", layout="wide")

st.title("📈 IDX Elliott Wave Analyzer")
st.write("Analisis otomatis gelombang Elliott untuk saham di Bursa Efek Indonesia.")

# Input Ticker
ticker_input = st.text_input("Masukkan Kode Saham (contoh: BBCA, TLKM, GOTO):", "BBCA").upper()
ticker = f"{ticker_input}.JK"

# Sidebar untuk parameter
period = st.sidebar.selectbox("Periode Data", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)
order = st.sidebar.slider("Sensitivitas Wave (Order)", 5, 50, 20)

@st.cache_data
def load_data(symbol, period):
    df = yf.download(symbol, period=period, interval="1d")
    return df

try:
    data = load_data(ticker, period)
    
    if data.empty:
        st.error("Data tidak ditemukan. Pastikan kode ticker benar.")
    else:
        # Deteksi Peaks dan Troughs untuk Elliott Wave
        data['Close_Smooth'] = data['Close'].rolling(window=5).mean() # Smoothing sedikit
        data.dropna(inplace=True)
        
        # Cari titik ekstrim
        ilocs_max = argrelextrema(data['Close'].values, np.greater, order=order)[0]
        ilocs_min = argrelextrema(data['Close'].values, np.less, order=order)[0]
        
        # Gabungkan dan urutkan berdasarkan waktu
        extrema = pd.concat([data.iloc[ilocs_max], data.iloc[ilocs_min]]).sort_index()
        
        # Ambil 5 titik terakhir sebagai representasi Wave 1-5
        if len(extrema) >= 5:
            last_5_waves = extrema.tail(5).copy()
            last_5_waves['Wave_Label'] = ['Wave 1', 'Wave 2', 'Wave 3', 'Wave 4', 'Wave 5']
            
            # --- TABEL 1: DATA HARGA WAVE ---
            st.subheader(f"Tabel 1: Titik Harga Elliott Wave - {ticker_input}")
            st.table(last_5_waves[['Close']].rename(columns={'Close': 'Harga Penutupan'}))
            
            # --- VISUALISASI ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Harga Saham', line=dict(color='gray', width=1)))
            fig.add_trace(go.Scatter(x=last_5_waves.index, y=last_5_waves['Close'], 
                                     mode='lines+markers+text',
                                     name='Elliott Wave Count',
                                     text=last_5_waves['Wave_Label'],
                                     textposition="top center",
                                     line=dict(color='blue', width=3)))
            
            st.plotly_chart(fig, use_container_width=True)

            # --- KESIMPULAN STATUS ---
            p1, p2, p3, p4, p5 = last_5_waves['Close'].values
            
            st.subheader("📌 Kesimpulan Status & Proyeksi")
            
            # Logika Sederhana Elliott Wave
            is_bullish = p3 > p1 and p5 > p3 and p4 > p2
            
            if is_bullish:
                current_status = "Siklus Impulsif Bullish (1-2-3-4-5) terdeteksi."
                next_move = "Memasuki Fase Koreksi (ABC). Waspadai penurunan harga sementara."
            else:
                current_status = "Siklus sedang berkonsolidasi atau dalam pola korektif."
                next_move = "Menunggu konfirmasi terbentuknya Low baru untuk memulai Wave 1 yang baru."

            col1, col2 = st.columns(2)
            col1.metric("Status Fase Sekarang", "Bullish" if is_bullish else "Korektif/Sideways")
            col2.metric("Proyeksi Berikutnya", "Koreksi ABC" if is_bullish else "Akumulasi")
            
            st.info(f"**Analisis:** {current_status} Harga kemungkinan besar **{next_move}**.")
            
        else:
            st.warning("Data tidak cukup untuk mendeteksi 5 gelombang. Coba perpanjang periode atau kurangi sensitivitas di sidebar.")

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
