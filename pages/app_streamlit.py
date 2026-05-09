import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from datetime import date, timedelta

st.set_page_config(page_title="AI Direction Predictor", layout="wide")
st.title("🎯 AI Stock Direction Predictor (Binary)")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Konfigurasi")
    ticker_input = st.text_input("Kode Saham (Tanpa .JK)", value="BBCA").upper().strip()
    ticker = f"{ticker_input}.JK"
    btn_analyze = st.button("Latih & Prediksi Arah", type="primary", use_container_width=True)

# --- FUNGSI FITUR ---
def add_classification_features(df):
    df = df.copy()
    
    # 1. TARGET: 1 jika Besok Naik, 0 jika Besok Turun/Tetap
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    
    # 2. Fitur Momentum & Volatilitas
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['EMA_Diff'] = ta.ema(df['Close'], length=12) - ta.ema(df['Close'], length=26)
    
    # 3. Fitur Lag (Perubahan 3 hari terakhir)
    for i in range(1, 4):
        df[f'Return_Lag_{i}'] = df['Close'].pct_change(i)
        df[f'Vol_Lag_{i}'] = df['Volume'].pct_change(i)
    
    return df.dropna()

# --- EKSEKUSI ---
if btn_analyze:
    with st.spinner(f"Menganalisis pergerakan {ticker}..."):
        # Ambil data 5 tahun untuk pola yang lebih kuat
        end = date.today()
        start = end - timedelta(days=5*365)
        raw_df = yf.download(ticker, start=start, end=end, auto_adjust=True)
        
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.get_level_values(0)
            
        if not raw_df.empty:
            df = add_classification_features(raw_df)
            
            # Fitur yang digunakan untuk belajar
            features = ['RSI', 'EMA_Diff', 'Return_Lag_1', 'Return_Lag_2', 'Return_Lag_3', 
                        'Vol_Lag_1', 'Vol_Lag_2', 'Vol_Lag_3']
            
            X = df[features]
            y = df['Target']

            # Split Data (Time-Series Split: Jangan di-shuffle!)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

            # Latih Model Klasifikasi
            # Menggunakan class_weight='balanced' untuk menangani ketidakseimbangan tren
            model = RandomForestClassifier(n_estimators=500, max_depth=8, random_state=42, class_weight='balanced')
            model.fit(X_train, y_train)

            # --- PREDIKSI BESOK ---
            x_latest = X.tail(1)
            pred_direction = model.predict(x_latest)[0]
            pred_proba = model.predict_proba(x_latest)[0] # Peluang naik vs turun
            
            # Skor Akurasi
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)

            # --- DASHBOARD TAMPILAN ---
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Harga Saat Ini", f"Rp {raw_df['Close'].iloc[-1]:,.0f}")
            
            with col2:
                hasil = "NAIK 🚀" if pred_direction == 1 else "TURUN 📉"
                confidence = pred_proba[1] if pred_direction == 1 else pred_proba[0]
                st.metric("Prediksi Arah Besok", hasil, f"Confidence: {confidence:.2%}")
            
            with col3:
                st.metric("Akurasi Model (Validasi)", f"{acc:.2%}")

            st.divider()
            
            # Strategi Berdasarkan Confidence
            if acc > 0.51:
                if pred_direction == 1 and confidence > 0.55:
                    st.success(f"🔥 **SINYAL KUAT:** Model cukup yakin {ticker_input} akan naik besok.")
                elif pred_direction == 0 and confidence > 0.55:
                    st.error(f"⚠️ **PERINGATAN:** Model mendeteksi potensi penurunan besar besok.")
                else:
                    st.info("⚖️ **KONSOLIDASI:** Sinyal masih lemah, harga mungkin bergerak sideways.")
            else:
                st.warning("⚠️ **AKURASI RENDAH:** Model masih belajar. Jangan jadikan satu-satunya acuan.")
