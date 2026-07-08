import yfinance as yf
import requests
from datetime import datetime

# =====================================
# CONFIGURACIÓN
# =====================================

TICKER = "XRP-EUR"

MEDIA = 90          # Media móvil
DIAS = 5            # Días para calcular la pendiente

TOKEN = "TELEGRAM_TOKEN"
CHAT_ID = "TELEGRAM_CHAT_ID"

# =====================================
# FUNCIÓN TELEGRAM
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
    period="1y",
    interval="1d",
    progress=False,
    multi_level_index=False
)

if df.empty:
    raise Exception("No se pudieron descargar datos.")

# =====================================
# CALCULAR SMA
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
# CLASIFICAR LA PENDIENTE
# =====================================

if pendiente > 0.30:

    estado = "🟢 Tendencia fuerte"
    enviar = False

elif pendiente > 0.10:

    estado = "🟡 Tendencia debilitándose"
    enviar = False

elif pendiente >= 0:

    estado = "🟠 Casi plana"
    enviar = True

else:

    estado = "🔴 Bajando"
    enviar = True

# =====================================
# MENSAJE
# =====================================

if enviar:

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    mensaje = f"""
⚠️ XRP-EUR

Estado de la SMA{MEDIA}

{estado}

Fecha:
{fecha}

Precio:
{precio:.4f} €

SMA{MEDIA} hoy:
{sma_hoy:.4f} €

SMA{MEDIA} hace {DIAS} días:
{sma_5dias:.4f} €

Pendiente ({DIAS} días):
{pendiente:.4f} %
"""

    enviar_telegram(mensaje)

    print("Mensaje enviado a Telegram.")

else:

    print("No se envía aviso.")

print()
print("========== RESUMEN ==========")
print(f"Precio: {precio:.4f} €")
print(f"SMA{MEDIA}: {sma_hoy:.4f} €")
print(f"Pendiente {DIAS} días: {pendiente:.4f} %")
print(f"Estado: {estado}")
print("=============================")

input("Pulsa Enter para salir...")