import streamlit as st
import pandas as pd
import numpy as np

def calculate_vwap(df, prd=50, baseAPT=20.0, useAdapt=False, volBias=10.0):
    # 1. Identifikasi Swing High/Low (Pivots)
    df['ph'] = df['high'].rolling(window=prd*2+1, center=True).max()
    df['pl'] = df['low'].rolling(window=prd*2+1, center=True).min()
    
    # 2. Adaptation (ATR Ratio)
    atr_len = 50
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.ewm(span=atr_len, adjust=False).mean() # rma di pine ≈ ewm
    df['atrAvg'] = df['atr'].ewm(span=atr_len, adjust=False).mean()
    
    df['ratio'] = np.where(df['atrAvg'] > 0, df['atr'] / df['atrAvg'], 1.0)
    
    if useAdapt:
        apt_raw = baseAPT / (df['ratio'] ** volBias)
    else:
        apt_raw = pd.Series(baseAPT, index=df.index)
        
    df['apt_clamped'] = apt_raw.clip(5.0, 300.0).round()
    
    # Fungsi Alpha dari Pine Script
    def get_alpha(apt):
        decay = np.exp(-np.log(2.0) / np.maximum(1.0, apt))
        return 1.0 - decay

    # 3. Main Logic (Looping untuk meniru stateful behavior Pine Script)
    # Karena indikator ini 'anchored' dan 'dynamic', kita harus melakukan iterasi
    vwap_values = []
    p = 0.0
    vol_acc = 0.0
    current_dir = 0
    last_anchor_idx = 0
    
    # Identifikasi titik pivot (sederhana) untuk menentukan arah (dir)
    df['is_high'] = (df['high'] == df['high'].rolling(prd).max())
    df['is_low'] = (df['low'] == df['low'].rolling(prd).min())

    for i in range(len(df)):
        hlc3 = (df['high'].iloc[i] + df['low'].iloc[i] + df['close'].iloc[i]) / 3
        vol = df['volume'].iloc[i]
        
        # Deteksi perubahan arah (Swing)
        new_dir = current_dir
        if df['is_high'].iloc[i]:
            new_dir = -1
        elif df['is_low'].iloc[i]:
            new_dir = 1
            
        # Jika arah berubah (Anchor point baru)
        if new_dir != current_dir:
            current_dir = new_dir
            p = hlc3 * vol
            vol_acc = vol
        else:
            # Perhitungan Dynamic (Adaptive EWMA)
            alpha = get_alpha(df['apt_clamped'].iloc[i])
            p = (1.0 - alpha) * p + alpha * (hlc3 * vol)
            vol_acc = (1.0 - alpha) * vol_acc + alpha * vol
            
        vwap_val = p / vol_acc if vol_acc > 0 else np.nan
        vwap_values.append(vwap_val)

    df['Dynamic_VWAP'] = vwap_values
    df['Trend'] = np.where(df['is_high'], 'Downtrend (R)', np.where(df['is_low'], 'Uptrend (S)', 'Neutral'))
    
    return df

# --- UI Streamlit ---
st.set_page_config(page_title="Dynamic Swing VWAP Converter", layout="wide")
st.title("📊 Dynamic Swing Anchored VWAP (Python Version)")

st.sidebar.header("Konfigurasi Parameter")
prd = st.sidebar.number_input("Swing Period", value=50, min_value=2)
baseAPT = st.sidebar.number_input("Adaptive Price Tracking", value=20.0, min_value=1.0)
useAdapt = st.sidebar.checkbox("Adapt APT by ATR ratio", value=False)
volBias = st.sidebar.slider("Volatility Bias", 0.1, 20.0, 10.0)

# Dummy Data - Di dunia nyata, Anda akan mengupload CSV atau fetch dari API
st.subheader("Input Data (Contoh)")
data = {
    'high': [150, 152, 153, 151, 149, 148, 147, 150, 155, 158],
    'low': [148, 149, 150, 148, 146, 145, 144, 146, 152, 154],
    'close': [149, 151, 152, 149, 147, 146, 145, 149, 154, 157],
    'volume': [1000, 1200, 1100, 1300, 900, 800, 1500, 2000, 2500, 2200]
}
df_input = pd.DataFrame(data)

if st.button("Hitung VWAP"):
    result_df = calculate_vwap(df_input.copy(), prd, baseAPT, useAdapt, volBias)
    
    st.subheader("Hasil Kalkulasi Tabel")
    # Menampilkan tabel dengan highlight trend
    st.dataframe(result_df[['high', 'low', 'close', 'volume', 'Dynamic_VWAP', 'Trend']].style.highlight_max(axis=0))
    
    st.download_button(
        label="Download Tabel sebagai CSV",
        data=result_df.to_csv().encode('utf-8'),
        file_name='vwap_result.csv',
        mime='text/csv',
    )
