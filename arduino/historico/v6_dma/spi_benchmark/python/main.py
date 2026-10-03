"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("SPI DMA V6: sin ADC. Usar tools/spi_benchmark.py --firmware v6_dma.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
