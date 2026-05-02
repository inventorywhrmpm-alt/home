import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import date
import io

st.set_page_config(page_title="Stock ML Dataset Creator", layout="wide")

st.title("🤖 Stock ML Dataset Generator")
st.write("Dataset ini dirancang dengan label Naik, Turun, dan Tetap untuk kebutuhan training model.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Konfigurasi")
    ticker_input = st.text_input("Kode Saham (Tanpa .JK)", value="BBCA").upper().strip()
    ticker = f"{ticker_input}.JK"
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Mulai", value=pd.to_datetime("2023-01-01"))
    with col2:
        end_date = st.date_input("Akhir", value=date.today())

    vol_period = st.number_input("Periode Rata-rata Vol", min_value=5, max_value=20, value=14)
    btn_fetch = st.button("Generate Dataset")

# --- FUNGSI LOGIKA ---
def classify_volume(current_vol, avg_vol):
    if current_vol > (1.5 * avg_vol): return "HIGH"
    elif current_vol < (0.7 * avg_vol): return "LOW"
    else: return "NORMAL"

def label_movement(change):
    if change > 0: return "NAIK"
    elif change < 0: return "TURUN"
    else: return "TETAP"

# --- EKSEKUSI ---
if btn_fetch:
    try:
        # Buffer 50 hari untuk indikator teknikal
        fetch_start = start_date - pd.Timedelta(days=50)
        df = yf.download(ticker, start=fetch_start, end=end_date)
        
        if df.empty:
            st.error("Data tidak ditemukan!")
        else:
            # Perbaikan MultiIndex yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 1. Indikator Teknikal (Features)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            macd = ta.macd(df['Close'])
            df = pd.concat([df, macd], axis=1)
            
            # 2. Volume Status
            df['Vol_Avg'] = df['Volume'].rolling(window=vol_period).mean()
            df['Volume_Status'] = df.apply(lambda x: classify_volume(x['Volume'], x['Vol_Avg']), axis=1)

            # 3. Labeling untuk Machine Learning
            # 'Change' adalah pergerakan hari ini vs kemarin
            df['Daily_Change'] = df['Close'].diff()
            
            # Target: Pergerakan harga besok (Shift -1)
            # Ini yang biasanya ditebak oleh model ML
            df['Next_Day_Change'] = df['Daily_Change'].shift(-1)
            df['Label_Text'] = df['Next_Day_Change'].apply(label_movement)
            
            # Label Numerik (Sering digunakan di algoritma seperti SVM, Random Forest, atau XGBoost)
            # Naik = 1, Tetap = 0, Turun = -1
            df['Label_Num'] = df['Next_Day_Change'].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))

            # Potong sesuai rentang user
            df_final = df.loc[start_date:].copy()
            
            # --- TAMPILAN ---
            st.subheader(f"Dataset Saham {ticker_input}")
            st.info("Catatan: Kolom 'Label_Text' dan 'Label_Num' merujuk pada pergerakan harga di hari kerja berikutnya (Next Day).")
            
            # Preview Tabel (Urutan terbaru di atas)
            st.dataframe(df_final.sort_index(ascending=False), use_container_width=True)

            # --- DOWNLOAD DATASET ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, sheet_name='ML_Dataset')
            
            st.download_button(
                label="📥 Download Dataset (Excel)",
                data=output.getvalue(),
                file_name=f"dataset_ml_{ticker_input}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Terjadi error: {e}")