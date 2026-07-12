import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE TELEGRAM Y STRATEGY
# ==========================================
TELEGRAM_TOKEN = "TU_TOKEN_DE_TELEGRAM_AQUI"
TELEGRAM_CHAT_ID = "TU_CHAT_ID_AQUI"
FICHERO_SISTEMA = "estado_cartera_etfs.json"

TICKERS = [
    "IUSQ.DE", "VWCE.DE", "EUNL.DE", "SXR8.DE", "XDEW.DE", 
    "EUNK.DE", "IS3N.DE", "ZPRV.DE", "SXR1.DE", "XMK9.DE", 
    "SPY4.PA", "EGLN.L"
]

MEDIA_90 = 90
MEDIA_250 = 250
DIAS_PENDIENTE = 5
APORTACION_DIARIA = 20.0  

# ==========================================
# GESTIÓN DEL SISTEMA DE CARTERA (PERSISTENCIA)
# ==========================================
def cargar_estado():
    if os.path.exists(FICHERO_SISTEMA):
        with open(FICHERO_SISTEMA, "r") as f:
            return json.load(f)
    else:
        # Estado inicial si no existe el archivo
        estado = {
            "caja_actual": 0.0,
            "ultimo_acceso": "",
            "cartera": {} # Estructura: {"TICKER": {"participaciones": 0.0, "precio_medio": 0.0}}
        }
        for ticker in TICKERS:
            estado["cartera"][ticker] = {"participaciones": 0.0, "precio_medio": 0.0}
        return estado

def guardar_estado(estado):
    with open(FICHERO_SISTEMA, "w") as f:
        json.dump(estado, f, indent=4)

def calcular_extra_sma250(dist_pct):
    if dist_pct >= 0: return 0.0
    caida = abs(dist_pct)
    if caida <= 0.2:
        return (caida / 0.2) * 2.0
    elif caida <= 1.0:
        valor_inf = 2.0
        valor_sup = 8.0 + (2.0 ** 1.8)
        proporcion = (caida - 0.2) / (1.0 - 0.2)
        return valor_inf + proporcion * (valor_sup - valor_inf)
    else:
        base_exponencial = (caida - 1.0) + 2.0
        return 8.0 + (base_exponencial ** 1.8)

def enviar_mensaje_telegram(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: print("⚠️ No se pudo enviar el reporte a Telegram.")

# ==========================================
# PROCESO PRINCIPAL
# ==========================================
estado = cargar_estado()
hoy_str = datetime.now().strftime("%Y-%m-%d")

print("="*60)
print(f"💰 SISTEMA INTERACTIVO DE CARTERA Y RENTABILIDAD")
print("="*60)

if estado["ultimo_acceso"] != hoy_str:
    estado["caja_actual"] += APORTACION_DIARIA
    estado["ultimo_acceso"] = hoy_str
    print(f"🟢 ¡Nuevo día! Se han sumado {APORTACION_DIARIA}€ automáticamente a tu caja.")
else:
    print("ℹ️ Ya habías abierto el script hoy. No se duplica la aportación diaria.")

print(f"💵 Tu saldo de caja acumulado actual es: {estado['caja_actual']:.2f}€\n")
print("🔄 Descargando datos y analizando mercado...")

mensaje_tg = "📊 *INFORME DIARIO: ESTRATEGIA PROGRESIVA*\n"
mensaje_tg += f"💰 *Caja disponible hoy:* `{estado['caja_actual']:.2f}€`\n"
mensaje_tg += "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"

hay_sugerencias = False
bloque_compras = ""
bloque_acumulacion = ""
precios_hoy = {}

for ticker in TICKERS:
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        columna_cierre = "Close" if "Close" in df.columns else "Adj Close"
        df = df.rename(columns={columna_cierre: "Close"})
        
        df["SMA_90"] = df["Close"].rolling(MEDIA_90).mean()
        df["SMA_250"] = df["Close"].rolling(MEDIA_250).mean()
        
        ultimo_dia = df.iloc[-1]
        dia_previo_pendiente = df.iloc[-1 - DIAS_PENDIENTE]
        
        precio_actual = float(ultimo_dia["Close"])
        precios_hoy[ticker] = precio_actual # Guardamos el precio para el proceso interactivo posterior
        
        pendiente = ((float(ultimo_dia["SMA_90"]) - float(dia_previo_pendiente["SMA_90"])) / float(dia_previo_pendiente["SMA_90"])) * 100
        dist_sma250 = ((precio_actual - float(ultimo_dia["SMA_250"])) / float(ultimo_dia["SMA_250"])) * 100
        
        if pendiente <= -0.05:
            inv_pendiente = 30.0 + (abs(pendiente) * 10) ** 2
        else:
            inv_pendiente = 0.0
            
        inv_sma250 = calcular_extra_sma250(dist_sma250)
        total_sugerido = inv_pendiente + inv_sma250
        
        emoji_pend = "🟢" if pendiente > 0 else ("🟡" if pendiente >= -0.05 else "🔴")
        emoji_250 = "🟢" if dist_sma250 >= 0 else "🚨"

        linea_etf = (
            f"🔹 *{ticker}* | Prc: `{precio_actual:.2f}€`\n"
            f"  {emoji_pend} Pend. SMA90: `{pendiente:.4f}%`\n"
            f"  {emoji_250} Dist. SMA250: `{dist_sma250:.2f}%`\n"
        )

        if total_sugerido > 0:
            hay_sugerencias = True
            linea_etf += f"  💰 *COMPRA SUGERIDA: {total_sugerido:.2f}€*\n\n"
            bloque_compras += linea_etf
        else:
            linea_etf += "  ⚪️ Sin señal\n\n"
            bloque_acumulacion += linea_etf
    except:
        pass

if hay_sugerencias:
    mensaje_tg += "🔥 *SEÑALES DE COMPRA ACTIVAS* 🔥\n" + bloque_compras + "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n"
mensaje_tg += "💤 *ETFS EN ACUMULACIÓN DE CAJA*\n" + bloque_acumulacion

enviar_mensaje_telegram(mensaje_tg)
print("📢 ¡Reporte de señales enviado a Telegram!")

# ==========================================
# PARTE INTERACTIVA: REGISTRO DE COMPRA POR ETF
# ==========================================
print("\n" + "="*60)
print("📝 REGISTRO DE COMPRA DIARIA")
print("="*60)

while True:
    print("¿Has realizado alguna compra hoy? Elige una opción:")
    print("0. No, hoy no he comprado nada (Todo va a la caja)")
    for idx, ticker in enumerate(TICKERS, 1):
        print(f"{idx}. Invertir en {ticker}")
        
    opcion = input("\nIntroduce el número de tu opción: ").strip()
    
    if opcion == "0" or opcion == "":
        print("💤 Guardando presupuesto diario intacto en la caja.")
        break
    elif opcion.isdigit() and 1 <= int(opcion) <= len(TICKERS):
        ticker_elegido = TICKERS[int(opcion) - 1]
        precio_etf = precios_hoy.get(ticker_elegido)
        
        if not precio_etf:
            print("⚠️ No se disponen de precios de hoy para este ETF. Cancela e intenta de nuevo.")
            break
            
        try:
            dinero_invertido = input(f"¿Cuántos euros has invertido en {ticker_elegido} hoy?: ")
            dinero_invertido = float(dinero_invertido.replace(",", "."))
            
            if dinero_invertido > estado["caja_actual"]:
                print(f"⚠️ Alerta: Estás gastando más de lo que tienes acumulado en caja ({estado['caja_actual']:.2f}€). El saldo quedará en negativo.")
                
            # --- CÁLCULO DE PARTICIPACIONES Y PRECIO MEDIO (RENTABILIDAD) ---
            partes_compradas = dinero_invertido / precio_etf
            
            datos_actuales = estado["cartera"].get(ticker_elegido, {"participaciones": 0.0, "precio_medio": 0.0})
            partes_viejas = datos_actuales["participaciones"]
            precio_medio_viejo = datos_actuales["precio_medio"]
            
            # Nueva cantidad total de participaciones
            nuevas_participaciones = partes_viejas + partes_compradas
            
            # Recalcular el Precio Medio Ponderado (PMP)
            if nuevas_participaciones > 0:
                nuevo_precio_medio = ((partes_viejas * precio_medio_viejo) + (partes_compradas * precio_etf)) / nuevas_participaciones
            else:
                nuevo_precio_medio = 0.0
                
            # Actualizamos el JSON interno
            estado["cartera"][ticker_elegido] = {
                "participaciones": nuevas_participaciones,
                "precio_medio": round(nuevo_precio_medio, 4)
            }
            estado["caja_actual"] -= dinero_invertido
            
            print(f"\n✅ Compra registrada con éxito:")
            print(f"   - Compradas: {partes_compradas:.4f} participaciones a {precio_etf:.2f}€")
            print(f"   - Nuevo saldo de este ETF: {nuevas_participaciones:.4f} participaciones")
            print(f"   - Tu nuevo precio medio en {ticker_elegido} es: {nuevo_precio_medio:.2f}€")
            break
        except ValueError:
            print("⚠️ Cantidad no válida. Introduce un número correcto.")
    else:
        print("⚠️ Opción incorrecta. Selecciona un número de la lista.")

# ==========================================
# REPORTE EN CONSOLA DE TU CARTERA Y SU RENTABILIDAD REAL
# ==========================================
print("\n" + "="*70)
print("📈 RESUMEN ACTUALIZADO DE TU CARTERA Y RENTABILIDAD")
print("="*70)
print(f"{'ETF':<12} | {'Partic.':<10} | {'Pr. Medio':<10} | {'Pr. Actual':<10} | {'Valor Tot.':<10} | {'Rent. (%)':<10}")
print("-"*70)

valor_total_cartera = 0.0

for ticker, datos in estado["cartera"].items():
    part = datos["participaciones"]
    pm = datos["precio_medio"]
    pa = precios_hoy.get(ticker, 0.0)
    
    if part > 0:
        valor_etf = part * pa
        valor_total_cartera += valor_etf
        # Calcular rentabilidad porcentual real
        rentabilidad = ((pa / pm) - 1) * 100
        print(f"{ticker:<12} | {part:<10.4f} | {pm:<10.2f}€ | {pa:<10.2f}€ | {valor_etf:<10.2f}€ | {rentabilidad:+.2f}%")

print("-"*70)
print(f"💰 CAPITAL EN ACCIONES: {valor_total_cartera:.2f}€")
print(f"💵 EFECTIVO EN CAJA:    {estado['caja_actual']:.2f}€")
print(f"📊 VALOR TOTAL (NETO):  {valor_total_cartera + estado['caja_actual']:.2f}€")
print("="*70)

# Guardar cambios
guardar_estado(estado)
print("💾 Fichero actualizado correctamente. ¡Buen trading!")
input("\nPresiona Enter para cerrar...")