import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import yfinance as yf

# --- FUNGSI LOGIC SUPERTREND (SAMA SEPERTI SEBELUMNYA) ---
def calculate_supertrend(df, period=10, multiplier=3.0):
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=period)
    src = (df['High'] + df['Low']) / 2
    df['up'] = src - (multiplier * atr)
    df['dn'] = src + (multiplier * atr)
    df['trend'] = 1
    df['st'] = 0.0

    for i in range(1, len(df)):
        prev_close = df.loc[df.index[i-1], 'Close']
        # Up Trend
        curr_up = df.loc[df.index[i], 'up']
        prev_up = df.loc[df.index[i-1], 'up']
        df.loc[df.index[i], 'up'] = curr_up if prev_close > prev_up else max(curr_up, prev_up)
        # Down Trend
        curr_dn = df.loc[df.index[i], 'dn']
        prev_dn = df.loc[df.index[i-1], 'dn']
        df.loc[df.index[i], 'dn'] = curr_dn if prev_close < prev_dn else min(curr_dn, prev_dn)
        
        prev_trend = df.loc[df.index[i-1], 'trend']
        if prev_trend == -1 and df.loc[df.index[i], 'Close'] > df.loc[df.index[i-1], 'dn']:
            df.loc[df.index[i], 'trend'] = 1
        elif prev_trend == 1 and df.loc[df.index[i], 'Close'] < df.loc[df.index[i-1], 'up']:
            df.loc[df.index[i], 'trend'] = -1
        else:
            df.loc[df.index[i], 'trend'] = prev_trend
            
        df.loc[df.index[i], 'st'] = df.loc[df.index[i], 'up'] if df.loc[df.index[i], 'trend'] == 1 else df.loc[df.index[i], 'dn']

    df['buy_signal'] = (df['trend'] == 1) & (df['trend'].shift(1) == -1)
    df['sell_signal'] = (df['trend'] == -1) & (df['trend'].shift(1) == 1)
    return df

# --- UI STREAMLIT ---
st.set_page_config(layout="wide", page_title="Supertrend IDX Label Harga")

st.sidebar.header("Konfigurasi")
ticker_input = st.sidebar.text_input("Kode Saham (Tanpa .JK)", value="MINA").upper()
ticker_idx = f"{ticker_input}.JK"

data_period = st.sidebar.selectbox("Rentang Waktu", options=['3mo', '6mo', '1y', '2y'], index=1)
atr_p = st.sidebar.number_input("ATR Period", value=10)
atr_m = st.sidebar.number_input("ATR Multiplier", value=1.0, step=0.1) # Di gambar kamu pakenya multiplier 1.0

try:
    df_raw = yf.download(ticker_idx, period=data_period, interval='1d')
    if isinstance(df_raw.columns, pd.MultiIndex):
        df_raw.columns = df_raw.columns.get_level_values(0)

    if not df_raw.empty:
        df_result = calculate_supertrend(df_raw.copy(), atr_p, atr_m)

        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df_result.index, open=df_result['Open'], high=df_result['High'],
            low=df_result['Low'], close=df_result['Close'], name=ticker_input
        ))

        # Supertrend Line
        df_result['up_line'] = df_result['st'].where(df_result['trend'] == 1)
        df_result['dn_line'] = df_result['st'].where(df_result['trend'] == -1)

        fig.add_trace(go.Scatter(x=df_result.index, y=df_result['up_line'], line=dict(color='#00FF00', width=2), name="Up"))
        fig.add_trace(go.Scatter(x=df_result.index, y=df_result['dn_line'], line=dict(color='#FF0000', width=2), name="Down"))

        # --- LABEL HARGA BUY ---
        buy_sig = df_result[df_result['buy_signal']]
        for index, row in buy_sig.iterrows():
            fig.add_annotation(
                x=index, y=row['Low'],
                text=f"{row['Close']:.0f}", # Menampilkan harga Close
                showarrow=True, arrowhead=1, ax=0, ay=25,
                bgcolor="#00FF00", font=dict(color="white", size=12),
                bordercolor="green", borderpad=4
            )

        # --- LABEL HARGA SELL ---
        sell_sig = df_result[df_result['sell_signal']]
        for index, row in sell_sig.iterrows():
            fig.add_annotation(
                x=index, y=row['High'],
                text=f"{row['Close']:.0f}", # Menampilkan harga Close
                showarrow=True, arrowhead=1, ax=0, ay=-25,
                bgcolor="#FF0000", font=dict(color="white", size=12),
                bordercolor="red", borderpad=4
            )

        fig.update_layout(height=700, template='plotly_dark', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        st.success(f"Berhasil memuat {ticker_input}. Trend saat ini: {'BULLISH' if df_result['trend'].iloc[-1] == 1 else 'BEARISH'}")
    else:
        st.error("Data tidak ditemukan.")
except Exception as e:
    st.error(f"Error: {e}")
