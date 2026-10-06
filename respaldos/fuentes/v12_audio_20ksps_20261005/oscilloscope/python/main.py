"""Mantiene la app; el verificador se ejecuta separadamente en Linux."""
import time
from arduino.app_utils import App

print("Scope WAV V12 Audio candidato: usar Monitor V13 y relay v12_audio SCP1 V3/992.", flush=True)


def loop():
    time.sleep(1)


App.run(user_loop=loop)
