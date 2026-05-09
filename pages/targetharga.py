import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- LOGIKA INTI INDIKATOR ---

def yang_zhang_sigma(df, length=20):
    """Menghitung Realized Volatility Yang-Zhang (2000)"""
    if len(df) < length + 1:
        return pd.Series([1e-10] * len(df))
    
    # Menghitung komponen log
    log_ho = np.log(df['High'] / df['Open'])
    log_lo = np.log(df['Low'] / df['Open'])
    log_co = np.log(df['Close'] / df['Open'])
    
    # Menggunakan shift(1) untuk Open-to-Close semalam
    log_oc_sq = np.log(df['Open'] / df['Close'].shift(1))**2
    log_cc_sq = np.log(df['Close'] / df['Close'].shift(1))**2
    
    rs_var = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    k = 0.34 / (1.34 + (length + 1) / (length - 1))
    
    sigma_sq = (log_oc_sq.rolling(length).mean() + 
                k * log_cc_sq.rolling(length).mean() + 
                (1 - k) * rs_var.rolling(length).mean())
    
    return np.sqrt(sigma_sq).fillna(1e-10)

def compute_isotropic_trend(df, period, groups, threshold, sigma):
    """Menghitung sudut tren dalam ruang Isotropik (Volatility-Adjusted)"""
    mid_log = np.log((df['High'] + df['Low']) / 2)
    current_sigma = sigma.iloc[-1]
    
    if np.isnan(current_sigma) or current_sigma == 0:
        current_sigma = 1e-10

    blocks = []
    for i in range(groups):
        start = -(i + 1) * period
        end = -i * period if i > 0 else None
        if abs(start) > len(mid_log):
            return "N/A", 0
        block_val = mid_log.iloc[start:end].mean()
        blocks.insert(0, block_val)
    
    slopes = np.diff(blocks)
    # Normalisasi slope terhadap volatilitas (Isotropic Scaling)
    avg_slope = np.mean(slopes) / (current_sigma * np.sqrt(period))
    angle_deg = np.degrees(np.arctan(avg_slope))
    
    if abs(angle_deg) < threshold:
        return "◈ RNG", angle_deg
    elif angle_deg > 0:
        return "▲ UP", angle_deg
    else:
        return "▼ DN", angle_deg

# --- TAMPILAN STREAMLIT ---

st.set_page_config(page_title="Smart Trader EP06 - IDX", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    .trend-card {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        background-color: #1e2127;
        border: 1px solid #333;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Smart Trader: Isotropic Trend Analysis")

with st.sidebar:
    st.header("🔍 Market & Params")
    user_ticker = st.text_input("Ticker IDX", value="BBCA").upper()
    full_ticker = f"{user_ticker}.JK"
    
    st.divider()
    i_period = st.number_input("Core Block Period", 5, 100, 26)
    i_groups = st.number_input("Trend Block Groups", 2, 10, 5)
    i_thresh = st.slider("Range Threshold (°)", 0.0, 5.0, 0.5, step=0.1)
    i_sigma_len = st.number_input("Volatility Window", 5, 100, 20)

@st.cache_data(ttl=3600)
def load_idx_data(symbol):
    try:
        data = yf.download(symbol, period="2y", interval="1d")
        if data.columns.nlevels > 1: # Flatten MultiIndex columns
            data.columns = data.columns.get_level_values(0)
        return data
    except Exception as e:
        return None

df = load_idx_data(full_ticker)

if df is not None and not df.empty:
    sigma = yang_zhang_sigma(df, i_sigma_len)
    scales = [3, 7, 13, i_period, 47, 60] # Variasi Timeframe (Micro ke Macro)

    # Header Dashboard
    col_price, col_vol = st.columns(2)
    last_price = df['Close'].iloc[-1]
    last_sigma = sigma.iloc[-1]
    
    col_price.metric(f"Price {user_ticker}", f"Rp {last_price:,.0f}")
    col_vol.metric("Yang-Zhang Volatility", f"{last_sigma:.5f}")

    st.write("### 🧭 Isotropic Multi-Scale Analysis")
    
    # Layout Horizontal Status
    cols = st.columns(len(scales))
    results = []
    
    for i, s in enumerate(scales):
        dir_name, angle = compute_isotropic_trend(df, s, i_groups, i_thresh, sigma)
        results.append({"Trend": dir_name, "Angle": angle})
        
        # Color Logic
        color = "#26a69a" if "UP" in dir_name else "#ef5350" if "DN" in dir_name else "#9e9e9e"
        
        with cols[i]:
            st.markdown(f"""
                <div class="trend-card">
                    <p style='color: #888; margin-bottom: 5px;'>P-{s}</p>
                    <h3 style='color: {color}; margin: 0;'>{dir_name}</h3>
                    <p style='color: #555; font-size: 0.8rem;'>{angle:.2f}°</p>
                </div>
            """, unsafe_allow_html=True)

    # Narrative Summary
    trend_list = [r['Trend'] for r in results]
    dominant_trend = max(set(trend_list), key=trend_list.count)
    consensus = trend_list.count(dominant_trend)

    st.info(f"**Analisis Kesimpulan:** Saham {user_ticker} sedang berada dalam fase **{dominant_trend}** dengan kekuatan konsensus **{consensus}/{len(scales)}** skala waktu. " + 
            ("Akurasi tren tinggi karena didukung berbagai timeframe." if consensus > 4 else "Hati-hati, tren belum stabil di semua skala."))

else:
    st.error(f"Gagal memuat data {user_ticker}. Cek kembali kode saham di Yahoo Finance.")

st.caption("Disclaimer: Analisis ini berbasis volatilitas statistik dan bukan saran investasi.")
