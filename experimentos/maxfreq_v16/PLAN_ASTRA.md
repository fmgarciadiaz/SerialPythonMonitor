# Barrido CH1 nativo ADC8/10/14

Plan de Astra solicitado por el usuario el 11/10/2026; ejecución a cargo de Codex.
Fuentes estables V16 no se modifican ni se incorporan tasas a la GUI durante el ensayo.

## Límites y contrato

ADC1 a 54 MHz (máximo especificado 55 MHz), cinco ciclos de adquisición.
Conversión requiere SMP + bits + 3: 16/18/22 ciclos en ADC8/10/14.
El mínimo de disparo externo publicado para ADC14 es 26 ciclos: límite conservador
de 78 ticks TIM2 a 160 MHz. SPI permanece a 32 MHz, por debajo del máximo esclavo
dúplex de 38,5 MHz especificado a 2,7–3,6 V.
Fuentes: [DS13086, tablas 105 y 150](https://www.st.com/resource/en/datasheet/stm32u585ri.pdf)
y [RM0456 Rev3, secciones 29.4.19 y 29.4.22](https://www.stmcu.jp/wp/wp-content/uploads/2021/07/RM0456_Rev3.pdf).

Un único firmware experimental CH1, protocolo kind20/SCP1 V4/992.
SET_ACQUISITION codifica tamaño de nodo en high16 y ticks en low16.
Cabecera de métricas en 84..115; datos empaquetados desde 116.
Capacidad por trama 864/696/496 muestras para ADC8/10/14.
Nodos múltiplos de 16; timestamps DMA individuales conservados.
Mediciones de cola incluyen nodo prestado y reserva del productor; máximo de copia
y polling en ticks CPU. Margen de sobrescritura medido después de validar el nodo:
`int32_t(timestamp_inicial + 2*N*ticks - TIM5->CNT)`.
Servicio completo del nodo desde take hasta release, observado en el siguiente nodo.
Estas métricas agregan costo: distinguir referencia estable e instrumento experimental.

## Matriz y aceptación

Ticks: 480,400,320,267,242,224,208,200,192,176,160,144,133,128,120,112,104,96,88,80,78.
ADC8 nodos 3456/3584/6912/8192; ADC10 2784/5568/8192;
ADC14 1984/3968/7936. Cinco segundos medidos tras un segundo de asentamiento;
128 nodos completos mínimos. Refinamiento de todos los ticks enteros entre el pase
más rápido y el fallo inmediato superior de cada tamaño; diez segundos por punto.
Repetir el fallo de frontera con reinicio independiente.
Los mejores candidatos requieren 60 s, tres arranques de 120 s y 600 s.

Integridad: CRC, secuencia, época, índice/timestamp modular, configuración, rango ADC,
propiedad DMA, dropped=fatal=0 y tasa recibida ±2%. Margen adicional: envío medio
menor que 90% del período del nodo, cola máxima menor que 4 y margen positivo.
Reportar máximo íntegro y margen por separado; no inferir precisión analógica.
Si 78 ticks pasa, ampliar ADC8 hacia 60 y ADC10 hacia 66 con el modelo conservador
de cuatro ciclos adicionales al tiempo de conversión. Esos límites son derivados,
no mínimos publicados explícitamente por ST para 8/10 bits.

## Estado previo y restauración

Recuperar snapshot real antes del reset, incluso si el relay ya rechazó la adquisición.
El relay de recuperación admite únicamente lectura de estado con CRC/secuencia:
ninguna muestra suya es evidencia del barrido. Guardar fallos previos y bajo carga.
Tras cada fallo reiniciar MCU/relay experimental antes del siguiente caso.
Finalmente detener app experimental, arrancar app/relay V16 estable, restaurar
snapshot ADC/generador/SPI y confirmar sus campos. Verificar diez segundos y
reportar por separado si el perfil previo ya es inestable.

La primera compilación mostró RAM de 325.556 bytes frente a los 262.144 disponibles
en el sketch. La variante usa cola CH1 de uint16 y reserva WAV reducida a cuatro
slots para dejar espacio a nodos grandes. No se prueba ni ofrece WAV en el barrido.

## Revisión tras campaña parcial, 11/10/2026

La campaña original se archivó en `instrumentado_generico/`: se interrumpió
controladamente antes de aceptar finalistas. Restauró los campos del snapshot;
la comprobación de integridad del perfil original volvió a fallar, como antes
del ensayo. No hay máximos sostenidos certificados en esa campaña.

Astra identificó dos regresiones respecto del ADC8 integrado: N3584 requiere
cinco tramas de 864 muestras, frente a cuatro de 904; además el empaquetador
genérico usa desplazamientos de 64 bits y borra el payload completo. Los fallos
observados llenan la cola con dropped=1 y fatal=0. No son límites del ADC.

La revisión `specialized_packing_v2` conserva el protocolo y las métricas,
especializa ADC8, ADC10 cuatro muestras/cinco bytes y ADC14 cuatro/siete, y
borra solo padding. El helper C++ se compara contra una referencia independiente
con ceros, máximos y muestras aleatorias. No se reutiliza evidencia de la revisión
anterior; cada campaña registra hashes de fuentes y rechaza resume incompatible.

El refinamiento incluye pases de repetición independiente. La aceptación busca
por separado máximo íntegro y máximo con margen; ambas categorías requieren
60 s, tres arranques de 120 s y 600 s. Son máximos validados entre los perfiles
ensayados: descartar tasas tras dos fallos no demuestra monotonicidad universal.
La ampliación por debajo de 78 ticks permanece pendiente de otro contrato.
