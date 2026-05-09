import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from datetime import date, timedelta

st.set_page_config(page_title="AI Price Action Pro", layout="wide")
st.title("🎯 AI Predictor: Percentage & Lag Edition")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Konfigurasi")
    ticker_input = st.text_input("Kode Saham (Tanpa .JK)", value="BBCA").upper().strip()
    ticker = f"{ticker_input}.JK"
    btn_analyze = st.button("Latih & Prediksi", type="primary", use_container_width=True)

# --- FUNGSI DATA ---
def add_features_with_lag(df):
    df = df.copy()
    
    # 1. Target: Persentase Perubahan (Log Return) untuk Besok
    # Ini jauh lebih stasioner dibanding harga nominal
    df['Target_Pct'] = np.log(df['Close'].shift(-1) / df['Close'])
    
    # 2. Fitur Lag (t-1, t-2, t-3)
    # Memberikan AI "memori" tentang pergerakan harga 3 hari terakhir
    for i in range(1, 4):
        df[f'Lag_Return_{i}'] = df['Close'].pct_change(i)
        df[f'Lag_Vol_{i}'] = df['Volume'].pct_change(i)
    
    # 3. Indikator Teknis Tambahan
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    return df.dropna()

# --- EKSEKUSI ---
if btn_analyze:
    with st.spinner(f"Melatih model dengan fitur Lag untuk {ticker}..."):
        # Ambil data 5 tahun untuk histori yang cukup
        end = date.today()
        start = end - timedelta(days=5*365)
        raw_df = yf.download(ticker, start=start, end=end, auto_adjust=True)
        
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.get_level_values(0)
            
        if not raw_df.empty:
            df = add_features_with_lag(raw_df)
            
            # Definisi Fitur (Termasuk Lag)
            features = ['RSI', 'ATR', 'Lag_Return_1', 'Lag_Return_2', 'Lag_Return_3', 
                        'Lag_Vol_1', 'Lag_Vol_2', 'Lag_Vol_3']
            
            X = df[features]
            y = df['Target_Pct']

            # Split Data secara kronologis
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

            # Latih Model
            model = RandomForestRegressor(n_estimators=500, max_depth=10, random_state=42)
            model.fit(X_train, y_train)

            # --- PREDIKSI ---
            # Ambil baris data paling terakhir (hari ini) untuk memprediksi besok
            x_latest = X.tail(1)
            pred_pct = model.predict(x_latest)[0]
            
            current_price = raw_df['Close'].iloc[-1]
            pred_price = current_price * np.exp(pred_pct) # Konversi balik dari log ke nominal
            change_real_pct = (np.exp(pred_pct) - 1) * 100

            # Hitung Skor Akurasi Validasi
            test_preds = model.predict(X_test)
            r2_val = r2_score(y_test, test_preds)

            # --- DASHBOARD ---
            col1, col2, col3 = st.columns(3)
            col1.metric("Harga Terakhir", f"Rp {current_price:,.0f}")
            
            # Tampilkan Prediksi dalam Persentase
            color = "normal" if change_real_pct > 0 else "inverse"
            col2.metric("Prediksi Perubahan", f"{change_real_pct:.2f}%", f"Est: Rp {pred_price:,.0f}", delta_color=color)
            
            # Akurasi yang lebih jujur
            col3.metric("Akurasi Validasi (R²)", f"{r2_val:.2%}")

            if r2_val < 0:
                st.error("⚠️ **Akurasi Validasi Minus:** Model kesulitan menemukan pola pada lag ini. Coba tambahkan data atau ganti saham.")
            else:
                st.success("✅ Model berhasil divalidasi dengan data terbaru.")
