"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("ADC SPI V6: adquisición aislada. Usar tools/spi_benchmark.py --firmware v6_adc --implementation c.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
