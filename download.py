import pandas as pd
import pandas_ta as ta
import yfinance as yf
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder
import joblib
st.title("Halaman Download")
st.write("Klik tombol di bawah untuk download")
# 1. Download Data untuk Training (Ambil data agak banyak agar model pintar)
ticker = "SCMA.JK"
df = yf.download(ticker, start="2020-01-01", end="2026-05-01")

# Bersihkan kolom jika MultiIndex
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# 2. Feature Engineering (Indikator)
df['RSI'] = ta.rsi(df['Close'], length=14)
macd = ta.macd(df['Close'])
df = pd.concat([df, macd], axis=1)

# Volume Status
df['Vol_Avg'] = df['Volume'].rolling(window=14).mean()
df['Volume_Status'] = df.apply(lambda x: "HIGH" if x['Volume'] > (1.5 * x['Vol_Avg']) 
                               else ("LOW" if x['Volume'] < (0.7 * x['Vol_Avg']) else "NORMAL"), axis=1)

# 3. Labeling (TARGET: Prediksi Besok)
df['Price_Change'] = df['Close'].diff().shift(-1) # Selisih harga besok
df['Target'] = df['Price_Change'].apply(lambda x: "NAIK" if x > 0 else ("TURUN" if x < 0 else "TETAP"))

# Hapus baris kosong (akibat rolling & shift)
df.dropna(inplace=True)

# 4. Encoding Teks ke Angka
# Kita perlu simpan encoder ini atau gunakan cara manual agar di Streamlit sama
le = LabelEncoder()
df['Volume_Status_Encoded'] = le.fit_transform(df['Volume_Status'])

# 5. Pilih Fitur (X) dan Target (y)
# Gunakan nama kolom yang persis sama dengan yang akan diinput di Streamlit
X = df[['Volume', 'RSI', 'MACD_12_26_9', 'Vol_Avg', 'Volume_Status_Encoded']]
y = df['Target']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 6. Training dengan Random Forest
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Cek Akurasi
y_pred = model.predict(X_test)
print(f"Akurasi Model: {accuracy_score(y_test, y_pred)*100:.2f}%")
print(classification_report(y_test, y_pred))

# 7. Simpan Model
joblib.dump(model, "model_saham_rf.joblib")
print("Model baru berhasil disimpan sebagai 'model_saham_rf.joblib'")