import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

# Konfigurasi Halaman
st.set_page_config(page_title="IDX Pattern Scanner", layout="wide")

st.title("📈 IDX Trend & Phase Scanner")
st.write("Deteksi otomatis Puncak (Peak), Lembah (Valley), dan Fase Market.")

# Sidebar Input
ticker = st.sidebar.text_input("Masukkan Kode Saham IDX", "BBCA.JK")
window = st.sidebar.slider("Sensitivitas Deteksi (Window)", 3, 20, 5)

def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d")
        if df.empty:
            return None
        return df
    except:
        return None

def analyze_structure(df, order):
    # Pastikan mengambil nilai Close sebagai array 1D
    prices = df['Close'].values.flatten()
    
    # Mencari Puncak dan Lembah
    peak_idx = argrelextrema(prices, np.greater, order=order)[0]
    valley_idx = argrelextrema(prices, np.less, order=order)[0]
    
    # Menggabungkan dan mengurutkan titik ekstrem
    extrema = []
    for p in peak_idx: extrema.append((p, float(prices[p]), 'Peak'))
    for v in valley_idx: extrema.append((v, float(prices[v]), 'Valley'))
    extrema.sort(key=lambda x: x[0])
    
    # Default values jika tidak memenuhi syarat
    fase = "Konsolidasi"
    kemungkinan = "Wait and See"
    target = float(prices[-1]) # Default target ke harga saat ini

    if len(extrema) < 3:
        return "Data Kurang", "Ganti Sensitivitas", target

    # Ambil titik terakhir untuk logika
    last_point_val = float(extrema[-1][1])
    last_point_type = extrema[-1][2]
    prev_point_val = float(extrema[-2][1])
    current_price = float(prices[-1])
    
    # Logika Fase & Target
    if last_point_type == 'Valley':
        if current_price > last_point_val:
            fase = "Impulse Up (Bullish)"
            kemungkinan = "Menuju Peak Baru"
            # Fibonacci Extension 1.618
            target = last_point_val + (abs(prev_point_val - last_point_val) * 1.618)
        else:
            fase = "Downtrend"
            kemungkinan = "Mencari Support"
            target = last_point_val * 0.95
            
    elif last_point_type == 'Peak':
        if current_price < last_point_val:
            fase = "Correction Down (Bearish)"
            kemungkinan = "Mencari Valley Baru"
            # Fibonacci Retracement 0.618
            target = prev_point_val + (abs(last_point_val - prev_point_val) * 0.618)
        else:
            fase = "Strong Breakout"
            kemungkinan = "Uptrend Berlanjut"
            target = last_point_val * 1.05
    
    return fase, kemungkinan, float(target)

# Main Logic
data = get_data(ticker)

if data is not None:
    fase, prediksi, harga_target = analyze_structure(data, window)
    current_price = round(data['Close'].iloc[-1], 2)
    change = round(((current_price - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100, 2)

    # Menampilkan Tabel Hasil
    hasil_data = {
        "Indikator": [
            "Kode Saham", 
            "Harga Terakhir", 
            "Perubahan (%)", 
            "Fase Saat Ini", 
            "Prediksi Langkah Selanjutnya", 
            "Estimasi Target Harga (Fibonacci)"
        ],
        "Nilai": [
            ticker.upper(), 
            f"Rp {current_price}", 
            f"{change}%", 
            fase, 
            prediksi, 
            f"Rp {harga_target}"
        ]
    }
    
    df_hasil = pd.DataFrame(hasil_data)
    
    # Tampilan UI
    st.subheader(f"Hasil Analisis: {ticker.upper()}")
    st.table(df_hasil)
    
    # Penjelasan Teknis Singkat
    with st.expander("Lihat Penjelasan Logika"):
        st.write("""
        - **Impulse Up**: Harga telah membentuk lembah (valley) dan mulai merangkak naik melebihi titik terendah terakhir.
        - **Correction Down**: Harga telah mencapai puncak (peak) dan sedang mengalami penurunan teknis.
        - **Target Harga**: Dihitung menggunakan rasio Fibonacci dasar (0.618 untuk koreksi dan 1.618 untuk ekstensi impulse).
        """)
else:
    st.error("Gagal mengambil data. Pastikan kode saham benar (gunakan akhiran .JK untuk IDX).")
