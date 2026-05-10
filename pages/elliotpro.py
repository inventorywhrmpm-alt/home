import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import argrelextrema

st.set_page_config(page_title="IDX Elliott Wave Dual-Direction", layout="wide")

st.title("📉 IDX Elliott Wave Pro (Bullish & Bearish)")
st.write("Sistem mendeteksi pola 5 gelombang naik (Impulse) maupun turun (Bearish Impulse) sesuai aturan baku.")

ticker_input = st.text_input("Masukkan Kode Saham:", "BBCA").upper()
ticker = f"{ticker_input}.JK"

# Sidebar
period = st.sidebar.selectbox("Periode Analisis", ["6mo", "1y", "2y", "5y"], index=1)
order = st.sidebar.slider("Sensitivitas (Order)", 5, 40, 12)

def validate_bullish(p):
    # p[0]=W1, p[1]=W2, p[2]=W3, p[3]=W4, p[4]=W5
    # 1. W2 tidak boleh balik ke titik awal W1 (dalam tren naik, W2 > Start W1)
    rule1 = p[1] > (p[0] * 0.7) # Pendekatan teknis
    # 2. W3 bukan yang terpendek
    w1_len, w3_len, w5_len = abs(p[0]-0), abs(p[2]-p[1]), abs(p[4]-p[3]) # Start W1 diasumsikan 0/low prev
    rule2 = not (w3_len < w1_len and w3_len < w5_len)
    # 3. W4 tidak overlap W1
    rule3 = p[3] > p[0]
    # Struktur: W3 > W1 dan W5 > W3
    structure = p[2] > p[0] and p[4] > p[2]
    return rule1 and rule2 and rule3 and structure

def validate_bearish(p):
    # p[0]=W1, p[1]=W2, p[2]=W3, p[3]=W4, p[4]=W5
    # 1. W2 tidak boleh naik melebihi awal W1
    rule1 = p[1] < (p[0] * 1.3)
    # 2. W3 bukan yang terpendek
    w1_len, w3_len, w5_len = abs(p[0]-0), abs(p[2]-p[1]), abs(p[4]-p[3])
    rule2 = not (w3_len < w1_len and w3_len < w5_len)
    # 3. W4 tidak overlap W1 (Dalam bearish, W4 harus di bawah W1)
    rule3 = p[3] < p[0]
    # Struktur: W3 < W1 dan W5 < W3
    structure = p[2] < p[0] and p[4] < p[2]
    return rule1 and rule2 and rule3 and structure

try:
    df = yf.download(ticker, period=period, interval="1d")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if not df.empty:
        prices = df['Close'].values
        max_idx = argrelextrema(prices, np.greater, order=order)[0]
        min_idx = argrelextrema(prices, np.less, order=order)[0]
        indices = np.sort(np.concatenate((max_idx, min_idx)))
        points = df.iloc[indices]
        
        found_mode = None # 'Bullish', 'Bearish', or None
        valid_waves = None

        if len(points) >= 5:
            for i in range(len(points) - 5, -1, -1):
                subset = points.iloc[i:i+5]
                p = subset['Close'].values
                
                if validate_bullish(p):
                    valid_waves = subset.copy()
                    found_mode = "BULLISH"
                    break
                elif validate_bearish(p):
                    valid_waves = subset.copy()
                    found_mode = "BEARISH"
                    break

        if found_mode:
            valid_waves['Wave_Label'] = ['W1', 'W2', 'W3', 'W4', 'W5']
            
            # Tabel Harga (Tanpa Nol)
            st.subheader(f"📊 Tabel Harga Elliott Wave ({found_mode})")
            tbl = valid_waves[['Close']].copy()
            tbl['Harga'] = tbl['Close'].astype(int)
            st.table(tbl[['Harga']].T)

            # Plot
            color = "green" if found_mode == "BULLISH" else "red"
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Price', line=dict(color='green')))
            fig.add_trace(go.Scatter(x=valid_waves.index, y=valid_waves['Close'], 
                                     mode='lines+markers+text',
                                     text=valid_waves['Wave_Label'],
                                     textposition="top center",
                                     line=dict(color=color, width=3),
                                     name=f'Valid {found_mode} Path'))
            st.plotly_chart(fig, use_container_width=True)

            # Kesimpulan Dinamis
            if found_mode == "BULLISH":
                st.success("✅ Pola BULLISH IMPULSE Terdeteksi")
                st.info("**Arah Selanjutnya:** Wave 5 selesai, potensi **Koreksi ABC (Turun)**.")
            else:
                st.error("⚠️ Pola BEARISH IMPULSE Terdeteksi")
                st.info("**Arah Selanjutnya:** Wave 5 (bawah) selesai, potensi **Pantulan/Rebound ABC (Naik)**.")
        else:
            st.warning("Pola valid tidak ditemukan. Coba sesuaikan 'Sensitivitas' di sidebar.")

except Exception as e:
    st.error(f"Error: {e}")
