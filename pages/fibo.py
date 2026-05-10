import streamlit as st
import yfinance as yf
import pandas as pd

# Fungsi untuk menghitung Fibonacci dengan pembersihan data ketat
def get_clean_fibonacci(ticker_input):
    # 1. Standarisasi Ticker (hapus .JK jika user input manual, lalu tambah lagi untuk yfinance)
    clean_ticker = ticker_input.strip().upper().replace(".JK", "")
    yf_ticker = f"{clean_ticker}.JK"
    
    try:
        # Ambil data 60 hari terakhir
        df = yf.download(yf_ticker, period="60d", interval="1d", progress=False)
        
        if df.empty:
            return None

        # 2. Ambil nilai skalar menggunakan .item() agar tidak muncul 'dtype' atau 'Name'
        # Kita ambil baris terakhir untuk harga penutupan terbaru
        current_price = float(df['Close'].iloc[-1].item())
        high_price = float(df['High'].max().item())
        low_price = float(df['Low'].min().item())
        
        diff = high_price - low_price

        # 3. Masukkan ke dictionary (Hanya angka murni)
        return {
            "Ticker": clean_ticker,
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
    except Exception as e:
        return None

# --- KONFIGURASI STREAMLIT ---
st.set_page_config(page_title="IDX Fibonacci Table", layout="wide")

st.title("📈 IDX Fibonacci Retracement")
st.write("Menghitung level Fibonacci berdasarkan High/Low 60 hari terakhir.")

# Input ticker (bisa banyak dipisah koma)
input_user = st.text_input("Masukkan Ticker Saham (Contoh: SCMA, BBCA, GOTO)", "SCMA, BBCA")

if st.button("Generate Tabel"):
    tickers = [t.strip() for t in input_user.split(",")]
    results = []

    with st.spinner('Processing data...'):
        for t in tickers:
            data = get_clean_fibonacci(t)
            if data:
                results.append(data)
    
    if results:
        # Membuat DataFrame dari list of dictionaries
        final_df = pd.DataFrame(results)
        
        # Menampilkan tabel bersih di Streamlit
        st.subheader("Hasil Analisis Retracement")
        st.dataframe(
            final_df, 
            use_container_width=True, 
            hide_index=True # Sembunyikan kolom index angka di kiri
        )
        
        # Tombol Download
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Tabel (CSV)", csv, "fibonacci_idx.csv", "text/csv")
    else:
        st.error("Gagal mengambil data. Pastikan kode ticker benar.")
