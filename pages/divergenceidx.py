import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="IDX Divergence Screener", layout="wide")

# --- 2. CORE LOGIC (DIVERGENCE ENGINE) ---
def get_divergence_status(df, rsi_len=14):
    """
    Logika mendeteksi 4 jenis divergensi:
    - Regular Bullish: Price Lower Low, RSI Higher Low (Reversal)
    - Hidden Bullish: Price Higher Low, RSI Lower Low (Continuation)
    - Regular Bearish: Price Higher High, RSI Lower High (Reversal)
    - Hidden Bearish: Price Lower High, RSI Higher High (Continuation)
    """
    # Hitung RSI menggunakan pandas_ta
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)
    
    # Hapus bar awal yang RSI-nya masih NaN
    df = df.dropna(subset=['rsi']).copy()
    
    if len(df) < 20:
        return "Data Kurang"

    # Deteksi Pivot menggunakan rolling window (Radius 3 bar)
    # Pivot Low
    df['is_pl'] = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(2)) & \
                  (df['Low'] < df['Low'].shift(-1)) & (df['Low'] < df['Low'].shift(-2))
    # Pivot High
    df['is_ph'] = (df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(2)) & \
                  (df['High'] > df['High'].shift(-1)) & (df['High'] > df['High'].shift(-2))

    pivots_l = df[df['is_pl']].tail(2)
    pivots_h = df[df['is_ph']].tail(2)

    status = "No Divergence"

    # Bullish Check (Berdasarkan Pivot Low)
    if len(pivots_l) == 2:
        p1_price, p2_price = pivots_l['Low'].iloc[0], pivots_l['Low'].iloc[1]
        p1_rsi, p2_rsi = pivots_l['rsi'].iloc[0], pivots_l['rsi'].iloc[1]

        if p2_price < p1_price and p2_rsi > p1_rsi:
            status = "🟢 Bullish Divergence"
        elif p2_price > p1_price and p2_rsi < p1_rsi:
            status = "🟢 Bullish Hidden"

    # Bearish Check (Berdasarkan Pivot High)
    if len(pivots_h) == 2 and status == "No Divergence":
        p1_price, p2_price = pivots_h['High'].iloc[0], pivots_h['High'].iloc[1]
        p1_rsi, p2_rsi = pivots_h['rsi'].iloc[0], pivots_h['rsi'].iloc[1]

        if p2_price > p1_price and p2_rsi < p1_rsi:
            status = "🔴 Bearish Divergence"
        elif p2_price < p1_price and p2_rsi > p1_rsi:
            status = "🔴 Bearish Hidden"

    return status

# --- 3. UI LAYOUT ---
st.title("🌊 IDX Divergence Screener")
st.caption("Berdasarkan Logika Trendoscope & BOSWaves untuk Bursa Efek Indonesia")

with st.sidebar:
    st.header("⚙️ Settings")
    # Contoh input: BBCA, ASII, TLKM, UNVR
    raw_tickers = st.text_area("List Kode Saham IDX (Tanpa .JK)", 
                               value="BBCA, BBRI, TLKM, ASII, GOTO, ADRO, AMRT, UNVR",
                               help="Pisahkan dengan koma. Contoh: BBCA, ASII")
    
    timeframe = st.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
    rsi_val = st.slider("RSI Period", 5, 30, 14)
    scan_button = st.button("🚀 Start Scan", use_container_width=True)

# --- 4. DATA PROCESSING ---
if scan_button:
    ticker_list = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
    final_data = []

    progress_text = "Sedang mengambil data dari Yahoo Finance..."
    my_bar = st.progress(0, text=progress_text)

    for i, sym in enumerate(ticker_list):
        ticker_jk = f"{sym}.JK"
        try:
            # Mengambil data 1 tahun agar pivot lebih akurat
            df_stock = yf.download(ticker_jk, period="1y", interval=timeframe, progress=False)
            
            if df_stock.empty:
                st.error(f"Data {sym} kosong atau tidak ditemukan.")
                continue

            # Hitung Status
            res_status = get_divergence_status(df_stock, rsi_len=rsi_val)
            last_close = df_stock['Close'].iloc[-1]

            final_data.append({
                "Ticker": sym,
                "Last Price": f"Rp {last_close:,.0f}",
                "Signal Status": res_status,
                "Timeframe": timeframe
            })
        except Exception as e:
            st.warning(f"Gagal memproses {sym}: {e}")
        
        # Update Progress
        my_bar.progress((i + 1) / len(ticker_list), text=f"Scanning: {sym}")

    # --- 5. DISPLAY RESULTS ---
    if final_data:
        df_display = pd.DataFrame(final_data)
        
        # Fungsi warna untuk tabel
        def color_signal(val):
            if "🟢" in val: return 'background-color: #002b00; color: #00ff00'
            if "🔴" in val: return 'background-color: #2b0000; color: #ff4b4b'
            return ''

        st.subheader("📊 Hasil Pemindaian")
        st.table(df_display.style.applymap(color_signal, subset=['Signal Status']))
        st.success(f"Berhasil memindai {len(final_data)} saham.")
    else:
        st.info("Klik tombol scan untuk memulai.")

else:
    st.info("💡 **Tips:** Masukkan kode saham seperti 'BBCA, TLKM' lalu klik Start Scan.")
