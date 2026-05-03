import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

st.set_page_config(page_title="Stock Predictor Pro", layout="wide")
st.title("📈 AI Stock Dashboard")

ticker_input = st.sidebar.text_input("Ticker (Tanpa .JK)", value="SCMA").upper()
ticker = f"{ticker_input}.JK"

@st.cache_data
def load_data(symbol):
    return yf.download(symbol, start="2020-01-01")

if ticker_input:
    df = load_data(ticker)
    
    if not df.empty:
        # Preprocessing Sederhana
        df['S_5'] = df['Close'].rolling(window=5).mean()
        df['V_5'] = df['Volume'].rolling(window=5).mean()
        df = df.dropna()

        # Model
        X = df[['S_5', 'V_5']]
        y = df['Close']
        split = int(len(df) * 0.8)
        model = RandomForestRegressor(n_estimators=50).fit(X[:split], y[:split].values.ravel())
        y_pred = model.predict(X[split:])

        # --- BAGIAN GRAFIK ---
        try:
            st.subheader("Interactive Candlestick Chart")
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                name='Market'
            )])
            
            # Tambahkan Prediksi
            fig.add_trace(go.Scatter(x=df.index[split:], y=y_pred, name='AI Prediction', line=dict(color='orange')))
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            
            # Perintah Utama
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error("Gagal menampilkan grafik Plotly.")
            st.exception(e) # Ini akan menampilkan detail error jika ada
            
        st.metric("Estimasi Harga Besok", f"Rp{model.predict(X.tail(1))[0]:.2f}")
