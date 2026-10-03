# V8: UNO Q directo por USB

Primer recorrido completo del **paso uno** del
[Plan de trabajo](../../../Plan%20de%20trabajo.md): misma adquisición y funciones
del monitor V7, utilizando solamente el UNO Q para transmitir al PC.

```text
ADC + timestamps DMA → SPI DMA/READY → Linux Q → USB/ADB → Python V8
```

El puerto USB serial del Q (`ttyGS0`) ya está asignado al servicio
`arduino-router-serial`. Se usa el ADB existente sobre USB, con un túnel TCP
local; no se modifican gadget USB, Arduino Router, consola ni recuperación.
El relay escucha solamente en `127.0.0.1:8765` del Q, sin exponerlo por Wi-Fi.

Probado en el PC a 31,25 kHz: **3.747.628 pares en dos minutos sin errores**,
grabación CSV de 293.163 filas sin huecos y reconexión sin reiniciar el Q.
La [validación](../../../diagnosticos/USB_Q_V8.md) conserva los resultados y límites.

## Inicio

Requiere la aplicación experimental `Scope ADC SPI V6` ya importada en el Q,
las dependencias Python de `requirements.txt` y ADB (incluido en las herramientas
Arduino del Q en macOS, o disponible en PATH/`UNOQ_ADB`).

Desde la raíz del proyecto:

```sh
# Primera vez o si cambió el código C del relay:
python3 tools/usb_stream.py start --firmware v6_adc --build-native

# Inicios posteriores; reinicia la adquisición y arranca el relay:
python3 tools/usb_stream.py start --firmware v6_adc

# Abrir el nuevo monitor:
python monitor/historico/v8/app.py
```

Usar **uno** de los dos comandos `start`, según corresponda. Después elegir
el UNO Q en el selector y pulsar **Conectar**. La adquisición está fija en
14 bits y 31,25 kHz. El indicador de enlace dice USB, sin baudios UART.
V6/V7 y sus firmwares R4 se conservan como alternativas separadas.

El relay se ejecuta en su propio contenedor y reutiliza el firmware ADC
validado; aún no está empaquetado dentro de la app App Lab. La compilación
C usa un contenedor temporal y se conserva por hash en el Q. No instala GCC
en el sistema del Q. Después de reiniciar la placa hay que repetir `start`.

## Funcionamiento

- V8 contiene su propia implementación del gráfico, escalas, estilos, trigger,
  mediciones, demo y CSV; no importa código de V7. Comparte con los diagnósticos
  los módulos de protocolo de `transport/`.
- Guarda capturas en `capturas/experimental_v8/`.
- Conserva los registros ADC de 8 bytes y sus timestamps, encapsulados en
  SCP1 tipo 3. El PC verifica CRC, secuencia, ACK, configuración, rango ADC,
  continuidad temporal e índices **antes** de entregar muestras al gráfico.
- Ante corrupción, pérdida, error MCU o cierre del flujo, interrumpe la
  sesión y muestra el error. No intenta ocultarlo resincronizando.
- El relay sigue consumiendo SPI aunque no haya un monitor conectado.
  **Desconectar** detiene la sesión del PC, no la adquisición del MCU.
- Sólo un cliente puede consumir el relay. Cerrar el verificador de consola
  antes de conectar el monitor. Un segundo cliente es rechazado.
- Si el PC deja de consumir y se llena el socket, se cierra esa sesión;
  el relay sigue atendiendo al ADC. Una escritura parcial termina la sesión,
  nunca se continúa con otra trama detrás de un fragmento.
- Cada conexión crea un puerto local ADB asignado automáticamente y al cerrar
  elimina solamente ese túnel. No usa `forward --remove-all`.

## Diagnósticos y parada

```sh
python3 tools/usb_stream.py status --firmware v6_adc
python3 tools/usb_stream.py logs --firmware v6_adc
python3 diagnosticos/verificar_usb_q.py --serial 1060031107 --seconds 120
python diagnosticos/verificar_monitor_v8.py  # Qt offscreen, CSV temporal y reconexión
python3 tools/usb_stream.py stop --firmware v6_adc
```

Detener el relay antes de ejecutar los verificadores SPI aislados o cambiar
el firmware. El relay utiliza exclusivamente SPI y READY; no ejecutar otro
consumidor sobre los mismos dispositivos. `stop` sólo elimina su contenedor;
el siguiente `start` reinicia el MCU para limpiar los contadores de adquisición.

## Próximos pasos del plan

Esta etapa mantiene fijos adquisición y generador. El túnel es dúplex, pero
ya se probó una [consulta PC → MCU con ACK](../../../docs/CONTROL_TRANSPORTE.md)
desde el verificador. Los cambios de configuración siguen pendientes. Luego vendrán
selección UART/SPI (paso dos),
configuración de adquisición (paso tres) y generador (paso cuatro).

[Resultados y límites de validación](../../../diagnosticos/USB_Q_V8.md).

## Validación de la consolidación

El 2 de octubre de 2026 se probó V8 independiente con el Q: **465.002 pares**,
**270.196 filas CSV sin huecos**, sin errores y con reconexión correcta.
[Resultado de la prueba](../../../diagnosticos/resultados_usb/20261002_093201_811341_monitor.json).
También se comprobó la ventana, demo y dibujo bloqueando las importaciones de V7.
Las 73 pruebas automatizadas del proyecto pasaron.
