import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="BOSWaves Swing Forecast", layout="wide")

def get_swing_data(ticker, tf, swing_len):
    # Download data
    df = yf.download(ticker, period="1mo", interval=tf, progress=False)
    if df.empty:
        return None
    
    # Menghitung Pivot Logic (mirip logic ta.highest/lowest swingLen)
    df['H'] = df['High'].rolling(window=swing_len, center=False).max()
    df['L'] = df['Low'].rolling(window=swing_len, center=False).min()
    
    # Deteksi Swing High/Low
    # Logic: high[1] == H[1] and high < H (Pivot terkonfirmasi saat harga turun dari peak)
    df['SH'] = (df['High'].shift(1) == df['H'].shift(1)) & (df['High'] < df['H'])
    df['SL'] = (df['Low'].shift(1) == df['L'].shift(1)) & (df['Low'] > df['L'])
    
    # Ambil pivot terakhir untuk deteksi divergence/bias
    last_sh = df[df['SH']]['High'].tail(2).values
    last_sl = df[df['SL']]['Low'].tail(2).values
    current_close = df['Close'].iloc[-1]
    
    # Logic Divergence / Structure
    # Bullish: Lower Low pada harga tapi Higher Low pada struktur (atau Break of Structure)
    # Di sini kita simpulkan status berdasarkan posisi harga terhadap pivot terakhir
    status = "Neutral"
    if len(last_sl) >= 2:
        if current_close > last_sh[-1]:
            status = "Bullish Break (BOS)"
        elif last_sl[-1] > last_sl[-2] and current_close > last_sl[-1]:
            status = "Bullish Structure"
            
    if len(last_sh) >= 2:
        if current_close < last_sl[-1]:
            status = "Bearish Break (BOS)"
        elif last_sh[-1] < last_sh[-2] and current_close < last_sh[-1]:
            status = "Bearish Structure"
            
    return {
        "Ticker": ticker,
        "TF": tf,
        "Price": f"{current_close:.2f}",
        "Status": status,
        "Last Pivot H": f"{last_sh[-1]:.2f}" if len(last_sh) > 0 else "N/A",
        "Last Pivot L": f"{last_sl[-1]:.2f}" if len(last_sl) > 0 else "N/A"
    }

# --- UI Streamlit ---
st.title("🌊 Swing Structure Forecast Dashboard")
st.markdown("Analisis otomatis berdasarkan logic **BOSWaves** (Swing Pivot Detection).")

with st.sidebar:
    st.header("Settings")
    tickers_input = st.text_input("Enter Tickers (pisahkan dengan koma)", "BTC-USD, ETH-USD, AAPL, TSLA, GC=F")
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=2)
    swing_length = st.number_input("Swing Length", value=16, min_value=10)
    run_button = st.button("Analyze Structure")

if run_button:
    ticker_list = [t.strip() for t in tickers_input.split(",")]
    results = []
    
    progress_bar = st.progress(0)
    for i, ticker in enumerate(ticker_list):
        try:
            data = get_swing_data(ticker, timeframe, swing_length)
            if data:
                results.append(data)
        except Exception as e:
            st.error(f"Error pada {ticker}: {e}")
        progress_bar.progress((i + 1) / len(ticker_list))
    
    if results:
        df_res = pd.DataFrame(results)
        
        # Styling Tabel
        def highlight_status(val):
            if "Bullish" in val: return 'background-color: #00ff0022; color: #00ff00'
            if "Bearish" in val: return 'background-color: #ff000022; color: #ff0000'
            return ''

        st.table(df_res.style.applymap(highlight_status, subset=['Status']))
    else:
        st.warning("Tidak ada data yang ditemukan.")
