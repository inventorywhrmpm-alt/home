import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from datetime import date, timedelta

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI Stock Classifier Pro", layout="wide")

st.title("🎯 AI Stock Direction Predictor")
st.markdown("""
Model ini memprediksi **Arah Pergerakan (Naik/Turun)** untuk hari bursa berikutnya. 
Akurasi di atas **51-55%** sudah dianggap sangat baik untuk data pasar saham.
""")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Konfigurasi Model")
    ticker_input = st.text_input("Kode Saham IDX (contoh: BBCA)", value="BBCA").upper().strip()
    ticker = f"{ticker_input}.JK"
    
    st.info("Menggunakan data historis 5 tahun terakhir untuk melatih pola.")
    btn_analyze = st.button("Latih & Prediksi", type="primary", use_container_width=True)

# --- FUNGSI PENGOLAHAN DATA ---
def get_clean_data(ticker):
    # Ambil data historis
    end = date.today()
    start = end - timedelta(days=5*365)
    df = yf.download(ticker, start=start, end=end, auto_adjust=True)
    
    if df.empty:
        return None
        
    # Perbaikan format kolom yfinance (jika MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.copy()

    # 1. TARGET: 1 jika Harga Besok > Harga Hari Ini, else 0
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)

    # 2. FITUR TEKNIS
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df['EMA_12'] = ta.ema(df['Close'], length=12)
    df['EMA_26'] = ta.ema(df['Close'], length=26)
    df['MACD_Diff'] = df['EMA_12'] - df['EMA_26']

    # 3. FITUR LAG (Memori Harga 3 Hari Terakhir)
    for i in range(1, 4):
        df[f'Return_Lag_{i}'] = df['Close'].pct_change(i)
        df[f'Vol_Lag_{i}'] = df['Volume'].pct_change(i)

    # 4. PEMBERSIHAN DATA (Mencegah ValueError)
    # Ganti infinity dengan NaN, lalu hapus semua baris yang ada NaN
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    
    return df

# --- PROSES UTAMA ---
if btn_analyze:
    with st.spinner(f"Menganalisis {ticker}..."):
        df = get_clean_data(ticker)
        
        if df is None or len(df) < 100:
            st.error("Data tidak cukup atau kode saham salah. Pastikan kode terdaftar di Yahoo Finance.")
        else:
            # Seleksi Fitur untuk Model
            features = ['RSI', 'ATR', 'MACD_Diff', 
                        'Return_Lag_1', 'Return_Lag_2', 'Return_Lag_3',
                        'Vol_Lag_1', 'Vol_Lag_2', 'Vol_Lag_3']
            
            X = df[features]
            y = df['Target']

            # Split Data (Tanpa Shuffle untuk menjaga urutan waktu bursa)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

            # Inisialisasi Model Klasifikasi
            model = RandomForestClassifier(
                n_estimators=500, 
                max_depth=8, 
                random_state=42, 
                class_weight='balanced' # Menyeimbangkan porsi Naik/Turun
            )
            
            # Training
            model.fit(X_train, y_train)

            # --- PREDIKSI UNTUK BESOK ---
            last_row = X.tail(1)
            prediction = model.predict(last_row)[0]
            probabilities = model.predict_proba(last_row)[0] # [Probabilitas Turun, Probabilitas Naik]

            # Evaluasi Akurasi pada data Test
            y_pred = model.predict(X_test)
            acc_score = accuracy_score(y_test, y_pred)

            # --- TAMPILAN DASHBOARD ---
            st.divider()
            c1, c2, c3 = st.columns(3)
            
            current_price = df['Close'].iloc[-1]
            c1.metric("Harga Terakhir", f"Rp {current_price:,.0f}")
            
            # Penentuan Label Prediksi
            if prediction == 1:
                label_pred = "NAIK 🚀"
                conf_val = probabilities[1]
                delta_type = "normal"
            else:
                label_pred = "TURUN 📉"
                conf_val = probabilities[0]
                delta_type = "inverse"

            c2.metric("Prediksi Arah Besok", label_pred, f"Confidence: {conf_val:.2%}", delta_color=delta_type)
            c3.metric("Akurasi Model (Validasi)", f"{acc_score:.2%}")

            # --- INTEPRETASI ---
            st.subheader("💡 Analisa Strategi")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if acc_score > 0.51:
                    st.success(f"Model memiliki akurasi di atas ambang batas standar (>{acc_score:.0%}). Sinyal ini cukup layak dipertimbangkan.")
                else:
                    st.warning("Akurasi model masih rendah. Disarankan untuk menambah indikator teknis lain atau mencoba timeframe yang berbeda.")

            with col_b:
                if conf_val > 0.60:
                    st.info(f"Tingkat kepercayaan model sangat tinggi ({conf_val:.2%}). Pola historis menunjukkan probabilitas kuat untuk arah ini.")
                else:
                    st.write("Tingkat kepercayaan sedang. Pergerakan harga mungkin akan cenderung sideways atau konsolidasi.")

            # Menampilkan Data Terakhir yang diolah
            with st.expander("Lihat Data Fitur Terakhir"):
                st.dataframe(last_row)

st.divider()
st.caption("Disclaimer: Prediksi ini berbasis AI dan data historis. Tidak ada jaminan akurasi 100%. Investasi saham berisiko tinggi.")
