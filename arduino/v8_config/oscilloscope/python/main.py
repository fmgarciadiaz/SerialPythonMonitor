"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("Output Select V7: control permanente del Q. Usar relay dual y verificar_salida_q.py.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
