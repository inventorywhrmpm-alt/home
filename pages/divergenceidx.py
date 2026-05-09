import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="IDX Divergence Screener", layout="wide")

def detect_divergence(df, rsi_len=14, lookback=60):
    """
    Logika penyederhanaan dari skrip Trendoscope:
    Mencari pivot pada harga dan oscillator untuk mendeteksi perbedaan arah.
    """
    if len(df) < lookback:
        return "Data Kurang"

    # Hitung RSI sebagai Oscillator Utama
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)
    
    # Mencari Pivot (Lows & Highs)
    # Pivot Low (untuk Bullish)
    df['pl'] = df['Low'][(df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))]
    # Pivot High (untuk Bearish)
    df['ph'] = df['High'][(df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))]

    # Ambil 2 pivot terakhir yang valid
    pivots_l = df.dropna(subset=['pl']).tail(2)
    pivots_h = df.dropna(subset=['ph']).tail(2)

    status = "No Divergence"

    # --- Bullish Divergence Logic ---
    if len(pivots_l) == 2:
        price_low1, price_low2 = pivots_l['Low'].iloc[0], pivots_l['Low'].iloc[1]
        rsi_low1, rsi_low2 = pivots_l['rsi'].iloc[0], pivots_l['rsi'].iloc[1]

        # Regular Bullish: Price LL, RSI HL
        if price_low2 < price_low1 and rsi_low2 > rsi_low1:
            status = "Bullish Divergence"
        # Hidden Bullish: Price HL, RSI LL
        elif price_low2 > price_low1 and rsi_low2 < rsi_low1:
            status = "Bullish Hidden"

    # --- Bearish Divergence Logic ---
    if len(pivots_h) == 2 and status == "No Divergence":
        price_high1, price_high2 = pivots_h['High'].iloc[0], pivots_h['High'].iloc[1]
        rsi_high1, rsi_high2 = pivots_h['rsi'].iloc[0], pivots_h['rsi'].iloc[1]

        # Regular Bearish: Price HH, RSI LH
        if price_high2 > price_high1 and rsi_high2 < rsi_high1:
            status = "Bearish Divergence"
        # Hidden Bearish: Price LH, RSI HH
        elif price_high2 < price_high1 and rsi_high2 > rsi_high1:
            status = "Bearish Hidden"

    return status

# --- UI Streamlit ---
st.title("📈 IDX Divergence Screener")
st.markdown("Mendeteksi **Regular** & **Hidden** Divergence pada saham-saham pilihan di Bursa Efek Indonesia (IDX).")

with st.sidebar:
    st.header("Pengaturan")
    # Input ticker tanpa .JK, nanti ditambahkan otomatis
    input_tickers = st.text_area("Masukkan Kode Saham (pisahkan koma)", 
                                 "BBCA, BBRI, TLKM, ASII, GOTO, UNVR, ADRO")
    
    tf = st.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
    rsi_length = st.slider("RSI Length", 5, 30, 14)
    run_btn = st.button("Jalankan Pemindaian")

if run_btn:
    # Parsing ticker dan tambah .JK
    ticker_list = [t.strip().upper() for t in input_tickers.split(",")]
    ticker_jk = [f"{t}.JK" for t in ticker_list]
    
    results = []
    
    progress_bar = st.progress(0)
    
    for i, t in enumerate(ticker_jk):
        try:
            # Download data (ambil 6 bulan terakhir untuk mencari pivot)
            df = yf.download(t, period="6mo", interval=tf, progress=False)
            
            if not df.empty:
                status = detect_divergence(df, rsi_len=rsi_length)
                last_price = df['Close'].iloc[-1]
                
                results.append({
                    "Ticker": t.replace(".JK", ""),
                    "Price": f"Rp {last_price:,.0f}",
                    "Status": status,
                    "Timeframe": tf
                })
        except Exception as e:
            continue
            
        progress_bar.progress((i + 1) / len(ticker_jk))

    # Tampilkan Hasil
    if results:
        df_final = pd.DataFrame(results)
        
        # Styling Tabel
        def color_status(val):
            if "Bullish" in val: color = '#00ff00; font-weight: bold' # Hijau
            elif "Bearish" in val: color = '#ff4b4b; font-weight: bold' # Merah
            else: color = 'white'
            return f'color: {color}'

        st.table(df_final.style.applymap(color_status, subset=['Status']))
    else:
        st.error("Tidak ada data yang berhasil diambil. Pastikan kode saham benar.")
