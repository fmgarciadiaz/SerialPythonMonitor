# V9: Q de control y destino SPI / UART-R4

Implementa el **paso dos** del [plan de trabajo](../../../Plan%20de%20trabajo.md).
Conserva gráfico, trigger, mediciones, Demo y CSV de V8, con adquisición fija de
14 bits y 31.250 pares/s. El Q sigue conectado por USB durante toda la sesión.

## Uso

Requiere la app **Scope Output Select V7** y el relay dual en el Q, las
[dependencias Python](../../../requirements.txt) y ADB. El R4 debe tener el puente
V5 y el cableado UART Q → R4 anterior a 3 Mbps.

El Q ya quedó con la app dual y su relay funcionando después de la validación.
Para abrir el monitor desde la raíz:

```bash
python monitor/historico/v9/app.py
```

También está la configuración **Monitor V9 — Q de control / SPI-R4** en VS Code.

1. En **CONTROL Q**, elegir el UNO Q conectado por USB.
2. En **DESTINO**, elegir **SPI · UNO Q** o **UART · R4**.
3. Para UART, elegir el USB del R4 en **PUERTO R4**. El serial del Q se excluye
   de esta lista porque pertenece al servicio de control de la placa.
4. Pulsar **Conectar**. **Destino confirmado** muestra la salida aplicada por
   el MCU; elegir una opción en el combo por sí solo no cambia el hardware.
5. Para cambiar durante la captura, elegir destino/puerto y pulsar
   **Aplicar destino**. Se conservan la captura y la grabación CSV en curso.

La selección del Q se bloquea mientras está conectado. Para cambiar de Q,
desconectar primero. **Actualizar** busca los Q por USB/ADB y los puertos USB
candidatos del R4. No se elige automáticamente un R4 si hay varios puertos.
En SPI no hace falta conectar el R4.

## Iniciar después de apagar o reiniciar el Q

```bash
python3 tools/usb_stream.py start --firmware v7_dual
python monitor/historico/v9/app.py
```

Para la primera instalación/importación y compilación del relay, seguir la
[guía del firmware dual](../../../arduino/historico/v7_dual/README.md). Si el relay todavía
no está compilado, agregar `--build-native` al comando de inicio.
Para usar otro Q con estas herramientas, indicar su identificador:

```bash
UNOQ_SERIAL=IDENTIFICADOR_USB python3 tools/usb_stream.py start --firmware v7_dual
```

Si estaba funcionando V8, detener su relay y app antes de iniciar la dual:

```bash
python3 tools/usb_stream.py stop
python3 tools/unoq.py stop --version v6_adc
python3 tools/usb_stream.py start --firmware v7_dual
```

V8 sigue disponible con **Scope ADC SPI V6** y su relay fijo. V9 usa la app
dual; enviar SET_TRANSPORT al firmware V6 ADC no es compatible.

## Control, continuidad y errores

- Q → Linux → USB sigue atendiendo control y estado en ambas salidas.
  El receptor envía PING periódicos y exige su confirmación del MCU.
- El firmware cambia en un límite de nodo de 2.048 pares; ACCEPTED no basta.
  El receptor espera APPLIED e identifica la primera muestra del nuevo destino.
- El lector R4 funciona en paralelo para drenar USB sin frenar el control.
  Si su último fragmento llega después de APPLIED para SPI, el monitor lo
  completa antes de entregar las nuevas muestras SPI.
- UART no transmite índices: V9 los asigna a partir de la frontera confirmada
  y comprueba los timestamps reales contra la última muestra del Q.
- Al abrir R4 se esperan tres segundos porque abrir USB puede reiniciarlo.
  Durante un cambio en vivo, SPI continúa dibujando y grabando en ese intervalo.
  Para cambiar de un R4 a otro, Q vuelve temporalmente a SPI, completa el tramo
  anterior y prepara el nuevo puerto antes de activar UART.
- Cada conexión empieza una captura nueva desde una frontera SPI confirmada,
  incluso si la sesión anterior dejó UART activo. Después aplica el destino
  elegido. Las señales Qt de una sesión cerrada se descartan.
- Ante CRC incorrecto, hueco, timeout de control, error ADC o fallo del R4,
  se detiene la sesión y la grabación. No se ocultan huecos resincronizando.
- **Desconectar** cierra la sesión del PC; el Q conserva la adquisición y el
  último destino aplicado. La siguiente conexión vuelve a confirmarlo.

ADC, frecuencia y generador siguen fijos. La configuración real del ADC es el
paso tres; el panel del generador es el paso cuatro.

## CSV y validación

Las capturas se guardan en `capturas/experimental_v9/`, con el mismo formato
que V8 y límite de 30 segundos por grabación. Los timestamps e índices no se
reinician al cambiar de destino durante una sesión.

[Validación física de V9](../../../diagnosticos/MONITOR_V9.md): cambios en vivo,
CSV y reconexiones usando Qt. Para repetirla con los monitores cerrados:

```bash
python diagnosticos/verificar_monitor_v9.py --serial 1060031107 --r4-port /dev/cu.usbmodemE8F60AAABD882
```

El puerto R4 del ejemplo debe reemplazarse por el de la placa conectada.
DATA UART conserva el formato sin CRC de V5; la verificación de rango y
continuidad no detecta toda posible corrupción de amplitud.
