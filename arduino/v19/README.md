# Pareja del Q para Arduscopio Q V19

Esta carpeta crea una identidad de despliegue independiente para V19, derivada
de la lógica de `arduino/v18`, salvo los metadatos de identidad `Scope V19`, la
ruta `scope-v19` y el nombre del relay. Sus fuentes tienen manifiesto SHA256;
comentarios y documentación pueden diferir sin cambiar el firmware. No modifica
la pareja V18.

- App: `Scope V19`, `/home/arduino/ArduinoApps/scope-v19`.
- Fuentes: `arduino/v19/oscilloscope` y `arduino/v19/relay`.
- Relay: `serialmonitor-usb-stream-v19`.
- Protocolo heredado: SCP1 V4, TCP 8766.
- Estado: pareja normal V19 instalada el 27/10/2026; hashes y recuperación
  inicial de 10,03 s verificados. La calificación de todos los modos/tasas y
  la medición de margen de memoria siguen pendientes.

## Dependencias

El firmware se compila con Arduino Core `arduino:zephyr` 1.0.0 y las versiones
fijadas en `oscilloscope/sketch/sketch.yaml`. `Arduino_RouterBridge` es requerida
por el core UNO Q para proporcionar `Serial`; el flujo de muestras del firmware
usa SPI hacia el relay. Se conservan las demás bibliotecas declaradas para
reproducir el entorno de compilación del core. No quitarlas ni actualizar sus
versiones sin recompilar la pareja.

La app instalada en App Lab es el lanzador de
`oscilloscope/python/main.py`, que usa `arduino.app_utils.App`. El monitor de
escritorio es independiente: requiere Python 3.13, PySide6 y las dependencias
de `monitor/v19/requirements.txt`.

## Fuentes, compilación e instalación

- Firmware STM32 y app Linux: `arduino/v19/oscilloscope/`. Incluye `sketch/`
  (firmware), `python/` (app de App Lab) y `app.yaml`.
- Relay Linux: `arduino/v19/relay/` (fuentes C y headers). Su binario se
  instala como `/work/unoq_stream` dentro del contenedor Docker.
- Configuración que empareja nombres y destinos: `arduino/v19/unoq.json`.

`python tools/unoq.py compile --version v19` valida Python y compila únicamente
el firmware del STM32 en un directorio temporal del Q. Para producir juntos
los dos binarios de V19, usar:

```sh
python tools/unoq.py compile-pair --version v19 --artifacts diagnosticos/builds_v19
```

El comando compila firmware STM32 y relay ARM64, copia BIN/ELF/ejecutable al
directorio indicado y escribe `build-v19-pair.json` con hashes de fuentes y
artefactos. **No instala ni activa** ninguno. Requiere Q conectado y todas sus
apps y contenedores detenidos; aborta si detecta actividad. El inventario se
consulta con `python tools/unoq.py inventory --version v19`.

El comando de compilación genera artefactos, no una aceptación. La instalación
inicial del firmware, app y relay se ejecuta desde `monitor/v19/q_support/`
mediante el recibo V19; las actualizaciones verificadas pasan por
`monitor/v19/q_support/prepare.py`. El relay no se carga con `arduino-cli`: se
construye como ejecutable Linux ARM64 y se monta en el contenedor nombrado
`serialmonitor-usb-stream-v19`. No reutilizar el relay V18.

La prueba de memoria más reciente está en
`diagnosticos/resultados_v19/probes/serial3_removed_variant/`. Una copia
temporal de la variante UNO Q conservó USART1 (UART del monitor) y LPUART1
(RouterBridge/Serial2), y excluyó USART3/Serial3. El firmware bajó de 258.228 a
256.036 bytes de RAM estática: recupera 2.192 bytes y deja 6.108. `Serial3` no
aparece en el ELF; `Serial1` y `Serial2` siguen presentes. El relay no cambió.
El compilador aún advierte poca memoria y la prueba sigue siendo candidata: no
se instaló ni se validó físicamente.

Para reproducir la compilación experimental de la pareja, usar
`python tools/unoq.py compile-pair --version v19 --artifacts RUTA --omit-serial3`.
El flag modifica sólo una copia temporal de la variante dentro del directorio
de build y registra el override en `build-v19-pair.json`. La compilación normal
no usa este ajuste. La pareja con el flag no forma parte del proceso de
despliegue/aceptación y no debe instalarse antes de las pruebas físicas y de
actualizar la identidad/configuración aceptada.

La prueba anterior, en `probes/routerbridge_include_removed/`, mostró que quitar
el include explícito de RouterBridge no ahorra nada; quitar la dependencia sí
rompe la compilación del core. Una variante con solo USART1 tampoco compila,
porque RouterBridge necesita LPUART1/Serial2. Por eso se conserva Serial2.

El mapa ELF muestra unos 213.400 bytes en `.bss`: aproximadamente 163.936 bytes
para almacenamiento de adquisición, 28.800 para el área compartida WAV/DAC y
dos pilas Zephyr de 4.096 bytes cada una (productor ADC/DMA y consumidor SPI).
No reducir buffers que sostienen perfiles existentes sin medirlos. El core tiene
`CONFIG_THREAD_STACK_INFO=y`, pero `CONFIG_INIT_STACKS` está apagado, así que
la API `k_thread_stack_space_get()` no se enlaza en el firmware cargable. El
build diagnóstico alternativo rellena ambas pilas con `0xA5` antes de crear los
hilos y mide cada 250 ms el prefijo intacto, publicándolo como trama SCP1 tipo
21. Se compila con:

```sh
python tools/unoq.py compile-pair --version v19 --artifacts RUTA --stack-diagnostic
```

El build Serial3-off compiló con 256.324 bytes de RAM usados y 5.820 libres,
288 bytes sobre esa variante sin instrumentación. Para coincidir con la variante
que App Lab compila al iniciar, se generó además el build estándar: 258.516 bytes
usados y 3.628 libres, con advertencia de memoria baja. Ambos son artefactos
privados, no se instalaron, y la lectura de pila aún necesita validación física
bajo carga. Retirar la dependencia RouterBridge hizo fallar la compilación;
quitar sólo el include explícito compila, pero no cambia el BIN ni libera RAM.
Se dejó fuera ese include redundante. No se recortaron buffers ni pilas, y no se
cargó firmware al Q.

En la variante de producción actual cada UART genérica reserva 2.156 bytes.
USART3/Serial3 se instancia por la lista global de la variante, aunque el sketch
no lo usa. La prueba ahorra 2.192 bytes al omitirlo sólo en la configuración de
compilación del candidato. El comando normal de compilación aún selecciona la
variante común; el flag experimental reproduce el override y registra su
configuración, pero todavía se requieren cambios de identidad y aceptación
antes de promoverla.

Para distinguir estados, consultar el inventario: `absent` significa que no
está instalado; `stopped` significa que existe pero no está corriendo;
`running` significa activo. Una pareja utilizable requiere `Scope V19`, su
contenedor principal `scope-v19-main-1` y el relay
`serialmonitor-usb-stream-v19` todos en `running`, con hashes de firmware y
relay que coincidan con el recibo. Los contenedores con sufijo `-saved-*` son
respaldos detenidos, no la pareja activa.

`manifest.json` registra SHA256 de cada archivo y su relación exacta con V18.
Las tasas y la evidencia de V18 sirven como antecedentes, no como aceptación
física de `Scope V19`.
