import yfinance as yf
import requests
from datetime import datetime

# =====================================
# CONFIGURACIÓN
# =====================================

TICKER = "WEBN.DE"
NOMBRE_ETF = "Amundi MSCI World UCITS ETF Acc"

MEDIA = 90
DIAS = 5

TOKEN = "TELEGRAM_TOKEN"
CHAT_ID = "TELEGRAM_CHAT_ID"

# =====================================
# TELEGRAM
# =====================================

def enviar_telegram(texto):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": texto
        },
        timeout=20
    )

# =====================================
# DESCARGAR DATOS
# =====================================

df = yf.download(
    TICKER,
    period="2y",
    interval="1d",
    progress=False,
    multi_level_index=False
)

if df.empty:
    raise Exception("No se pudieron descargar datos.")

# =====================================
# CALCULAR SMA90
# =====================================

df["SMA"] = df["Close"].rolling(MEDIA).mean()
df = df.dropna()

if len(df) < DIAS + 1:
    raise Exception("No hay suficientes datos.")

precio = float(df["Close"].iloc[-1])
sma_hoy = float(df["SMA"].iloc[-1])
sma_5dias = float(df["SMA"].iloc[-(DIAS + 1)])

pendiente = ((sma_hoy - sma_5dias) / sma_5dias) * 100

# =====================================
# CLASIFICACIÓN
# =====================================

if pendiente > 0.30:
    estado = "🟢 Tendencia fuerte"

elif pendiente > 0.10:
    estado = "🟡 Tendencia debilitándose"

elif pendiente >= 0:
    estado = "🟠 Casi plana"

else:
    estado = "🔴 Bajando"

# =====================================
# MENSAJE TELEGRAM
# =====================================

fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

mensaje = f"""
📊 INFORME DIARIO

Activo:
{NOMBRE_ETF}

Ticker:
{TICKER}

Fecha:
{fecha}

Precio:
{precio:.2f} €

SMA{MEDIA}:
{sma_hoy:.2f} €

SMA{MEDIA} hace {DIAS} días:
{sma_5dias:.2f} €

Pendiente ({DIAS} días):
{pendiente:.3f} %

Estado:
{estado}
"""

enviar_telegram(mensaje)

print("Mensaje enviado a Telegram.")

# =====================================
# RESUMEN EN PANTALLA
# =====================================

print()
print("========================================")
print(NOMBRE_ETF)
print("========================================")
print(f"Precio: {precio:.2f} €")
print(f"SMA{MEDIA}: {sma_hoy:.2f} €")
print(f"SMA{MEDIA} hace {DIAS} días: {sma_5dias:.2f} €")
print(f"Pendiente ({DIAS} días): {pendiente:.3f} %")
print(f"Estado: {estado}")
print("========================================")

input("Pulsa Enter para salir...")