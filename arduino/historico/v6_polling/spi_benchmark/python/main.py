"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("SPI polling V6: sin ADC. Usar tools/spi_benchmark.py --firmware v6_polling.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
