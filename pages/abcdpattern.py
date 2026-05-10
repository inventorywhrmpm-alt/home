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
    prices = df['Close'].values
    
    # Mencari Puncak dan Lembah
    peak_idx = argrelextrema(prices, np.greater, order=order)[0]
    valley_idx = argrelextrema(prices, np.less, order=order)[0]
    
    # Menggabungkan dan mengurutkan titik ekstrem
    extrema = []
    for p in peak_idx: extrema.append((p, prices[p], 'Peak'))
    for v in valley_idx: extrema.append((v, prices[v], 'Valley'))
    extrema.sort(key=lambda x: x[0])
    
    if len(extrema) < 3:
        return "Data tidak cukup untuk membentuk pola", "N/A", "N/A"

    # Ambil 3 titik terakhir untuk menentukan fase
    last_point = extrema[-1]
    prev_point = extrema[-2]
    current_price = prices[-1]
    
    # Logika Fase
    if last_point[2] == 'Valley':
        # Jika titik terakhir adalah lembah, dan harga sekarang di atas lembah tersebut
        if current_price > last_point[1]:
            fase = "Impulse Up (Awal Kenaikan)"
            kemungkinan = "Menuju Peak Baru"
            target = last_point[1] + (prev_point[1] - last_point[1]) * 1.618
        else:
            fase = "Downtrend Extreme"
            kemungkinan = "Mencari Bottom"
            target = last_point[1] * 0.95
            
    elif last_point[2] == 'Peak':
        # Jika titik terakhir adalah puncak, dan harga sekarang mulai turun
        if current_price < last_point[1]:
            fase = "Correction Down (Konsolidasi/Profit Taking)"
            kemungkinan = "Mencari Support (Valley) Baru"
            target = prev_point[1] + (last_point[1] - prev_point[1]) * 0.618
        else:
            fase = "Strong Uptrend"
            kemungkinan = "Breakout Resistance"
            target = last_point[1] * 1.05
    
    return fase, kemungkinan, round(target, 2)

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
