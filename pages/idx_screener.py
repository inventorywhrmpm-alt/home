import io
    label="Download Excel",
    data=excel_data,
    file_name="idx_screening.xlsx",
    mime="application/vnd.ms-excel",
)


# =========================
# HEATMAP
# =========================

st.subheader("Heatmap")

st.dataframe(
    screen_df[["Ticker", "Final Score"]].style.background_gradient(cmap="RdYlGn"),
    use_container_width=True,
)


# =========================
# TOP STOCKS
# =========================

st.subheader("Top Ranked")

col1, col2 = st.columns(2)

with col1:
    st.write("Top Stocks")
    st.dataframe(screen_df.head(5), use_container_width=True)

with col2:
    st.write("Lowest Ranked")
    st.dataframe(screen_df.tail(5), use_container_width=True)


# =========================
# CHARTS
# =========================

st.subheader("Technical Charts")

selected_ticker = st.selectbox(
    "Select Ticker",
    [r["Ticker"] for r in results],
)

selected_data = None

for item in results:
    if item["Ticker"] == selected_ticker:
        selected_data = item
        break

if selected_data:
    hist = selected_data["History"]

    # Candlestick
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=hist.index,
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            name
