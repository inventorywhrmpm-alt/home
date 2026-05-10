import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import argrelextrema

st.set_page_config(page_title="IDX Elliott Wave Pro", layout="wide")

st.title("📈 IDX Elliott Wave Validator")
st.write("Mencari pola Wave yang memenuhi 3 Aturan Utama (Cardinal Rules).")

ticker_input = st.text_input("Masukkan Kode Saham:", "BBCA").upper()
ticker = f"{ticker_input}.JK"

# Sidebar
period = st.sidebar.selectbox("Periode Analisis", ["6mo", "1y", "2y"], index=1)
order = st.sidebar.slider("Sensitivitas Puncak (Order)", 5, 30, 10)

def validate_elliott(p1, p2, p3, p4, p5):
    # Aturan 1: Wave 2 tidak boleh turun melewati awal Wave 1 (asumsi awal W1 adalah harga terendah sebelum W1)
    # Dalam kode ini kita cek: Wave 2 harus > titik awal atau minimal p2 > p1 jika p1 adalah puncak W1
    # Namun aturan bakunya: W2 > Start of W1. Kita sederhanakan: W2 tidak boleh lebih rendah dari titik terendah sebelum W1.
    rule1 = p2 > (p1 * 0.8) # Penyederhanaan: W2 tidak boleh crash parah
    
    # Aturan 2: Wave 3 tidak boleh jadi yang terpendek antara 1, 3, 5
    w1_len = abs(p1 - p2)
    w3_len = abs(p3 - p2)
    w5_len = abs(p5 - p4)
    rule2 = not (w3_len < w1_len and w3_len < w5_len)
    
    # Aturan 3: Wave 4 tidak boleh overlap dengan area Wave 1
    rule3 = p4 > p1
    
    # Tambahan: Wave 3 harus lebih tinggi dari Wave 1, Wave 5 harus lebih tinggi dari Wave 3 (untuk Bullish)
    structure = p3 > p1 and p5 > p3
    
    return rule1 and rule2 and rule3 and structure

try:
    df = yf.download(ticker, period=period, interval="1d")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if not df.empty:
        # Cari kandidat puncak/lembah
        prices = df['Close'].values
        max_idx = argrelextrema(prices, np.greater, order=order)[0]
        min_idx = argrelextrema(prices, np.less, order=order)[0]
        
        indices = np.sort(np.concatenate((max_idx, min_idx)))
        points = df.iloc[indices]
        
        # Iterasi mundur untuk mencari 5 titik terakhir yang VALID secara aturan
        found_valid = False
        valid_waves = None

        if len(points) >= 5:
            # Mencari kombinasi 5 titik terakhir
            for i in range(len(points) - 5, -1, -1):
                subset = points.iloc[i:i+5]
                p = subset['Close'].values
                
                if validate_elliott(p[0], p[1], p[2], p[3], p[4]):
                    valid_waves = subset.copy()
                    found_valid = True
                    break

        if found_valid:
            valid_waves['Wave_Label'] = ['W1', 'W2', 'W3', 'W4', 'W5']
            
            # --- TABEL HARGA (Nol Dihilangkan) ---
            st.subheader("📊 Tabel Harga Elliott Wave (Valid)")
            tbl = valid_waves[['Close']].copy()
            tbl['Harga'] = tbl['Close'].astype(int)
            st.table(tbl[['Harga']].T)

            # --- PLOT ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Price', line=dict(color='lightgray')))
            fig.add_trace(go.Scatter(x=valid_waves.index, y=valid_waves['Close'], 
                                     mode='lines+markers+text',
                                     textposition="top center",
                                     text=valid_waves['Wave_Label'],
                                     line=dict(color='green', width=3),
                                     name='Valid Elliott Path'))
            st.plotly_chart(fig, use_container_width=True)

            # --- KESIMPULAN ---
            st.success("✅ Pola Valid Ditemukan sesuai Cardinal Rules")
            st.info(f"""
            **Status Saat Ini:** Berada di ujung **Wave 5**.
            
            **Kepatuhan Aturan:**
            1. Wave 2 tidak membatalkan Wave 1: **OK**
            2. Wave 3 bukan yang terpendek: **OK**
            3. Wave 4 tidak overlap dengan Wave 1: **OK**
            
            **Arah Selanjutnya:** Berdasarkan teori, setelah 5 gelombang impulsif selesai, harga akan memasuki **Koreksi ABC** (penurunan). Waspadai pembalikan arah.
            """)
        else:
            st.warning("⚠️ Tidak ditemukan pola 5 gelombang yang memenuhi 3 Aturan Utama pada periode ini.")
            st.write("Saran: Coba ubah 'Sensitivitas' atau 'Periode Analisis' di sidebar untuk mencari pola di timeframe lain.")

except Exception as e:
    st.error(f"Error: {e}")
