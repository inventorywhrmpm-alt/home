import streamlit as st
import pandas as pd
import numpy as np

# Set Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Wyckoff Event Detection", layout="wide")

st.title("💎 Wyckoff Event Detection Dashboard")
st.caption("Diterjemahkan dari Pine Script [Alpha Extract] ke Python & Streamlit")

# ==========================================
# 1. SIDEBAR CONFIGURATION (INPUTS)
# ==========================================
st.sidebar.header("General Settings")
i_volLen = st.sidebar.number_input("Volume MA Length", min_value=1, value=20)
i_priceLookback = st.sidebar.number_input("Price Pattern Lookback", min_value=5, value=20)
i_minBarsWithoutSignal = st.sidebar.number_input("Minimum Bars Between Events", min_value=1, value=5)

st.sidebar.header("Trading Range Visualization")
i_showTradingRange = st.sidebar.checkbox("Show Trading Range", value=true)
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
# 2. GENERATE MOCK DATA / GENERASI DATA SINTETIS
# ==========================================
# Membuat data tiruan untuk simulasi chart jika tidak ada data asli
@st.cache_data
def load_mock_data():
    np.random.seed(42)
    n = 200
    price = 100.0
    prices = []
    volumes = []
    highs = []
    lows = []
    opens = []
    
    # Membuat siklus Accumulation -> Markup -> Distribution -> Markdown
    for i in range(n):
        if i < 50: # Accumulation (Sideways)
            move = np.random.normal(0, 0.5)
        elif i < 100: # Markup (Uptrend)
            move = np.random.normal(0.8, 0.6)
        elif i < 150: # Distribution (Sideways High)
            move = np.random.normal(-0.1, 0.7)
        else: # Markdown (Downtrend)
            move = np.random.normal(-1.0, 0.8)
            
        price += move
        op = price - np.random.uniform(-0.5, 0.5)
        hi = max(price, op) + np.random.uniform(0, 1.2)
        lo = min(price, op) - np.random.uniform(0, 1.2)
        vol = np.random.uniform(500, 2000)
        
        # Trigger anomali volume tinggi pada area kritis (Climax / Spring)
        if i in [45, 95, 140, 180]: 
            vol *= 3
            hi += 2 if i == 95 else 0
            lo -= 2 if i == 45 else 0

        prices.append(round(price, 2))
        opens.append(round(op, 2))
        highs.append(round(hi, 2))
        lows.append(round(lo, 2))
        volumes.append(int(vol))
        
    df = pd.DataFrame({'Open': opens, 'High': highs, 'Low': lows, 'Close': prices, 'Volume': volumes})
    return df

df = load_mock_data()

# ==========================================
# 3. WYCKOFF CALCULATION ENGINE
# ==========================================

# Technical Indicators
df['VolMA'] = df['Volume'].rolling(window=i_volLen).mean()
df['HighestHigh'] = df['High'].rolling(window=i_priceLookback).max()
df['LowestLow'] = df['Low'].rolling(window=i_priceLookback).min()
df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
df['ATR'] = df['TR'].rolling(window=i_priceLookback).mean()

# Fungsi pembantu untuk trend
def is_falling(series, n):
    return series.diff(n) < 0

def is_rising(series, n):
    return series.diff(n) > 0

# Deteksi Pivot Points (Manual Logic dari IsPivotHigh/Low)
def check_pivot(df, strength):
    p_high = np.zeros(len(df), dtype=bool)
    p_low = np.zeros(len(df), dtype=bool)
    for i in range(strength, len(df) - strength):
        # Pivot High
        if all(df['High'].iloc[i] > df['High'].iloc[i-j] for j in range(1, strength+1)) and \
           all(df['High'].iloc[i] > df['High'].iloc[i+j] for j in range(1, strength+1)):
            p_high[i] = True
        # Pivot Low
        if all(df['Low'].iloc[i] < df['Low'].iloc[i-j] for j in range(1, strength+1)) and \
           all(df['Low'].iloc[i] < df['Low'].iloc[i+j] for j in range(1, strength+1)):
            p_low[i] = True
    return p_high, p_low

df['PivotHigh'], df['PivotLow'] = check_pivot(df, i_pivotStrength)

# Menginisialisasi Kolom Event & Phase
df['Event'] = ""
df['Phase'] = "NEUTRAL"

bearishCount = 0
bullishCount = 0

# Iterasi bar per bar untuk replikasi logika sekuensial Pine Script
for idx in range(len(df)):
    if idx < i_priceLookback:
        continue
        
    row = df.iloc[idx]
    prev_row = df.iloc[idx-1]
    
    # Tentukan Phase saat ini berdasarkan counter kumulatif sebelumnya
    current_phase = "NEUTRAL"
    if bearishCount > bullishCount * 2.0:
        current_phase = "DISTRIBUTION"
    elif bullishCount > bearishCount * 2.0:
        current_phase = "ACCUMULATION"
    
    df.at[idx, 'Phase'] = current_phase

    # --- Logika Deteksi Event ---
    # Bearish Conditions
    psy = row['High'] > prev_row['HighestHigh'] and row['Volume'] > row['VolMA'] * i_volThreshMult and row['Close'] < row['High'] - (row['High'] - row['Low']) * i_priceThreshMult and is_falling(df['Close'], i_trendStrength).iloc[idx]
    ut_d = current_phase == "DISTRIBUTION" and row['High'] > prev_row['HighestHigh'] and row['Close'] < row['Open'] and row['Volume'] > row['VolMA'] * i_volumeFilter and (row['High'] - row['Close']) > row['ATR'] * i_priceThreshMult
    bc = row['High'] > df['High'].iloc[idx-2] and row['Volume'] > row['VolMA'] * (i_volThreshMult * 1.5) and row['Close'] > row['Open'] and ((row['Close'] - row['Open']) / (row['High'] - row['Low']) > 0.6 if (row['High'] - row['Low']) != 0 else False)
    sow = row['Close'] < row['Open'] and row['Low'] < prev_row['LowestLow'] and row['Volume'] > row['VolMA'] * i_volThreshMult and is_falling(df['Close'], i_trendStrength).iloc[idx]

    # Bullish Conditions
    ps = row['Low'] < prev_row['LowestLow'] and row['Volume'] > row['VolMA'] * i_volThreshMult and row['Close'] > row['Low'] + (row['High'] - row['Low']) * i_priceThreshMult and is_falling(df['Close'], i_trendStrength).iloc[idx]
    sc = row['Low'] < prev_row['LowestLow'] and row['Volume'] > row['VolMA'] * (i_volThreshMult * 1.2) and row['Close'] > row['Low'] + (row['High'] - row['Low']) * (i_priceThreshMult * 1.5)
    spring = row['Low'] < df['Low'].iloc[idx-3] and row['Close'] > row['Open'] and row['Close'] > row['Low'] + (row['High'] - row['Low']) * 0.6 and row['Volume'] > row['VolMA'] * i_volumeFilter
    sos = row['Close'] > row['Open'] and row['High'] > prev_row['HighestHigh'] and row['Volume'] > row['VolMA'] * i_volThreshMult and is_rising(df['Close'], i_trendStrength).iloc[idx]

    # Tulis Event & update counter
    if ut_d: df.at[idx, 'Event'] = "UT-D"; bearishCount += 1
    elif bc: df.at[idx, 'Event'] = "BC"; bearishCount += 1
    elif psy: df.at[idx, 'Event'] = "PSY"; bearishCount += 1
    elif sow: df.at[idx, 'Event'] = "SOW"; bearishCount += 1
    elif spring: df.at[idx, 'Event'] = "SPRING"; bullishCount += 1
    elif sc: df.at[idx, 'Event'] = "SC"; bullishCount += 1
    elif ps: df.at[idx, 'Event'] = "PS"; bullishCount += 1
    elif sos: df.at[idx, 'Event'] = "【SOS】"; bullishCount += 1

    # Reset counter jendela berkala (Pine Script: bar_index % i_phaseWindowBars == 0)
    if idx % 20 == 0:
        bearishCount = 0
        bullishCount = 0

# ==========================================
# 4. TRADING RANGE CALCULATION (OUTPUT HARGA)
# ==========================================
last_idx = len(df) - 1
upper_range = df['HighestHigh'].iloc[last_idx]
lower_range = df['LowestLow'].iloc[last_idx]

if i_rangeStyle == "Fixed":
    lookback = min(i_fixedRangeBars, len(df))
    upper_range = df['High'].iloc[-lookback:].max()
    lower_range = df['Low'].iloc[-lookback:].min()
elif i_rangeStyle == "Pivot-based":
    ph_indices = df[df['PivotHigh'] == True].index
    pl_indices = df[df['PivotLow'] == True].index
    upper_range = df['High'].loc[ph_indices[-1]].item() if len(ph_indices) > 0 else df['High'].max()
    lower_range = df['Low'].loc[pl_indices[-1]].item() if len(pl_indices) > 0 else df['Low'].min()

# ==========================================
# 5. STREAMLIT VISUALIZATION (UI)
# ==========================================

# Metric Blocks atas
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Current Phase State", df['Phase'].iloc[-1])
with col2:
    # Mengukur S/D State terakhir
    last_row = df.iloc[-1]
    sd_state = "IN BALANCE"
    if last_row['Volume'] > last_row['VolMA'] * 1.5:
        sd_state = "DEMAND DOMINANT" if last_row['Close'] > last_row['Open'] else "SUPPLY DOMINANT"
    st.metric("S/D State", sd_state)
with col3:
    st.metric("Trading Range Upper Bound", f"Rp {upper_range:,.2f}" if upper_range else "N/A")
with col4:
    st.metric("Trading Range Lower Bound", f"Rp {lower_range:,.2f}" if lower_range else "N/A")

st.markdown("---")

# Tab Tampilan: Tabel Deteksi Event & Trading Range Detail
tab1, tab2 = st.tabs(["📋 Wyckoff Detected Events Table", "📐 Trading Range Price Details"])

with tab1:
    st.subheader("Data Historis & Deteksi Event Terkini")
    # Memfilter baris yang hanya memiliki event terdeteksi untuk kenyamanan visualisasi
    detected_events = df[df['Event'] != ""][['Open', 'High', 'Low', 'Close', 'Volume', 'Phase', 'Event']].sort_index(ascending=False)
    
    if not detected_events.empty:
        st.dataframe(
            detected_events.style.map(
                lambda v: 'color: #ff4d4d; font-weight: bold;' if v in ['UT-D', 'BC', 'PSY', 'SOW'] else 'color: #2ed573; font-weight: bold;', 
                subset=['Event']
            ), 
            use_container_width=True
        )
    else:
        st.info("Tidak ada Event Wyckoff spesifik yang terdeteksi dengan sensitivitas saat ini. Coba longgarkan filter di Sidebar.")

with tab2:
    st.subheader("Detail Rentang Harga Konsolidasi (Trading Range)")
    
    range_pct = ((upper_range - lower_range) / lower_range) * 100
    
    range_data = {
        "Parameter Range": ["Batas Atas (Resistance/Upper)", "Batas Bawah (Support/Lower)", "Lebar Rentang (Spread)", "Persentase Lebar Rentang"],
        "Nilai Harga / Persen": [
            f"{upper_range:,.2f}",
            f"{lower_range:,.2f}",
            f"{(upper_range - lower_range):,.2f}",
            f"{range_pct:.2f}%"
        ]
    }
    
    st.table(pd.DataFrame(range_data))
    st.write(f"**Metode Perhitungan Terpilih:** `{i_rangeStyle}`")

# Keterangan Label Referensi Singkat di bawah dashboard
with st.expander("ℹ️ Kamus Istilah Event Wyckoff"):
    st.markdown("""
    *   **PSY (Preliminary Supply):** Semburan penjualan pertama yang mengindikasikan distribusi akan segera dimulai.
    *   **BC (Buying Climax):** Lonjakan kenaikan harga ekstrem akibat klimaks pembelian struktural.
    *   **UT-D (Upthrust in Distribution):** Kegagalan breakout di atas resistance; pasokan mendominasi pasar.
    *   **SOW (Sign of Weakness):** Penurunan harga menembus support yang disertai volume tebal (indikasi awal markdown).
    *   **PS (Preliminary Support):** Pembelian institusional pertama yang menahan laju penurunan tajam.
    *   **SC (Selling Climax):** Aksi jual panik (kapitulasi) dengan volume masif yang sering menjadi titik dasar dasar market.
    *   **SPRING:** Penembusan palsu ke bawah support yang dengan cepat ditarik kembali ke atas untuk menjebak seller.
    *   **【SOS】(Sign of Strength):** Reli kuat menembus batas atas Trading Range didorong dominasi demand yang tinggi.
    """)
