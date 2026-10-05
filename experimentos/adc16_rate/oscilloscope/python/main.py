"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("Scope ADC16 Rate Experiment: usar receiver aislado ADC16 y relay SCP1 V3/992.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
