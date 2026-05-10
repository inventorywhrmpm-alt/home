import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

# Konfigurasi Halaman
st.set_page_config(page_title="IDX Pattern Scanner", layout="wide")

st.title("📈 IDX Trend & Phase Scanner")
st.write("Analisis otomatis fase market untuk saham Bursa Efek Indonesia.")

# Sidebar Input
ticker_input = st.sidebar.text_input("Masukkan Kode Saham (Tanpa .JK)", "SCMA").upper()
# Otomatis tambahkan .JK jika belum ada
ticker = f"{ticker_input}.JK" if not ticker_input.endswith(".JK") else ticker_input

window = st.sidebar.slider("Sensitivitas Deteksi (Window)", 3, 20, 5)

def analyze_structure(df, order):
    # Mengambil nilai Close sebagai array 1D yang bersih
    prices = df['Close'].values.flatten()
    
    peak_idx = argrelextrema(prices, np.greater, order=order)[0]
    valley_idx = argrelextrema(prices, np.less, order=order)[0]
    
    extrema = []
    for p in peak_idx: extrema.append((p, float(prices[p]), 'Peak'))
    for v in valley_idx: extrema.append((v, float(prices[v]), 'Valley'))
    extrema.sort(key=lambda x: x[0])
    
    current_price = float(prices[-1])
    target = current_price
    
    if len(extrema) < 3:
        return "Data Kurang", "Ganti Sensitivitas", current_price

    last_point_val = float(extrema[-1][1])
    last_point_type = extrema[-1][2]
    prev_point_val = float(extrema[-2][1])
    
    if last_point_type == 'Valley':
        if current_price > last_point_val:
            fase = "Impulse Up (Bullish)"
            kemungkinan = "Menuju Peak Baru"
            target = last_point_val + (abs(prev_point_val - last_point_val) * 1.618)
        else:
            fase = "Downtrend"
            kemungkinan = "Mencari Support"
            target = last_point_val * 0.95
            
    elif last_point_type == 'Peak':
        if current_price < last_point_val:
            fase = "Correction Down (Bearish)"
            kemungkinan = "Mencari Valley Baru"
            target = prev_point_val + (abs(last_point_val - prev_point_val) * 0.618)
        else:
            fase = "Strong Breakout"
            kemungkinan = "Uptrend Berlanjut"
            target = last_point_val * 1.05
    
    return fase, kemungkinan, float(target)

# Ambil Data
try:
    data = yf.download(ticker, period="1y", interval="1d")

    if not data.empty:
        # Pembersihan data agar hanya mengambil nilai skalar (float)
        current_price = float(data['Close'].iloc[-1])
        prev_price = float(data['Close'].iloc[-2])
        change = ((current_price - prev_price) / prev_price) * 100
        
        fase, prediksi, harga_target = analyze_structure(data, window)

        # Menampilkan Tabel Hasil yang Bersih
        hasil_data = {
            "Indikator": [
                "Kode Saham", 
                "Harga Terakhir", 
                "Perubahan (%)", 
                "Fase Saat Ini", 
                "Prediksi Langkah Selanjutnya", 
                "Estimasi Target"
            ],
            "Nilai": [
                ticker_input, 
                f"Rp {current_price:,.0f}", 
                f"{change:+.2f}%", 
                fase, 
                prediksi, 
                f"Rp {harga_target:,.0f}"
            ]
        }
        
        df_hasil = pd.DataFrame(hasil_data)
        st.subheader(f"Analisis Teknikal: {ticker_input}")
        st.table(df_hasil)
        
    else:
        st.error(f"Data untuk {ticker_input} tidak ditemukan.")
except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
