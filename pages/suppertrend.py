import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf

# --- LOGIC SUPERTREND ---
def calculate_supertrend(df, period=10, multiplier=1.0):
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=period)
    src = (df['High'] + df['Low']) / 2
    df['up'] = src - (multiplier * atr)
    df['dn'] = src + (multiplier * atr)
    df['trend'] = 1
    
    for i in range(1, len(df)):
        prev_close = df.loc[df.index[i-1], 'Close']
        df.loc[df.index[i], 'up'] = df.loc[df.index[i], 'up'] if prev_close > df.loc[df.index[i-1], 'up'] else max(df.loc[df.index[i], 'up'], df.loc[df.index[i-1], 'up'])
        df.loc[df.index[i], 'dn'] = df.loc[df.index[i], 'dn'] if prev_close < df.loc[df.index[i-1], 'dn'] else min(df.loc[df.index[i], 'dn'], df.loc[df.index[i-1], 'dn'])
        
        prev_trend = df.loc[df.index[i-1], 'trend']
        if prev_trend == -1 and df.loc[df.index[i], 'Close'] > df.loc[df.index[i-1], 'dn']:
            df.loc[df.index[i], 'trend'] = 1
        elif prev_trend == 1 and df.loc[df.index[i], 'Close'] < df.loc[df.index[i-1], 'up']:
            df.loc[df.index[i], 'trend'] = -1
        else:
            df.loc[df.index[i], 'trend'] = prev_trend
    
    df['signal'] = "-"
    df.loc[(df['trend'] == 1) & (df['trend'].shift(1) == -1), 'signal'] = "buy"
    df.loc[(df['trend'] == -1) & (df['trend'].shift(1) == 1), 'signal'] = "sell"
    return df

# --- UI STREAMLIT ---
st.set_page_config(page_title="IDX Supertrend OHLC", layout="wide")

st.title("Tabel Sinyal Supertrend (OHLC)")

# Input Sidebar agar area utama luas untuk tabel
st.sidebar.header("Filter & Parameter")
ticker = st.sidebar.text_input("Kode Saham", value="MINA").upper()
atr_p = st.sidebar.number_input("ATR Period", value=10)
atr_m = st.sidebar.number_input("Multiplier", value=1.0, step=0.1)
show_n = st.sidebar.slider("Tampilkan jumlah baris", 5, 50, 15)

try:
    df_raw = yf.download(f"{ticker}.JK", period="6mo", interval="1d")
    if isinstance(df_raw.columns, pd.MultiIndex):
        df_raw.columns = df_raw.columns.get_level_values(0)

    if not df_raw.empty:
        df_res = calculate_supertrend(df_raw.copy(), atr_p, atr_m)
        
        # Mengambil kolom OHLC + Signal
        df_display = df_res[['Open', 'High', 'Low', 'Close', 'signal']].copy()
        
        # Format Tanggal
        df_display.index = df_display.index.strftime('%d-%b-%y')
        df_display = df_display.reset_index()
        
        # Rename kolom agar kecil semua sesuai seleramu
        df_display.columns = ['tanggal', 'open', 'high', 'low', 'close', 'signal']
        
        # Urutkan data terbaru di paling atas
        df_display = df_display.iloc[::-1]

        # Fungsi styling untuk mewarnai kolom signal
        def style_rows(row):
            styles = [''] * len(row)
            if row['signal'] == 'buy':
                styles[5] = 'background-color: #90ee90; color: black; font-weight: bold;'
            elif row['signal'] == 'sell':
                styles[5] = 'background-color: #ff4d4d; color: white; font-weight: bold;'
            return styles

        # Tampilkan tabel
        st.table(
            df_display.head(show_n).style.apply(style_rows, axis=1).format({
                'open': '{:.0f}', 
                'high': '{:.0f}', 
                'low': '{:.0f}', 
                'close': '{:.0f}'
            })
        )
        
        st.caption(f"Menampilkan {show_n} data perdagangan terakhir untuk {ticker}.JK")
        
    else:
        st.error("Data tidak ditemukan atau kode saham salah.")
except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
