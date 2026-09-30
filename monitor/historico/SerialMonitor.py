
# %%
# Importaciones
import serial
from serial.tools import list_ports
import pandas as pd
import time

# %%
# Listar dispositivos seriales e identificar Arduino

palabras_arduino = (
    "arduino",
    "usbmodem",
    "usb serial",
    "ch340",
    "cp210",
    "ftdi",
    "wch",
)

puertos = list(list_ports.comports())
puertos_arduino = []

if not puertos:
    print("No se encontraron dispositivos seriales.")
else:
    print("Dispositivos seriales encontrados:\n")

    for puerto in puertos:
        informacion = " ".join(
            str(valor or "")
            for valor in [
                puerto.device,
                puerto.description,
                puerto.manufacturer,
                puerto.product,
                puerto.hwid,
            ]
        ).lower()

        es_arduino = any(palabra in informacion for palabra in palabras_arduino)
        etiqueta = " <-- Arduino probable" if es_arduino else ""

        print(
            f"{puerto.device}: {puerto.description} | "
            f"fabricante: {puerto.manufacturer or 'N/D'}{etiqueta}"
        )

        if es_arduino:
            puertos_arduino.append(puerto.device)

if len(puertos_arduino) == 1:
    print(f"\nArduino identificado en: {puertos_arduino[0]}")
else:
    print("\nNo se pudo identificar un unico Arduino automaticamente.")



# %%
# Configuración

PORT = puertos_arduino[0] if len(puertos_arduino) == 1 else "COM7"
BAUD = 921600
N_CICLOS = 5
MUESTRA_INICIO = 1

# %%
# Conectar

ser = serial.Serial(PORT, BAUD, timeout=1)

# Esperar a que Arduino reinicie
time.sleep(2)

ser.reset_input_buffer()

print("Conectado a", PORT)

# %%
# Leer datos

datos = []

ciclo = 0
muestras_ciclo = 0
capturando = False
ultimo_estado = None

print(f"Esperando la muestra {MUESTRA_INICIO} enviada por Arduino...")

while ciclo < N_CICLOS:

    linea = ser.readline().decode("utf-8", errors="ignore").strip()

    if not linea:
        continue

    # Saltar encabezado
    if linea.startswith("estado"):
        continue

    partes = linea.split(",")

    if len(partes) != 4:
        continue

    estado = partes[0]
    muestra = int(partes[1])
    tiempo_us = int(partes[2])
    adc = int(partes[3])

    # Descartar todo hasta recibir la muestra inicial real de Arduino.
    if not capturando:
        if muestra == MUESTRA_INICIO:
            capturando = True
            ciclo = 0
            muestras_ciclo = 0
            print(
                f"Comenzando ciclo {ciclo + 1} "
                f"desde la muestra {MUESTRA_INICIO}."
            )
        else:
            continue
    elif ultimo_estado == "OFF" and estado == "ON":
        # Un ciclo nuevo comienza cuando vuelve la fase de carga.
        print(
            f"Ciclo {ciclo + 1} finalizado: "
            f"{muestras_ciclo} muestras capturadas."
        )
        ciclo += 1
        if ciclo >= N_CICLOS:
            break
        muestras_ciclo = 0
        print(f"Comenzando ciclo {ciclo + 1}.")

    datos.append([
        ciclo,
        estado,
        muestra,
        tiempo_us,
        adc
    ])

    muestras_ciclo += 1
    ultimo_estado = estado


ser.close()
print(f"Captura finalizada: {min(ciclo + 1, N_CICLOS)} ciclos completos.")

# %%
# Crear DataFrame y calcular voltaje

df = pd.DataFrame(
    datos,
    columns=[
        "ciclo",
        "estado",
        "muestra",
        "tiempo_us",
        "ADC"
    ]
)

# Voltaje calculado, sin perder el ADC original
df["voltaje_V"] = df["ADC"] * 3.3 / 4095
df["muestra_ciclo"] = df["muestra"]
# Arduino ya envia el tiempo relativo desde la muestra 0 de cada ciclo.
df["tiempo_ms"] = df["tiempo_us"] / 1000

print("\nListo.")
print("Muestras:", len(df))

df.head()

# %%
# Graficar voltaje en funcion del tiempo para cada ciclo

import matplotlib.pyplot as plt

if df.empty:
    print("No hay datos para graficar.")
else:
    fig, ejes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    fases = {
        "ON": (ejes[0], "Carga"),
        "OFF": (ejes[1], "Descarga"),
    }

    for estado, (eje, nombre_fase) in fases.items():
        datos_fase = df[df["estado"] == estado]

        for ciclo, datos_ciclo in datos_fase.groupby("ciclo"):
            eje.plot(
                datos_ciclo["tiempo_ms"],
                datos_ciclo["voltaje_V"],
                label=f"Ciclo {ciclo}",
            )

        eje.set_ylabel("Voltaje (V)")
        eje.set_title(nombre_fase)
        eje.grid(True, alpha=0.3)
        eje.legend()

    ejes[1].set_xlabel("Tiempo desde muestra 0 (ms)")
    fig.suptitle("Voltaje en funcion del tiempo: carga y descarga")
    plt.tight_layout()
    plt.show()

# %%

# Medir cinco respuestas de un segundo y estimar RC

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

N_MEDICIONES_RC = 5
DURACION_MEDICION_S = 1.0


def capturar_medicion_rc(numero_medicion):
    ser_rc.reset_input_buffer()
    datos_medicion = []
    inicio = time.perf_counter()

    while time.perf_counter() - inicio < DURACION_MEDICION_S:
        linea = ser_rc.readline().decode("utf-8", errors="ignore").strip()
        if not linea or linea.startswith("estado"):
            continue

        partes = linea.split(",")
        if len(partes) != 4:
            continue

        try:
            estado = partes[0]
            adc = int(partes[3])
        except ValueError:
            continue

        datos_medicion.append({
            "medicion": numero_medicion,
            "estado": estado,
            "tiempo_s": time.perf_counter() - inicio,
            "ADC": adc,
        })

    return datos_medicion


def estimar_tau(datos_fase, fase):
    if len(datos_fase) < 3:
        return np.nan

    tiempo = datos_fase["tiempo_s"].to_numpy()
    voltaje = datos_fase["voltaje_V"].to_numpy()

    if fase == "ON":
        def modelo(tiempo, voltaje_inicial, voltaje_final, tau):
            return voltaje_final - (
                voltaje_final - voltaje_inicial
            ) * np.exp(-tiempo / tau)
    else:
        def modelo(tiempo, voltaje_inicial, voltaje_final, tau):
            return voltaje_final + (
                voltaje_inicial - voltaje_final
            ) * np.exp(-tiempo / tau)

    try:
        parametros, _ = curve_fit(
            modelo,
            tiempo,
            voltaje,
            p0=[voltaje[0], voltaje[-1], max(tiempo[-1] / 3, 1e-6)],
            bounds=([-np.inf, -np.inf, 1e-9], [np.inf, np.inf, np.inf]),
            maxfev=10000,
        )
    except (RuntimeError, ValueError):
        return np.nan

    return parametros[2]


input(
    "Conecta la primera resistencia y presiona Enter "
    "para comenzar las mediciones..."
)

ser_rc = serial.Serial(PORT, BAUD, timeout=0.05)
time.sleep(1)
mediciones_rc = []

try:
    for numero_medicion in range(1, N_MEDICIONES_RC + 1):
        if numero_medicion > 1:
            input(
                f"Cambia la resistencia para la medicion {numero_medicion} "
                "y presiona Enter..."
            )

        print(
            f"Midiendo {numero_medicion}/{N_MEDICIONES_RC} "
            f"durante {DURACION_MEDICION_S:.0f} segundo..."
        )
        datos_nuevos = capturar_medicion_rc(numero_medicion)
        mediciones_rc.extend(datos_nuevos)
        print(
            f"Medicion {numero_medicion} finalizada: "
            f"{len(datos_nuevos)} muestras."
        )
finally:
    ser_rc.close()

df_rc = pd.DataFrame(mediciones_rc)

if df_rc.empty:
    print("No se recibieron datos para estimar RC.")
else:
    df_rc["voltaje_V"] = df_rc["ADC"] * 3.3 / 4095
    resultados_rc = []

    for numero_medicion, datos_medicion in df_rc.groupby("medicion"):
        tau_carga = estimar_tau(
            datos_medicion[datos_medicion["estado"] == "ON"],
            "ON",
        )
        tau_descarga = estimar_tau(
            datos_medicion[datos_medicion["estado"] == "OFF"],
            "OFF",
        )
        resultados_rc.append({
            "medicion": numero_medicion,
            "RC_carga_s": tau_carga,
            "RC_descarga_s": tau_descarga,
            "RC_promedio_s": np.nanmean([tau_carga, tau_descarga]),
        })

    resultados_rc = pd.DataFrame(resultados_rc)
    print("\nEstimacion de RC:")
    print(resultados_rc)

    fig, ejes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for estado, (eje, nombre_fase) in {
        "ON": (ejes[0], "Carga"),
        "OFF": (ejes[1], "Descarga"),
    }.items():
        for numero_medicion, datos_medicion in df_rc[
            df_rc["estado"] == estado
        ].groupby("medicion"):
            eje.plot(
                datos_medicion["tiempo_s"],
                datos_medicion["voltaje_V"],
                label=f"Medicion {numero_medicion}",
            )
        eje.set_title(nombre_fase)
        eje.set_ylabel("Voltaje (V)")
        eje.grid(True, alpha=0.3)
        eje.legend()

    ejes[1].set_xlabel("Tiempo desde el inicio de la medicion (s)")
    fig.suptitle("Cinco mediciones superpuestas y estimacion de RC")
    plt.tight_layout()
    plt.show()
