# V7 dual: Q siempre en control, salida SPI o UART

Aplicación experimental independiente del paso dos. Conserva ADC de 14 bits,
31.250 pares/s, timestamps de 32 µs y generación cuadrada fija en A2.
Usar el [monitor V9](../../../monitor/historico/v9/README.md) para elegir el Q de control y
el destino SPI/UART. V8 conserva su contrato SPI fijo y no admite este firmware.

## Separación de responsabilidades

- Adquisición: ADC y timestamps por DMA, con los mismos nodos y comprobaciones
  de V6 ADC. Publica nodos de 2.048 pares en una cola de cuatro posiciones.
- Salida: un consumidor es dueño del nodo completo. En SPI entrega fragmentos
  de hasta 53 pares; espera a que SPI termine físicamente antes de avanzar.
  En UART entrega cuatro paquetes DATA de 512 pares a 3 Mbps hacia R4 V5.
- Control: el bucle SPI atiende siempre PING y SET_TRANSPORT. En modo UART
  devuelve estados sin muestras; no espera a que UART entregue un nodo.
- Cambio: el consumidor aplica la solicitud al tomar el próximo nodo completo,
  después de terminar el anterior. APPLIED informa el índice de ese nodo.
  Las respuestas tienen su propia cola y prioridad sobre los datos SPI.

La adquisición nunca reutiliza un nodo prestado. El consumidor UART no toca
los buffers SPI DMA. El consumidor SPI conserva el nodo hasta la confirmación
de transmisión. Un fallo SPI detiene nuevos disparos ADC, sin avanzar el nodo
ni confirmar un cambio cuya frontera no se conoce.

## Preparación y prueba

Cerrar los monitores antes de probar. El R4 debe conservar el puente V5 y el
cableado UART anterior. El Q necesita USB durante toda la prueba.

```bash
python tools/unoq.py compile --version v7_dual
python tools/unoq.py backup --version v6_adc
python tools/unoq.py create --version v7_dual
python tools/usb_stream.py build --firmware v7_dual
python tools/usb_stream.py stop
python tools/unoq.py stop --version v6_adc
python tools/usb_stream.py start --firmware v7_dual
python diagnosticos/verificar_salida_q.py --r4-port /dev/cu.usbmodemE8F60AAABD882 --seconds 5
```

`create` es para la primera importación. Para actualizar una app ya importada,
usar `tools/unoq.py deploy --version v7_dual` con el relay detenido. No ejecutar
relays o benchmarks simultáneos sobre SPI.

El verificador abre el puerto R4 antes del cambio, recibe las tres etapas y
comprueba timestamps, rango ADC y los dos índices APPLIED. Envía PING durante
UART y después del retorno a SPI. Puede guardar el informe con `--output`.
El formato DATA por UART no lleva CRC, igual que V5.

Para volver a V8:

```bash
python tools/usb_stream.py stop
python tools/unoq.py stop --version v7_dual
python tools/usb_stream.py start --firmware v6_adc
python monitor/historico/v8/app.py
```

## Contratos

- [Cambio de transporte](../../../docs/PROTOCOLO_CAMBIO_TRANSPORTE.md).
- [Relay dual](../../../transport/unoq_dual_stream.c).
- [Sesión Python](../../../transport/unoq_dual.py).
- [Prueba física](../../../diagnosticos/verificar_salida_q.py).

SCP1 tipo 3 admite cantidad cero para estado sin muestras. En ese caso índice,
identificador de nodo y padding son cero; tasa, bits y período siguen presentes.
Tipos 3 y 5 comparten la secuencia global SPI. Los lectores verifican continuidad
de muestras SPI entre estados y respuestas; al volver desde UART, verifican la
primera muestra contra APPLIED. El verificador físico une ambos transportes
para comprobar continuidad también durante el tramo UART.

Los selectores están integrados en V9, con cambios en vivo y CSV continuo.
Bits, frecuencia y generador siguen fijos según el plan.

[Validación física: dos ciclos sin saltos y 81 pruebas aprobadas](../../../diagnosticos/SALIDA_DUAL_V7.md).
