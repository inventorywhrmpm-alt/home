import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ==========================================
# 1. PAGE & SIDEBAR CONFIGURATION (INPUTS)
# ==========================================
st.set_page_config(page_title="Wyckoff Event Detection Table (IDX)", layout="wide")

st.title("💎 IDX Wyckoff Event Detection Table")
st.caption("Aplikasi ini menggunakan data riil saham BEI (IDX) dan mempertahankan 100% logika kalkulasi Pine Script tanpa grafik.")

st.sidebar.header("Pilih Saham IDX")
# User cukup mengetik kode saham tanpa perlu mengetik .JK
ticker_input = st.sidebar.text_input("Masukkan Kode Saham (Ticker)", value="BBRI").upper().strip()
ticker_idx = f"{ticker_input}.JK"

st.sidebar.header("General Settings")
i_volLen = st.sidebar.number_input("Volume MA Length", min_value=1, value=20)
i_priceLookback = st.sidebar.number_input("Price Pattern Lookback", min_value=5, value=20)
i_minBarsWithoutSignal = st.sidebar.number_input("Minimum Bars Between Events", min_value=1, value=5)
i_phaseWindowBars = st.sidebar.number_input("Phase Window Evaluation (bars)", min_value=5, max_value=100, value=20)

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
@st.cache_data(ttl=3600) # Cache disimpan selama 1 jam
def load_idx_data(ticker):
    try:
        data = yf.download(ticker, period="1y", interval="1d")
        if data.empty:
            return pd.DataFrame()
        data = data.reset_index()
        # Meratakan multi-level index yang dihasilkan oleh yfinance versi terbaru
        data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
        return data
    except Exception as e:
        return pd.DataFrame()

# Proses Memuat Data
if ticker_input:
    df = load_idx_data(ticker_idx)
    if df.empty:
        st.error(f"Gagal mengambil data untuk saham `{ticker_input}`. Pastikan kode saham yang Anda masukkan benar (contoh: BBRI, TLKM, BUVA, ASII).")
        st.stop()
else:
    st.warning("Silakan masukkan kode saham di Sidebar terlebih dahulu.")
    st.stop()

# ==========================================
# 3. EXACT TRADINGVIEW LOGIC REPLICATION
# ==========================================

# 1. Fungsi Replikasi RMA (Wilder's Moving Average) Bawaan TradingView untuk ATR
def calculate_rma(series, length):
    alpha = 1.0 / length
    return series.ewm(alpha=alpha, adjust=False).mean()

# 2. Pembuatan Kolom Indikator Teknikal Dasar
df['VolMA'] = df['Volume'].rolling(window=i_volLen, min_periods=1).mean()

h_l = df['High'] - df['Low']
h_pc = abs(df['High'] - df['Close'].shift(1))
l_pc = abs(df['Low'] - df['Close'].shift(1))
df['TR'] = np.maximum(h_l, np.maximum(h_pc, l_pc))
df['ATR'] = calculate_rma(df['TR'], i_priceLookback)

df['HighestHigh'] = df['High'].rolling(window=i_priceLookback).max()
df['LowestLow'] = df['Low'].rolling(window=i_priceLookback).min()

# 3. Fungsi Tren Akurat (Mengikuti Aturan Rantai ta.falling / ta.rising Pine Script)
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

# 4. Fungsi Deteksi Pivot Mengikuti Aturan Offset Historis Pine Script
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

# 5. Simulasi Engine TradingView (Loop Bar-by-Bar)
df['Event'] = ""
df['Phase'] = "NEUTRAL"
bearishCount = 0
bullishCount = 0

for idx in range(len(df)):
    if idx < i_priceLookback + 1:
        continue
        
    row = df.iloc[idx]
    
    h_highest_1 = df['HighestHigh'].iloc[idx-1]
    l_lowest_1 = df['LowestLow'].iloc[idx-1]
    h_highest_2 = df['HighestHigh'].iloc[idx-2]
    l_lowest_3 = df['LowestLow'].iloc[idx-3]
    
    # Penentuan Awal Phase Per Bar
    current_phase = "NEUTRAL"
    if bearishCount > bullishCount * 2.0:
        current_phase = "DISTRIBUTION"
    elif bullishCount > bearishCount * 2.0:
        current_phase = "ACCUMULATION"
    df.at[idx, 'Phase'] = current_phase

    # Evaluasi Kondisi Sinyal Wyckoff
    psy_cond = row['High'] > h_highest_1 and row['Volume'] > row['VolMA'] * i_volThreshMult and row['Close'] < row['High'] - (row['High'] - row['Low']) * i_priceThreshMult and ta_falling(df['Close'], i_trendStrength).iloc[idx]
    ut_d_cond = current_phase == "DISTRIBUTION" and row['High'] > h_highest_1 and row['Close'] < row['Open'] and row['Volume'] > row['VolMA'] * i_volumeFilter and (row['High'] - row['Close']) > row['ATR'] * i_priceThreshMult
    bc_cond = row['High'] > h_highest_2 and row['Volume'] > row['VolMA'] * (i_volThreshMult * 1.5) and row['Close'] > row['Open'] and ((row['Close'] - row['Open']) / (row['High'] - row['Low']) > 0.6 if (row['High'] - row['Low']) != 0 else False)
    sow_cond = row['Close'] < row['Open'] and row['Low'] < l_lowest_1 and row['Volume'] > row['VolMA'] * i_volThreshMult and ta_falling(df['Close'], i_trendStrength).iloc[idx]

    ps_cond = row['Low'] < l_lowest_1 and row['Volume'] > row['VolMA'] * i_volThreshMult and row['Close'] > row['Low'] + (row['High'] - row['Low']) * i_priceThreshMult and ta_falling(df['Close'], i_trendStrength).iloc[idx]
    sc_cond = row['Low'] < l_lowest_1 and row['Volume'] > row['VolMA'] * (i_volThreshMult * 1.2) and row['Close'] > row['Low'] + (row['High'] - row['Low']) * (i_priceThreshMult * 1.5)
    spring_cond = row['Low'] < l_lowest_3 and row['Close'] > row['Open'] and row['Close'] > row['Low'] + (row['High'] - row['Low']) * 0.6 and row['Volume'] > row['VolMA'] * i_volumeFilter
    sos_cond = row['Close'] > row['Open'] and row['High'] > h_highest_1 and row['Volume'] > row['VolMA'] * i_volThreshMult and ta_rising(df['Close'], i_trendStrength).iloc[idx]

    # Pemetaan Label Event & Penambahan Counter Jendela Evaluasi
    if ut_d_cond: df.at[idx, 'Event'] = "UT-D"; bearishCount += 1
    elif bc_cond: df.at[idx, 'Event'] = "BC"; bearishCount += 1
    elif psy_cond: df.at[idx, 'Event'] = "PSY"; bearishCount += 1
    elif sow_cond: df.at[idx, 'Event'] = "SOW"; bearishCount += 1
    elif spring_cond: df.at[idx, 'Event'] = "SPRING"; bullishCount += 1
    elif sc_cond: df.at[idx, 'Event'] = "SC"; bullishCount += 1
    elif ps_cond: df.at[idx, 'Event'] = "PS"; bullishCount += 1
    elif sos_cond: df.at[idx, 'Event'] = "【SOS】"; bullishCount += 1

    # Reset Counter Periodik Menggunakan Variabel Sidebar yang Valid
    if idx % int(i_phaseWindowBars) == 0:
        bearishCount = 0
        bullishCount = 0

# ==========================================
# 4. TRADING RANGE PRICE CALCULATION
# ==========================================
last_idx = len(df) - 1
upper_range = df['HighestHigh'].iloc[last_idx]
lower_range = df['LowestLow'].iloc[last_idx]

if i_rangeStyle == "Fixed":
    safe_lookback = min(i_fixedRangeBars, len(df))
    upper_range = df['High'].iloc[-safe_lookback:].max()
    lower_range = df['Low'].iloc[-safe_lookback:].min()
    
elif i_rangeStyle == "Pivot-based":
    last_pivot_high = df['HighestHigh'].iloc[last_idx]
    last_pivot_low = df['LowestLow'].iloc[last_idx]
    
    max_safe_lookback = min(i_pivotLookback, 20)
    
    for length_i in range(5, max_safe_lookback + 1):
        if check_is_pivot_high(df, last_idx, length_i, i_pivotStrength):
            last_pivot_high = df['High'].iloc[last_idx - length_i]
            break
            
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

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Batas Atas Harga (Resistance)", f"Rp {upper_range:,.00f}")
with col2:
    st.metric("Batas Bawah Harga (Support)", f"Rp {lower_range:,.00f}")
with col3:
    spread = upper_range - lower_range
    spread_pct = (spread / lower_range) * 100 if lower_range != 0 else 0
    st.metric("Lebar Konsolidasi Range", f"Rp {spread:,.00f} ({spread_pct:.2f}%)")

st.markdown("---")

st.subheader("📋 Wyckoff Event Log Table")

df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
filtered_df = df[df['Event'] != ""].copy()

if not filtered_df.empty:
    display_table = filtered_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Phase', 'Event']].sort_values(by='Date', ascending=False)
    
    for col in ['Open', 'High', 'Low', 'Close']:
        display_table[col] = display_table[col].map(lambda x: f"Rp {x:,.00f}")
    display_table['Volume'] = display_table['Volume'].map(lambda x: f"{x:,.00f}")

    def color_event_row(val):
        if val in ['UT-D', 'BC', 'PSY', 'SOW']:
            return 'background-color: #fce8e6; color: #cc1e1e; font-weight: bold;'
        elif val in ['SPRING', 'SC', 'PS', '【SOS】']:
            return 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
        return ''

    styled_table = display_table.style.map(color_event_row, subset=['Event'])
    st.dataframe(styled_table, use_container_width=True, hide_index=True)
else:
    st.warning(f"Tidak ada Event Wyckoff yang terdeteksi pada saham {ticker_input} menggunakan parameter sensitivitas saat ini.")

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
