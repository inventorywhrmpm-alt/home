import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from datetime import date, timedelta

st.set_page_config(page_title="Price Action Predictor v2", layout="wide")

st.title("🎯 AI Price Action Predictor Pro")
st.markdown("Model ini menggunakan **Validation Split** untuk menghindari prediksi palsu.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Konfigurasi")
    ticker_input = st.text_input("Kode Saham (Tanpa .JK)", value="BBca").upper().strip()
    ticker = f"{ticker_input}.JK"
    
    years_back = st.slider("Data Historis (Tahun)", 1, 10, 5)
    training_days = years_back * 365

    btn_analyze = st.button("Latih & Prediksi", type="primary", use_container_width=True)

# --- FUNGSI DATA ---
def get_data(ticker, days):
    end = date.today()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start, end=end, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def add_features(df):
    # Hindari SettingWithCopyWarning
    df = df.copy()
    
    # 1. Indikator Momentum & Volatilitas
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    # 2. Moving Averages (Trend)
    df['MA20'] = ta.sma(df['Close'], length=20)
    df['MA50'] = ta.sma(df['Close'], length=50)
    
    # 3. Price Action: Gap & Body
    df['Pct_Change'] = df['Close'].pct_change()
    df['Gap'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)
    
    # 4. Target: Selisih harga besok (Bukan harga mutlak agar lebih stabil)
    # Kita memprediksi Log Return agar model lebih fokus pada pergerakan, bukan nominal
    df['Target_Return'] = np.log(df['Close'].shift(-1) / df['Close'])
    
    return df.dropna()

# --- EKSEKUSI ---
if btn_analyze:
    with st.spinner(f"Menganalisis {ticker}..."):
        raw_df = get_data(ticker, training_days)
        
        if raw_df.empty:
            st.error("Data tidak ditemukan.")
        else:
            df = add_features(raw_df)
            
            # FITUR TERPILIH
            features = ['RSI', 'ATR', 'MA20', 'MA50', 'Pct_Change', 'Gap']
            
            X = df[features]
            y = df['Target_Return']

            # --- VALIDASI: MENCEGAH OVERFITTING ---
            # Kita bagi data menjadi Train (80%) dan Test (20%)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

            model = RandomForestRegressor(n_estimators=500, max_depth=10, random_state=42)
            model.fit(X_train, y_train)

            # Hitung akurasi pada data yang BELUM pernah dilihat model (X_test)
            test_preds = model.predict(X_test)
            real_accuracy = r2_score(y_test, test_preds) * 100

            # --- PREDIKSI BESOK ---
            last_row_features = X.tail(1)
            pred_log_return = model.predict(last_row_features)[0]
            
            current_price = raw_df['Close'].iloc[-1]
            # Konversi balik dari log return ke harga estimasi
            pred_price = current_price * np.exp(pred_log_return)
            change_pct = ((pred_price - current_price) / current_price) * 100

            # --- TAMPILAN ---
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Harga Saat Ini", f"Rp {current_price:,.0f}")
            
            with col2:
                delta_color = "normal" if change_pct > 0 else "inverse"
                st.metric("Prediksi Harga Besok", f"Rp {pred_price:,.0f}", f"{change_pct:.2f}%", delta_color=delta_color)
            
            with col3:
                # Menampilkan akurasi asli (Out-of-sample)
                st.metric("Akurasi Validasi (R²)", f"{real_accuracy:.2f}%")

            st.divider()
            
            # --- STATUS SIGNAL ---
            st.subheader("📊 Signal Strength")
            if real_accuracy < 0:
                st.warning("⚠️ Model sedang kesulitan mengenali pola (Akurasi Minus). Jangan gunakan prediksi ini sebagai patokan utama.")
            elif change_pct > 0.5 and real_accuracy > 10:
                st.success("🚀 Sinyal BULLISH Terdeteksi")
            elif change_pct < -0.5 and real_accuracy > 10:
                st.error("📉 Sinyal BEARISH Terdeteksi")
            else:
                st.info("⚖️ Sinyal NETRAL / Konsolidasi")
