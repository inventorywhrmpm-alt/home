import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="IDX Parabolic SAR Scanner", layout="wide")
st.title("📊 IDX Parabolic SAR Scanner")

# --- SIDEBAR INPUT ---
st.sidebar.header("Konfigurasi Indikator")
start = st.sidebar.number_input("Start (AF)", value=0.02, step=0.01, format="%.2f")
increment = st.sidebar.number_input("Increment", value=0.02, step=0.01, format="%.2f")
maximum = st.sidebar.number_input("Maximum Value", value=0.20, step=0.01, format="%.2f")

st.sidebar.header("Input Saham")
ticker_input = st.sidebar.text_input("Masukkan Ticker IDX (Contoh: BBCA, BBRI, TLKM)", "BBCA, BBRI")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y", "2y"], index=2) # Default 1y agar data cukup untuk SAR

# --- PROSES DATA ---
if ticker_input:
    # Memisahkan input menjadi list dan membersihkan spasi
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    
    all_data = []
    
    for ticker in tickers:
        yf_ticker = f"{ticker}.JK"
        
        try:
            # Download data menggunakan group_by='ticker' untuk penanganan multi-index yang aman
            df = yf.download(yf_ticker, period=period, progress=False)
            
            if df.empty:
                continue
            
            # Jika kolom bertingkat (MultiIndex akibat perubahan library yfinance), kita ratakan
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            df = df.reset_index()
            
            # Pastikan nama kolom bertipe string biasa dan case-sensitive sesuai pandas_ta (Open, High, Low, Close)
            df.columns = [str(col) for col in df.columns]
            
            # Menghitung Parabolic SAR menggunakan pandas_ta
            psar = ta.psar(df['High'], df['Low'], df['Close'], af0=start, af=increment, max_af=maximum)
            
            if psar is not None and not psar.empty:
                # Menggabungkan kolom PSAR Long dan Short menjadi satu kolom tunggal 'SAR'
                df['SAR'] = psar.iloc[:, 0].fillna(psar.iloc[:, 1])
                
                # Menghapus baris awal yang bernilai NaN agar tabel bersih
                df = df.dropna(subset=['SAR'])
                
                if df.empty:
                    continue
                
                # Menentukan Aksi (BUY jika Close > SAR, SELL jika Close < SAR)
                df['Aksi'] = ['BUY' if float(close) > float(sar) else 'SELL' for close, sar in zip(df['Close'], df['SAR'])]
                
                # Menambahkan kolom Ticker tanpa .JK
                df['Ticker'] = ticker
                
                # Format Tanggal menjadi string YYYY-MM-DD
                df['Tanggal'] = df['Date'].dt.strftime('%Y-%m-%d')
                
                # Pilih kolom yang diminta
                df_selected = df[['Ticker', 'Tanggal', 'Open', 'High', 'Low', 'Volume', 'SAR', 'Aksi']].copy()
                df_selected.columns = ['Ticker', 'Tanggal', 'Open', 'High', 'Low', 'Volume', 'Signal Parabolic SAR', 'Aksi Buy/Sell']
                
                # Urutkan dari tanggal terbaru ke terlama
                all_data.append(df_selected.iloc[::-1])
                
        except Exception as e:
            st.error(f"Gagal memproses ticker {ticker}: {str(e)}")

    # Tampilkan Hasil dalam Bentuk Tabel
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Tampilkan Hasil dalam Bentuk Tabel
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        
        st.subheader("📋 Tabel Hasil Analisis Parabolic SAR")
        
        # Fungsi styling warna untuk aksi BUY dan SELL
        def color_action(val):
            color = '#d4edda' if val == 'BUY' else '#f8d7da'
            text_color = '#155724' if val == 'BUY' else '#721c24'
            return f'background-color: {color}; color: {text_color}; font-weight: bold;'
        
        # Konversi kolom numerik secara eksplisit untuk menghindari error formatting di Pandas terbaru
        num_cols = ['Open', 'High', 'Low', 'Volume', 'Signal Parabolic SAR']
        for col in num_cols:
            final_df[col] = pd.to_numeric(final_df[col], errors='coerce')
        
        # PERBAIKAN DI SINI: Menggunakan .map() sebagai pengganti .applymap()
        styled_df = final_df.style.map(color_action, subset=['Aksi Buy/Sell']).format({
            'Open': '{:,.2f}', 
            'High': '{:,.2f}', 
            'Low': '{:,.2f}', 
            'Volume': '{:,.0f}', 
            'Signal Parabolic SAR': '{:,.2f}'
        }, na_rep="-")
        
        st.dataframe(styled_df, use_container_width=True, height=600)
    else:
        st.warning("Tidak ada data yang berhasil diambil atau dihitung. Pastikan koneksi internet aktif dan kode ticker IDX sudah benar.")hasil diambil atau dihitung. Pastikan koneksi internet aktif dan kode ticker IDX sudah benar.")
