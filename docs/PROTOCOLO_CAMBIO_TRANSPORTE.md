# Contrato experimental para seleccionar SPI/UART

Subpaso del paso dos del [plan](../Plan%20de%20trabajo.md).
Integrado en la aplicación experimental [V7 dual](../arduino/historico/v7_dual/README.md),
su relay y una sesión Python de diagnóstico. El monitor V8 y V6 ADC conservan
el contrato anterior. No enviar estas tramas al relay V6: sólo admite PING.
El [monitor V9](../monitor/historico/v9/README.md) integra los selectores de control y destino.

## Formato

Bloques SCP1/v2 de 512 bytes, enteros little-endian y CRC-32/ISO-HDLC sobre
bytes 0–507, guardado en 508–511. Se conservan magic, versión y longitud de
payload 492. Los nuevos tipos son 4 (SET_TRANSPORT) y 5 (TRANSPORT_STATUS).
Los bytes no utilizados deben ser cero; un CRC válido no basta para aceptarlos.

| Offset | SET_TRANSPORT (tipo 4) | TRANSPORT_STATUS (tipo 5) |
|---|---|---|
| 8 | Identificador PC | Secuencia de respuesta |
| 16 | Modo solicitado, uint8 | Identificador PC, uint32 |
| 20 | Cero | Modo solicitado, uint8 |
| 21 | Cero | Modo activo, uint8 |
| 22 | Cero | Fase, uint8 |
| 23 | Cero | Motivo, uint8 |
| 24 | Cero | Índice inicial del siguiente nodo, uint32 |

Modos: SPI=0, UART=1. Identificadores PC: `0x80000000` a `0xfffffffe`.
Fases: ACCEPTED=1, APPLIED=2, REJECTED=3.
Motivos: OK=0, UNSUPPORTED=1, BUSY=2, ID_CONFLICT=3, HARDWARE=4.

## Semántica

- ACCEPTED reserva la solicitud; no cambia el modo activo. Su índice es cero.
- APPLIED sólo se emite tras completar el cambio físico en un límite de nodo
  de 2.048 pares, después del último paquete completo del modo anterior.
  El índice identifica la primera muestra destinada al nuevo modo. Cero también
  es un índice válido al desbordar uint32; la fase distingue su significado.
- REJECTED informa el modo que sigue activo. Un fallo de hardware debe mantener
  la salida anterior; si eso no puede garantizarse, la integración debe detener
  adquisición y reportar el fallo, no inventar un modo confirmado.
- Sólo hay una solicitud pendiente. Otra recibe BUSY sin reemplazarla.
- Repetir la última solicitud devuelve su estado almacenado sin reaplicarla.
  Reutilizar ese identificador con otro modo recibe ID_CONFLICT.
- Se conserva sólo la última solicitud aceptada o rechazada fuera de BUSY y
  conflicto. El cliente debe usar identificadores nuevos y no reenviar comandos
  antiguos después de iniciar uno nuevo. No hay historial persistente tras reset.
- Solicitar el modo ya activo también se confirma en un límite de nodo, con
  índice explícito. El integrador puede evitar reconfigurar el periférico.
- Python valida CRC, padding, identificador, modo solicitado y coherencia entre
  fase, motivo y modo activo. ACCEPTED nunca equivale a APPLIED.

## Código y prueba

- [Contrato y máquina de estados C++](../transport/control_protocol.h), sin dependencias de Arduino.
- [Codificador y lector Python](../transport/unoq_switch.py).
- [Pruebas cruzadas](../tests/test_transport_switch.py): compilan C++ y le envían
  bytes generados por Python; Python valida las respuestas reales de ese binario.

Validación local del 2 de octubre de 2026: 77 pruebas del proyecto aprobadas.
Incluye SPI → UART → SPI en la máquina de estados, reintentos, ocupado,
identificador conflictivo, fallo de hardware simulado, límites de nodo,
wrap de índice, corrupción, padding y ACK incorrecto. **No es una prueba física
ni mide continuidad durante un cambio de periférico.**

## Separación implementada en V7 dual

El firmware V6 ADC espera el intercambio SPI dentro del mismo consumidor que
posee el nodo ADC. Al activar UART no basta con cambiar una llamada de envío:
SPI debe continuar atendiendo comandos y estado independientemente de las
muestras UART, sin retener nodos mientras espera al maestro.

V7 dual separa un consumidor de salida y el intercambio SPI permanente.
UART usa los paquetes DATA de V5 y espera a que termine el último byte antes
de considerar otro nodo. SPI conserva el nodo hasta completar cada intercambio.
El relay dual admite respuestas tipo 5 y estados tipo 3 sin muestras; verifica
una secuencia global y el índice de retorno confirmado por APPLIED.
La prueba física combina las muestras SPI y UART para verificar ambas fronteras.

V9 integra los selectores Q/R4 con confirmación y continuidad entre receptores. Resolución,
frecuencia y generador siguen fijos en esta etapa.

[Validación física: dos ciclos sin saltos y 81 pruebas aprobadas](../diagnosticos/SALIDA_DUAL_V7.md).
