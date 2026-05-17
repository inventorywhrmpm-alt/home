import io
import json
import time
import concurrent.futures

import numpy as np
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ======================================================
# CONFIG
# ======================================================

st.set_page_config(
    page_title="IDX Stock Screener",
    page_icon="📈",
    layout="wide"
)

# ======================================================
# STYLE
# ======================================================

st.markdown("""
<style>
.main {
    background-color: #0E1117;
    color: white;
}

div[data-testid="metric-container"] {
    background-color: #1E1E1E;
    border-radius: 12px;
    padding: 15px;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# HELPERS
# ======================================================

WATCHLIST_FILE = "watchlist.json"


def normalize_ticker(ticker):
    ticker = ticker.strip().upper()

    if not ticker.endswith(".JK"):
        ticker += ".JK"

    return ticker


def load_watchlist():
    try:
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_watchlist(data):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f)


# ======================================================
# TECHNICAL INDICATORS
# ======================================================

def add_indicators(df):
    df = df.copy()

    df["MA20"] = ta.sma(df["Close"], length=20)
    df["MA50"] = ta.sma(df["Close"], length=50)

    df["RSI"] = ta.rsi(df["Close"], length=14)

    macd = ta.macd(df["Close"])

    df["MACD"] = macd["MACD_12_26_9"]
    df["MACD_SIGNAL"] = macd["MACDs_12_26_9"]

    df["VOL_MA20"] = ta.sma(df["Volume"], length=20)
    df["VOL_RATIO"] = df["Volume"] / df["VOL_MA20"]

    return df


def detect_trend(df):
    latest = df.iloc[-1]

    if latest["MA20"] > latest["MA50"]:
        return "Bullish"

    return "Bearish"


def generate_signal(df):
    latest = df.iloc[-1]

    if latest["RSI"] < 30:
        return "BUY"

    if latest["RSI"] > 70:
        return "SELL"

    return "HOLD"


# ======================================================
# SCORING
# ======================================================

def fundamental_score(row):
    score = 0

    if row["PER"] > 0 and row["PER"] < 15:
        score += 25

    if row["PBV"] > 0 and row["PBV"] < 3:
        score += 25

    if row["ROE"] > 15:
        score += 25

    if row["Net Margin"] > 10:
        score += 25

    return score


def technical_score(row):
    score = 0

    if row["RSI"] < 70:
        score += 25

    if row["Trend"] == "Bullish":
        score += 35

    if row["Volume Ratio"] > 1:
        score += 20

    if row["Signal"] == "BUY":
        score += 20

    return score


def final_score(fundamental, technical):
    return round((fundamental * 0.5) + (technical * 0.5), 2)


# ======================================================
# FILTER
# ======================================================

def apply_filters(df, max_per, max_pbv, min_roe, rsi_range, bullish_only):
    filtered = df.copy()

    filtered = filtered[
        (filtered["PER"] <= max_per)
        & (filtered["PBV"] <= max_pbv)
        & (filtered["ROE"] >= min_roe)
        & (filtered["RSI"] >= rsi_range[0])
        & (filtered["RSI"] <= rsi_range[1])
    ]

    if bullish_only:
        filtered = filtered[filtered["Trend"] == "Bullish"]

    return filtered


# ======================================================
# EXPORT
# ======================================================

def export_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def export_excel(df):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Screening")

    return output.getvalue()


# ======================================================
# FETCH DATA
# ======================================================

@st.cache_data(ttl=300)
def fetch_single_stock(ticker):
    try:
        stock = yf.Ticker(ticker)

        info = stock.info
        hist = stock.history(period="1y")

        if hist.empty:
            return None

        hist = add_indicators(hist)

        latest = hist.iloc[-1]

        data = {
            "Ticker": ticker.replace(".JK", ""),
            "Current Price": round(latest["Close"], 2),
            "Market Cap": info.get("marketCap", 0),
            "PER": info.get("trailingPE", 0) or 0,
            "PBV": info.get("priceToBook", 0) or 0,
            "ROE": round((info.get("returnOnEquity", 0) or 0) * 100, 2),
            "Net Margin": round((info.get("profitMargins", 0) or 0) * 100, 2),
            "RSI": round(latest["RSI"], 2),
            "Volume Ratio": round(latest["VOL_RATIO"], 2),
            "Trend": detect_trend(hist),
            "Signal": generate_signal(hist),
            "History": hist
        }

        return data

    except Exception:
        return None


@st.cache_data(ttl=300)
def fetch_multiple_stocks(tickers):
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_stock, t) for t in tickers]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()

            if result:
                results.append(result)

    return results


# ======================================================
# UI
# ======================================================

st.title("📈 IDX Stock Screener")

st.sidebar.header("Filters")

max_per = st.sidebar.slider("Max PER", 0, 100, 20)
max_pbv = st.sidebar.slider("Max PBV", 0, 20, 5)
min_roe = st.sidebar.slider("Min ROE", 0, 50, 10)

rsi_range = st.sidebar.slider(
    "RSI Range",
    0,
    100,
    (30, 70)
)

bullish_only = st.sidebar.checkbox("Bullish Only")

input_text = st.text_area(
    "Input IDX Tickers",
    value="BBCA\nBBRI\nTLKM\nASII",
    height=150
)

raw_tickers = [x.strip() for x in input_text.splitlines() if x.strip()]
tickers = [normalize_ticker(t) for t in raw_tickers]

with st.spinner("Fetching market data..."):
    results = fetch_multiple_stocks(tickers)

if not results:
    st.error("No valid ticker found")
    st.stop()

rows = []

for item in results:

    f_score = fundamental_score(item)
    t_score = technical_score(item)

    rows.append({
        "Ticker": item["Ticker"],
        "Current Price": item["Current Price"],
        "PER": item["PER"],
        "PBV": item["PBV"],
        "ROE": item["ROE"],
        "RSI": item["RSI"],
        "Trend": item["Trend"],
        "Signal": item["Signal"],
        "Volume Ratio": item["Volume Ratio"],
        "Fundamental Score": f_score,
        "Technical Score": t_score,
        "Final Score": final_score(f_score, t_score)
    })

screen_df = pd.DataFrame(rows)

screen_df = apply_filters(
    screen_df,
    max_per,
    max_pbv,
    min_roe,
    rsi_range,
    bullish_only
)

screen_df = screen_df.sort_values(
    by="Final Score",
    ascending=False
)

# ======================================================
# METRICS
# ======================================================

col1, col2, col3, col4 = st.columns(4)

col1.metric("Stocks", len(screen_df))
col2.metric("Avg PER", round(screen_df["PER"].mean(), 2))
col3.metric("Avg ROE", round(screen_df["ROE"].mean(), 2))
col4.metric("Avg RSI", round(screen_df["RSI"].mean(), 2))

# ======================================================
# TABLE
# ======================================================

st.subheader("Screener Table")

st.dataframe(
    screen_df,
    use_container_width=True
)

# ======================================================
# EXPORT
# ======================================================

csv_data = export_csv(screen_df)
excel_data = export_excel(screen_df)

col1, col2 = st.columns(2)

col1.download_button(
    "Download CSV",
    csv_data,
    "idx_screening.csv",
    "text/csv"
)

col2.download_button(
    "Download Excel",
    excel_data,
    "idx_screening.xlsx"
)

# ======================================================
# CHARTS
# ======================================================

st.subheader("Technical Charts")

selected = st.selectbox(
    "Select Ticker",
    [r["Ticker"] for r in results]
)

selected_data = None

for r in results:
    if r["Ticker"] == selected:
        selected_data = r
        break

if selected_data:

    hist = selected_data["History"]

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=hist.index,
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            name="Candlestick"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist["MA20"],
            mode="lines",
            name="MA20"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist["MA50"],
            mode="lines",
            name="MA50"
        )
    )

    fig.update_layout(
        template="plotly_dark",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
