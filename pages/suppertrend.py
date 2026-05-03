import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime

# --- LOGIC SUPERTREND IDENTIK PINE SCRIPT ---
def calculate_supertrend(df, period=10, multiplier=1.0):
    # TradingView atr() secara default menggunakan RMA (Running Moving Average)
    df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=period, mamode="rma")
    
    # hl2 (Source)
    df['src'] = (df['High'] + df['Low']) / 2
    
    # Menghitung Up dan Dn dasar
    df['up_base'] = df['src'] - (multiplier * df['atr'])
    df['dn_base'] = df['src'] + (multiplier * df['atr'])
    
    # Inisialisasi array untuk proses looping (karena Pine Script bersifat rekursif)
    upperband = df['up_base'].values
    lowerband = df['dn_base'].values
    close = df['Close'].values
    trend = [1] * len(df)
    
    # Looping mulai dari bar kedua untuk meniru nz() dan referensi bar sebelumnya [1]
    for i in range(1, len(df)):
        # Logic Up: up := close[1] > up1 ? max(up, up1) : up
        if close[i-1] > upperband[i-1]:
            upperband[i] = max(upperband[i], upperband[i-1])
        else:
            upperband[i] = upperband[i]
            
        # Logic Dn: dn := close[1] < dn1 ? min(dn, dn1) : dn
        if close[i-1] < lowerband[i-1]:
            lowerband[i] = min(lowerband[i], lowerband[i-1])
        else:
            lowerband[i] = lowerband[i]
            
        # Logic Trend Direction
        if close[i] > lowerband[i-1] and trend[i-1] == -1:
            trend[i] = 1
        elif close[i] < upperband[i-1] and trend[i-1] == 1:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]

    # Masukkan kembali hasil loop ke dataframe
    df['trend'] = trend
    df['final_up'] = upperband
    df['final_dn'] = lowerband
    
    # Buat kolom signal
    df['signal'] = "-"
    # Buy: saat trend berubah dari -1 ke 1
    df.loc[(df['trend'] == 1) & (df['trend'].shift(1) == -1), 'signal'] = "buy"
    # Sell: saat trend berubah dari 1 ke -1
    df.loc[(df['trend'] == -1) & (df['trend'].shift(1) == 1), 'signal'] = "sell"
    
    return df

# --- UI STREAMLIT ---
st.set_page_config(page_title="Supertrend IDX Precise", layout="wide")

# CSS untuk styling tabel agar mirip gambar
st.markdown("""
<style>
    .reportview-container { background: #ffffff; }
    th { background-color: #f0f2f6 !important; }
</style>
""", unsafe_allow_html=True)

st.title("Tabel Sinyal Supertrend Precision (Identik TradingView)")

# Sidebar untuk parameter
st.sidebar.header("Konfigurasi Strategi")
ticker = st.sidebar.text_input("Kode Saham (IDX)", value="MINA").upper()
atr_p = st.sidebar.number_input("ATR Period", value=10)
atr_m = st.sidebar.number_input("Multiplier", value=1.0, step=0.1)
# Pemanasan data sangat penting agar RMA stabil
history_range = st.sidebar.selectbox("Ambil Data History", ["6mo", "1y", "2y", "max"], index=1)

try:
    # Tarik data dari Yahoo Finance
    with st.spinner("Mengunduh data..."):
        df_raw = yf.download(f"{ticker}.JK", period=history_range, interval="1d")
    
    # Bersihkan kolom jika formatnya multi-index
    if isinstance(df_raw.columns, pd.MultiIndex):
        df_raw.columns = df_raw.columns.get_level_values(0)

    if not df_raw.empty:
        # Jalankan kalkulasi
        df_res = calculate_supertrend(df_raw.copy(), atr_p, atr_m)
        
        # Siapkan dataframe untuk tampilan
        df_display = df_res[['Open', 'High', 'Low', 'Close', 'signal']].copy()
        
        # Format Tanggal menjadi dd-Mon-yy (Contoh: 08-Apr-26)
        df_display.index = df_display.index.strftime('%d-%b-%y')
        df_display = df_display.reset_index()
        df_display.columns = ['tanggal', 'open', 'high', 'low', 'close', 'signal']
        
        # Urutkan dari yang terbaru (Descending)
        df_display = df_display.sort_index(ascending=False)

        # Fungsi Styling untuk warna background kolom signal
        def apply_color(row):
            styles = [''] * len(row)
            if row['signal'] == 'buy':
                styles[5] = 'background-color: #90ee90; color: black;' # Hijau
            elif row['signal'] == 'sell':
                styles[5] = 'background-color: #ff4d4d; color: white;' # Merah
            return styles

        # Tampilkan tabel
        st.write(f"### Histori Sinyal {ticker}.JK")
        st.table(
            df_display.head(30).style.apply(apply_color, axis=1).format({
                'open': '{:.0f}', 
                'high': '{:.0f}', 
                'low': '{:.0f}', 
                'close': '{:.0f}'
            })
        )
        
        st.info("Catatan: Pastikan Multiplier diatur ke 1.0 jika ingin sesuai dengan gambar TradingView Anda.")
        
    else:
        st.warning("Data tidak ditemukan. Coba cek kode ticker sahamnya.")

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
