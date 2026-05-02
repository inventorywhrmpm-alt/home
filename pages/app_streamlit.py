import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from datetime import date, timedelta

st.set_page_config(page_title="Price Action Predictor", layout="wide")

st.title("🎯 Live Price Action Predictor")
st.markdown("Model ini melatih diri secara otomatis menggunakan data terbaru untuk memprediksi harga besok.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Konfigurasi")
    ticker_input = st.text_input("Kode Saham (Tanpa .JK)", value="BBCA").upper().strip()
    ticker = f"{ticker_input}.JK"
    
    # Ambil data 5 tahun ke belakang untuk training yang kuat
    years_back = st.slider("Data Historis (Tahun)", 1, 10, 5)
    training_days = years_back * 365

    btn_analyze = st.button("Latih & Prediksi", type="primary", use_container_width=True)

# --- FUNGSI ANALISA ---
def get_data(ticker, days):
    end = date.today()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start, end=end)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def add_features(df):
    # 1. Indikator Standar
    df['RSI'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)
    
    # 2. Price Action: Volatility & Spike
    df['Body'] = abs(df['Close'] - df['Open'])
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    df['Vol_Spike'] = (df['Volume'] > (df['Vol_Avg'] * 1.5)).astype(int)
    
    # 3. Support & Resistance (Pivot Points Sederhana)
    df['High_Roll'] = df['High'].rolling(window=20).max()
    df['Low_Roll'] = df['Low'].rolling(window=20).min()
    
    # 4. Momentum Lag
    df['Return_1d'] = df['Close'].pct_change(1)
    df['Return_5d'] = df['Close'].pct_change(5)
    
    # TARGET: Harga Close Besok (Untuk Regresi)
    df['Target_Price'] = df['Close'].shift(-1)
    
    return df.dropna()

# --- EKSEKUSI ---
if btn_analyze:
    with st.spinner(f"Sedang menarik data {ticker} dan melatih AI..."):
        raw_df = get_data(ticker, training_days)
        
        if raw_df.empty:
            st.error("Data tidak ditemukan.")
        else:
            df = add_features(raw_df)
            
            # FITUR UNTUK MODEL
            features = ['Open', 'Close', 'Volume', 'RSI', 'MACD_12_26_9', 
                        'Vol_Spike', 'Return_1d', 'Return_5d', 'High_Roll', 'Low_Roll']
            
            X = df[features]
            y = df['Target_Price']

            # Latih Model Regresi (Bukan Klasifikasi agar dapat angka harga)
            model = RandomForestRegressor(n_estimators=200, random_state=42)
            model.fit(X, y)

            # --- PREDIKSI MASA DEPAN ---
            # Ambil baris terakhir dari data asli untuk input prediksi besok
            last_data = raw_df.iloc[-1:].copy()
            # Hitung indikator untuk baris terakhir tersebut
            full_data_with_last = add_features(raw_df) 
            x_input = full_data_with_last[features].iloc[-1:]
            
            pred_price = model.predict(x_input)[0]
            current_price = raw_df['Close'].iloc[-1]
            change_pct = ((pred_price - current_price) / current_price) * 100

            # --- TAMPILAN DASHBOARD ---
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Harga Saat Ini", f"Rp {current_price:,.0f}")
            
            with col2:
                color = "normal" if change_pct > 0 else "inverse"
                st.metric("Prediksi Harga Besok", f"Rp {pred_price:,.0f}", f"{change_pct:.2f}%", delta_color=color)
            
            with col3:
                # Menghitung akurasi simulasi pada data training
                score = model.score(X, y) * 100
                st.metric("Confidence Score (R²)", f"{score:.2f}%")

            st.divider()

            # --- PRICE ACTION DETAIL ---
            st.subheader("💡 Analisa Price Action & SNR")
            c1, c2, c3 = st.columns(3)
            
            last_row = full_data_with_last.iloc[-1]
            with c1:
                st.write(f"**Support (20d):** {last_row['Low_Roll']:,.0f}")
                st.write(f"**Resistance (20d):** {last_row['High_Roll']:,.0f}")
            
            with c2:
                vol_status = "SPIKE! 🔥" if last_row['Vol_Spike'] == 1 else "Normal"
                st.write(f"**Status Volume:** {vol_status}")
                st.write(f"**RSI (14):** {last_row['RSI']:.2f}")

            with c3:
                trend = "Bullish" if last_row['Return_5d'] > 0 else "Bearish"
                st.write(f"**Trend 5 Hari:** {trend}")
                st.write(f"**MACD:** {last_row['MACD_12_26_9']:.4f}")

            # Tabel Data Terakhir
            st.subheader("Data Historis Terakhir")
            st.dataframe(full_data_with_last[features + ['Target_Price']].tail(10))

            st.info("""
            **Cara Membaca:** 
            - **Confidence Score:** Semakin mendekati 100%, semakin baik model mempelajari pola masa lalu.
            - **Prediksi Harga:** Ini adalah angka estimasi penutupan market besok.
            - Gunakan Support & Resistance sebagai batasan Stop Loss dan Take Profit manual.
            """)
st.divider()
st.caption("💡 Dibuat oleh Yonz Suharyono | Menggunakan Random Forest Classifier")
