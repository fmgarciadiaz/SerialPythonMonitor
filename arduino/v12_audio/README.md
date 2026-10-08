# Firmware de adquisición, generador y audio

Aplicación independiente **Scope WAV V12 Audio**, carpeta remota
`/home/arduino/ArduinoApps/scope-wav-v12-audio`. No reemplaza las fuentes
ni los valores predeterminados de [V11 P992](../historico/v11_p992/README.md).
La MCU del Q ejecuta una sola aplicación de adquisición a la vez.

Reutiliza adquisición ADC A2/A3 y transporte P992 SCP1 V3/992, SPI 32 MHz.
Añade reproducción WAV mono a 20/40/50 mil muestras/s negociadas por A0/DAC0, TIM6 y
GPDMA1 canal 4. Python lee el archivo, selecciona L/R/mezcla, elimina su
media, remuestrea con filtro antialias y ajusta amplitud/offset a la tasa elegida antes de
cuantizar a 12 bits. No usa la salida de audio de la computadora.

El MCU mantiene 16 bloques de 480 muestras, 384 ms a 20 ksps (192 ms a 40; 153,6 ms a 50); Python
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

## Instalación y activación

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
MONITOR_V13_WAV_FIRMWARE=v12_audio python monitor/historico/v13/app.py
```

El monitor actual negocia la capacidad WAV con el MCU. La variable permite
exigir esta pareja al recuperar el enlace; el firmware anterior no admite WAV.
Sketch y relay compilados; 51 pruebas locales aprobadas.
Prueba física inicial aprobada: WAV estéreo 44,1 kHz remuestreado a 20 ksps;
L 997 Hz, R 2003 Hz y Mix con ambos tonos medidos en A2/A3. Cada pasada
reprodujo 40000 códigos sin underrun ni discontinuidad ADC14/31,25 kHz.
En ese ensayo histórico, Detener confirmó IDLE y restauró el generador previo.
El comportamiento actual deja el generador apagado al finalizar o detener Wav. La pareja candidata
quedó activa en el Q. Los ensayos sostenidos posteriores se describen en la sección de tasas.
Evidencia: [informe físico](../../diagnosticos/resultados_wav/20261005_fisico.json).
Para volver, detener el monitor, el relay (`python tools/usb_stream.py stop`)
y el candidato (`python tools/unoq.py stop --version v12_audio`).
Luego arrancar la pareja anterior con
`python tools/usb_stream.py start --firmware v11_p992`.

## Negociación de tasa

BEGIN puede incluir tasa en el campo reservado de offset 28; cero conserva
20 ksps. El estado confirma la tasa real en offset 40 y anuncia máscara 7
en offset 44 (bits 0/1/2: 20/40/50 ksps). Python admite el estado anterior
con máscara cero como sólo 20 ksps y bloquea tasas no anunciadas. Usar el
relay y Monitor V13 actualizados juntos con este firmware.

## Tasas mayores: ensayo aprobado con límites

40 y 50 ksps completaron 120 s con ADC14/40 kHz; 50 ksps también con
ADC14/100 kHz, sin underrun ni pérdida de muestras. ADC125 falló en dos
intentos con WAV50; Monitor V13 bloquea esa combinación antes de Play.
STOP y restauración ADC/generador confirmados en los ensayos aprobados.
El candidato de tasas negociadas queda activo; respaldo del anterior:
`respaldos/unoq/osciloscopio_20261005_181834_429412.zip`.
Ver [evidencia y límites](../../docs/WAV_TASAS.md).

## Preparación desde el monitor

Preparar Q comprueba herramientas, compila el sketch, respalda la app instalada,
importa/actualiza las fuentes, construye el relay y verifica recepción.
Conectar intenta primero el enlace disponible y después inicia la app/relay
instalados si falta respuesta. Desconectar confirma salida apagada antes de cerrar.
No instala Linux ni sustituye las herramientas base del Q.

## Correcciones recientes del generador

Al arrancar se mantiene el primer valor de la onda en lugar de pasar por 0 V.
Sweep/Chirp descartan diferencias de tiempo negativas antes de calcular duración.
Firmware cargado el 6 de octubre; 24 Chirps seno completos de 2 s tras la corrección.
[Informe](../../diagnosticos/README.md). El usuario confirmó que volvió a funcionar.

## Versiones y enlaces

- Esta carpeta: V12 Audio, con [Monitor V13](../../monitor/historico/v13/README.md).
- [V11 P992](../historico/v11_p992/README.md): pareja anterior sin comandos WAV.
- [Firmware histórico](../historico/README.md) · [Catálogo](../apps_catalogo.json).
