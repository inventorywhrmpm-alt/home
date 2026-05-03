import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kalman Trend IDX", layout="wide")

# Fungsi Kalman Filter (Logika BigBeluga)
def kalman_filter(src, length, R=0.01, Q=0.1):
    if len(src) == 0: return pd.Series([])
    estimate = src[0]
    error_est = 1.0
    error_meas = R * length
    estimates = []
    
    for val in src:
        prediction = estimate
        kalman_gain = error_est / (error_est + error_meas)
        estimate = prediction + kalman_gain * (val - prediction)
        error_est = (1 - kalman_gain) * error_est + Q / length
        estimates.append(estimate)
    return pd.Series(estimates, index=src.index)

def analyze_trend(df, short_len, long_len):
    # Hitung Kalman & Bulatkan (Hapus desimal mengganggu)
    df['Short_K'] = kalman_filter(df['Close'], short_len).round(0).astype(int)
    df['Long_K'] = kalman_filter(df['Close'], long_len).round(0).astype(int)
    df['Price'] = df['Close'].round(0).astype(int)
    
    # Logika Trend
    df['Trend_Up'] = df['Short_K'] > df['Long_K']
    
    # Sinyal Buy/Sell (Hanya muncul saat perpotongan, sisanya kosong)
    df['Signal'] = ""
    mask_buy = (df['Trend_Up']) & (~df['Trend_Up'].shift(1).fillna(False))
    mask_sell = (~df['Trend_Up']) & (df['Trend_Up'].shift(1).fillna(False))
    df.loc[mask_buy, 'Signal'] = "🟢 BUY"
    df.loc[mask_sell, 'Signal'] = "🔴 SELL"
    
    # Status Visual
    df['Mom_Up'] = df['Short_K'] > df['Short_K'].shift(2)
    df['Status'] = "Neutral"
    df.loc[(df['Trend_Up']) & (df['Mom_Up']), 'Status'] = "🟩 BULLISH"
    df.loc[(~df['Trend_Up']) & (~df['Mom_Up']), 'Status'] = "🟥 BEARISH"
    
    return df

# --- INTERFACE STREAMLIT ---
st.title("📈 Kalman Trend Analysis")

# Sidebar
st.sidebar.header("Pencarian & Parameter")
# User input tanpa .JK
ticker_input = st.sidebar.text_input("Kode Saham (Tanpa .JK)", value="BBCA").upper()
ticker_full = f"{ticker_input}.JK"

period = st.sidebar.selectbox("Periode Data", ["6mo", "1y", "2y"], index=1)
s_len = st.sidebar.slider("Short Length", 10, 100, 50)
l_len = st.sidebar.slider("Long Length", 50, 300, 150)

if ticker_input:
    try:
        with st.spinner(f'Mengambil data {ticker_full}...'):
            data = yf.download(ticker_full, period=period, progress=False)
        
        if not data.empty:
            # Flatten columns jika ada multi-index
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            result = analyze_trend(data, s_len, l_len)
            
            # Tampilan Ringkasan Atas
            last_row = result.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("Ticker", ticker_full)
            c2.metric("Last Price", f"{last_row['Price']}")
            c3.metric("Current Status", last_row['Status'])

            # Tabel Visualisasi Teks
            st.subheader(f"History Tabel: {ticker_input}")
            
            # Ambil kolom yang diperlukan saja
            show_df = result[['Price', 'Short_K', 'Long_K', 'Signal', 'Status']].tail(30).copy()
            
            # Balik urutan agar data terbaru di atas
            show_df = show_df.iloc[::-1]

            # Style Tabel
            def style_rows(val):
                if "BULLISH" in val: return 'color: #13bd6e; font-weight: bold'
                if "BEARISH" in val: return 'color: #af0d4b; font-weight: bold'
                return ''

            st.table(show_df.style.applymap(style_rows, subset=['Status']))
            
        else:
            st.warning(f"Saham {ticker_full} tidak ditemukan di Yahoo Finance.")
            
    except Exception as e:
        st.error(f"Error: {e}")
