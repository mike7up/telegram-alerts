from datetime import datetime
import os
import requests
import yfinance as yf

# =====================================
# CONFIGURACIÓN
# =====================================

# GitHub Actions inyectará estos secretos de forma segura como variables de entorno
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("❌ Error: No se han encontrado las variables de entorno TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")

TICKERS_CONFIG = {
    "XDEW.DE": "Xtrackers MSCI World Value",
    "SXR8.DE": "iShares Core S&P 500",
    "MEUD.FR": "Amundi MSCI Europe",
    "IS3N.DE": "iShares MSCI Emerging Markets IM",
    "ZPRV.DE": "SPDR MSCI USA Small Cap Value",
    "SXR1.DE": "iShares Core MSCI Pacific ex-Japan",
    "EGLN.L": "iShares Physical Gold",
    "XMK9.DE": "Xtrackers MSCI EM Asia",
    "SPY4.DE": "SPDR S&P 400 US Mid Cap",
    "SPYY.DE": "SPDR MSCI ACWI",
}

MEDIA = 90
DIAS = 5

# =====================================
# TELEGRAM
# =====================================


def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": texto,
        "parse_mode": "Markdown" # Asegura que procese los asteriscos básicos
    }
    try:
        response = requests.post(url, data=payload, timeout=20)
        # Esto hará que si Telegram devuelve un error (ej. código 400), salte al except y veas el porqué
        response.raise_for_status() 
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")
        # Si la API de Telegram responde con error, imprimimos la respuesta del servidor
        if 'response' in locals() and response:
            print(f"Detalle del error de Telegram: {response.text}")

# =====================================
# PROCESAMIENTO DE TICKERS
# =====================================

bloque_mensaje = ""
fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

print("Procesando activos...")
print("========================================")

for ticker, nombre in TICKERS_CONFIG.items():
    try:
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

        df["SMA"] = df["Close"].rolling(MEDIA).mean()
        df = df.dropna()

        if len(df) < DIAS + 1:
            print(f"⚠️ Datos insuficientes para {ticker}")
            continue

        precio = float(df["Close"].iloc[-1])
        sma_hoy = float(df["SMA"].iloc[-1])
        sma_5dias = float(df["SMA"].iloc[-(DIAS + 1)])

        pendiente = ((sma_hoy - sma_5dias) / sma_5dias) * 100
        distancia_precio = ((precio - sma_hoy) / sma_hoy) * 100

        if pendiente > 0.30:
            estado = "🟢 Fuerte"
        elif pendiente > 0.10:
            estado = "🟡 Debilitándose"
        elif pendiente >= 0:
            estado = "🟠 Casi plana"
        else:
            estado = "🔴 Bajando"

        signo_distancia = "+" if distancia_precio >= 0 else ""

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
    mensaje_final = (
        f"📊 *INFORME DE MERCADO*\nFecha: {fecha}\n\n{bloque_mensaje}"
    )
    enviar_telegram(mensaje_final)
    print("Mensaje enviado a Telegram.")
    print(mensaje_final.replace("*", ""))
else:
    print("No se generaron datos para enviar.")
