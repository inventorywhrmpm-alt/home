import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="IDX Parabolic SAR Scanner", layout="wide")
st.title("📊 IDX Parabolic SAR Scanner (Presisi TradingView)")
st.write("Menampilkan data historis beserta sinyal akurat Parabolic SAR tanpa memunculkan grafik.")

# --- SIDEBAR INPUT ---
st.sidebar.header("Konfigurasi Indikator")
start = st.sidebar.number_input("Start (AF)", value=0.02, step=0.01, format="%.2f")
increment = st.sidebar.number_input("Increment", value=0.02, step=0.01, format="%.2f")
maximum = st.sidebar.number_input("Maximum Value", value=0.20, step=0.01, format="%.2f")

st.sidebar.header("Input Saham")
# User bisa input multi ticker dipisahkan koma, otomatis diubah ke uppercase
ticker_input = st.sidebar.text_input("Masukkan Ticker IDX (Contoh: BBCA, BBRI, TLKM)", "BBCA, BBRI")

st.sidebar.header("Filter Tampilan Tabel")
display_days = st.sidebar.slider("Tampilkan data berapa hari terakhir?", min_value=10, max_value=120, value=60)

# --- PROSES DATA ---
if ticker_input:
    # Memisahkan input menjadi list dan membersihkan spasi
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    
    all_data = []
    
    for ticker in tickers:
        # Tambahkan .JK secara otomatis untuk data Yahoo Finance
        yf_ticker = f"{ticker}.JK"
        
        try:
            # PENTING: Paksa ambil history 1 tahun agar kalkulasi rumus SAR stabil & akurat seperti TV
            df = yf.download(yf_ticker, period="1y", progress=False)
            
            if df.empty:
                continue
            
            # Meratakan kolom jika yfinance mengembalikan MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            df = df.reset_index()
            df.columns = [str(col) for col in df.columns]
            
            # Hitung Parabolic SAR menggunakan pandas_ta (Algoritma J. Welles Wilder)
            psar = ta.psar(df['High'], df['Low'], df['Close'], af0=start, af=increment, max_af=maximum)
            
            if psar is not None and not psar.empty:
                # Menggabungkan kolom PSAR Long dan Short menjadi satu kolom tunggal 'SAR'
                df['SAR'] = psar.iloc[:, 0].fillna(psar.iloc[:, 1])
                
                # Menentukan Aksi (BUY jika Close > SAR, SELL jika Close < SAR)
                df['Aksi'] = ['BUY' if float(close) > float(sar) else 'SELL' for close, sar in zip(df['Close'], df['SAR'])]
                
                # Memasukkan kode ticker asli tanpa .JK ke DataFrame
                df['Ticker'] = ticker
                
                # Format Tanggal menjadi string YYYY-MM-DD
                df['Tanggal'] = df['Date'].dt.strftime('%Y-%m-%d')
                
                # --- STRATEGI FILTER AKURASI ---
                # Mengambil x hari terakhir sesuai pilihan slider user setelah SAR selesai dihitung
                df_filtered = df.tail(display_days)
                
                # Ambil kolom sesuai urutan permintaan user:
                # Ticker || Tanggal || Open || High || Low || Volume || Signal Parabolic SAR || Aksi Buy/Sell
                df_selected = df_filtered[['Ticker', 'Tanggal', 'Open', 'High', 'Low', 'Volume', 'SAR', 'Aksi']].copy()
                df_selected.columns = ['Ticker', 'Tanggal', 'Open', 'High', 'Low', 'Volume', 'Signal Parabolic SAR', 'Aksi Buy/Sell']
                
                # Membalik urutan agar tanggal terbaru muncul di baris paling atas
                all_data.append(df_selected.iloc[::-1])
                
        except Exception as e:
            st.error(f"Gagal memproses ticker {ticker}: {str(e)}")

    # --- TAMPILKAN HASIL DALAM BENTUK TABEL ---
    if all_data:
        # Menggabungkan semua data ticker menjadi satu dataframe besar
        final_df = pd.concat(all_data, ignore_index=True)
        
        st.subheader("📋 Tabel Hasil Analisis Parabolic SAR")
        
        # Fungsi styling warna background kolom Aksi
        def color_action(val):
            color = '#d4edda' if val == 'BUY' else '#f8d7da'
            text_color = '#155724' if val == 'BUY' else '#721c24'
            return f'background-color: {color}; color: {text_color}; font-weight: bold;'
        
        # Memastikan kolom angka bertipe numerik agar tidak error saat formatting
        num_cols = ['Open', 'High', 'Low', 'Volume', 'Signal Parabolic SAR']
        for col in num_cols:
            final_df[col] = pd.to_numeric(final_df[col], errors='coerce')
        
        # Menerapkan style warna dan format angka desimal dua angka di belakang koma
        styled_df = final_df.style.map(color_action, subset=['Aksi Buy/Sell']).format({
            'Open': '{:,.2f}', 
            'High': '{:,.2f}', 
            'Low': '{:,.2f}', 
            'Volume': '{:,.0f}', 
            'Signal Parabolic SAR': '{:,.2f}'
        }, na_rep="-")
        
        # Tampilkan tabelinteraktif di Streamlit
        st.dataframe(styled_df, use_container_width=True, height=650)
    else:
        st.warning("Tidak ada data yang berhasil diambil atau dihitung. Pastikan kode saham IDX yang dimasukkan benar.")
