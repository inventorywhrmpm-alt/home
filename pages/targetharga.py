import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- LOGIKA INTI INDIKATOR (Logic Asli) ---

def yang_zhang_sigma(df, length=20):
    """Menghitung Realized Volatility Yang-Zhang (2000)"""
    # Menghindari error jika data terlalu pendek
    if len(df) < length + 1:
        return pd.Series([1e-10] * len(df))
        
    log_ho = np.log(df['High'] / df['Open'])
    log_lo = np.log(df['Low'] / df['Open'])
    log_co = np.log(df['Close'] / df['Open'])
    
    log_oc_sq = np.log(df['Open'] / df['Close'].shift(1))**2
    log_cc_sq = np.log(df['Close'] / df['Close'].shift(1))**2
    
    rs_var = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    k = 0.34 / (1.34 + (length + 1) / (length - 1))
    
    sigma_sq = (log_oc_sq.rolling(length).mean() + 
                k * log_cc_sq.rolling(length).mean() + 
                (1 - k) * rs_var.rolling(length).mean())
    
    return np.sqrt(sigma_sq).fillna(1e-10)

def compute_isotropic_trend(df, period, groups, threshold, sigma):
    """Logika utama Isotropic Trend Line"""
    # 1. Block Construction
    mid_log = np.log((df['High'] + df['Low']) / 2)
    current_sigma = sigma.iloc[-1]
    
    # Ambil data blok terakhir
    blocks = []
    for i in range(groups):
        start = -(i + 1) * period
        end = -i * period if i > 0 else None
        if abs(start) > len(mid_log):
            return "N/A", 0
        block_val = mid_log.iloc[start:end].mean()
        blocks.insert(0, block_val)
    
    # 2. ICS Angle Calculation
    slopes = np.diff(blocks)
    avg_slope = np.mean(slopes) / (current_sigma * np.sqrt(period))
    angle_deg = np.degrees(np.arctan(avg_slope))
    
    # Klasifikasi Arah
    if abs(angle_deg) < threshold:
        direction = "◈ RNG"
    elif angle_deg > 0:
        direction = "▲ UP"
    else:
        direction = "▼ DN"
        
    return direction, round(angle_deg, 2)

# --- TAMPILAN STREAMLIT ---

st.set_page_config(page_title="Smart Trader EP06 - IDX", layout="wide")

# Custom CSS untuk gaya "Glassmorphism" ringan
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { color: #26a69a; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Smart Trader EP06: Isotropic Trend Lines (IDX)")

# Sidebar Inputs
with st.sidebar:
    st.header("🔍 Market & Params")
    # Input Ticker Tanpa .JK
    user_ticker = st.text_input("Ticker IDX (Contoh: BBCA, ASII, GOTO)", value="BBCA").upper()
    full_ticker = f"{user_ticker}.JK"
    
    st.divider()
    i_period = st.number_input("Trend Block Period", 5, 100, 26)
    i_groups = st.number_input("Trend Block Groups", 2, 10, 5)
    i_thresh = st.slider("Range Threshold (°)", 0.0, 45.0, 0.5)
    i_sigma_len = st.number_input("Yang-Zhang Sigma Length", 5, 100, 20)

# Fetch Data dari Yahoo Finance
@st.cache_data(ttl=3600)
def load_idx_data(symbol):
    try:
        data = yf.download(symbol, period="1y", interval="1d")
        return data
    except:
        return None

df = load_idx_data(full_ticker)

if df is not None and not df.empty:
    # Eksekusi Logika
    sigma = yang_zhang_sigma(df, i_sigma_len)
    scales_actual = [3, 7, 13, i_period, 29, 47]

    results = []
    for s in scales_actual:
        dir_name, angle = compute_isotropic_trend(df, s, i_groups, i_thresh, sigma)
        results.append({
            "Scale": f"Period {s}",
            "Trend": dir_name,
            "Angle": f"{angle}°"
        })

    # Header Dashboard
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        st.subheader(f"📊 Dashboard: {user_ticker} (IDX)")
    with col_b:
        st.metric("Live Price", f"Rp {df['Close'].iloc[-1]:,.0f}")
    with col_c:
        st.metric("Volatility (σ)", f"{sigma.iloc[-1]:.5f}")

    # Visualisasi Tabel (Horizontal ala Dashboard TradingView)
    res_df = pd.DataFrame(results).set_index("Scale").T
    
    # Menampilkan Tabel
    st.table(res_df)

    # Narrative Analysis
    trend_counts = pd.DataFrame(results)['Trend'].value_counts()
    dominant_trend = trend_counts.idxmax()
    consensus_score = trend_counts.max()

    st.markdown(f"""
    > **Narrative Summary:**  
    > Instrumen **{user_ticker}** saat ini menunjukkan tren dominan **{dominant_trend}** dengan tingkat konsensus **{consensus_score}/6** skala. 
    > Analisis menggunakan ruang Isotropik memastikan sudut tren tidak terdistorsi oleh lonjakan volatilitas harian.
    """)

else:
    st.error(f"Data untuk ticker {user_ticker} tidak ditemukan. Pastikan kode saham benar.")

st.divider()
st.caption("Data source: Yahoo Finance | Isotropic Analysis by Gemini")
