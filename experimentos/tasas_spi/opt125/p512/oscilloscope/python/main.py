"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("Scope Opt125 P512: receptor aislado de tasas altas.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
