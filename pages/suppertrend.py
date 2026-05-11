import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import numpy as np

# --- LOGIC SUPERTREND PERSISI ---
def calculate_supertrend(df, period=10, multiplier=1.0):
    # Gunakan RMA agar sama dengan TradingView
    df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=period, mamode="rma")
    df['src'] = (df['High'] + df['Low']) / 2
    
    # Hitung dasar band
    df['up_base'] = df['src'] - (multiplier * df['atr'])
    df['dn_base'] = df['src'] + (multiplier * df['atr'])
    
    # MENGATASI READ-ONLY: Ubah ke list Python murni agar bisa dimodifikasi
    close = df['Close'].tolist()
    upperband = df['up_base'].tolist()
    lowerband = df['dn_base'].tolist()
    
    size = len(df)
    trend = [1] * size
    
    # Mulai loop dari bar ke-1 (bar kedua)
    for i in range(1, size):
        # Jika nilai ATR masih NaN, lewati
        if np.isnan(upperband[i]) or np.isnan(lowerband[i]):
            continue
            
        # Logic Up: up := close[1] > up1 ? max(up, up1) : up
        if close[i-1] > upperband[i-1]:
            upperband[i] = max(upperband[i], upperband[i-1])
        
        # Logic Dn: dn := close[1] < dn1 ? min(dn, dn1) : dn
        if close[i-1] < lowerband[i-1]:
            lowerband[i] = min(lowerband[i], lowerband[i-1])
            
        # Logic Trend
        if close[i] > lowerband[i-1] and trend[i-1] == -1:
            trend[i] = 1
        elif close[i] < upperband[i-1] and trend[i-1] == 1:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]

    # Kembalikan ke DataFrame
    df['trend'] = trend
    df['signal'] = "-"
    df.loc[(df['trend'] == 1) & (df['trend'].shift(1) == -1), 'signal'] = "buy"
    df.loc[(df['trend'] == -1) & (df['trend'].shift(1) == 1), 'signal'] = "sell"
    
    return df

# --- UI STREAMLIT ---
st.set_page_config(page_title="Supertrend Fix", layout="wide")

st.sidebar.header("Setting")
ticker = st.sidebar.text_input("Kode Saham", value="SCMA").upper()
atr_p = st.sidebar.number_input("ATR Period", value=10)
atr_m = st.sidebar.number_input("Multiplier", value=1.0, step=0.1)

try:
    # Tarik data (Gunakan period minimal 1y agar perhitungan April akurat)
    df_raw = yf.download(f"{ticker}.JK", period="1y", interval="1d")
    
    if isinstance(df_raw.columns, pd.MultiIndex):
        df_raw.columns = df_raw.columns.get_level_values(0)

    if not df_raw.empty:
        # Proses kalkulasi
        df_res = calculate_supertrend(df_raw.copy(), atr_p, atr_m)
        
        # Filter & Format Tabel
        df_display = df_res[['Open', 'High', 'Low', 'Close', 'signal']].copy()
        df_display.index = df_display.index.strftime('%d-%b-%y')
        df_display = df_display.reset_index()
        df_display.columns = ['tanggal', 'open', 'high', 'low', 'close', 'signal']
        
        # Tampilkan data terbaru di atas
        df_display = df_display.sort_index(ascending=False)

        def color_signal(row):
            styles = [''] * len(row)
            if row['signal'] == 'buy': styles[5] = 'background-color: #90ee90; color: black;'
            elif row['signal'] == 'sell': styles[5] = 'background-color: #ff4d4d; color: white;'
            return styles

        st.title(f"Sinyal Supertrend: {ticker}.JK")
        st.table(df_display.head(25).style.apply(color_signal, axis=1).format({
            'open': '{:.0f}', 'high': '{:.0f}', 'low': '{:.0f}', 'close': '{:.0f}'
        }))
    else:
        st.error("Data tidak ditemukan.")
except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
