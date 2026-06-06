import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta  # Pastikan install: pip install pandas-ta

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="IDX Parabolic SAR Scanner", layout="wide")
st.title("📊 IDX Parabolic SAR Scanner")

# --- SIDEBAR INPUT ---
st.sidebar.header("Konfigurasi Indikator")
start = st.sidebar.number_input("Start (AF)", value=0.02, step=0.01, format="%.2f")
increment = st.sidebar.number_input("Increment", value=0.02, step=0.01, format="%.2f")
maximum = st.sidebar.number_input("Maximum Value", value=0.20, step=0.01, format="%.2f")

st.sidebar.header("Input Saham")
# User bisa input multi ticker dipisahkan koma, otomatis diubah ke uppercase
ticker_input = st.sidebar.text_input("Masukkan Ticker IDX (Contoh: BBCA, BBRI, TLKM)", "BBCA, BBRI")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y", "2y"], index=1)

# --- PROSES DATA ---
if ticker_input:
    # Memisahkan input menjadi list dan membersihkan spasi
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    
    all_data = []
    
    for ticker in tickers:
        # Tambahkan .JK secara otomatis untuk fetch data dari Yahoo Finance
        yf_ticker = f"{ticker}.JK"
        
        try:
            # Download data dari yfinance
            df = yf.download(yf_ticker, period=period, progress=False)
            
            if df.empty:
                continue
                
            # Reset index agar tanggal jadi kolom biasa
            df = df.reset_index()
            
            # Hitung Parabolic SAR menggunakan pandas_ta (Metode Wilder sesuai TradingView)
            # Kolom hasil defaultnya biasanya bernama 'PSARs_0.02_0.2' tergantung input
            psar = ta.psar(df['High'], df['Low'], df['Close'], af0=start, af=increment, max_af=maximum)
            
            if psar is not None:
                # pandas_ta menghasilkan 4 kolom (psarl, psars, psarf, psarb). 
                # Kita gabungkan kolom long dan short untuk mendapatkan nilai tunggal SAR seperti di TV
                df['SAR'] = psar.iloc[:, 0].fillna(psar.iloc[:, 1])
                
                # Menentukan Aksi (Buy / Sell) berdasarkan posisi SAR terhadap Harga Close
                # Jika harga di atas SAR -> Bullish (Buy), jika di bawah SAR -> Bearish (Sell)
                df['Aksi'] = ['BUY' if close > sar else 'SELL' for close, sar in zip(df['Close'], df['SAR'])]
                
                # Ambil kolom yang dibutuhkan saja
                df['Ticker'] = ticker # Menghilangkan .JK dengan hanya menampilkan text asli input
                
                # Format Tanggal
                df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
                
                # Pilih dan urutkan kolom sesuai permintaan
                # Ticker || Tanggal || Open || High || Low || Volume || Signal Indikator Parabolic SAR || Aksi Buy atau Sell
                df_selected = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Volume', 'SAR', 'Aksi']].copy()
                
                # Rename kolom agar rapi di tabel
                df_selected.columns = ['Ticker', 'Tanggal', 'Open', 'High', 'Low', 'Volume', 'Signal Parabolic SAR', 'Aksi Buy/Sell']
                
                # Masukkan ke list (urutkan dari tanggal terbaru di atas)
                all_data.append(df_selected.iloc[::-1])
                
        except Exception as e:
            st.error(f"Gagal memproses ticker {ticker}: {str(e)}")

    # Tampilkan Hasil dalam Bentuk Tabel
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        
        st.subheader("📋 Tabel Hasil Analisis Parabolic SAR")
        
        # Style mewarnai aksi BUY (Hijau) dan SELL (Merah) agar mudah dibaca
        def color_action(val):
            color = '#d4edda' if val == 'BUY' else '#f8d7da'
            text_color = '#155724' if val == 'BUY' else '#721c24'
            return f'background-color: {color}; color: {text_color}; font-weight: bold;'
        
        styled_df = final_df.style.applymap(color_action, subset=['Aksi Buy/Sell']).format({
            'Open': '{:,.2f}', 'High': '{:,.2f}', 'Low': '{:,.2f}', 
            'Volume': '{:,.0f}', 'Signal Parabolic SAR': '{:,.2f}'
        })
        
        st.dataframe(styled_df, use_container_width=True, height=500)
    else:
        st.warning("Tidak ada data yang berhasil diambil. Periksa kembali ticker yang Anda masukkan.")
