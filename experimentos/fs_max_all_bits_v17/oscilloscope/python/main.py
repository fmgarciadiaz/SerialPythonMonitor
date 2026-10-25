"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("Scope V17: usar Monitor V17 y relay V16 SCP1 V4/992.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
