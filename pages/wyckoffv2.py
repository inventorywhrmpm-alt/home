import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# Set Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Wyckoff Event Detection Table (IDX)", layout="wide")

st.title("💎 IDX Wyckoff Event Detection Table")
st.caption("Aplikasi ini menggunakan data riil saham BEI (IDX) dan mempertahankan 100% logika kalkulasi Pine Script tanpa grafik.")

# ==========================================
# 1. SIDEBAR CONFIGURATION (INPUTS)
# ==========================================
st.sidebar.header("Pilih Saham IDX")
# User cukup mengetik kode saham tanpa perlu repot mengetik .JK
ticker_input = st.sidebar.text_input("Masukkan Kode Saham (Ticker)", value="BBRI").upper().strip()
ticker_idx = f"{ticker_input}.JK"

st.sidebar.header("General Settings")
i_volLen = st.sidebar.number_input("Volume MA Length", min_value=1, value=20)
i_priceLookback = st.sidebar.number_input("Price Pattern Lookback", min_value=5, value=20)
i_minBarsWithoutSignal = st.sidebar.number_input("Minimum Bars Between Events", min_value=1, value=5)

st.sidebar.header("Trading Range Visualization")
i_rangeStyle = st.sidebar.selectbox("Range Style", options=["Dynamic", "Fixed", "Pivot-based"], index=2)
i_fixedRangeBars = st.sidebar.number_input("Fixed Range Lookback (bars)", min_value=10, max_value=500, value=50)
i_pivotStrength = st.sidebar.number_input("Pivot Strength (bars)", min_value=1, max_value=10, value=3)
i_pivotLookback = st.sidebar.number_input("Pivot Lookback (bars)", min_value=20, max_value=500, value=100)

st.sidebar.header("Sensitivity & Filters")
i_volThreshMult = st.sidebar.slider("Volume Threshold Multiplier", 1.0, 5.0, 2.0, 0.1)
i_priceThreshMult = st.sidebar.slider("Price Movement Threshold", 0.1, 1.0, 0.3, 0.1)
i_trendStrength = st.sidebar.slider("Trend Strength (bars)", 1, 10, 3)
i_volumeFilter = st.sidebar.slider("Volume Filter", 1.0, 5.0, 1.5, 0.1)
i_priceRangeFilter = st.sidebar.slider("Price Range Filter", 0.1, 1.0, 0.5, 0.1)

# ==========================================
# 2. DOWNLOAD DATA REAL-TIME DARI YFINANCE
# ==========================================
@st.cache_data(ttl=3600) # Simpan cache selama 1 jam agar hemat kuota internet
def load_idx_data(ticker):
    try:
        # Mengambil data harian sepanjang 1 tahun terakhir
        data = yf.download(ticker, period="1y", interval="1d")
        if data.empty:
            return pd.DataFrame()
        # Meratakan multi-level index jika ada (fitur yfinance versi baru)
        data = data.reset_index()
        data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
        return data
    except Exception as e:
        return pd.DataFrame()

# Proses Memuat Data
if ticker_input:
    df = load_idx_data(ticker_idx)
    
    if df.empty:
        st.error(f"Gagal mengambil data untuk saham `{ticker_input}`. Pastikan kode saham yang Anda masukkan benar (contoh: BBRI, TLKM, ASII, GOTO).")
        st.stop()
else:
    st.warning("Silakan masukkan kode saham di Sidebar terlebih dahulu.")
    st.stop()

# ==========================================
# ==========================================
# ==========================================
# 3. EXACT TRADINGVIEW LOGIC REPLICATION
# ==========================================

# ... (Kalkulasi VolMA, TR, ATR, HighestHigh, LowestLow ada di sini) ...

# Fungsi Pendeteksi Tren (ta_falling & ta_rising)
def ta_falling(series, length):
    is_falling = True
    for i in range(length):
        is_falling = is_falling & (series.shift(i) < series.shift(i + 1))
    return is_falling

def ta_rising(series, length):
    is_rising = True
    for i in range(length):
        is_rising = is_rising & (series.shift(i) > series.shift(i + 1))
    return is_rising


# PASTIKAN DUA FUNGSI INI ADA DI SINI (SEBELUM DI-CALL DI BAWAH)
def check_is_pivot_high(df, idx, length, strength):
    MAX_HISTORICAL_OFFSET = 20
    if length < strength or length > MAX_HISTORICAL_OFFSET or idx < (length + strength):
        return False
    
    target_high = df['High'].iloc[idx - length]
    
    for i in range(1, strength + 1):
        forward_offset = length + i
        backward_offset = length - i
        
        if forward_offset <= MAX_HISTORICAL_OFFSET and backward_offset >= 0:
            if target_high <= df['High'].iloc[idx - forward_offset] or target_high <= df['High'].iloc[idx - backward_offset]:
                return False
        else:
            return False
    return True

def check_is_pivot_low(df, idx, length, strength):
    MAX_HISTORICAL_OFFSET = 20
    if length < strength or length > MAX_HISTORICAL_OFFSET or idx < (length + strength):
        return False
    
    target_low = df['Low'].iloc[idx - length]
    
    for i in range(1, strength + 1):
        forward_offset = length + i
        backward_offset = length - i
        
        if forward_offset <= MAX_HISTORICAL_OFFSET and backward_offset >= 0:
            if target_low >= df['Low'].iloc[idx - forward_offset] or target_low >= df['Low'].iloc[idx - backward_offset]:
                return False
        else:
            return False
    return True


# ==========================================
# 4. TRADING RANGE PRICE CALCULATION (Baris 182 ke bawah)
# ==========================================
last_idx = len(df) - 1

if i_rangeStyle == "Pivot-based":
    last_pivot_high = df['HighestHigh'].iloc[last_idx]
    
    max_safe_lookback = min(i_pivotLookback, 20)
    
    for length_i in range(5, max_safe_lookback + 1):
        # Di sini fungsi dipanggil, jadi fungsinya WAJIB sudah dideklarasikan di atas
        if check_is_pivot_high(df, last_idx, length_i, i_pivotStrength):
            last_pivot_high = df['High'].iloc[last_idx - length_i]
            break
            
    # Cari pivot low terakhir dari urutan bar mundur
    for length_i in range(5, max_safe_lookback + 1):
        if check_is_pivot_low(df, last_idx, length_i, i_pivotStrength):
            last_pivot_low = df['Low'].iloc[last_idx - length_i]
            break
            
    upper_range = last_pivot_high
    lower_range = last_pivot_low

# ==========================================
# 5. STREAMLIT METRICS & DATA OUTPUT (TABLE)
# ==========================================

st.subheader(f"📈 Hasil Analisis Saham: {ticker_input}")

# Bagian Informasi Utama Rentang Harga Saat Ini
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Batas Atas Harga (Resistance)", f"Rp {upper_range:,.00f}")
with col2:
    st.metric("Batas Bawah Harga (Support)", f"Rp {lower_range:,.00f}")
with col3:
    spread = upper_range - lower_range
    spread_pct = (spread / lower_range) * 100
    st.metric("Lebar Konsolidasi Range", f"Rp {spread:,.00f} ({spread_pct:.2f}%)")

st.markdown("---")

# Bagian Tabel Deteksi Utama
st.subheader("📋 Wyckoff Event Log Table")

# Format tanggal agar mudah dibaca manusia
df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

# Format subset dataframe khusus bar yang memicu sinyal/event saja agar rapi
filtered_df = df[df['Event'] != ""].copy()

if not filtered_df.empty:
    display_table = filtered_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Phase', 'Event']].sort_values(by='Date', ascending=False)
    
    # Menghilangkan desimal berlebih khusus untuk nominal mata uang rupiah saham IDX
    for col in ['Open', 'High', 'Low', 'Close']:
        display_table[col] = display_table[col].map(lambda x: f"Rp {x:,.00f}")
    display_table['Volume'] = display_table['Volume'].map(lambda x: f"{x:,.00f}")

    # Styling mewarnai teks sel Event agar mirip dengan visual skema TradingView
    def color_event_row(val):
        if val in ['UT-D', 'BC', 'PSY', 'SOW']:
            return 'background-color: #fce8e6; color: #cc1e1e; font-weight: bold;' # Soft Red
        elif val in ['SPRING', 'SC', 'PS', '【SOS】']:
            return 'background-color: #e6f4ea; color: #137333; font-weight: bold;' # Soft Green
        return ''

    styled_table = display_table.style.map(color_event_row, subset=['Event'])
    st.dataframe(styled_table, use_container_width=True, hide_index=True)
else:
    st.warning(f"Tidak ada Event Wyckoff yang terdeteksi pada saham {ticker_input} menggunakan parameter sensitivitas saat ini.")

# Ringkasan Statistik Market State Saat Ini dalam Bentuk Tabel Ringkas
st.subheader("📊 Current Market State")
state_data = {
    "Kategori Analisis": ["Market Phase Saat Ini", "Estimasi Supply / Demand", "Model Perhitungan Rentang"],
    "Nilai Output": [
        df['Phase'].iloc[-1],
        "SUPPLY DOMINANT" if df['Close'].iloc[-1] < df['Open'].iloc[-1] and df['Volume'].iloc[-1] > df['VolMA'].iloc[-1] else "DEMAND DOMINANT" if df['Close'].iloc[-1] > df['Open'].iloc[-1] and df['Volume'].iloc[-1] > df['VolMA'].iloc[-1] else "IN BALANCE",
        i_rangeStyle
    ]
}
st.table(pd.DataFrame(state_data))
