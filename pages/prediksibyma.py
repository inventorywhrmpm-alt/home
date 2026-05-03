import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Stock Analyzer Pro MA50 Edition", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Stock Dashboard: MA5, MA20, MA50, MA100")

# --- SIDEBAR ---
st.sidebar.header("Konfigurasi")
input_ticker = st.sidebar.text_input("Masukkan Kode Saham (Tanpa .JK)", value="BBCA").upper()
period = st.sidebar.selectbox("Rentang Waktu", ["6mo", "1y", "2y", "5y"], index=1)

# Handle .JK otomatis
ticker_yf = f"{input_ticker}.JK" if not input_ticker.endswith(".JK") and "-" not in input_ticker else input_ticker

@st.cache_data
def load_data(ticker, p):
    df = yf.download(ticker, period=p)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = load_data(ticker_yf, period)

if not data.empty and len(data) > 100:
    # --- CALCULATIONS ---
    data['MA5'] = ta.sma(data['Close'], length=5)
    data['MA20'] = ta.sma(data['Close'], length=20)
    data['MA50'] = ta.sma(data['Close'], length=50) # MA50 Ditambahkan
    data['MA100'] = ta.sma(data['Close'], length=100)
    data['RSI'] = ta.rsi(data['Close'], length=14)
    
    # MACD
    macd = ta.macd(data['Close'])
    data = pd.concat([data, macd], axis=1)
    
    # Nilai Terakhir (Skalar)
    last_close = data['Close'].iloc[-1].item()
    change = last_close - data['Close'].iloc[-2].item()
    current_rsi = data['RSI'].iloc[-1].item()
    current_ma5 = data['MA5'].iloc[-1].item()
    current_ma20 = data['MA20'].iloc[-1].item()
    current_ma50 = data['MA50'].iloc[-1].item()
    current_ma100 = data['MA100'].iloc[-1].item()
    
    # MACD Values
    c_macd = data['MACD_12_26_9'].iloc[-1].item()
    c_sig = data['MACDs_12_26_9'].iloc[-1].item()

    # --- METRICS PANEL ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Harga Terakhir", f"{last_close:,.0f}", f"{change:,.0f}")
    col2.metric("RSI (14)", f"{current_rsi:.2f}")
    col3.metric("MA50 (Mid)", f"{current_ma50:,.0f}")
    col4.metric("MA100 (Long)", f"{current_ma100:,.0f}")

    # --- CHARTING ---
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.04, 
                        subplot_titles=(f'Price Action & All MA: {ticker_yf}', 'Volume', 'RSI', 'MACD'),
                        row_heights=[0.4, 0.1, 0.2, 0.3])

    # 1. Candlestick & 4 MA
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], name="MA5", line=dict(color='blue', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], name="MA20", line=dict(color='green', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], name="MA50", line=dict(color='orange', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MA100'], name="MA100", line=dict(color='red', width=2)), row=1, col=1)

    # 2. Volume
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name="Volume", marker_color='red', opacity=0.4), row=2, col=1)

    # 3. RSI
    fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='purple')), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold", row=3, col=1)

    # 4. MACD
    fig.add_trace(go.Scatter(x=data.index, y=data['MACD_12_26_9'], name="MACD", line=dict(color='blue')), row=4, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['MACDs_12_26_9'], name="Signal", line=dict(color='orange')), row=4, col=1)
    hist_colors = ['green' if val >= 0 else 'red' for val in data['MACDh_12_26_9']]
    fig.add_trace(go.Bar(x=data.index, y=data['MACDh_12_26_9'], name="Hist", marker_color=hist_colors), row=4, col=1)

    fig.update_layout(height=1000, xaxis_rangeslider_visible=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # --- ANALYSIS SUMMARY ---
    st.subheader("💡 Kesimpulan Analisa")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.write("**🛡️ Trend Status:**")
        # Jangka Panjang
        if last_close > current_ma100: st.success("✅ MA100: BULLISH")
        else: st.error("⚠️ MA100: BEARISH")
        
        # Jangka Menengah
        if last_close > current_ma50: st.success("✅ MA50: BULLISH")
        else: st.error("⚠️ MA50: BEARISH")
            
    with c2:
        st.write("**⚡ Momentum Sinyal:**")
        # Golden/Death Cross
        if current_ma5 > current_ma20: st.success("🚀 MA5 > MA20 (Golden)")
        else: st.error("📉 MA5 < MA20 (Death)")
        
        # RSI Status
        if current_rsi > 70: st.warning("🔥 RSI: Overbought")
        elif current_rsi < 30: st.success("❄️ RSI: Oversold")
        else: st.info("⚖️ RSI: Netral")

    with c3:
        st.write("**🎯 Rekomendasi:**")
        # Logika Final
        if last_close > current_ma50 and current_ma5 > current_ma20 and c_macd > c_sig:
            st.markdown("### 🟢 **BUY**")
            st.write("Harga kokoh di atas MA50 dengan momentum positif.")
        elif last_close < current_ma50 or current_ma5 < current_ma20:
            st.markdown("### 🔴 **WAIT / SELL**")
            st.write("Tren jangka menengah lemah atau di bawah MA50.")
        else:
            st.markdown("### 🟡 **WATCHING**")
            st.write("Sinyal belum seragam. Tunggu konfirmasi.")

elif data.empty:
    st.error("Data tidak ditemukan.")
else:
    st.warning("Data tidak mencukupi untuk indikator (Min 100 bar).")
