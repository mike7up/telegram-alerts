import yfinance as yf
import pandas as pd
import numpy as np
import requests

# ==========================================
# CONFIGURACIÓN DE TELEGRAM Y STRATEGY
# ==========================================
TELEGRAM_TOKEN = "TU_TOKEN_DE_TELEGRAM_AQUI"
TELEGRAM_CHAT_ID = "TU_CHAT_ID_AQUI"

TICKERS = [
    "IUSQ.DE", "VWCE.DE", "EUNL.DE", "SXR8.DE", "XDEW.DE", 
    "EUNK.DE", "IS3N.DE", "ZPRV.DE", "SXR1.DE", "XMK9.DE", 
    "SPY4.PA", "EGLN.L"
]

MEDIA_90 = 90
MEDIA_250 = 250
DIAS_PENDIENTE = 5
CAJA_REFERENCIA = 30.0  

def enviar_mensaje_telegram(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Mensaje enviado con éxito a Telegram.")
        else:
            print(f"Error al enviar a Telegram: {response.text}")
    except Exception as e:
        print(f"Error de conexión con Telegram: {e}")

print("Obteniendo datos de mercado y procesando señales...")

# Encabezado del mensaje de Telegram
mensaje_tg = "📊 *INFORME DIARIO: ESTRATEGIA PROGRESIVA*\n"
mensaje_tg += "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"

hay_sugerencias = False
bloque_compras = ""
bloque_acumulacion = ""

for ticker in TICKERS:
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty:
            continue
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        columna_cierre = "Close" if "Close" in df.columns else "Adj Close"
        df = df.rename(columns={columna_cierre: "Close"})
        
        df["SMA_90"] = df["Close"].rolling(MEDIA_90).mean()
        df["SMA_250"] = df["Close"].rolling(MEDIA_250).mean()
        
        ultimo_dia = df.iloc[-1]
        dia_previo_pendiente = df.iloc[-1 - DIAS_PENDIENTE]
        
        precio_actual = float(ultimo_dia["Close"])
        sma90_actual = float(ultimo_dia["SMA_90"])
        sma90_previa = float(dia_previo_pendiente["SMA_90"])
        sma250_actual = float(ultimo_dia["SMA_250"])
        
        pendiente = ((sma90_actual - sma90_previa) / sma90_previa) * 100
        dist_sma250 = ((precio_actual - sma250_actual) / sma250_actual) * 100
        
        # --- Cálculo de Inversión ---
        if pendiente <= -0.05:
            inv_pendiente = 30.0 + (abs(pendiente) * 10) ** 2
        else:
            inv_pendiente = 0.0
            
        if dist_sma250 < 0:
            inv_sma250 = CAJA_REFERENCIA * ((abs(dist_sma250) / 20.0) ** 2)
        else:
            inv_sma250 = 0.0
            
        total_sugerido = inv_pendiente + inv_sma250
        
        # --- Lógica de Semáforos (Puntos de colores) ---
        # 1. Color para la Pendiente SMA90
        if pendiente > 0:
            emoji_pend = "🟢"  # Subiendo limpia
        elif pendiente >= -0.05:
            emoji_pend = "🟡"  # En zona de alerta, pero sin compra
        else:
            emoji_pend = "🔴"  # Caída que activa compra cuadrática
            
        # 2. Color para la distancia SMA250
        emoji_250 = "🟢" if dist_sma250 >= 0 else "🚨"

        # Formatear la línea de información resumida del ETF
        linea_etf = (
            f"🔹 *{ticker}* | Prc: `{precio_actual:.2f}€`\n"
            f"  {emoji_pend} Pend. SMA90: `{pendiente:.4f}%`\n"
            f"  {emoji_250} Dist. SMA250: `{dist_sma250:.2f}%`\n"
        )

        if total_sugerido > 0:
            hay_sugerencias = True
            linea_etf += f"  💰 *COMPRA SUGERIDA: {total_sugerido:.2f}€* (Pend: {inv_pendiente:.1f}€ + 250: {inv_sma250:.1f}€)\n\n"
            bloque_compras += linea_etf
        else:
            linea_etf += "  ⚪️ Sin señal (Guardar efectivo en caja)\n\n"
            bloque_acumulacion += linea_etf
            
    except Exception as e:
        print(f"Error procesando {ticker}: {e}")

# Construcción final del mensaje estructurado para Telegram
if hay_sugerencias:
    mensaje_tg += "🔥 *SEÑALES DE COMPRA ACTIVAS* 🔥\n"
    mensaje_tg += bloque_compras
    mensaje_tg += "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"

mensaje_tg += "💤 *ETFS EN ACUMULACIÓN DE CAJA*\n"
mensaje_tg += bloque_acumulacion
mensaje_tg += f"\n💡 _Nota: Multiplicador SMA250 basado en {CAJA_REFERENCIA}€._"

# Enviar el informe compilado
enviar_mensaje_telegram(mensaje_tg)