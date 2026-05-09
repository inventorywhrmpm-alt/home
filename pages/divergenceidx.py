import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="IDX Divergence Screener", layout="wide")

# --- 2. CORE LOGIC ---
def get_divergence_status(df, rsi_len=14):
    # Pastikan dataframe tidak kosong
    if df is None or df.empty:
        return "Data Kosong"

    # Perbaikan struktur kolom yfinance (Menghapus Multi-Index jika ada)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Standarisasi nama kolom ke lowercase
    df.columns = [str(col).lower() for col in df.columns]

    # Hapus bar yang NaN pada kolom utama
    df = df.dropna(subset=['close', 'high', 'low'])

    if len(df) < rsi_len + 5:
        return "Data Kurang"

    try:
        # Hitung RSI
        df['rsi'] = ta.rsi(df['close'], length=rsi_len)
        df = df.dropna(subset=['rsi']).copy()
    except Exception as e:
        return f"Gagal RSI: {str(e)}"

    if len(df) < 5:
        return "Data Kurang"

    # Deteksi Pivot Radius 2
    df['is_pl'] = (df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(2)) & \
                  (df['low'] < df['low'].shift(-1)) & (df['low'] < df['low'].shift(-2))
    df['is_ph'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(2)) & \
                  (df['high'] > df['high'].shift(-1)) & (df['high'] > df['high'].shift(-2))

    pivots_l = df[df['is_pl']].tail(2)
    pivots_h = df[df['is_ph']].tail(2)

    status = "No Divergence"

    # Bullish Check
    if len(pivots_l) == 2:
        p1_p, p2_p = pivots_l['low'].iloc[0], pivots_l['low'].iloc[1]
        p1_r, p2_r = pivots_l['rsi'].iloc[0], pivots_l['rsi'].iloc[1]
        if p2_p < p1_p and p2_r > p1_r: status = "🟢 Bullish Div"
        elif p2_p > p1_p and p2_r < p1_r: status = "🟢 Bullish Hid"

    # Bearish Check
    if len(pivots_h) == 2 and status == "No Divergence":
        p1_p, p2_p = pivots_h['high'].iloc[0], pivots_h['high'].iloc[1]
        p1_r, p2_r = pivots_h['rsi'].iloc[0], pivots_h['rsi'].iloc[1]
        if p2_p > p1_p and p2_r < p1_r: status = "🔴 Bearish Div"
        elif p2_p < p1_p and p2_r > p1_r: status = "🔴 Bearish Hid"

    return status

# --- 3. UI LAYOUT ---
st.title("🌊 IDX Divergence Screener")

with st.sidebar:
    st.header("⚙️ Settings")
    raw_tickers = st.text_area("List Kode Saham (Tanpa .JK)", value="BBCA, BBRI, SCMA, GOTO, TLKM", height=150)
    timeframe = st.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
    scan_button = st.button("🚀 Start Scan", use_container_width=True)

# --- 4. DATA PROCESSING ---
if scan_button:
    ticker_list = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
    final_results = []

    progress_bar = st.progress(0)

    for i, sym in enumerate(ticker_list):
        t_jk = f"{sym}.JK"
        try:
            # Unduh data
            df_raw = yf.download(t_jk, period="2y", interval=timeframe, progress=False)
            
            if df_raw.empty:
                sig = "Ticker Salah/Data Kosong"
                price = "-"
            else:
                sig = get_divergence_status(df_raw)
                price = f"{df_raw.iloc[-1]['Close']:,.0f}" if 'Close' in df_raw.columns else f"{df_raw.iloc[-1].iloc[3]:,.0f}"

            final_results.append({
                "Ticker": sym,
                "Price": price,
                "Signal Status": sig,
                "Timeframe": timeframe
            })
        except Exception as e:
            final_results.append({"Ticker": sym, "Price": "Error", "Signal Status": f"Gagal: {str(e)}", "Timeframe": timeframe})
        
        progress_bar.progress((i + 1) / len(ticker_list))

    # --- 5. DISPLAY (FIXED MAP ERROR) ---
    if final_results:
        df_display = pd.DataFrame(final_results)
        
        def color_signal(val):
            s_val = str(val)
            if "🟢" in s_val: return 'background-color: #002b00; color: #00ff00'
            if "🔴" in s_val: return 'background-color: #2b0000; color: #ff4b4b'
            return ''

        st.subheader("📊 Hasil Pemindaian")
        
        # Menggunakan try-except untuk kompatibilitas versi Pandas (map vs applymap)
        try:
            styled_df = df_display.style.map(color_signal, subset=['Signal Status'])
        except AttributeError:
            styled_df = df_display.style.applymap(color_signal, subset=['Signal Status'])
            
        st.table(styled_df)
