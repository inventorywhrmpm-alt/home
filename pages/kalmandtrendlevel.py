import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kalman Trend IDX", layout="wide")

# Fungsi Kalman Filter (Logika BigBeluga)
def kalman_filter(src, length, R=0.01, Q=0.1):
    if len(src) == 0: return pd.Series([])
    src_values = src.values # Mengambil nilai murni agar tidak bentrok dengan index
    estimate = src_values[0]
    error_est = 1.0
    error_meas = R * length
    estimates = []
    
    for val in src_values:
        prediction = estimate
        kalman_gain = error_est / (error_est + error_meas)
        estimate = prediction + kalman_gain * (val - prediction)
        error_est = (1 - kalman_gain) * error_est + Q / length
        estimates.append(estimate)
    return pd.Series(estimates, index=src.index)

def analyze_trend(df, short_len, long_len):
    # Hitung Kalman & Bulatkan (Hapus desimal)
    df['Short_K'] = kalman_filter(df['Close'], short_len).round(0).astype(int)
    df['Long_K'] = kalman_filter(df['Close'], long_len).round(0).astype(int)
    df['Price'] = df['Close'].round(0).astype(int)
    
    # Logika Trend
    df['Trend_Up'] = df['Short_K'] > df['Long_K']
    
    # Sinyal Buy/Sell (Hanya perpotongan)
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
ticker_raw = st.sidebar.text_input("Kode Saham (Contoh: BBCA)", value="BBCA").upper().strip()

# Proteksi agar tidak dobel .JK
if ticker_raw:
    if ticker_raw.endswith(".JK"):
        ticker_full = ticker_raw
    else:
        ticker_full = f"{ticker_raw}.JK"
else:
    ticker_full = ""

period = st.sidebar.selectbox("Periode Data", ["6mo", "1y", "2y"], index=1)
s_len = st.sidebar.slider("Short Length", 10, 100, 50)
l_len = st.sidebar.slider("Long Length", 50, 300, 150)

if ticker_full:
    try:
        with st.spinner(f'Fetching {ticker_full}...'):
            # Ambil data dengan auto_adjust agar tidak ada kolom Adj Close yang mengganggu
            data = yf.download(ticker_full, period=period, progress=False, auto_adjust=True)
        
        if data is not None and not data.empty:
            # Perbaikan untuk masalah Multi-index yfinance terbaru
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Reset index jika perlu untuk memastikan Close ada
            df_proc = data.copy()
            
            result = analyze_trend(df_proc, s_len, l_len)
            
            # Tampilan Metric
            last_row = result.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("Ticker", ticker_full)
            c2.metric("Last Price", f"{int(last_row['Price'])}")
            c3.metric("Current Status", last_row['Status'])

            # Tabel History
            st.subheader(f"History Tabel: {ticker_raw}")
            show_df = result[['Price', 'Short_K', 'Long_K', 'Signal', 'Status']].tail(30).copy()
            show_df = show_df.iloc[::-1] # Terbaru di atas

            def style_rows(val):
                if "BULLISH" in val: return 'color: #13bd6e; font-weight: bold'
                if "BEARISH" in val: return 'color: #af0d4b; font-weight: bold'
                return ''

            st.table(show_df.style.applymap(style_rows, subset=['Status']))
            
        else:
            st.error(f"Gagal menarik data untuk {ticker_full}. Pastikan koneksi internet aktif.")
            
    except Exception as e:
        st.error(f"Terjadi Kesalahan: {e}")
