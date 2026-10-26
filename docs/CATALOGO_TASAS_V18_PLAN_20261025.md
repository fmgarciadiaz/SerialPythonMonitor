# Catálogo de tasas V18 · propuesta y validación

Usuario confirma 44,1 kHz y respetar límites actuales. Revisión con Astra:

- Separar catálogo visible de perfiles históricos reconocidos. No borrar entradas
  necesarias para ACK/restauración ni alterar métodos de tasas actuales.
- Identidad actual por bits+tasa: no duplicar el mismo período CH1/dual.
  Audio común será dual donde sea posible; CH1 extiende por encima de máximo dual.
- No cambiar UART, reloj ADC/SPI, resolución ni sobremuestreo16x.

| Nominal audio | Período a 160 MHz | Real S/s | Error ppm |
|---|---:|---:|---:|
|44,1 kHz|3628|44101,433|+32,5|
|48 kHz|3333|48004,800|+100,0|
|96 kHz|1667|95980,804|−200,0|
|192 kHz|833|192076,831|+400,2|

No son tasas exactas. La interfaz muestra el nominal aproximado y la tasa real;
la cabecera WAV conserva la tasa real redondeada a Hz enteros. En 16 bits,
192 kHz queda fuera del límite; 96 kHz está disponible sólo en CH1 y
44,1/48 kHz mantienen los perfiles duales existentes.

## Distribución propuesta

Conservar las tasas bajas de 1/5/10/20/31,25/40 kHz y agregar los anclajes de
audio. Reutilizar tres tasas duales existentes y distribuir tres puntos CH1
entre el máximo dual y el máximo CH1. El catálogo tiene 17 opciones para
8–14 bits y 15 para 16 bits. Los perfiles históricos siguen reconocidos y
pueden mostrarse desde el menú contextual del selector.

| Bits | Períodos CH1 añadidos (ticks) | Bloque | Cola | Método conservado |
|---|---|---:|---:|---|
| 8 | 170 / 128 / 104 | 3488 | 8 | SPI 40 e IPC compacto |
| 10 | 220 / 171 / 141 | 5568 | 4 | Ruta rápida actual |
| 12 | 265 / 208 / 171 | 7488 | 4 | Ruta rápida actual |
| 14 | 306 / 235 / 190 | 5952 | 4 | Ruta rápida actual |
| 16 | 1458 / 1296 / 1166 | 3488 | 4 | Sobremuestreo ×16 actual |

## Evidencia privada completada

- Audio: 17 perfiles, 60 s por caso, integridad y holgura aprobadas,
  cola máxima 1. Informe `experimentos/fs_max_v18/resultados/20261025_194759/report.json`.
- Intermedios CH1, pareja integrada: 15 perfiles, 60 s por caso,
  integridad y holgura aprobadas. Cola máxima 1 salvo 8 bits/ticks 104,
  que alcanzó 2. Informe `experimentos/fs_max_v18/resultados/20261025_201421/report.json`.
- Regresión de audio en la pareja integrada: 17 perfiles, 15 s por caso,
  aprobados. Informe `experimentos/fs_max_v18/resultados/20261025_203801/report.json`.
- GUI visible: 10 casos representativos aprobados, con RADIO/A0, Scan,
  WAV, Synth y cierre. Informe
  `diagnosticos/resultados_v18/catalog_private_gui_20261025_205321/report.json`.
  WAV/Synth usan la tasa de adquisición compatible prevista por el ensayo;
  esto no acredita WAV simultáneo a cada tasa alta.
- Restauración del Q verificada en todas esas campañas. Los fallos previos
  del ensayo de Scan se conservan: el arnés esperaba tres bloques totales,
  en vez de tres bloques nuevos desde el cambio de generador. Se corrigió
  esa condición y se agregó una prueba de regresión.

## Incorporación y cierre

Los 32 perfiles están incorporados en Monitor V18 y Scope V18. Rollback exacto,
compilación de producción, respaldo previo y actualización transaccional
aprobados. Firmware `37f049fa…`, relay `27da0bc4…`.

- Regresión instalada: 32/32 perfiles, 15 s por caso, integridad y holgura
  aprobadas; cola máxima 2, sin pérdidas ni fatales.
  `experimentos/fs_max_v18/installed_campaign/20261025_223730/report.json`.
- GUI instalada visible: 10/10 recorridos aprobados y restaurados, sin
  inyección de perfiles privados.
  `diagnosticos/resultados_v18/catalog_installed_gui_20261025_224618/report.json`.
- Regresión posterior: 237 pruebas V18 y 30 adicionales aprobadas.
- 148 rutas históricas de Scan verificadas sin cambios.
- Preparar Q final verificó la identidad y 10 s de adquisición:
  `experimentos/fs_max_v18/release_catalog_20261025_222651/final_prepare.json`.
- V17 conserva sus 175 archivos protegidos. Los máximos públicos y los métodos
  de adquisición anteriores permanecen iguales.

El intento instalado `223700` se conserva como fallido: el arnés omitía la marca
dual al codificar una configuración y no llegó a medir casos. Restauró el Q;
se corrigió para usar Configuration y comprobar la geometría antes de medir.
La evidencia de transporte no certifica ENOB ni calidad analógica.

Respaldo pareado final: `respaldos/parejas/v18_catalogo_20261025_230123/manifest.json`.
