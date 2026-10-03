"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("SPI benchmark V6: sin ADC. Ejecutar diagnosticos/verificar_spi.py en Linux.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
