import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime, timedelta

# --- FUNGSI LOGIC SUPERTREND (SAMA SEPERTI SEBELUMNYA) ---
def calculate_supertrend(df, period=10, multiplier=1.0):
    # Menghitung ATR menggunakan pandas_ta
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=period)
    
    # Menghitung Source (hl2)
    src = (df['High'] + df['Low']) / 2
    
    # Inisialisasi kolom
    df['up'] = src - (multiplier * atr)
    df['dn'] = src + (multiplier * atr)
    df['trend'] = 1
    df['st'] = 0.0

    # Logic Iterasi (Meniru behavior Pine Script bar-by-bar)
    for i in range(1, len(df)):
        # Up Trend Logic
        curr_up = df.loc[df.index[i], 'up']
        prev_up = df.loc[df.index[i-1], 'up']
        prev_close = df.loc[df.index[i-1], 'Close']
        df.loc[df.index[i], 'up'] = curr_up if prev_close > prev_up else max(curr_up, prev_up)
        
        # Down Trend Logic
        curr_dn = df.loc[df.index[i], 'dn']
        prev_dn = df.loc[df.index[i-1], 'dn']
        df.loc[df.index[i], 'dn'] = curr_dn if prev_close < prev_dn else min(curr_dn, prev_dn)
        
        # Trend Direction
        prev_trend = df.loc[df.index[i-1], 'trend']
        if prev_trend == -1 and df.loc[df.index[i], 'Close'] > df.loc[df.index[i-1], 'dn']:
            df.loc[df.index[i], 'trend'] = 1
        elif prev_trend == 1 and df.loc[df.index[i], 'Close'] < df.loc[df.index[i-1], 'up']:
            df.loc[df.index[i], 'trend'] = -1
        else:
            df.loc[df.index[i], 'trend'] = prev_trend
            
        # Final Supertrend Line
        df.loc[df.index[i], 'st'] = df.loc[df.index[i], 'up'] if df.loc[df.index[i], 'trend'] == 1 else df.loc[df.index[i], 'dn']

    # Signal Buy/Sell
    df['buy_signal'] = (df['trend'] == 1) & (df['trend'].shift(1) == -1)
    df['sell_signal'] = (df['trend'] == -1) & (df['trend'].shift(1) == 1)
    
    return df

# --- CONFIG & STYLING (CSS) ---
st.set_page_config(layout="wide", page_title="IDX Supertrend Dashboard")

# CSS kustom untuk card
st.markdown("""
<style>
    .metric-card {
        background-color: #0d1a24;
        border: 1px solid #1f3747;
        border-radius: 12px;
        padding: 20px;
        color: white;
    }
    .metric-card-title {
        font-size: 1.1em;
        font-weight: 600;
        margin-bottom: 15px;
        color: #e0e0e0;
    }
    .metric-value-container {
        display: flex;
        justify-content: space-around;
        align-items: center;
        text-align: center;
    }
    .metric-value-item {
        flex: 1;
    }
    .metric-label {
        font-size: 0.9em;
        color: #b0b0b0;
        margin-bottom: 5px;
    }
    .metric-value-buy {
        font-size: 2.2em;
        font-weight: bold;
        color: #00e676; /* Hijau */
    }
    .metric-value-sell {
        font-size: 2.2em;
        font-weight: bold;
        color: #ff5252; /* Merah */
    }
    .metric-value-neutral {
        font-size: 2.2em;
        font-weight: bold;
        color: #e0e0e0; /* Putih/Abu */
    }
    .metric-subtext {
        font-size: 0.8em;
        color: #808080;
        margin-top: 10px;
    }
    /* Styling tabel data */
    .table-buy {
        color: #00e676;
        font-weight: bold;
    }
    .table-sell {
        color: #ff5252;
        font-weight: bold;
    }
</style>
""", unsafe_allow_stdio=True)

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Konfigurasi")
st.sidebar.markdown("### Pilih Saham (IDX)")
ticker_input = st.sidebar.text_input("Kode Saham (Contoh: MINA, BBCA)", value="MINA").upper()
ticker_idx = f"{ticker_input}.JK"

# Interval data
st.sidebar.markdown("### Rentang Waktu")
periods_dict = {
    '6 Bulan': '6mo',
    '1 Tahun': '1y',
    '2 Tahun': '2y',
    'Max': 'max'
}
data_period = st.sidebar.selectbox("Pilih Rentang", options=list(periods_dict.keys()), index=0)
interval_dict = {'1 Hari': '1d', '1 Minggu': '1wk', '1 Bulan': '1mo'}
data_interval = st.sidebar.selectbox("Pilih Interval", options=list(interval_dict.keys()), index=0)

# Parameter Supertrend
st.sidebar.markdown("### Parameter Supertrend")
atr_period = st.sidebar.number_input("ATR Period", value=10)
atr_multiplier = st.sidebar.number_input("ATR Multiplier", value=1.0, step=0.1)

# Status indicators
st.sidebar.markdown("### Status")
st.sidebar.markdown("🟢 Ready")

# --- MAIN PAGE HEADER ---
st.title(f"IDX Supertrend Dashboard | {ticker_idx}")

# --- FETCH DATA & PROCESS ---
@st.cache_data(ttl=3600)
def get_processed_data(symbol, period_name, interval_name, atr_p, atr_m):
    period = periods_dict[period_name]
    interval = interval_dict[interval_name]
    df = yf.download(symbol, period=period, interval=interval)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty:
        return pd.DataFrame()
        
    df = calculate_supertrend(df.copy(), atr_p, atr_m)
    return df

try:
    df_result = get_processed_data(ticker_idx, data_period, data_interval, atr_period, atr_multiplier)

    if not df_result.empty:
        # --- CARDS VISUALIZATION (LAYOUT) ---
        # Membuat 2 kolom untuk baris pertama cards
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="metric-card-title">Metrik Kumulatif (3 Bulan Terakhir)</div>', unsafe_allow_stdio=True)
            # Filter data untuk 3 bulan terakhir
            end_date = df_result.index[-1]
            start_date_3m = end_date - timedelta(days=90)
            df_3m = df_result[start_date_3m:]

            # Menghitung metrik
            total_buy_3m = df_3m['buy_signal'].sum()
            total_sell_3m = df_3m['sell_signal'].sum()
            avg_buy_price = df_3m[df_3m['buy_signal']]['Close'].mean()

            # Membuat container card dengan HTML kustom
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value-container">
                    <div class="metric-value-item">
                        <div class="metric-label">Total Buy</div>
                        <div class="metric-value-buy">{total_buy_3m}</div>
                    </div>
                    <div class="metric-value-item">
                        <div class="metric-label">Total Sell</div>
                        <div class="metric-value-sell">{total_sell_3m}</div>
                    </div>
                    <div class="metric-value-item">
                        <div class="metric-label">Rata-rata Harga Buy</div>
                        <div class="metric-value-neutral">{avg_buy_price:,.0f}</div>
                    </div>
                </div>
                <div class="metric-subtext">Data per: {end_date.strftime('%Y-%m-%d')}</div>
            </div>
            """, unsafe_allow_stdio=True)

        with col2:
            st.markdown('<div class="metric-card-title">Metrik Kumulatif Seluruh Periode</div>', unsafe_allow_stdio=True)
            # Menghitung metrik
            total_buy = df_result['buy_signal'].sum()
            total_sell = df_result['sell_signal'].sum()
            avg_sell_price = df_result[df_result['sell_signal']]['Close'].mean()

            # Membuat container card dengan HTML kustom
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value-container">
                    <div class="metric-value-item">
                        <div class="metric-label">Total Buy</div>
                        <div class="metric-value-buy">{total_buy}</div>
                    </div>
                    <div class="metric-value-item">
                        <div class="metric-label">Total Sell</div>
                        <div class="metric-value-sell">{total_sell}</div>
                    </div>
                    <div class="metric-value-item">
                        <div class="metric-label">Rata-rata Harga Sell</div>
                        <div class="metric-value-neutral">{avg_sell_price:,.0f}</div>
                    </div>
                </div>
                <div class="metric-subtext">Periode: {data_period}</div>
            </div>
            """, unsafe_allow_stdio=True)

        # Baris kedua: Tabel Data
        st.markdown("<br>", unsafe_allow_stdio=True) # Jarak
        st.markdown('<div class="metric-card-title">Tampilan Data Mentah (Tabel Isyarat)</div>', unsafe_allow_stdio=True)
        
        # Menyiapkan data tabel yang diformat
        # Kita ambil sinyal saja untuk tabel yang lebih informatif seperti gambar
        df_table = df_result[df_result['buy_signal'] | df_result['sell_signal']].copy()
        
        # Reset index agar tanggal jadi kolom
        df_table = df_table.reset_index()
        # Format tanggal
        df_table['Date'] = df_table['Date'].dt.strftime('%Y-%m-%d')
        # Buat kolom 'Signal' yang digabung dengan harga
        df_table['Signal'] = ''
        df_table.loc[df_table['buy_signal'], 'Signal'] = 'Buy'
        df_table.loc[df_table['sell_signal'], 'Signal'] = 'Sell'
        
        # Pilih kolom yang relevan dan rapikan urutan
        df_table_final = df_table[['Date', 'Open', 'High', 'Low', 'Close', 'Signal']]
        
        # Fungsi styling tabel
        def format_signal(val):
            if val == 'Buy':
                return 'table-buy'
            elif val == 'Sell':
                return 'table-sell'
            return ''

        # Tampilkan tabel dengan styling CSS
        # Karena Streamlit `st.dataframe` tidak mendukung class CSS kustom,
        # kita tampilkan 50 data terakhir saja
        st.write(df_table_final.tail(50))

    else:
        st.error(f"Data tidak ditemukan untuk {ticker_input}. Pastikan kode saham benar.")

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
