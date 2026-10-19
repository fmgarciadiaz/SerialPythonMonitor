"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("Scope V16: usar Monitor V16 y relay V16 SCP1 V4/992.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
