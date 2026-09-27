import serial
import struct
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import time

# ============================================================
# CONFIGURACIÓN
# ============================================================

PORT = "/dev/cu.usbmodemE8F60AAABD882" 
BAUD = 2_000_000                # USB del R4, no el UART del Q

N_SAMPLES = 1000

HEADER_SIZE = 7
SAMPLE_SIZE = 8
BLOCK_SIZE = HEADER_SIZE + N_SAMPLES * SAMPLE_SIZE

WINDOW_SECONDS = 2.0

# ============================================================
# SERIAL
# ============================================================

ser = serial.Serial(
    PORT,
    BAUD,
    timeout=0.01
)

print(f"Puerto: {PORT}")
print(f"Baud USB: {BAUD}")
print("Esperando datos...")

# ============================================================
# BUFFER DE RECEPCIÓN
# ============================================================

rx_buffer = bytearray()

# ============================================================
# BUFFERS PARA GRAFICAR
# ============================================================

time_buffer = deque()
adc_in_buffer = deque()
adc_out_buffer = deque()

blocks_ok = 0
blocks_bad = 0
bytes_received = 0

last_status = time.monotonic()


# ============================================================
# FUNCIÓN PARA PROCESAR UN BLOQUE
# ============================================================

def process_block(block):

    global blocks_ok, blocks_bad

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    if block[0:4] != b"DATA":
        blocks_bad += 1
        return

    estado = block[4]

    n = struct.unpack_from("<H", block, 5)[0]

    if n != N_SAMPLES:
        blocks_bad += 1
        return

    # --------------------------------------------------------
    # Decodificar las 1000 muestras
    #
    # timestamp : uint32
    # adc_in    : uint16
    # adc_out   : uint16
    # --------------------------------------------------------

    timestamps = np.empty(n, dtype=np.uint32)
    adc_in = np.empty(n, dtype=np.uint16)
    adc_out = np.empty(n, dtype=np.uint16)

    offset = 7

    for i in range(n):

        timestamp, ain, aout = struct.unpack_from(
            "<IHH",
            block,
            offset
        )

        timestamps[i] = timestamp
        adc_in[i] = ain
        adc_out[i] = aout

        offset += 8

    # --------------------------------------------------------
    # Validación
    # --------------------------------------------------------

    if np.any(adc_in > 4095) or np.any(adc_out > 4095):
        blocks_bad += 1
        return

    # --------------------------------------------------------
    # Timestamp recibido desde el Q
    #
    # Está expresado en microsegundos.
    # --------------------------------------------------------

    t = timestamps.astype(np.float64) * 1e-6

    # --------------------------------------------------------
    # Agregar al buffer de gráficos
    # --------------------------------------------------------

    time_buffer.extend(t)
    adc_in_buffer.extend(adc_in)
    adc_out_buffer.extend(adc_out)

    # --------------------------------------------------------
    # Eliminar muestras demasiado viejas
    # --------------------------------------------------------

    if len(time_buffer) > 0:

        newest = time_buffer[-1]
        limit = newest - WINDOW_SECONDS

        while time_buffer and time_buffer[0] < limit:
            time_buffer.popleft()
            adc_in_buffer.popleft()
            adc_out_buffer.popleft()

    blocks_ok += 1


# ============================================================
# MATPLOTLIB
# ============================================================

plt.ion()

fig, ax = plt.subplots(figsize=(11, 6))

line_in, = ax.plot(
    [],
    [],
    label="ADC_IN"
)

line_out, = ax.plot(
    [],
    [],
    label="ADC_OUT"
)

ax.set_xlabel("Tiempo [s]")
ax.set_ylabel("ADC [0–4095]")

ax.set_ylim(0, 4095)

ax.grid(True)
ax.legend()

fig.tight_layout()

# ============================================================
# LOOP PRINCIPAL
# ============================================================

try:

    while True:

        # ----------------------------------------------------
        # Leer UART/USB
        # ----------------------------------------------------

        n_available = ser.in_waiting

        if n_available > 0:

            data = ser.read(n_available)

            if data:
                rx_buffer.extend(data)
                bytes_received += len(data)

        # ----------------------------------------------------
        # Procesar todos los bloques completos disponibles
        # ----------------------------------------------------

        while True:

            # Buscar DATA
            pos = rx_buffer.find(b"DATA")

            if pos < 0:

                # No encontramos DATA.
                #
                # Conservamos solamente los últimos 3 bytes
                # porque podrían ser el comienzo de "DATA".
                #
                if len(rx_buffer) > 3:
                    del rx_buffer[:-3]

                break

            # ------------------------------------------------
            # Eliminar cualquier basura antes de DATA
            # ------------------------------------------------

            if pos > 0:
                del rx_buffer[:pos]

            # ------------------------------------------------
            # ¿Tenemos header completo?
            # ------------------------------------------------

            if len(rx_buffer) < HEADER_SIZE:
                break

            # ------------------------------------------------
            # Leer cantidad de muestras
            # ------------------------------------------------

            n = struct.unpack_from(
                "<H",
                rx_buffer,
                5
            )[0]

            # ------------------------------------------------
            # Header inválido
            # ------------------------------------------------

            if n != N_SAMPLES:

                blocks_bad += 1

                # Avanzamos un byte y buscamos nuevamente DATA
                del rx_buffer[0]

                continue

            # ------------------------------------------------
            # ¿Llegó todo el bloque?
            # ------------------------------------------------

            if len(rx_buffer) < BLOCK_SIZE:
                break

            # ------------------------------------------------
            # Extraer bloque
            # ------------------------------------------------

            block = bytes(rx_buffer[:BLOCK_SIZE])

            del rx_buffer[:BLOCK_SIZE]

            # ------------------------------------------------
            # Procesar
            # ------------------------------------------------

            process_block(block)

        # ----------------------------------------------------
        # Actualizar gráfico
        # ----------------------------------------------------

        if len(time_buffer) > 1:

            t = np.asarray(time_buffer)

            y_in = np.asarray(adc_in_buffer)
            y_out = np.asarray(adc_out_buffer)

            # Mostrar tiempo relativo al último punto
            t_plot = t - t[-1]

            line_in.set_data(
                t_plot,
                y_in
            )

            line_out.set_data(
                t_plot,
                y_out
            )

            ax.set_xlim(
                -WINDOW_SECONDS,
                0
            )

            ax.set_ylim(
                0,
                4095
            )

        fig.canvas.draw_idle()
        fig.canvas.flush_events()

        # ----------------------------------------------------
        # Status cada segundo
        # ----------------------------------------------------

        now = time.monotonic()

        if now - last_status >= 1.0:

            print(
                f"\r"
                f"bloques OK: {blocks_ok:6d}   "
                f"BAD: {blocks_bad:4d}   "
                f"bytes: {bytes_received:10d}   "
                f"buffer: {len(rx_buffer):6d}",
                end="",
                flush=True
            )

            last_status = now

        # ----------------------------------------------------
        # Pequeño descanso para no consumir 100% CPU
        # ----------------------------------------------------

        time.sleep(0.001)


except KeyboardInterrupt:

    print("\n\nDetenido por usuario.")

finally:

    ser.close()
    plt.ioff()
    plt.show()