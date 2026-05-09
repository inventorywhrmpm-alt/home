import streamlit as st
import pandas as pd
import numpy as np

# --- LOGIKA INTI INDIKATOR (Calculations) ---

def yang_zhang_sigma(df, length=20):
    """Menghitung Realized Volatility Yang-Zhang (2000)"""
    log_ho = np.log(df['high'] / df['open'])
    log_lo = np.log(df['low'] / df['open'])
    log_co = np.log(df['close'] / df['open'])
    
    log_oc_sq = np.log(df['open'] / df['close'].shift(1))**2
    log_cc_sq = np.log(df['close'] / df['close'].shift(1))**2
    
    rs_var = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    
    k = 0.34 / (1.34 + (length + 1) / (length - 1))
    
    sigma_sq = (log_oc_sq.rolling(length).mean() + 
                k * log_cc_sq.rolling(length).mean() + 
                (1 - k) * rs_var.rolling(length).mean())
    
    return np.sqrt(sigma_sq).fillna(1e-10)

def compute_isotropic_trend(df, period, groups, threshold, sigma):
    """Logika utama Isotropic Trend Line"""
    # 1. Block Construction (Geometric Mean of Midpoints)
    mid_log = np.log((df['high'] + df['low']) / 2)
    
    # Ambil bar terakhir berdasarkan anchor (simulasi bar [0])
    current_sigma = sigma.iloc[-1]
    
    # 2. Direction Detection & Angle Calculation
    # Mengambil midpoint dari blok-blok terakhir
    blocks = []
    for i in range(groups):
        start = -(i + 1) * period
        end = -i * period if i > 0 else None
        block_val = mid_log.iloc[start:end].mean()
        blocks.insert(0, block_val)
    
    # Hitung slope (dimensi normalized terhadap sigma)
    slopes = np.diff(blocks)
    avg_slope = np.mean(slopes) / (current_sigma * np.sqrt(period))
    
    # Isotropic Angle (ICS)
    angle_deg = np.degrees(np.arctan(avg_slope))
    
    # Klasifikasi Arah
    if abs(angle_deg) < threshold:
        direction = "RNG"
        color = "grey"
    elif angle_deg > 0:
        direction = "UP"
        color = "green"
    else:
        direction = "DN"
        color = "red"
        
    return direction, round(angle_deg, 2), color

# --- TAMPILAN STREAMLIT ---

st.set_page_config(page_title="Smart Trader EP06 - Isotropic Dashboard", layout="wide")

st.title("🛡️ Smart Trader EP06: Isotropic Trend Lines")
st.markdown("Multi-scale structural trend channel built on Isotropic Coordinate System (ICS).")

# Sidebar Inputs (Sesuai Pine Script)
with st.sidebar:
    st.header("Settings")
    i_period = st.number_input("Trend Block Period", 5, 100, 26)
    i_groups = st.number_input("Trend Block Groups", 2, 10, 5)
    i_thresh = st.slider("Range Threshold (°)", 0.0, 45.0, 0.5)
    i_sigma_len = st.number_input("Yang-Zhang Sigma Length", 5, 100, 20)

# Dummy Data Generator (Ganti dengan data asli Anda)
def get_data():
    dates = pd.date_range(start="2024-01-01", periods=300, freq="D")
    data = pd.DataFrame({
        'open': np.random.uniform(100, 110, 300),
        'high': np.random.uniform(110, 115, 300),
        'low': np.random.uniform(95, 100, 300),
        'close': np.random.uniform(100, 110, 300)
    }, index=dates)
    return data

df = get_data()

# Eksekusi Logika
sigma = yang_zhang_sigma(df, i_sigma_len)
scales = [3, 7, 13, 19, 29, 47]
# Skala 19 dipetakan ke input user i_period
scales_actual = [3, 7, 13, i_period, 29, 47]

results = []
for s in scales_actual:
    dir_name, angle, _ = compute_isotropic_trend(df, s, i_groups, i_thresh, sigma)
    results.append({"Scale Period": s, "Trend": dir_name, "ICS Angle": f"{angle}°"})

# --- VISUALISASI TABEL DASHBOARD ---

st.subheader("📊 Multi-Scale Analysis Dashboard")

# Mengubah list hasil menjadi DataFrame untuk tabel
res_df = pd.DataFrame(results).T
res_df.columns = [f"Scale {i+1}" for i in range(len(scales_actual))]

# Menampilkan tabel dengan gaya highlight
def style_trend(val):
    if val == "UP": return 'background-color: #26a69a; color: white'
    if val == "DN": return 'background-color: #ef5350; color: white'
    if val == "RNG": return 'background-color: #888888; color: white'
    return ''

st.table(res_df)

# Consensus & Narrative (Step 5 & 6)
trend_counts = pd.DataFrame(results)['Trend'].value_counts()
primary_trend = results[3]['Trend'] # Skala i_period

st.info(f"**Consensus:** {trend_counts.max()} out of 6 scales agree on **{trend_counts.idxmax()}**")

# Simulasi Narrative Row
col1, col2 = st.columns(2)
with col1:
    st.metric("Primary Trend (Period %d)" % i_period, primary_trend)
with col2:
    st.metric("Current Volatility (σ)", f"{sigma.iloc[-1]:.6f}")

st.divider()
st.caption("Note: This dashboard uses Yang-Zhang volatility to normalize price movement into a dimensionless space (Isotropic).")
