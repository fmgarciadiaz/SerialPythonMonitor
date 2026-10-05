# Transporte · relay Linux y protocolos

[Proyecto](../README.md) · [Monitor](MONITOR_TECNICO.md) · [MCU](UNO_Q_TECNICO.md)

```mermaid
flowchart LR
 PC[Monitor Python V12] <-->|USB / ADB: TCP reenviado| RELAY[Relay nativo en Linux del UNO Q]
 RELAY <-->|SPI y READY: datos y control| MCU[MCU UNO Q: V11 P992]
 MCU -->|UART Serial1| R4[UNO R4: puente V5]
 R4 -->|USB serial: muestras| PC
 PC -.->|Selección SPI/UART, ADC y DAC| RELAY
```

En SPI, el relay recibe muestras del MCU y las transmite al monitor. En UART,
las muestras llegan por R4; el Q continúa conectado para controlar adquisición,
generador y destino. El relay admite un solo cliente PC: desconectar el monitor
antes de ejecutar diagnósticos que necesitan el mismo enlace.

El pequeño [main.py de App Lab](../arduino/v11_p992/oscilloscope/python/main.py)
mantiene viva la aplicación; el relay de datos es un proceso nativo separado.
[tools/usb_stream.py](../tools/usb_stream.py) administra su compilación y estado;
[tools/unoq.py](../tools/unoq.py) administra las apps y firmware.

## Pareja actual V12 / V11 P992

El relay del MPU está en `arduino/v11_p992/relay/unoq_config_stream.c`;
se compila para Linux ARM y corre en un contenedor independiente. No es
el sketch MCU ni el pequeño Python de App Lab. Valida CRC, secuencias y
estado de adquisición; transmite muestras y canaliza comandos ADC/DAC.
El PC usa el receptor propio de `monitor/v12/receiver/`.

SPI funciona a 32 MHz con SCP1 V3: 992 bytes por trama, 113 pares de
muestras por fragmento y 19 fragmentos por nodo de 2048 pares. TCP escucha
en 8766; USB/ADB reenvía esa conexión, sin depender de Wi-Fi. UART conserva
su formato DATA de 512 pares y su máximo de 31,25 kHz; la validación física
del puente R4 sigue pendiente para esta pareja.

La sección siguiente conserva detalles del formato UART y del contrato
anterior V2/512; no usar sus offsets CRC para las tramas SPI V3/992.

## Contrato binario

Cada paquete DATA tiene cabecera de siete bytes y `count` registros de ocho
bytes: timestamp uint32 y dos ADC uint16. Bajar resolución no estrecha el
registro. El receptor acumula lecturas parciales; un read USB no equivale a un
paquete. Índices y timestamps permiten comprobar continuidad y cambios de época.

Los comandos de transporte, adquisición y generador tienen identificadores y
respuestas ACCEPTED/APPLIED/REJECTED. El monitor refleja el estado aplicado y
espera la confirmación correspondiente antes de iniciar la medición de Bode.

[Selección de salida](CONTROL_TRANSPORTE.md) ·
[Contrato de cambio](PROTOCOLO_CAMBIO_TRANSPORTE.md) ·
[Adquisición configurable](CONFIGURACION_ADQUISICION.md) ·
[Relay actual](../arduino/v11_p992/relay/) · [Puente R4](../arduino/historico/v5/r4_bridge_v5/README.md)

## Operación

```sh
python3 tools/unoq.py status --version v11_p992
python3 tools/usb_stream.py status --firmware v11_p992
python3 tools/usb_stream.py logs --firmware v11_p992
python3 tools/usb_stream.py start --firmware v11_p992
```

Para actualizar, cerrar el monitor y detener el relay antes de cargar firmware.
Usar la [guía V11 P992](../arduino/v11_p992/README.md) para compilar, importar
la app y desplegarla. No confundir la app de App Lab con el proceso relay.
