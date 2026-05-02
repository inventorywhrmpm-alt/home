import yfinance as yf
import pandas as pd
import os
from datetime import datetime

def load_tickers():
    file_path = "saham.txt"
    tickers = []
    
    # Cek apakah file saham.txt ada di folder
    if os.path.exists(file_path):
        print(f"--- Memuat daftar saham dari {file_path} ---")
        with open(file_path, "r") as f:
            content = f.read()
            # Membersihkan koma, spasi, dan newline
            raw_list = content.replace('\n', ',').split(',')
            tickers = [t.strip().upper() + ".JK" for t in raw_list if t.strip()]
    else:
        print(f"--- File {file_path} tidak ditemukan! Menggunakan daftar default ---")
        tickers = ["GOTO.JK", "BUKA.JK", "BRMS.JK", "ANTM.JK", "BRIS.JK"]
        
    return list(set(tickers)) # Menghapus duplikat jika ada

def run_scanner():
    tickers = load_tickers()
    hasil_filter = []
    total = len(tickers)
    
    print(f"Memulai scan {total} saham...")
    print("Kriteria: Harga < 2000 | Vol Spike > 1x | Naik 0-3%\n")

    for i, ticker in enumerate(tickers):
        try:
            # Download data cepat (1 bulan terakhir)
            data = yf.download(ticker, period="30d", interval="1d", progress=False)
            
            if data.empty or len(data) < 21:
                continue

            # --- FILTER 1: HARGA (Paling Utama) ---
            last_price = float(data['Close'].iloc[-1])
            if last_price >= 2000 or last_price < 50:
                continue

            # --- FILTER 2: VOLUME SPIKE ---
            curr_volume = float(data['Volume'].iloc[-1])
            avg_vol_20 = float(data['Volume'].iloc[-21:-1].mean())
            
            if avg_vol_20 == 0: continue
            vol_ratio = curr_volume / avg_vol_20

            if vol_ratio > 1:
                # --- FILTER 3: KENAIKAN HARGA ---
                prev_close = float(data['Close'].iloc[-2])
                price_change = ((last_price - prev_close) / prev_close) * 100
                
                if 0 < price_change <= 3:
                    print(f"MATCH! >> {ticker:8} | Rp {last_price:5.0f} | Vol: {vol_ratio:4.2f}x | +{price_change:4.2f}%")
                    
                    hasil_filter.append({
                        'Ticker': ticker.replace('.JK', ''),
                        'Harga': int(last_price),
                        'Vol_Ratio': round(vol_ratio, 2),
                        'Naik_%': round(price_change, 2)
                    })

        except Exception:
            continue

    # Hasil Akhir
    print("\n" + "="*50)
    if hasil_filter:
        df = pd.DataFrame(hasil_filter).sort_values(by='Vol_Ratio', ascending=False)
        print(df.to_string(index=False))
        
        # Simpan ke Excel agar rapi
        nama_file = f"Hasil_Scan_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df.to_excel(nama_file, index=False)
        print(f"\nFile hasil scan disimpan ke: {nama_file}")
    else:
        print("Tidak ada saham yang cocok hari ini.")
    print("="*50)

if __name__ == "__main__":
    run_scanner()