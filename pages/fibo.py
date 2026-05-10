import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

def get_fibonacci_analysis(ticker_input, timeframe):
    clean_ticker = ticker_input.strip().upper().replace(".JK", "")
    yf_ticker = f"{clean_ticker}.JK"
    
    try:
        df = yf.download(yf_ticker, period="60d", interval=timeframe, progress=False)
        if df.empty: return None

        current_price = float(df['Close'].iloc[-1].item())
        high_price = float(df['High'].max().item())
        low_price = float(df['Low'].min().item())
        diff = high_price - low_price

        # Definisi Level Fibonacci (Tanpa 0% dan 100%)
        fib_levels = {
            "23.6%": round(high_price - (0.236 * diff), 2),
            "38.2%": round(high_price - (0.382 * diff), 2),
            "50.0%": round(high_price - (0.5 * diff), 2),
            "61.8%": round(high_price - (0.618 * diff), 2),
            "78.6%": round(high_price - (0.786 * diff), 2)
        }

        # --- Logika Penentuan Posisi & Target ---
        # Gabungkan semua level untuk perbandingan
        all_points = sorted([
            {"lvl": "100%", "px": low_price},
            {"lvl": "78.6%", "px": fib_levels["78.6%"]},
            {"lvl": "61.8%", "px": fib_levels["61.8%"]},
            {"lvl": "50.0%", "px": fib_levels["50.0%"]},
            {"lvl": "38.2%", "px": fib_levels["38.2%"]},
            {"lvl": "23.6%", "px": fib_levels["23.6%"]},
            {"lvl": "0%", "px": high_price}
        ], key=lambda x: x['px'])

        status_ket = "Di luar range"
        target_lvl = "-"
        target_px = 0.0

        for i in range(len(all_points) - 1):
            lower = all_points[i]
            upper = all_points[i+1]
            
            if lower['px'] <= current_price <= upper['px']:
                # Cek mana yang lebih dekat
                dist_lower = abs(current_price - lower['px'])
                dist_upper = abs(current_price - upper['px'])
                
                closer = lower['lvl'] if dist_lower < dist_upper else upper['lvl']
                status_ket = f"Dekat {closer}"
                
                # Target adalah level di atasnya jika sedang naik, atau level itu sendiri jika belum tercapai
                target_lvl = upper['lvl']
                target_px = upper['px']
                break

        return {
            "Ticker": clean_ticker,
            "Price": round(current_price, 2),
            "Status": status_ket,
            "Target Level": target_lvl,
            "Target Price": target_px,
            "Fibo 23.6%": fib_levels["23.6%"],
            "Fibo 38.2%": fib_levels["38.2%"],
            "Fibo 50.0%": fib_levels["50.0%"],
            "Fibo 61.8%": fib_levels["61.8%"],
            "Fibo 78.6%": fib_levels["78.6%"],
            "High (Ref)": high_price,
            "Low (Ref)": low_price
        }
    except: return None

# --- UI STREAMLIT ---
st.set_page_config(page_title="IDX Fibonacci Pro", layout="wide")

with st.sidebar:
    st.header("Settings")
    input_user = st.text_input("Ticker (contoh: SCMA, BBCA)", "SCMA, BBCA, GOTO")
    tf_choice = st.selectbox("Timeframe:", ["1h", "4h", "1d"], index=2)
    btn_run = st.button("Analyze")

st.title("🎯 Fibonacci Target & Status")

if btn_run:
    tickers = [t.strip() for t in input_user.split(",")]
    results = []
    
    for t in tickers:
        data = get_fibonacci_analysis(t, tf_choice)
        if data: results.append(data)
    
    if results:
        df = pd.DataFrame(results)
        
        # Penataan kolom agar Status dan Target berada di depan
        cols = ["Ticker", "Price", "Status", "Target Level", "Target Price", 
                "Fibo 23.6%", "Fibo 38.2%", "Fibo 50.0%", "Fibo 61.8%", "Fibo 78.6%"]
        
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
    else:
        st.error("Data tidak ditemukan.")
