import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# --- LOGIKA INTI ---

def yang_zhang_sigma(df, length=20):
    if len(df) < length + 1:
        return pd.Series([1e-10] * len(df))
    log_ho = np.log(df['High'] / df['Open'])
    log_lo = np.log(df['Low'] / df['Open'])
    log_co = np.log(df['Close'] / df['Open'])
    log_oc_sq = np.log(df['Open'] / df['Close'].shift(1))**2
    log_cc_sq = np.log(df['Close'] / df['Close'].shift(1))**2
    rs_var = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    k = 0.34 / (1.34 + (length + 1) / (length - 1))
    sigma_sq = (log_oc_sq.rolling(length).mean() + k * log_cc_sq.rolling(length).mean() + (1 - k) * rs_var.rolling(length).mean())
    return np.sqrt(sigma_sq).fillna(1e-10)

def compute_isotropic_trend(df, period, groups, threshold, sigma):
    mid_log = np.log((df['High'] + df['Low']) / 2)
    current_sigma = sigma.iloc[-1]
    blocks = []
    for i in range(groups):
        start = -(i + 1) * period
        end = -i * period if i > 0 else None
        if abs(start) > len(mid_log): return "N/A", 0
        blocks.insert(0, mid_log.iloc[start:end].mean())
    slopes = np.diff(blocks)
    avg_slope = np.mean(slopes) / (current_sigma * np.sqrt(period))
    angle_deg = np.degrees(np.arctan(avg_slope))
    
    if abs(angle_deg) < threshold: return "◈ RNG", angle_deg
    return ("▲ UP", angle_deg) if angle_deg > 0 else ("▼ DN", angle_deg)

# --- UI & STYLING ---

st.set_page_config(page_title="ST-EP06 Dashboard", layout="centered")

st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    th { color: #888 !important; font-weight: normal !important; text-align: center !important; border: 0.1px solid #333 !important; }
    td { text-align: center !important; border: 0.1px solid #333 !important; font-family: monospace; }
    .blue-text { color: #44aaff; font-weight: bold; }
    .up-text { color: #26a69a; font-weight: bold; }
    .dn-text { color: #ef5350; font-weight: bold; }
    .rng-text { color: #888; }
    .header-box { border: 1px solid #333; padding: 10px; border-bottom: none; background: #131722; margin-top: 20px; }
    .footer-box { border: 1px solid #333; padding: 10px; border-top: none; background: #131722; font-size: 0.85rem; color: #bbb; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    user_ticker = st.text_input("Ticker IDX", value="BBCA").upper()
    i_thresh = st.slider("Threshold Sudut (°)", 0.0, 2.0, 0.5)
    st.info("Gunakan threshold lebih tinggi untuk memfilter noise pada market yang sideways.")

# Load Data
df = yf.download(f"{user_ticker}.JK", period="1y", interval="1d", progress=False)
if df.columns.nlevels > 1: df.columns = df.columns.get_level_values(0)

if not df.empty:
    sigma = yang_zhang_sigma(df)
    scales = [3, 7, 13, 26, 29, 47]
    results = []
    for s in scales:
        trend, _ = compute_isotropic_trend(df, s, 5, i_thresh, sigma)
        results.append(trend)

    # --- DASHBOARD RENDERING ---
    last_price = df['Close'].iloc[-1]
    
    st.markdown(f"""
    <div class="header-box">
        <span style="color:white; font-weight:bold;">ST-EP06 • #{user_ticker} • 1D</span>
        <span style="float:right; color:white;">{last_price:,.0f} IDR</span>
    </div>
    """, unsafe_allow_html=True)

    def get_trend_class(t):
        if "UP" in t: return "up-text"
        if "DN" in t: return "dn-text"
        return "rng-text"

    table_html = f"""
    <table style="width:100%; border-collapse: collapse; background: #131722;">
        <tr>
            <th style="width:15%;">period</th>
            {" ".join([f'<td><span class="blue-text">{s}</span></td>' for s in scales])}
        </tr>
        <tr>
            <th>trend</th>
            {" ".join([f'<td><span class="{get_trend_class(r)}">{r}</span></td>' for r in results])}
        </tr>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)

    # Agreement & Channel Logic
    up_count = sum(1 for r in results if "UP" in r)
    dn_count = sum(1 for r in results if "DN" in r)
    dominant = f"{up_count}/6 UP ▲" if up_count >= dn_count else f"{dn_count}/6 DN ▼"
    
    low_47 = df['Low'].tail(47).min()
    high_47 = df['High'].tail(47).max()
    pct_from_floor = ((last_price - low_47) / (high_47 - low_47)) * 100

    st.markdown(f"""
    <div class="footer-box">
        agreement: {dominant} | H: {high_47:,.0f} | L: {low_47:,.0f}<br>
        <div style="margin-top:5px; border-top: 0.5px solid #333; padding-top:5px;">
        Inside channel - <b>{pct_from_floor:.1f}%</b> from floor - <b>{100-pct_from_floor:.1f}%</b> to ceiling
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- SEKSI PANDUAN & REKOMENDASI ---
    st.write("---")
    with st.expander("📖 Cara Baca & Rekomendasi Strategi"):
        st.markdown(f"""
        ### 1. Cara Membaca Skala
        *   **Period Kecil (3-13):** Tren jangka pendek (Mikro). Cepat berubah, cocok untuk konfirmasi entri cepat.
        *   **Period Menengah (26-29):** Tren utama untuk *Swing Trading*.
        *   **Period Besar (47):** Struktur pasar jangka panjang. Jika ini **UP**, abaikan koreksi kecil.

        ### 2. Rekomendasi Berdasarkan Konsensus
        *   ✅ **Strong Bullish (5/6 - 6/6 UP):** Konfirmasi beli sangat kuat. Layak di-hold.
        *   ⚠️ **Conflicting (Bercampur):** Market sedang galau. Sebaiknya *wait and see*.
        *   ❌ **Bearish (Dominan DN):** Hindari emiten ini sampai skala kecil (3-7) mulai berbalik UP.

        ### 3. Eksekusi Berdasarkan Channel
        *   **Near Floor (<20%):** Area *High Reward, Low Risk*. Bagus untuk akumulasi beli.
        *   **Near Ceiling (>80%):** Area jenuh beli. Hati-hati koreksi meskipun tren masih UP.
        """)

else:
    st.error("Data tidak ditemukan. Pastikan ticker benar.")
