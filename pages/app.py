import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

def calculate_vwap_logic(df, prd, baseAPT, useAdapt, volBias):
    # Standarisasi nama kolom ke lowercase
    df.columns = [col.lower() for col in df.columns]
    
    # 1. Deteksi Pivot (Swing Points)
    # Menggunakan window yang lebih presisi untuk mendeteksi High/Low
    df['high_max'] = df['high'].rolling(window=prd, center=True).max()
    df['low_min'] = df['low'].rolling(window=prd, center=True).min()
    
    df['is_ph'] = df['high'] == df['high_max']
    df['is_pl'] = df['low'] == df['low_min']
    
    # 2. Adaptation & ATR Logic
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

    # 3. Labeling Market Structure & VWAP Calculation
    df['structure'] = ""
    last_ph = np.nan
    last_pl = np.nan
    
    vwap_values = []
    p_acc, v_acc = 0.0, 0.0

    for i in range(len(df)):
        # Perhitungan harga rata-rata (HLC3)
        hlc3 = (df['high'].iloc[i] + df['low'].iloc[i] + df['close'].iloc[i]) / 3
        vol = df['volume'].iloc[i]
        
        # Logika Deteksi HH, HL, LL, LH
        if df['is_ph'].iloc[i]:
            val = df['high'].iloc[i]
            label = "HH" if val > last_ph else "LH"
            df.at[df.index[i], 'structure'] = label
            last_ph = val
            # Reset Anchor VWAP pada Pivot High baru
            p_acc, v_acc = hlc3 * vol, vol 
            
        elif df['is_pl'].iloc[i]:
            val = df['low'].iloc[i]
            label = "LL" if val < last_pl else "HL"
            df.at[df.index[i], 'structure'] = label
            last_pl = val
            # Reset Anchor VWAP pada Pivot Low baru
            p_acc, v_acc = hlc3 * vol, vol 
        else:
            # Perhitungan Dynamic VWAP (Adaptive EWMA)
            apt = df['apt_clamped'].iloc[i]
            alpha = 1.0 - np.exp(-np.log(2.0) / max(1.0, apt))
            p_acc = (1.0 - alpha) * p_acc + alpha * (hlc3 * vol)
            v_acc = (1.0 - alpha) * v_acc + alpha * vol
            
        vwap_values.append(p_acc / v_acc if v_acc > 0 else np.nan)

    df['dynamic_vwap'] = vwap_values
    return df

# --- Antarmuka Streamlit ---
st.set_page_config(page_title="Zeiierman VWAP Multi-Ticker", layout="wide")
st.title("📊 Dynamic Swing Anchored VWAP")

with st.sidebar:
    st.header("Konfigurasi")
    # Input Multi-Ticker
    ticker_input = st.text_input("Ticker (Pisahkan dengan koma)", value="SCMA, BBCA, ASII")
    prd = st.number_input("Swing Period", value=20, min_value=2, help="Periode untuk mencari High/Low")
    baseAPT = st.number_input("Base APT", value=20.0, help="Kecepatan tracking harga")
    useAdapt = st.checkbox("Adaptasi Volatilitas (ATR)", value=True)
    volBias = st.slider("Volatility Bias", 0.1, 15.0, 10.0)

if ticker_input:
    # Memproses list ticker
    raw_tickers = [t.strip().upper() for t in ticker_input.split(",")]
    
    for ticker in raw_tickers:
        # Menghapus suffix .JK jika ada, lalu menambahkannya secara paksa untuk yfinance
        clean_name = ticker.replace(".JK", "")
        search_name = f"{clean_name}.JK"
        
        with st.expander(label=f"Data Saham: {clean_name}", expanded=True):
            try:
                # Mengunduh data dari Yahoo Finance
                df = yf.download(search_name, period="150d", interval="1d", progress=False, auto_adjust=True)
                
                if df.empty:
                    st.warning(f"Data untuk {clean_name} tidak ditemukan.")
                    continue

                # Meratakan kolom jika formatnya MultiIndex
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                # Membersihkan kolom duplikat
                df = df.loc[:, ~df.columns.duplicated()]

                # Eksekusi logika VWAP
                result = calculate_vwap_logic(df.copy(), prd, baseAPT, useAdapt, volBias)
                
                # Memilih kolom untuk tabel
                cols_to_show = ['high', 'low', 'close', 'volume', 'dynamic_vwap', 'structure']
                final_table = result[cols_to_show].tail(20)

                # --- PERBAIKAN STYLER (Gunakan .map sebagai ganti .applymap) ---
                def style_structure(val):
                    if val in ['HH', 'HL']:
                        return 'background-color: #27ae60; color: white; font-weight: bold'
                    elif val in ['LL', 'LH']:
                        return 'background-color: #c0392b; color: white; font-weight: bold'
                    return ''

                styled_df = final_table.style.format({
                    'high': '{:.2f}', 'low': '{:.2f}', 'close': '{:.2f}', 
                    'dynamic_vwap': '{:.2f}', 'volume': '{:,.0f}'
                }).map(style_structure, subset=['structure'])

                st.table(styled_df)

            except Exception as e:
                st.error(f"Error pada ticker {clean_name}: {str(e)}")
else:
    st.info("Silakan masukkan kode saham pada sidebar (contoh: SCMA, TLKM, BBRI).")
