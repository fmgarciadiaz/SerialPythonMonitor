# Paso dos: canal de control y selección del transmisor

La pareja actual es V12 / V11 P992 con SCP1 V3/992; ver
[transporte actual](TRANSPORTE_TECNICO.md). El contrato y las capturas V2/512
de este documento se conservan como antecedentes; sus offsets CRC y
longitudes no se aplican a V3.

Este documento desglosa el paso dos del [Plan de trabajo](../Plan%20de%20trabajo.md).
El paso uno conserva su monitor V8 y su adquisición fija a 31,25 kHz / 14 bits.

## Subpaso actual: consulta con respuesta del MCU

El PC envía una trama PING SCP1/v2 de 512 bytes usando el túnel USB existente.
El relay Linux reconstruye la trama aunque TCP la entregue fragmentada,
comprueba su formato/CRC/patrón y la envía al MCU en la siguiente transacción SPI.
El MCU devuelve su identificador en `last_ping` del siguiente bloque DATA.
Python acepta la consulta sólo al recibir ese ACK en una trama íntegra.
La misma respuesta contiene frecuencia, resolución, canales, período,
índice de muestra y contadores de adquisición del MCU.

- Identificadores Linux: bit alto cero.
- Identificadores PC: `0x80000000` a `0xfffffffe`, sin reutilizarlos dentro
  de una vuelta del contador. `0xffffffff` se reserva para el estado de arranque.
- Timeout de una consulta PC: 2 s.
- Comando incompleto durante más de 1 s o comando inválido: cierre de la sesión
  del PC; la adquisición continúa. No se transmite ese comando al MCU.
- El relay comprueba el ACK contra el identificador efectivamente transmitido.
- Python comprueba explícitamente el identificador solicitado y mantiene
  las verificaciones de datos, CRC, secuencias y timestamps durante la consulta.

Se reutiliza PING; esto no agrega todavía un opcode GET_STATUS/SET_TRANSPORT
al firmware. Tampoco afirma que UART esté activo o disponible: consulta los
campos que el MCU ya reporta. No se modifican ADC, DMA, timers ni generador.

```sh
python3 tools/usb_stream.py start --build-native  # instalar relay actualizado
python3 diagnosticos/verificar_control_q.py --serial 1060031107 --requests 1000
```

El verificador y V8 usan la misma sesión exclusiva; cerrar uno antes de abrir
otro. V8 sigue usando su lector normal, con comprobación de ACK consecutivo.
El lector de consultas empareja ACK con sus solicitudes porque sus identificadores
se intercalan con los PING generados por Linux.

[Resultados físicos y límites](../diagnosticos/CONTROL_Q_V8.md).

## Selección de salida: V7 dual experimental

Se integró el [contrato SET_TRANSPORT](PROTOCOLO_CAMBIO_TRANSPORTE.md) en una
[aplicación independiente V7 dual](../arduino/historico/v7_dual/README.md), relay y sesión
Python de diagnóstico. Q conserva SPI para control mientras envía muestras
UART al R4. El cambio se confirma con APPLIED al comenzar un nodo completo.

La aplicación V6 ADC y el monitor V8 siguen disponibles con su contrato fijo.
El firmware dual necesita su relay y lector; no es compatible con V8.

## Selectores implementados: monitor V9

[V9](../monitor/historico/v9/README.md) separa CONTROL Q, DESTINO SPI/UART y PUERTO R4.
El Q permanece conectado; Aplicar destino espera APPLIED y conserva gráfico
y CSV. El receptor combina ambos caminos en una secuencia de índices y
timestamps, incluyendo una cola UART que puede llegar después de la respuesta
SPI. Al reconectar empieza una captura nueva desde una frontera confirmada y
descarta señales Qt de la sesión anterior.

[Validación de la interfaz y CSV](../diagnosticos/MONITOR_V9.md).

El siguiente paso es configurar bits y frecuencia según el transmisor
(paso tres). El generador corresponde al paso cuatro.

[Validación física del firmware dual](../diagnosticos/SALIDA_DUAL_V7.md).
