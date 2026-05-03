import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- FUNGSI LOGIC SUPERTREND ---
def calculate_supertrend(df, period=10, multiplier=1.0):
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=period)
    src = (df['High'] + df['Low']) / 2
    df['up'] = src - (multiplier * atr)
    df['dn'] = src + (multiplier * atr)
    df['trend'] = 1
    df['st'] = 0.0

    for i in range(1, len(df)):
        prev_close = df.loc[df.index[i-1], 'Close']
        curr_up, prev_up = df.loc[df.index[i], 'up'], df.loc[df.index[i-1], 'up']
        df.loc[df.index[i], 'up'] = curr_up if prev_close > prev_up else max(curr_up, prev_up)
        curr_dn, prev_dn = df.loc[df.index[i], 'dn'], df.loc[df.index[i-1], 'dn']
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

# --- CONFIG & CSS ---
st.set_page_config(layout="wide", page_title="IDX Supertrend Dashboard")

st.markdown("""
<style>
    .main { background-color: #050a0e; }
    .stMetric { background-color: #0d1a24; border: 1px solid #1f3747; padding: 15px; border-radius: 10px; }
    .card-box {
        background-color: #0d1a24;
        border: 1px solid #1f3747;
        border-radius: 12px;
        padding: 15px;
        height: 100%;
    }
    .card-title { color: #e0e0e0; font-size: 16px; font-weight: bold; margin-bottom: 10px; }
    .big-num { font-size: 35px; font-weight: bold; text-align: center; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("Konfigurasi")
ticker_input = st.sidebar.text_input("Kode Saham", value="MINA").upper()
ticker_idx = f"{ticker_input}.JK"
data_period = st.sidebar.selectbox("Rentang Waktu", ['6mo', '1y', '2y'], index=0)
atr_p = st.sidebar.number_input("ATR Period", value=10)
atr_m = st.sidebar.number_input("ATR Multiplier", value=1.0, step=0.1)

# --- PROCESSING ---
try:
    df = yf.download(ticker_idx, period=data_period, interval='1d')
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    if not df.empty:
        df = calculate_supertrend(df.copy(), atr_p, atr_m)
        
        # --- UI LAYOUT ---
        st.subheader(f"IDX Supertrend Dashboard | {ticker_idx}")
        
        row1_col1, row1_col2 = st.columns(2)
        
        # Menyiapkan data untuk Chart Sinyal (Group by Month)
        df_signals = df[(df['buy_signal']) | (df['sell_signal'])].copy()
        df_signals['Month'] = df_signals.index.strftime('%b %Y')
        
        def create_signal_chart(signal_type, color):
            sig_data = df_signals[df_signals[f'{signal_type}_signal']]
            summary = sig_data.groupby('Month').size().reset_index(name='Counts')
            # Ambil harga terakhir untuk label (seperti di gambar)
            prices = sig_data.groupby('Month')['Close'].last().values
            
            fig = go.Figure(data=[go.Bar(
                x=summary['Month'], y=prices,
                text=prices.round(0), textposition='outside',
                marker_color=color, opacity=0.7,
                hovertemplate='Bulan: %{x}<br>Harga: %{y}<extra></extra>'
            )])
            fig.update_layout(
                height=250, margin=dict(l=0,r=0,t=30,b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'), yaxis=dict(showgrid=True, gridcolor='#1f3747')
            )
            return fig

        with row1_col1:
            with st.container():
                st.markdown(f'<div class="card-box"><div class="card-title">Sinyal Buy Saham {ticker_input}</div>', unsafe_allow_html=True)
                st.plotly_chart(create_signal_chart('buy', '#00ff88'), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        with row1_col2:
            with st.container():
                st.markdown(f'<div class="card-box"><div class="card-title">Sinyal Sell Saham {ticker_input}</div>', unsafe_allow_html=True)
                st.plotly_chart(create_signal_chart('sell', '#ff4b4b'), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        row2_col1, row2_col2 = st.columns([1, 1.5])
        
        with row2_col1:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Metrik Kumulatif (3 Bulan Terakhir)</div>', unsafe_allow_html=True)
            last_3m = df[df.index > (df.index[-1] - timedelta(days=90))]
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<p style='color:#b0b0b0;text-align:center'>Total Buy</p><p class='big-num' style='color:#00ff88'>{last_3m['buy_signal'].sum()}</p>", unsafe_allow_html=True)
            c2.markdown(f"<p style='color:#b0b0b0;text-align:center'>Total Sell</p><p class='big-num' style='color:#ff4b4b'>{last_3m['sell_signal'].sum()}</p>", unsafe_allow_html=True)
            avg_b = last_3m[last_3m['buy_signal']]['Close'].mean()
            c3.markdown(f"<p style='color:#b0b0b0;text-align:center'>Avg Harga Buy</p><p class='big-num'>{avg_b if not pd.isna(avg_b) else 0:,.0f}</p>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with row2_col2:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Tampilan Data Mentah</div>', unsafe_allow_html=True)
            raw_display = df_signals[['Close', 'Open', 'High', 'Low']].tail(10).reset_index()
            raw_display['Signal'] = df_signals['buy_signal'].apply(lambda x: 'Buy' if x else 'Sell').tail(10).values
            st.dataframe(raw_display.sort_values(by='Date', ascending=False), use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")
