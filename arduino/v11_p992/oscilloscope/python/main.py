"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("Scope Acquisition P992 V11: usar Monitor V12 y relay SCP1 V3/992.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
