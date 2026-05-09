import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Konfigurasi Halaman
st.set_page_config(page_title="Price Target Visualizer", layout="wide")

## --- LOGIC ASLI PINE SCRIPT --- ##

def calculate_percent_change(target, current_close):
    if not current_close: return "0%"
    change = ((target / current_close) - 1) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}%"

def get_color(price, compared_to, pos_color, neg_color):
    # Mengembalikan warna berdasarkan apakah target di atas harga penutupan
    return pos_color if price >= compared_to else neg_color

## --- UI STREAMLIT --- ##

st.title("📊 Analyst Price Target Visualizer")

# Input Sidebar (Mirip input.color di Pine Script)
with st.sidebar:
    st.header("Settings")
    ticker_input = st.text_input("Symbol", value="AAPL").upper()
    pos_color = st.color_picker("Positive Color", "#089981")
    neg_color = st.color_picker("Negative Color", "#f23645")
    
    # Konversi hex ke RGBA untuk transparansi (fill)
    pos_fill = f"rgba(8, 153, 129, 0.2)"
    neg_fill = f"rgba(242, 54, 69, 0.2)"

# Fetch Data
try:
    ticker_data = yf.Ticker(ticker_input)
    df = ticker_data.history(period="1y")
    info = ticker_data.info

    if df.empty:
        st.error("No data found for this symbol.")
    else:
        # Mengambil Analyst Targets (Mirip syminfo.target_price_*)
        target_high = info.get('targetHighPrice')
        target_low = info.get('targetLowPrice')
        target_avg = info.get('targetMeanPrice')
        current_close = df['Close'].iloc[-1]
        
        # Simulasi YearFromNow (12 bulan dari sekarang)
        last_date = df.index[-1]
        target_date = last_date + timedelta(days=365)

        if target_high and target_low and target_avg:
            # Membuat Plotly Chart
            fig = go.Figure()

            # 1. Plot Candlestick
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                name="Price"
            ))

            # 2. Logic Menggambar Target (Mirip drawTarget & linefill)
            targets = [
                ("Max", target_high),
                ("Avg", target_avg),
                ("Min", target_low)
            ]

            for label_text, price in targets:
                p_change = calculate_percent_change(price, current_close)
                line_color = get_color(price, current_close, pos_color, neg_color)
                fill_color = get_color(price, current_close, pos_fill, neg_fill)

                # Garis Proyeksi (Dotted Line)
                fig.add_trace(go.Scatter(
                    x=[last_date, target_date],
                    y=[current_close, price],
                    mode='lines+text',
                    name=f"Target {label_text}",
                    line=dict(color=line_color, width=2, dash='dot'),
                    text=["", f"{label_text} {p_change}"],
                    textposition="top right"
                ))

                # Area Fill (Simulasi linefill Pine Script)
                fig.add_trace(go.Scatter(
                    x=[last_date, target_date, target_date, last_date],
                    y=[current_close, price, current_close, current_close],
                    fill='toself',
                    fillcolor=fill_color,
                    line=dict(color='rgba(255,255,255,0)'),
                    hoverinfo='skip',
                    showlegend=False
                ))

            # Update Layout agar terlihat seperti TradingView
            fig.update_layout(
                height=700,
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                yaxis_title="Price",
                margin=dict(l=10, r=10, t=10, b=10)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Info Box (Mirip tooltip label.new)
            num_analysts = info.get('numberOfAnalystOpinions', 'N/A')
            st.info(f"**Analyst Insights:** The {num_analysts} analysts offering 1 year price forecasts for {ticker_input} "
                    f"have a max estimate of {target_high} and a min estimate of {target_low}.")

        else:
            # Warning jika data analis tidak ada (Mirip barstate.islast logic)
            st.warning("No analyst predictions found for this symbol.")
            st.info("If there are any new predictions, they should appear once the market data providers update.")

except Exception as e:
    st.error(f"Error fetching data: {e}")
