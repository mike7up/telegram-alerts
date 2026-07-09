import os
from datetime import datetime
import requests
import yfinance as yf

# =====================================
# CONFIGURACIÓN
# =====================================

# Diccionario con los tickers y sus nombres correspondientes
TICKERS_CONFIG = {
    "XDEW.DE": "Xtrackers MSCI World Value",
    "SXR8.DE": "iShares Core S&P 500",
    "MEUD.FR": "Amundi MSCI Europe",
    "IS3N.DE": "iShares MSCI Emerging Markets IM",
    "ZPRV.DE": "SPDR MSCI USA Small Cap Value",
    "SXR1.DE": "iShares NASDAQ 100",
    "EGLN.L": "iShares Physical Gold",
    "XMK9.DE": "Xtrackers MSCI EM Asia",
    "SPY4.DE": "SPDR S&P 400 US Mid Cap",
    "SPYY.DE": "SPDR MSCI ACWI",
}

MEDIA = 90
DIAS = 5

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# =====================================
# TELEGRAM
# =====================================


def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(
            url, data={"chat_id": CHAT_ID, "text": texto}, timeout=20
        )
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")


# =====================================
# PROCESAMIENTO DE TICKERS
# =====================================

bloque_mensaje = ""
fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

print("Procesando activos...")
print("========================================")

for ticker, nombre in TICKERS_CONFIG.items():
    try:
        # Descargar datos
        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            progress=False,
            multi_level_index=False,
        )

        if df.empty:
            print(f"⚠️ No se pudieron descargar datos para {ticker}")
            continue

        # Calcular SMA90
        df["SMA"] = df["Close"].rolling(MEDIA).mean()
        df = df.dropna()

        if len(df) < DIAS + 1:
            print(f"⚠️ Datos insuficientes para {ticker}")
            continue

        # Extraer valores necesarios
        precio = float(df["Close"].iloc[-1])
        sma_hoy = float(df["SMA"].iloc[-1])
        sma_5dias = float(df["SMA"].iloc[-(DIAS + 1)])

        # Cálculos solicitados
        pendiente = ((sma_hoy - sma_5dias) / sma_5dias) * 100
        distancia_precio = ((precio - sma_hoy) / sma_hoy) * 100

        # Clasificación por pendiente
        if pendiente > 0.30:
            estado = "🟢 Fuerte"
        elif pendiente > 0.10:
            estado = "🟡 Debilitándose"
        elif pendiente >= 0:
            estado = "orange_circle Casi plana"  # Reemplazar por emoji naranja real si tu entorno lo soporta
        else:
            estado = "🔴 Bajando"

        # Formatear el signo de la distancia (+ o -)
        signo_distancia = "+" if distancia_precio >= 0 else ""

        # Construir el bloque de texto para este activo
        bloque_mensaje += f"📌 *{nombre}* ({ticker})\n"
        bloque_mensaje += f"• Pendiente ({DIAS}d): {pendiente:.3f}%\n"
        bloque_mensaje += (
            f"• Distancia a SMA: {signo_distancia}{distancia_precio:.2f}%\n"
        )
        bloque_mensaje += f"• Estado: {estado}\n\n"

    except Exception as e:
        print(f"❌ Error procesando {ticker}: {e}")

# =====================================
# CONSTRUCCIÓN Y ENVÍO DEL REPORTE
# =====================================

if bloque_mensaje:
    mensaje_final = f"📊 *INFORME DIARIO DE MERCADO*\nFecha: {fecha}\n\n{bloque_mensaje}"

    # Envío a Telegram
    enviar_telegram(mensaje_final)
    print("Mensaje enviado a Telegram.")

    # Mostrar por pantalla (sin formato Markdown)
    print(mensaje_final.replace("*", ""))
else:
    print("No se generaron datos para enviar.")

print("========================================")
input("Pulsa Enter para salir...")
