import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# --- Fungsi Kalkulasi Inti ---
def calculate_vwap_logic(df, prd, baseAPT, useAdapt, volBias):
    # 1. Hitung Pivot
    df['high_max'] = df['high'].rolling(window=prd, center=True).max()
    df['low_min'] = df['low'].rolling(window=prd, center=True).min()
    
    df['is_ph'] = df['high'] == df['high_max']
    df['is_pl'] = df['low'] == df['low_min']
    
    # 2. Adaptation & ATR
    atr_len = 50
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.ewm(span=atr_len, adjust=False).mean()
    df['atrAvg'] = df['atr'].ewm(span=atr_len, adjust=False).mean()
    
    df['ratio'] = np.where(df['atrAvg'] > 0, df['atr'] / df['atrAvg'], 1.0)
    apt_raw = baseAPT / (df['ratio'] ** volBias) if useAdapt else pd.Series(baseAPT, index=df.index)
    df['apt_clamped'] = apt_raw.clip(5.0, 300.0).round()

    # 3. Labeling HH, HL, LL, LH
    df['Structure'] = ""
    last_ph = np.nan
    last_pl = np.nan
    
    vwap_values = []
    p_acc, v_acc = 0.0, 0.0
    current_dir = 0 # 1 untuk Up, -1 untuk Down

    for i in range(len(df)):
        hlc3 = (df['high'].iloc[i] + df['low'].iloc[i] + df['close'].iloc[i]) / 3
        vol = df['volume'].iloc[i]
        
        # Logika Swing & Label
        if df['is_ph'].iloc[i]:
            val = df['high'].iloc[i]
            label = "HH" if val > last_ph else "LH"
            df.at[df.index[i], 'Structure'] = label
            last_ph = val
            current_dir = -1 # Anchor baru (Down)
            p_acc, v_acc = hlc3 * vol, vol # Reset Anchor
            
        elif df['is_pl'].iloc[i]:
            val = df['low'].iloc[i]
            label = "LL" if val < last_pl else "HL"
            df.at[df.index[i], 'Structure'] = label
            last_pl = val
            current_dir = 1 # Anchor baru (Up)
            p_acc, v_acc = hlc3 * vol, vol # Reset Anchor
        else:
            # Update VWAP Dynamic (Running)
            apt = df['apt_clamped'].iloc[i]
            alpha = 1.0 - np.exp(-np.log(2.0) / max(1.0, apt))
            p_acc = (1.0 - alpha) * p_acc + alpha * (hlc3 * vol)
            v_acc = (1.0 - alpha) * v_acc + alpha * vol
            
        vwap_values.append(p_acc / v_acc if v_acc > 0 else np.nan)

    df['Dynamic_VWAP'] = vwap_values
    return df

# --- Streamlit UI ---
st.set_page_config(page_title="Zeiierman VWAP Multi-Ticker", layout="wide")

st.title("📈 Dynamic Swing VWAP & Market Structure")
st.markdown("Menghitung VWAP Adaptif dan mendeteksi level **HH, HL, LL, LH** secara otomatis.")

# Sidebar Inputs
with st.sidebar:
    st.header("Pengaturan Parameter")
    ticker_input = st.text_input("Masukkan Ticker (Pisahkan dengan koma)", value="BBCA, ASII, TLKM")
    period = st.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
    
    st.divider()
    prd = st.number_input("Swing Period", value=20, min_value=2)
    baseAPT = st.number_input("Adaptive APT", value=20.0)
    useAdapt = st.checkbox("Gunakan Adaptasi Volatilitas", value=True)
    volBias = st.slider("Volatility Bias", 0.1, 15.0, 10.0)

# Main Logic
if ticker_input:
    tickers = [t.strip().upper() for t in ticker_input.split(",")]
    
    for ticker in tickers:
        # Bersihkan .JK untuk pencarian dan tampilan
        clean_ticker = ticker.replace(".JK", "")
        search_ticker = f"{clean_ticker}.JK"
        
        with st.expander(label=f"Hasil Tabel: {clean_ticker}", expanded=True):
            try:
                # Fetch Data
                df = yf.download(search_ticker, period="60d", interval=period, progress=False)
                
                if df.empty:
                    st.error(f"Data untuk {clean_ticker} tidak ditemukan.")
                    continue

                # Flatten columns if multi-index (yfinance fix)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # Jalankan Kalkulasi
                result = calculate_vwap_logic(df, prd, baseAPT, useAdapt, volBias)
                
                # Filter hanya baris yang punya pergerakan signifikan atau 20 bar terakhir
                display_df = result[['high', 'low', 'close', 'volume', 'Dynamic_VWAP', 'Structure']].tail(20)
                
                # Tampilkan Tabel
                st.table(display_df.style.format({
                    'high': '{:.2f}', 'low': '{:.2f}', 'close': '{:.2f}', 
                    'Dynamic_VWAP': '{:.2f}', 'volume': '{:,.0f}'
                }).applymap(lambda x: 'background-color: #2ecc71; color: white' if x in ['HH', 'HL'] 
                            else ('background-color: #e74c3c; color: white' if x in ['LL', 'LH'] else ''), subset=['Structure']))

            except Exception as e:
                st.error(f"Gagal memproses {clean_ticker}: {e}")

else:
    st.info("Silakan masukkan ticker saham di sidebar (contoh: BBCA, TLKM).")
