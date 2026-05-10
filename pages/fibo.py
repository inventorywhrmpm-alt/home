import streamlit as st
import yfinance as yf
import pandas as pd

def calculate_fibonacci(ticker):
    # Menambahkan kembali .JK untuk proses download data
    full_ticker = f"{ticker.upper()}.JK"
    df = yf.download(full_ticker, period="60d", interval="1d", progress=False)
    
    if df.empty:
        return None

    recent_high = df['High'].max()
    recent_low = df['Low'].min()
    diff = recent_high - recent_low
    current_price = df['Close'].iloc[-1]

    # Rasio Fibonacci Umum
    levels = {
        "Ticker": ticker.upper(),
        "Price": round(current_price, 2),
        "High": round(recent_high, 2),
        "Low": round(recent_low, 2),
        "0%": round(recent_high, 2),
        "23.6%": round(recent_high - 0.236 * diff, 2),
        "38.2%": round(recent_high - 0.382 * diff, 2),
        "50.0%": round(recent_high - 0.5 * diff, 2),
        "61.8%": round(recent_high - 0.618 * diff, 2),
        "78.6%": round(recent_high - 0.786 * diff, 2),
        "100%": round(recent_low, 2)
    }
    return levels

# UI Streamlit
st.set_page_config(page_title="IDX Fibonacci Scanner", layout="wide")
st.title("📊 Fibonacci Retracement Scanner - IDX")

# Input multi-ticker
input_tickers = st.text_input("Masukkan Ticker (pisahkan dengan koma, tanpa .JK)", "BBCA, ASII, TLKM, GOTO")

if st.button("Hitung Fibonacci"):
    ticker_list = [t.strip() for t in input_tickers.split(",")]
    all_data = []

    with st.spinner('Mengambil data dari Yahoo Finance...'):
        for ticker in ticker_list:
            # Membersihkan input jika user tidak sengaja memasukkan .JK
            clean_ticker = ticker.replace(".JK", "").replace(".jk", "")
            result = calculate_fibonacci(clean_ticker)
            if result:
                all_data.append(result)

    if all_data:
        final_df = pd.DataFrame(all_data)
        
        # Menampilkan Tabel
        st.subheader("Tabel Retracement (60 Hari Terakhir)")
        st.dataframe(final_df, use_container_width=True)
        
        # Opsi Download
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "fibonacci_idx.csv", "text/csv")
    else:
        st.error("Data tidak ditemukan. Pastikan kode ticker benar.")
