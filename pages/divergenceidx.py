import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="IDX Divergence Screener V2", layout="wide")

# --- 2. CORE LOGIC (DIVERGENCE ENGINE) ---
def get_divergence_status(df, rsi_len=14):
    # Salin dataframe untuk menghindari SettingWithCopyWarning
    df = df.copy()
    
    # Pastikan nama kolom lowercase untuk konsistensi dengan pandas_ta
    df.columns = [str(col).lower() for col in df.columns]

    # CLEANING: Hapus bar yang tidak lengkap
    df = df.dropna(subset=['close', 'high', 'low'])

    # VALIDASI: Butuh minimal rsi_len + beberapa bar untuk pivot
    if len(df) < rsi_len + 10:
        return "Data Kurang"

    # HITUNG RSI: Gunakan try-except spesifik untuk perhitungan
    try:
        df['rsi'] = ta.rsi(df['close'], length=rsi_len)
        # Hapus bar awal yang RSI-nya NaN
        df = df.dropna(subset=['rsi'])
    except Exception:
        return "Gagal Hitung RSI"

    if len(df) < 5:
        return "Data Kurang"

    # DETEKSI PIVOT: (Radius 2 bar)
    # Pivot Low (Support)
    df['is_pl'] = (df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(2)) & \
                  (df['low'] < df['low'].shift(-1)) & (df['low'] < df['low'].shift(-2))
    # Pivot High (Resistance)
    df['is_ph'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(2)) & \
                  (df['high'] > df['high'].shift(-1)) & (df['high'] > df['high'].shift(-2))

    pivots_l = df[df['is_pl']].tail(2)
    pivots_h = df[df['is_ph']].tail(2)

    status = "No Divergence"

    # Bullish Check
    if len(pivots_l) == 2:
        p1_price, p2_price = pivots_l['low'].iloc[0], pivots_l['low'].iloc[1]
        p1_rsi, p2_rsi = pivots_l['rsi'].iloc[0], pivots_l['rsi'].iloc[1]

        if p2_price < p1_price and p2_rsi > p1_rsi:
            status = "🟢 Bullish Div"
        elif p2_price > p1_price and p2_rsi < p1_rsi:
            status = "🟢 Bullish Hid"

    # Bearish Check
    if len(pivots_h) == 2 and status == "No Divergence":
        p1_price, p2_price = pivots_h['high'].iloc[0], pivots_h['high'].iloc[1]
        p1_rsi, p2_rsi = pivots_h['rsi'].iloc[0], pivots_h['rsi'].iloc[1]

        if p2_price > p1_price and p2_rsi < p1_rsi:
            status = "🔴 Bearish Div"
        elif p2_price < p1_price and p2_rsi > p1_rsi:
            status = "🔴 Bearish Hid"

    return status

# --- 3. UI LAYOUT ---
st.title("🌊 IDX Divergence Screener")
st.caption("Fix Error: ['rsi'] - Versi Lebih Stabil")

with st.sidebar:
    st.header("⚙️ Settings")
    raw_tickers = st.text_area("List Kode Saham (Tanpa .JK)", 
                               value="BBCA, BBRI, TLKM, ASII, SCMA, GOTO, ADRO",
                               height=150)
    
    timeframe = st.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
    rsi_val = st.slider("RSI Period", 5, 30, 14)
    scan_button = st.button("🚀 Start Scan", use_container_width=True)

# --- 4. DATA PROCESSING ---
if scan_button:
    ticker_list = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
    final_data = []

    my_bar = st.progress(0, text="Menghubungkan ke Yahoo Finance...")

    for i, sym in enumerate(ticker_list):
        ticker_jk = f"{sym}.JK"
        try:
            # Ambil data sedikit lebih banyak (2 tahun) untuk menjamin histori cukup
            df_stock = yf.download(ticker_jk, period="2y", interval=timeframe, progress=False)
            
            if df_stock is None or df_stock.empty:
                final_data.append({"Ticker": sym, "Price": "-", "Signal Status": "Data Tidak Ditemukan", "Timeframe": timeframe})
                continue

            res_status = get_divergence_status(df_stock, rsi_len=rsi_val)
            last_close = df_stock['Close'].iloc[-1]

            final_data.append({
                "Ticker": sym,
                "Price": f"{last_close:,.0f}",
                "Signal Status": res_status,
                "Timeframe": timeframe
            })
        except Exception as e:
            final_data.append({"Ticker": sym, "Price": "Error", "Signal Status": f"Gagal: {str(e)}", "Timeframe": timeframe})
        
        my_bar.progress((i + 1) / len(ticker_list), text=f"Memproses: {sym}")

    # --- 5. DISPLAY ---
    if final_data:
        df_display = pd.DataFrame(final_data)
        
        # Fungsi warna untuk tabel
        def color_signal(val):
            # Pastikan val diubah ke string untuk pengecekan safety
            str_val = str(val)
            if "🟢" in str_val: 
                return 'background-color: #002b00; color: #00ff00'
            if "🔴" in str_val: 
                return 'background-color: #2b0000; color: #ff4b4b'
            if "Gagal" in str_val or "Data Kurang" in str_val: 
                return 'color: #888888'
            return ''

        st.subheader("📊 Hasil Pemindaian")
        
        # PERBAIKAN DI SINI:
        # Gunakan .map() jika pandas >= 2.1.0, atau tetap gunakan .applymap() jika versi lama.
        # Untuk Streamlit Cloud, biasanya menggunakan versi terbaru, jadi gunakan .map()
        try:
            styled_df = df_display.style.map(color_signal, subset=['Signal Status'])
        except AttributeError:
            styled_df = df_display.style.applymap(color_signal, subset=['Signal Status'])
            
        st.table(styled_df)
    else:
        st.warning("Tidak ada ticker yang valid.")
