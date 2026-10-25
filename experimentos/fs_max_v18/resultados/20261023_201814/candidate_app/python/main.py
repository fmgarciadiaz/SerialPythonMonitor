"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("Scope V18 Rate Probe BatchFast: 2 x SCP1 V4/992, app experimental privada.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
