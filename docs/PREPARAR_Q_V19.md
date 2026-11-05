# Preparación de la pareja Scope V19

## Revisión de transacción · 28/10/2026

La actualización verifica primero el respaldo pareado; pausa adquisición y
detiene relay/app antes de compilar. El rollback cubre ahora también fallos de
build y recheck, y reporta estado incierto si la restauración no se verifica.
Primera instalación comprueba Q vacío. La verificación de una pareja ya exacta
no compila. Ver [correcciones y pruebas](CORRECCIONES_REVISION_V19_20261028.md).

## Estado actual · 27/10/2026

`arduino/v19` es una pareja independiente derivada de la lógica de V18. El
nombre de app, ruta remota y contenedor relay ya son V19; las fuentes conservan
su propia copia y manifiesto SHA256. Algunos comentarios/documentación ahora
difieren, sin cambios funcionales respecto de la compilación registrada.

La pareja V19 fue instalada en `/home/arduino/ArduinoApps/scope-v19` y usa el
relay `serialmonitor-usb-stream-v19`. El recibo V19 contiene sus fuentes,
firmware, relay y evidencia propios; la aceptación V18 no se reutilizó. V18 y
V19 no deben ejecutarse a la vez porque comparten ADC/SPI/READY.

«Preparar Q» completó la primera instalación, verificó hashes/entorno y sostuvo
10,03 s de adquisición: 313.344 muestras, sin pérdidas ni errores fatales;
confirmó salida apagada y restauración. El smoke visible de GUI dibujó FFT
16.384 en ADC8/1,860 MS/s con 744 Paint events, cero errores, sin activar A0;
cerró liberando el receptor. Evidencias en
`diagnosticos/resultados_v19/prepare_q_20261027/`. La aceptación de campo sólo
cubre ese perfil y recorrido; los otros bits/tasas/modos, RADIO/A0, WAV y la
respuesta analógica siguen pendientes de calificación.

La compilación de referencia está en
`diagnosticos/resultados_v19/probes/routerbridge_include_removed/`; conserva los
hashes de firmware y relay de V18 y reporta 258.228/262.144 bytes de RAM. La
prueba de RAM más reciente, en
`diagnosticos/resultados_v19/probes/serial3_removed_variant/`, usa una copia
temporal de la variante UNO Q con USART1 y LPUART1, sin USART3. Compiló y reportó
256.036 bytes (97%), 6.108 libres; relay sin cambios. No se instaló. El override
ya es reproducible; estos artefactos aún requieren aceptación física.

El inventario read-only del Q antes de importar V19 encontró V17 y V18
sin inicializar, sus relays detenidos, V19 ausente y ningún componente activo.
Hay cuatro contenedores de relay V18 `*-saved-*`, todos respaldos detenidos.
Volver a consultar el inventario antes de cualquier transición porque el estado
del Q puede cambiar.

### Revisión de RAM y dependencias

Arduino reportó 258.228/262.144 bytes de RAM estática (98%), con 3.916 bytes
libres y advertencia de poca memoria. El mapa ELF separa 213.400 bytes de
`.bss`; predominan almacenamiento de adquisición (≈163.936 bytes), memoria
compartida WAV/DAC (≈28.800 bytes) y dos pilas Zephyr de 4.096 bytes cada una:
productor ADC/DMA y consumidor que valida/envía por SPI.
El mapa y el resumen del compilador tienen alcances distintos: su diferencia no
se debe contar automáticamente como RAM disponible.

No se redujeron buffers, que sostienen las tasas y funciones existentes. El
candidato diagnóstico de pilas ya compila; falta capturar sus valores con una
carga representativa antes de ensayar reducciones. `Arduino_RouterBridge` debe
permanecer en las dependencias porque el core UNO Q la requiere para proporcionar
`Serial`; el transporte de muestras del firmware usa SPI. Quitar sólo el include
explícito compila, pero deja exactamente el mismo BIN y consumo de RAM. Quitar la
dependencia sí hace fallar la compilación.

La prueba de un solo UART falló al compilar porque RouterBridge necesita
LPUART1/Serial2. La prueba que conserva USART1 (Serial1) y LPUART1 (Serial2), y
omite USART3 (Serial3), compila y el ELF ya no contiene Serial3; recupera 2.192
bytes de RAM estática. Se hizo con una copia temporal de la variante, sin editar
la configuración compartida instalada. Se puede reproducir con
`python tools/unoq.py compile-pair --version v19 --artifacts RUTA --omit-serial3`.
El manifiesto registra el override y el hash de la herramienta de build. El
build normal mantiene la variante común; este candidato aún requiere pruebas
físicas y actualización de la identidad/recibo antes de poder desplegarse.

El core local exporta `CONFIG_THREAD_STACK_INFO=y`, pero `k_thread_stack_space_get()`
no tiene implementación enlazable desde la app cargable; un primer build que
intentó usar la API falló en el link. El método diagnóstico actual marca con
`0xA5` las dos pilas inmediatamente antes de crear sus hilos y cada 250 ms mide
el prefijo que permanece intacto. Reporta el mínimo observado en el tipo SCP1
21, manteniendo el tipo 20 y el protocolo normal sin cambios.

El build estándar se reproduce con
`python tools/unoq.py compile-pair --version v19 --artifacts RUTA --stack-diagnostic`.
Modifica sólo el sketch del stage y compila con la variante UNO Q normal, sin
instalar nada. En la medición 2026-10-27 usó 258.516 bytes de RAM (3.628 libres)
y advirtió memoria baja. La variante optimizada se compila con
`--stack-diagnostic --omit-serial3`; ese build quedó en 256.324 bytes (5.820
libres), 288 bytes sobre Serial3-off sin instrumentación. Ambos producen SCP1
tipo 21. El lector V19 reconoce `producer_stack_free_bytes` y
`output_stack_free_bytes`. Capturarlas desde una conexión exclusiva al flujo del
Q (sin otra instancia receptora) con:

```sh
python tools/read_stack_diag_v19.py --serial NUMERO_ADB --duration 120 \
  --output diagnosticos/resultados_v19/stack_usage_8bit_1860.json
```

El lector selecciona el perfil nativo solicitado (por defecto 8 bits/1,860 MS/s)
y restaura la configuración ADC original al terminar, incluso al interrumpir la
captura si el flujo sigue disponible. Requiere ser el único receptor conectado;
no instala firmware. Registra el mínimo libre observado de cada hilo y un
resumen por segundo. Falta validar físicamente esos valores bajo carga; no
reducir los 4 KiB de ninguna pila antes de esa aceptación. La captura escribe
informe incluso si falla, restaura el perfil ADC original y retorna error si
hubo fallo de flujo o no se pudo restaurar.

## Diagnóstico previo a la instalación (2026-10-27)

Las notas siguientes documentan pruebas de compilación y medición privadas
anteriores a la instalación. Las variantes de diagnóstico USART3-off y
stack-diagnostic continúan sin instalar ni promover.

Inventario previo: ninguna app/relay estaba activa; V19 aún no estaba importada.
Los cuatro relays guardados de V18 siguen detenidos. El Q conserva un binario en
el caché de `scope-v17`, pero no hay binario compilado en el caché de `scope-v18`.
Por eso no se debe arrancar una app diagnóstica hasta fijar una restauración
física comprobable. Además, `arduino-app-cli app start` prepara la app y vuelve a
compilar/cargar el sketch; no se puede asumir que iniciará el BIN local especial.
Una medición posterior debe usar una app temporal de nombre/ruta propios y
verificar el hash del firmware cargado, sin sustituir Scope V17/V18 ni cruzar
sus relays.

Cada pareja se identifica por la misma versión en tres componentes: app de
App Lab, contenedor principal `scope-vXX-main-1` y relay
`serialmonitor-usb-stream-vXX` (V17 usa el nombre histórico sin sufijo). Para
operación normal, los tres deben corresponder a la misma versión y sólo una
pareja puede estar activa. Los contenedores `*-saved-*` son respaldos detenidos,
no relays activos. Consultar el estado sin modificar el Q con:

```sh
python tools/unoq.py inventory --version v19
```

El informe separa `active_components` (apps o relays encendidos) de
`coherent_active_pair_versions` (versiones con app y relay encendidos). El
campo `exactly_one_coherent_pair` sólo es verdadero si hay exactamente una
pareja completa activa y ningún componente suelto de otra versión.

## Alcance y siguientes verificaciones

La instalación inicial está hecha. Antes de extender el alcance de la aceptación,
completar y guardar evidencia independiente de:

1. Compilación de la pareja V19 y hashes del firmware y relay resultantes.
2. Revisión de los identificadores, puertos, app path, relay y compatibilidad SCP1.
3. Validación de adquisición en más perfiles/tasas, RADIO/A0, WAV, restauración y recuperación
   continua. Separar integridad, holgura, respuesta analógica y comportamiento
   visible del monitor.
4. Aceptación manual de los paneles y de la respuesta analógica; mantener tasas
   fuera de la evidencia como disponibles pero no calificadas físicamente.

No usar `tools/unoq.py deploy` ni `create` con `--version v19`: la herramienta
no administra la pareja aceptada. «Preparar Q» es la ruta de verificación y
actualización: exige recibo, respaldo y rollback. El método directo
`Board.deploy()` permanece bloqueado. V18 continúa administrándose por su
preparador propio.

[README de firmware V19](../arduino/v19/README.md) ·
[Estado de versiones y respaldos](VERSIONES.md).
