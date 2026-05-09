import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="IDX Divergence Screener", layout="wide")

# --- 2. CORE LOGIC ---
def get_divergence_status(df, rsi_len=14):
    if df is None or df.empty:
        return "Data Kosong"

    # Standarisasi nama kolom ke lowercase
    df.columns = [str(col).lower() for col in df.columns]
    
    # Hapus kolom NaN yang mengganggu
    df = df.dropna(subset=['close', 'high', 'low'])

    if len(df) < rsi_len + 10:
        return "Data Kurang"

    try:
        df['rsi'] = ta.rsi(df['close'], length=rsi_len)
        df = df.dropna(subset=['rsi']).copy()
    except:
        return "Gagal RSI"

    # Pivot Radius 2
    df['is_pl'] = (df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(2)) & \
                  (df['low'] < df['low'].shift(-1)) & (df['low'] < df['low'].shift(-2))
    df['is_ph'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(2)) & \
                  (df['high'] > df['high'].shift(-1)) & (df['high'] > df['high'].shift(-2))

    pivots_l = df[df['is_pl']].tail(2)
    pivots_h = df[df['is_ph']].tail(2)

    status = "No Divergence"
    if len(pivots_l) == 2:
        p1_p, p2_p = pivots_l['low'].iloc[0], pivots_l['low'].iloc[1]
        p1_r, p2_r = pivots_l['rsi'].iloc[0], pivots_l['rsi'].iloc[1]
        if p2_p < p1_p and p2_r > p1_r: status = "🟢 Bullish Div"
        elif p2_p > p1_p and p2_r < p1_r: status = "🟢 Bullish Hid"

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
    tf_choice = st.selectbox("Timeframe", ["1d", "4h", "1h", "15m"], index=0)
    scan_button = st.button("🚀 Start Scan", use_container_width=True)

# --- 4. DATA PROCESSING ---
if scan_button:
    ticker_list = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
    final_results = []
    progress_bar = st.progress(0)

    for i, sym in enumerate(ticker_list):
        t_jk = f"{sym}.JK"
        try:
            # Pengaturan Periode (Intraday 1h/15m terbatas 730 hari)
            data_period = "2y" if tf_choice in ["1d", "4h"] else "60d"
            
            # Download Data
            fetch_tf = "1h" if tf_choice == "4h" else tf_choice
            df_raw = yf.download(t_jk, period=data_period, interval=fetch_tf, progress=False)
            
            if df_raw.empty:
                final_results.append({"Ticker": sym, "Price": "-", "Signal Status": "Data Kosong", "Timeframe": tf_choice})
                continue

            # Perbaikan Multi-Index yfinance
            if isinstance(df_raw.columns, pd.MultiIndex):
                df_raw.columns = df_raw.columns.get_level_values(0)

            # Logic Resampling 4h
            if tf_choice == "4h":
                logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
                df_raw = df_raw.resample('4h').apply(logic).dropna()

            # Deteksi Divergensi
            sig = get_divergence_status(df_raw)
            
            # Ambil harga terakhir dengan aman (tanpa case sensitive)
            price_val = df_raw['Close'].iloc[-1] if 'Close' in df_raw.columns else df_raw['close'].iloc[-1]
            price_str = f"{price_val:,.0f}"

            final_results.append({
                "Ticker": sym,
                "Price": price_str,
                "Signal Status": sig,
                "Timeframe": tf_choice
            })
            
        except Exception as e:
            final_results.append({"Ticker": sym, "Price": "Error", "Signal Status": f"Gagal: {str(e)}", "Timeframe": tf_choice})
        
        progress_bar.progress((i + 1) / len(ticker_list))

    # --- 5. DISPLAY ---
    if final_results:
        df_display = pd.DataFrame(final_results)
        def color_signal(val):
            s_val = str(val)
            if "🟢" in s_val: return 'background-color: #002b00; color: #00ff00'
            if "🔴" in s_val: return 'background-color: #2b0000; color: #ff4b4b'
            return ''

        st.subheader(f"📊 Hasil Pemindaian - Timeframe {tf_choice}")
        try:
            styled_df = df_display.style.map(color_signal, subset=['Signal Status'])
        except AttributeError:
            styled_df = df_display.style.applymap(color_signal, subset=['Signal Status'])
        st.table(styled_df)
