import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

def calculate_vwap_logic(df, prd, baseAPT, useAdapt, volBias):
    # Pastikan nama kolom huruf kecil untuk konsistensi
    df.columns = [col.lower() for col in df.columns]
    
    # 1. Hitung Pivot
    # Kita gunakan shift untuk menghindari 'look-ahead bias' pada bar berjalan
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
    df['atr_avg'] = df['atr'].ewm(span=atr_len, adjust=False).mean()
    
    df['ratio'] = np.where(df['atr_avg'] > 0, df['atr'] / df['atr_avg'], 1.0)
    apt_raw = baseAPT / (df['ratio'] ** volBias) if useAdapt else pd.Series(baseAPT, index=df.index)
    df['apt_clamped'] = apt_raw.clip(5.0, 300.0).round()

    # 3. Labeling & VWAP Calculation
    df['structure'] = ""
    last_ph = np.nan
    last_pl = np.nan
    
    vwap_values = []
    p_acc, v_acc = 0.0, 0.0

    for i in range(len(df)):
        hlc3 = (df['high'].iloc[i] + df['low'].iloc[i] + df['close'].iloc[i]) / 3
        vol = df['volume'].iloc[i]
        
        # Logika Swing & Label
        if df['is_ph'].iloc[i]:
            val = df['high'].iloc[i]
            label = "HH" if val > last_ph else "LH"
            df.at[df.index[i], 'structure'] = label
            last_ph = val
            # Reset Anchor pada Pivot High
            p_acc, v_acc = hlc3 * vol, vol 
            
        elif df['is_pl'].iloc[i]:
            val = df['low'].iloc[i]
            label = "LL" if val < last_pl else "HL"
            df.at[df.index[i], 'structure'] = label
            last_pl = val
            # Reset Anchor pada Pivot Low
            p_acc, v_acc = hlc3 * vol, vol 
        else:
            # Update VWAP Dynamic
            apt = df['apt_clamped'].iloc[i]
            alpha = 1.0 - np.exp(-np.log(2.0) / max(1.0, apt))
            p_acc = (1.0 - alpha) * p_acc + alpha * (hlc3 * vol)
            v_acc = (1.0 - alpha) * v_acc + alpha * vol
            
        vwap_values.append(p_acc / v_acc if v_acc > 0 else np.nan)

    df['dynamic_vwap'] = vwap_values
    return df

# --- Streamlit UI ---
st.set_page_config(page_title="Zeiierman VWAP Multi-Ticker", layout="wide")
st.title("📈 Dynamic Swing VWAP (Fixed)")

with st.sidebar:
    st.header("Pengaturan")
    ticker_input = st.text_input("Ticker (contoh: BBCA, SCMA, TLKM)", value="SCMA, BBCA")
    prd = st.number_input("Swing Period", value=20, min_value=2)
    baseAPT = st.number_input("Adaptive APT", value=20.0)
    useAdapt = st.checkbox("Gunakan Adaptasi Volatilitas", value=True)
    volBias = st.slider("Volatility Bias", 0.1, 15.0, 10.0)

if ticker_input:
    tickers = [t.strip().upper() for t in ticker_input.split(",")]
    
    for ticker in tickers:
        clean_ticker = ticker.replace(".JK", "")
        search_ticker = f"{clean_ticker}.JK"
        
        with st.expander(label=f"Tabel Data: {clean_ticker}", expanded=True):
            try:
                # Menggunakan auto_adjust=True untuk menghindari masalah kolom
                df = yf.download(search_ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
                
                if df.empty:
                    st.warning(f"Ticker {clean_ticker} tidak ditemukan di Yahoo Finance.")
                    continue

                # PERBAIKAN KRITIKAL: Menangani MultiIndex Columns
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                # Pastikan tidak ada kolom duplikat dan konversi ke lowercase
                df = df.loc[:, ~df.columns.duplicated()]

                # Jalankan kalkulasi
                result = calculate_vwap_logic(df.copy(), prd, baseAPT, useAdapt, volBias)
                
                # Pilih kolom untuk ditampilkan
                display_cols = ['high', 'low', 'close', 'volume', 'dynamic_vwap', 'structure']
                final_df = result[display_cols].tail(15)

                # Styling Tabel
                st.table(final_df.style.format({
                    'high': '{:.2f}', 'low': '{:.2f}', 'close': '{:.2f}', 
                    'dynamic_vwap': '{:.2f}', 'volume': '{:,.0f}'
                }).applymap(lambda x: 'background-color: #27ae60; color: white' if x in ['HH', 'HL'] 
                            else ('background-color: #c0392b; color: white' if x in ['LL', 'LH'] else ''), subset=['structure']))

            except Exception as e:
                st.error(f"Gagal memproses {clean_ticker}: {str(e)}")
