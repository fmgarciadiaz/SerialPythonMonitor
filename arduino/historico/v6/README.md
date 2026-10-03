# V6: primer paso hacia el enlace directo del UNO Q

Esta versión prueba **STM32 → SPI3 interno → Linux del UNO Q**, con comandos
de vuelta por el mismo enlace. Usa datos sintéticos; todavía no transporta el
ADC ni conecta el monitor del PC por USB. El conjunto Q V5 + R4 V5 + monitor
V7 sigue siendo la referencia para adquirir señales.

La aplicación independiente se llama **Scope SPI Benchmark V6**. El número
V6 aquí corresponde al firmware experimental, no al monitor Python V6.

## Qué prueba

Linux es el maestro (`/dev/spidev0.0`) y el STM32 es el periférico SPI3.
Cada intercambio full-duplex de 512 bytes contiene una trama DATA hacia
Linux y una trama PING hacia el STM32. La siguiente DATA confirma el PING
anterior. Se comprueban secuencia, todos los bytes del patrón, CRC32 y
contadores del driver. El último intercambio adicional confirma el último
PING del intervalo medido.

El core instalado es Arduino Zephyr 1.0.0: SPI peripheral e interrupciones
habilitados, **DMA SPI deshabilitado**. La implementación usa
`device_init()` y `spi_transceive()` síncrono, con buffers estáticos de vida
útil suficiente y modo 0, 8 bits, MSB primero. En este driver el retorno
correcto es el número de bytes recibidos: 512. La adquisición ADC, sus
temporizadores y sus canales DMA no forman parte del benchmark.

`Arduino_RouterBridge` permanece como dependencia obligatoria del core;
los bloques y PING del benchmark viajan por SPI, sin llamadas RPC/Bridge.

## Protocolo binario

Todos los enteros multibyte se codifican little-endian, sin padding C++.

| Offset | Bytes | Contenido |
|---:|---:|---|
| 0 | 4 | Magic `SCP1` |
| 4 | 2 | Versión: 2 (instrumentada) |
| 6 | 2 | Tipo: DATA=1, PING=2 |
| 8 | 4 | Secuencia uint32, con wrap |
| 12 | 4 | Longitud del payload: 492 |
| 16 | 492 | Payload |
| 508 | 4 | CRC32 de los primeros 508 bytes |

CRC32/ISO-HDLC: polinomio reflejado `0xEDB88320`, inicial y XOR final
`0xFFFFFFFF`, compatible con `zlib.crc32`. Vector `123456789`: `0xCBF43926`.

PING contiene 492 bytes deterministas. En DATA, los primeros 32 bytes del
payload contienen ocho campos de 32 bits: último PING válido (inicialmente
`0xFFFFFFFF`), errores SPI, comandos inválidos, transferencias cortas y último
retorno del driver, último error negativo del driver (ambos con signo), tiempo
de preparación y tiempo de verificación del MCU en microsegundos. El error
negativo se conserva hasta otro error o reinicio; los tiempos describen el
trabajo de la iteración anterior y pueden incluir interrupciones.
Los otros **460 bytes** contienen
el patrón determinista. Su definición compartida está en
[benchmark_protocol.h](spi_benchmark/sketch/benchmark_protocol.h) y
[verificar_spi.py](../../../diagnosticos/verificar_spi.py); una prueba compila
el C++ real y compara sus bytes con Python.

La versión de protocolo 1 del primer ensayo tenía 20 bytes de estado y 472
de patrón. Las versiones no son compatibles: actualizar firmware y verificadores
juntos. Los registros anteriores se conservan y señalan el formato utilizado.

## Ejecutar desde la computadora

El UNO Q debe estar conectado por USB/ADB. Antes de cambiar el firmware,
respaldar la versión activa y detener su aplicación. Estas instrucciones
suponen que se está usando V5:

```sh
python3 tools/unoq.py compile --version v6
python3 tools/unoq.py backup --version v5
python3 tools/unoq.py stop --version v5
python3 tools/unoq.py create --version v6  # sólo la primera instalación
python3 tools/unoq.py start --version v6
# Esperar a que start termine correctamente antes de medir.
python3 tools/spi_benchmark.py --hz 1000000 --seconds 5 --gap-us 1000
python3 tools/spi_benchmark.py --hz 3000000 --seconds 60 --gap-us 250
```

Para comparar el receptor Python con el receptor C independiente:

```sh
# Compilar una vez por revisión del C; no cambia el firmware activo.
python3 tools/spi_benchmark.py --build-native
python3 tools/spi_benchmark.py --implementation python --hz 3000000 --seconds 10 --gap-us 250
python3 tools/spi_benchmark.py --implementation c --hz 3000000 --seconds 10 --gap-us 250
```

La compilación nativa descarga la imagen Debian indicada por digest en el
ejecutor e instala GCC/libc-dev dentro de un contenedor temporal. No instala
paquetes en el sistema base del UNO Q. Guarda el binario ARM64 en `/tmp`, en
una carpeta identificada por el SHA256 del fuente; repetir tras reiniciar
la placa o modificar el C. Ambos receptores se ejecutan en la misma imagen
Arduino, sin red durante la medición y sin compilaciones simultáneas.

Los nuevos informes separan `timing_s.prepare`, `exchange`, `check` y `gap`.
`ioctl` es un subconjunto de `exchange`, no se suma otra vez; incluye la
espera dentro del kernel y no mide exclusivamente los pulsos SCK. Se informa
también el máximo de una llamada ioctl y los tiempos del MCU. Un receptor C
más rápido puede cambiar el tiempo disponible para rearmar el periférico:
comparar integridad además de caudal. `--replay` del binario C valida tramas
de stdin sin hardware y se usa para las pruebas de equivalencia con Python.

Para actualizar una V6 ya instalada, usar `deploy --version v6` en lugar de
`create`: compila, respalda, copia e inicia. No ejecutar dos benchmarks ni
otra aplicación que use SPI3 durante la medición.

El ejecutor copia temporalmente el verificador a Linux y usa la imagen ya
instalada `ghcr.io/arduino/app-bricks/python-apps-base:0.12.0`. El contenedor
corre como root para acceder al dispositivo, sin red ni capabilities, con
filesystem de sólo lectura y acceso al único dispositivo `spidev0.0`.
No cambia sus permisos globales ni la configuración USB. El verificador
usa sólo la biblioteca estándar de Python y `SPI_IOC_MESSAGE(1)`.

Los resultados quedan en `diagnosticos/resultados_spi/`. Un código de salida
**1** también puede significar que los datos son íntegros pero el caudal no
alcanza el objetivo: consultar `integrity_pass` y `throughput_pass` por separado.
El reloj solicitado y leído del driver no sustituye una medición eléctrica
del reloj efectivo.

Para recuperar la adquisición anterior:

```sh
python3 tools/unoq.py stop --version v6
python3 tools/unoq.py start --version v5
```

Esto carga el firmware Q V5; el R4 debe conservar su V5 y el monitor usar V7.

## Criterio para avanzar

El caudal se calcula con bytes de patrón realmente verificados (460 por DATA en v2)
y tiempo de pared, incluyendo generación, comprobaciones, ioctl y pausas.
El objetivo inicial es **750.000 B/s**, tres veces los aproximadamente
250.000 B/s actuales (31.250 pares/s × 8 bytes por registro). Los contadores
MCU se informan tanto al inicio/final como por diferencia: errores históricos
de una prueba anterior no se atribuyen a la siguiente.

Sólo avanzar al ADC después de lograr margen de caudal y una prueba prolongada
sin errores. Después vienen el transporte USB y los comandos de configuración.
Este PING verifica el camino bidireccional; aún no modifica bits, frecuencia ni
generador de ondas. Resultados y limitaciones en
[Validación V6](../../../diagnosticos/VALIDACION_V6.md).
La [comparación instrumentada Python/C](../../../diagnosticos/PERFIL_SPI_V6.md)
detalla los tiempos, la optimización del patrón y el problema de rearmado.
El [barrido a 3,8 MHz](../../../diagnosticos/BARRIDO_SPI_38MHZ.md) pasó dos minutos
sin errores con C y pausa de 250 µs, a unos 294 kB/s. Aún no alcanza el margen
de aceptación; 4 MHz sigue fallando en estas condiciones.

La [variante posterior por registros](../../../diagnosticos/POLLING_SPI_V6.md)
superó 4 MHz y sostuvo 6 MHz durante dos minutos sin errores, a unos
402 kB/s útiles. Sigue siendo un ensayo sintético y aún no alcanza el umbral.

La [variante posterior con DMA TX/RX](../../../diagnosticos/DMA_SPI_V6.md)
superó el umbral: 813.510 B/s durante dos minutos sin errores a 20 MHz y
pausa solicitada de 150 µs. La integración ADC/USB continúa pendiente.
