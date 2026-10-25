# Arquitectura V18

El STM32 del UNO Q adquiere A2/A3 y genera A0 con temporizadores y DMA.
Linux ejecuta Scope V18 y un relay nativo independiente; USB/ADB lleva muestras
y control al PC. [Presentación con imágenes de cada módulo](../README.md).

```mermaid
flowchart LR
 ADC[A2 / A3 ADC] --> MCU[STM32 · DMA y temporizadores]
 MCU <--> Relay[Relay Linux del Q]
 Relay <-->|USB / ADB| RX[Proceso receptor V18]
 RX --> DSP[DSP / RADIO / FILTER]
 DSP --> GUI[V(t) / FFT / Heatmap / Bode]
 DSP --> PCM[Cola PCM]
 WAV[WAV / Synth] --> PCM
 PCM --> RX
 MCU --> DAC[A0 DAC]
```

El receptor valida CRC, secuencia, época y continuidad. La GUI consume lotes
con presupuesto acotado; no se descartan muestras para esconder atrasos.
ADC8/1,818 MS/s transporta valores compactos entre procesos y reconstruye
la misma matriz en el host. Las confirmaciones de configuración preservan el
orden de la historia; el audio tiene canal de pedidos independiente.

`monitor/v18` contiene GUI, DSP, receptor, helpers y soporte de Preparar Q.
`arduino/v18` contiene la pareja de fuentes MCU/relay. El paquete aceptado del
preparador incluye binarios y hashes; sus operaciones usan un único propietario
del Q y respaldos bajo `respaldos/parejas/`. La conexión normal no programa.

[Uso y límites](GUIA_V18.md) · [Evidencia física](VALIDACION_V18.md).

## Lugares de ejecución y propiedad

| Parte | Dónde corre | Responsabilidad |
|---|---|---|
| GUI | PC, hilo Qt | Controles, historia visible, V(t), FFT, heatmap y Bode |
| Receptor | PC, proceso separado | Socket, protocolo, continuidad, configuración y créditos |
| DSP | PC, ejecutor separado | Conversión, FILTER, demodulación RADIO y resultados |
| Synth | PC, proceso de render | Estado de voces, controles y producción PCM |
| Relay | Linux del Q | Transferencias SPI, validación y puente TCP/ADB |
| App Python del Q | Linux del Q | Mantener la app App Lab que contiene el sketch |
| MCU | STM32U585, Arduino/Zephyr | Temporizadores, ADC/DAC, DMA y propiedad de los buffers |

El audio no crea un dispositivo USB Audio del sistema. WAV, Synth y RADIO
producen códigos para A0 a través del protocolo del instrumento.

## Entrada ADC y temporización

Los perfiles fijan resolución, cantidad de canales, período y geometría de nodo.
CH1 utiliza A2; dual adquiere A2/A3. Los timestamps e índices viajan asociados
al bloque y el receptor verifica que no se pierdan ni repitan muestras.
El perfil ADC8 CH1 de 88 ticks utiliza un reloj de timestamps de 160 MHz y
N3488. La tasa real es 160.000.000/88 = 1.818.181,818 S/s. Los contadores de
32 bits pueden envolver; decoder e historia conservan continuidad durante wrap.

DMA escribe la adquisición en memoria del MCU. El consumidor prepara tramas
cuando el nodo está disponible. La propiedad de una región no vuelve al
productor hasta completar la transferencia correspondiente; no se acepta
sobrescribir un bloque que SPI todavía está utilizando. Las interrupciones
actualizan estados de finalización; los cálculos de la GUI no fijan Fs.

ADC16 usa oversampling; no implica dieciséis bits de precisión analógica efectiva.
El rango nominal de las entradas y A0 es 0–3,3 V.

## SPI, relay y conexión con el host

El contrato lógico es SCP1 V4 de 992 bytes, con CRC, secuencia, época y tipo.
La pareja actual agrupa dos tramas lógicas en una transferencia SPI de 1984
bytes con geometría de 16 bits. Ambos lados validan cada mitad antes de
confirmar el bloque; una mitad parcial no se publica como una trama válida.

El relay es un proceso nativo independiente de la app Python de App Lab.
Mantiene un backlog TCP acotado y conserva el orden de los bytes, incluso si
un envío es parcial. El PC accede al puerto8766 mediante un túnel ADB que tiene
un único propietario. Los cambios de reloj/prioridad/CPU del relay pertenecen
al perfil; la verificación y restauración comprueban ese estado por separado.

## Receptor, lotes y barreras

El decoder comprueba encabezado, CRC, secuencia, geometría, rangos, contadores
y continuidad antes de entregar datos. Publica eventos en orden; no concatena
un segundo resultado de muestras que el receptor no consume.

Los lotes normales de RF están acotados a 40 ms de la tasa real. Un atraso no
se convierte en un único pickle gigantesco. El límite total pendiente sigue
siendo acotado y superar el presupuesto produce un error visible, no descarte
silencioso. ADC8 CH1 a1,818MS/s envía valores uint8 y metadatos entre procesos;
el padre reconstruye la misma matriz de valores, timestamps e índices.

Los ACK de configuración no adelantan muestras antiguas ni resultados DSP.
Cambiar perfil invalida resultados de una generación anterior. Los créditos
IPC y la propiedad de los lotes GUI son controles distintos; liberar uno no
implica descartar la historia del otro.

## DSP, RADIO, FILTER y presentación

RADIO sintoniza y demodula el canal RF, con salida de audio configurada por el
panel. FILTER tiene su propia entrada y no procesa con entrada OFF. Los modos
de análisis seleccionan fuentes sin quitar CH1 de FFT por reproducir RADIO.
El dial se ajusta a Fs; US extiende la selección y mapea frecuencia real/alias.

La GUI dibuja resultados e historia a su cadencia, no a Fs. Si la ventana no
está expuesta puede omitir dibujo, manteniendo adquisición y DSP. Las métricas
de timer no acreditan FPS visibles: los informes registran exposición y paints.

## Audio PCM y A0

RADIO alimenta primero el audio listo y luego observa la correlación pasiva
del detector de loops. WAV y Synth producen muestras en el host; el proceso
receptor mantiene la entrega y las confirmaciones del Q. El canal de pedidos
PCM es independiente de la FIFO de eventos RF/configuración.

La cola DAC y los créditos están acotados. BEGIN/PLAY/STOP se serializan; los
bloques PCM pueden llenar la ventana durante el cebado y PLAY espera todos
los ACK. El receptor atiende audio entre tramas RF y evita repetir el sondeo
IPC cuando no corresponde publicar un lote. Un UNDERRUN se conserva como
fallo, con tiempos y reserva disponible, para distinguir generación de audio
de demora de entrega/confirmación. No se oculta ampliando buffers sin evidencia.

El volumen de Generador Radio actúa sobre la salida y el objetivo del gain auto;
el ajuste normal es gradual, salvo clipping extremo. El clamp DAC no constituye
protección eléctrica contra cualquier carga externa. El detector de loops puede
detener salida si la entrada parece estar leyendo A0.

## Preparación, conexión y recuperación

«Preparar Q» y «Conectar» tienen responsabilidades distintas. Conectar abre la
pareja instalada, comprueba identidad y conserva un snapshot. Preparar utiliza
recibo, binarios y verificadores propios de V18. Si la pareja ya coincide,
verifica diez segundos de recepción sin reinstalarla. Si actualiza una pareja
existente, primero respalda fuentes, caché completa, ELF/BIN y relay, prueba la
reconstrucción del archivo y guarda el manifiesto pareado.

La instalación usa caché nueva de Scope V18. El hash MCU debe coincidir con el
aceptado antes de arrancar el relay. Si algo falla, restaura fuentes y caché
originales, recupera el relay anterior y comprueba identidad, CPU y adquisición.
Nunca trasplanta caché de otra app. La GUI espera el cierre seguro de esta
operación antes de permitir cerrar la ventana o iniciar adquisición.

Los informes separan tests locales, integridad física, holgura, estabilidad
conjunta, aceptación analógica y rendimiento de dibujo. Pasar una de esas
pruebas no equivale automáticamente a pasar las demás.
