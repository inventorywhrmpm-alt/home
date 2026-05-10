import streamlit as st
import yfinance as yf
import pandas as pd

# Fungsi untuk menghitung Fibonacci dengan pilihan interval
def get_clean_fibonacci(ticker_input, timeframe):
    # Standarisasi Ticker
    clean_ticker = ticker_input.strip().upper().replace(".JK", "")
    yf_ticker = f"{clean_ticker}.JK"
    
    # Konfigurasi period berdasarkan interval agar data cukup untuk High/Low
    # Jika 1h/4h, kita ambil data 60 hari terakhir (cukup untuk intraday)
    # Jika 1d, kita ambil 60 hari atau lebih
    period_map = "60d" 

    try:
        df = yf.download(yf_ticker, period=period_map, interval=timeframe, progress=False)
        
        if df.empty:
            return None

        # Ambil nilai skalar dengan .item() untuk membuang dtype/noise
        current_price = float(df['Close'].iloc[-1].item())
        high_price = float(df['High'].max().item())
        low_price = float(df['Low'].min().item())
        
        diff = high_price - low_price

        return {
            "Ticker": clean_ticker,
            "TF": timeframe,
            "Price": round(current_price, 2),
            "High": round(high_price, 2),
            "Low": round(low_price, 2),
            "Fib 0.0%": round(high_price, 2),
            "Fib 23.6%": round(high_price - (0.236 * diff), 2),
            "Fib 38.2%": round(high_price - (0.382 * diff), 2),
            "Fib 50.0%": round(high_price - (0.5 * diff), 2),
            "Fib 61.8%": round(high_price - (0.618 * diff), 2),
            "Fib 78.6%": round(high_price - (0.786 * diff), 2),
            "Fib 100%": round(low_price, 2)
        }
    except Exception:
        return None

# --- UI STREAMLIT ---
st.set_page_config(page_title="IDX Fibonacci Multi-TF", layout="wide")

# Sidebar untuk Input agar area utama fokus ke Tabel
with st.sidebar:
    st.header("Konfigurasi Scanner")
    input_user = st.text_input("Ticker (pisahkan koma)", "SCMA, BBCA, TLKM")
    
    # PILIHAN TIMEFRAME
    tf_choice = st.selectbox(
        "Pilih Timeframe:",
        options=["1h", "4h", "1d"],
        index=2  # Default ke 1d
    )
    
    btn_generate = st.button("Generate Tabel")

st.title("📊 Fibonacci Retracement Scanner")
st.info(f"Menganalisis data berdasarkan High & Low dalam 60 hari terakhir dengan interval **{tf_choice}**")

if btn_generate:
    tickers = [t.strip() for t in input_user.split(",")]
    results = []

    with st.spinner(f'Mengambil data {tf_choice} dari Yahoo Finance...'):
        for t in tickers:
            data = get_clean_fibonacci(t, tf_choice)
            if data:
                results.append(data)
    
    if results:
        final_df = pd.DataFrame(results)
        
        # Tampilkan Tabel
        st.subheader(f"Hasil Analisis - Timeframe {tf_choice}")
        st.dataframe(
            final_df, 
            use_container_width=True, 
            hide_index=True 
        )
        
        # Download
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, f"fib_{tf_choice}_idx.csv", "text/csv")
    else:
        st.error("Data tidak ditemukan. Cek kembali penulisan ticker.")
