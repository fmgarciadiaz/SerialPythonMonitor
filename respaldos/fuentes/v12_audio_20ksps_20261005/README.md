# Firmware V12 Audio · candidato del Monitor V13

Aplicación independiente **Scope WAV V12 Audio**, carpeta remota
`/home/arduino/ArduinoApps/scope-wav-v12-audio`. No reemplaza las fuentes
ni los valores predeterminados de [V11 P992](../v11_p992/README.md).
La MCU del Q ejecuta una sola aplicación de adquisición a la vez.

Reutiliza adquisición ADC A2/A3 y transporte P992 SCP1 V3/992, SPI 32 MHz.
Añade reproducción WAV mono a 20.000 muestras/s por A0/DAC0, TIM6 y
GPDMA1 canal 4. Python lee el archivo, selecciona L/R/mezcla, elimina su
media, remuestrea con filtro antialias y ajusta amplitud/offset antes de
cuantizar a 12 bits. No usa la salida de audio de la computadora.

El MCU mantiene 16 bloques de 480 muestras, 384 ms de reserva; Python
repone bloques por crédito confirmado. Los descriptores libres llevan a
una salida central neutral; falta de datos detiene y reporta underrun.
ADC y DAC tienen buffers y canales DMA propios.

Comandos WAV: 11 control (consultar, preparar, reproducir, detener), 13
bloque de hasta 480 códigos; respuesta 12 con sesión, estado, espacio y
contadores aceptados/reproducidos. Cada trama conserva CRC SCP1.
El relay MPU propio valida estos comandos antes de pasarlos a la MCU;
el receptor Python preserva el control del Q y la adquisición.

## Compilación sin cargar firmware

```sh
python tools/unoq.py compile --version v12_audio
```

## Activación posterior a revisión

Requiere respaldo de la aplicación actual y un cambio explícito de firmware
MCU y relay MPU. No iniciar el candidato junto con la aplicación anterior.
Primera instalación: `python tools/unoq.py create --version v12_audio`
importa fuentes sin iniciar. Antes de arrancar, detener el relay con `python tools/usb_stream.py stop`
y la app anterior con `python tools/unoq.py stop --version v11_p992`.
Cargar y arrancar mediante App Lab o
`python tools/unoq.py start --version v12_audio`, después iniciar el relay:

```sh
python tools/usb_stream.py start --firmware v12_audio --build-native
conda activate Python_3_13_DataScience
MONITOR_V13_WAV_FIRMWARE=v12_audio python monitor/v13/app.py
```

La variable habilita comandos WAV únicamente para esta pareja. No usarla
con el firmware anterior: sus validadores no admiten los nuevos tipos.
Sketch y relay compilados; 51 pruebas locales aprobadas.
Prueba física inicial aprobada: WAV estéreo 44,1 kHz remuestreado a 20 ksps;
L 997 Hz, R 2003 Hz y Mix con ambos tonos medidos en A2/A3. Cada pasada
reprodujo 40000 códigos sin underrun ni discontinuidad ADC14/31,25 kHz.
Detener confirmó IDLE y el generador previo se restauró. La pareja candidata
quedó activa en el Q. Falta ensayo sostenido y evaluación visual del usuario.
Evidencia: [informe físico](../../diagnosticos/resultados_wav/20261005_fisico.json).
Para volver, detener el monitor, el relay (`python tools/usb_stream.py stop`)
y el candidato (`python tools/unoq.py stop --version v12_audio`).
Luego arrancar la pareja anterior con
`python tools/usb_stream.py start --firmware v11_p992`.
