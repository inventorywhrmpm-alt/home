import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

# Konfigurasi Halaman
st.set_page_config(page_title="IDX Multi-Scanner", layout="wide")

st.title("📈 IDX Multi-Ticker Phase Scanner")
st.write("Masukkan beberapa kode saham dipisahkan dengan koma untuk analisis massal.")

# Sidebar Input
ticker_input_raw = st.sidebar.text_input("Masukkan Kode Saham (Contoh: BBCA, SCMA, TLKM)", "BBCA, SCMA, TLKM")
window = st.sidebar.slider("Sensitivitas Deteksi (Window)", 3, 20, 5)

def analyze_structure(prices, order):
    peak_idx = argrelextrema(prices, np.greater, order=order)[0]
    valley_idx = argrelextrema(prices, np.less, order=order)[0]
    
    extrema = []
    for p in peak_idx: extrema.append((p, float(prices[p]), 'Peak'))
    for v in valley_idx: extrema.append((v, float(prices[v]), 'Valley'))
    extrema.sort(key=lambda x: x[0])
    
    current_price = float(prices[-1])
    target = current_price
    
    if len(extrema) < 3:
        return "Sideways", "Data Kurang", current_price

    last_point_val = float(extrema[-1][1])
    last_point_type = extrema[-1][2]
    prev_point_val = float(extrema[-2][1])
    
    if last_point_type == 'Valley':
        if current_price > last_point_val:
            fase = "Impulse Up 🚀"
            kemungkinan = "Menuju Peak"
            target = last_point_val + (abs(prev_point_val - last_point_val) * 1.618)
        else:
            fase = "Downtrend 📉"
            kemungkinan = "Mencari Support"
            target = last_point_val * 0.95
            
    elif last_point_type == 'Peak':
        if current_price < last_point_val:
            fase = "Correction ⚠️"
            kemungkinan = "Mencari Valley"
            target = prev_point_val + (abs(last_point_val - prev_point_val) * 0.618)
        else:
            fase = "Strong Breakout 🔥"
            kemungkinan = "Uptrend Lanjut"
            target = last_point_val * 1.05
    
    return fase, kemungkinan, float(target)

# Memproses List Ticker
ticker_list = [t.strip().upper() for t in ticker_input_raw.split(",")]
all_results = []

if st.button("Jalankan Analisis"):
    for t_name in ticker_list:
        ticker_jk = f"{t_name}.JK"
        try:
            data = yf.download(ticker_jk, period="1y", interval="1d", progress=False)
            
            if not data.empty:
                close_prices = data['Close'].values.flatten()
                close_prices = close_prices[~np.isnan(close_prices)]
                
                if len(close_prices) >= 2:
                    current_price = float(close_prices[-1])
                    prev_price = float(close_prices[-2])
                    change = ((current_price - prev_price) / prev_price) * 100
                    
                    fase, prediksi, harga_target = analyze_structure(close_prices, window)
                    
                    all_results.append({
                        "Ticker": t_name,
                        "Price": f"Rp {current_price:,.0f}",
                        "Change": f"{change:+.2f}%",
                        "Phase": fase,
                        "Next Move": prediksi,
                        "Target": f"Rp {harga_target:,.0f}"
                    })
            else:
                st.warning(f"Data {t_name} tidak ditemukan.")
        except Exception as e:
            st.error(f"Error pada {t_name}: {e}")

    # Menampilkan Tabel Final
    if all_results:
        df_final = pd.DataFrame(all_results)
        st.subheader("📋 Hasil Pemindaian Massal")
        st.dataframe(df_final, use_container_width=True, hide_index=True)
    else:
        st.info("Silakan masukkan kode saham dan klik tombol Jalankan Analisis.")
