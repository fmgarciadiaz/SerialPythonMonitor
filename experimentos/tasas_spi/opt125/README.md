# Optimización aislada de 125 kHz

P512 conserva tramas de 512 bytes; P992 utiliza SCP1 V3 de 992 bytes y
19 fragmentos por nodo de 2048 pares, frente a 39. Cada variante requiere
su propio firmware, relay y receptor. A2/A3 son entradas y A0 es DAC.
V11/V9 Fast siguen separados del candidato P992.

## Validación del 4 de octubre de 2026

Las mediciones instrumentadas P992 a 14 bits y 125 kHz por canal pasan
el criterio de margen medio mínimo del 10 %:

| Generador | Envío medio por nodo | Margen medio | Cola máxima | Evidencia |
|---|---:|---:|---:|---|
| Apagado | 14,118 ms | 13,83 % | 2/4 | [Informe](resultados/20261004_201315_290479/informe.json) |
| Cuadrada 2,5 Hz | 14,067 ms | 14,14 % | 2/4 | [Informe](resultados/20261004_201404_617808/informe.json) |

Cada ventana duró aproximadamente 5 segundos: 622705 pares, 305 nodos y
304 envíos completos, sin pérdidas ni errores fatales. El presupuesto es
16,384 ms por nodo y el umbral de aceptación medio es 14,7456 ms.
Las medias inicial/final de ocupación permanecen alrededor de un nodo.
Es margen medio observado, sin garantía de peor caso ni extrapolación a
otros estímulos. La aceptación sostenida del candidato normal se registra
por separado.

Pasaron 185 pruebas locales, incluidas 13 del contrato y monitor P992.

P992 normal aprobó dos capturas de 120 segundos a 14 bits / 125 kHz:

| Condición | Pares validados | Comandos concurrentes | Evidencia |
|---|---:|---:|---|
| DAC apagado | 14989425 | 0 | [Informe](resultados/20261004_201635_739423/informe.json) |
| Cuadrada 2,5 Hz | 14989425 | 119 | [Informe](resultados/20261004_201847_338256/informe.json) |

Ambas capturas preservan el binario, no presentan errores de CRC, índices,
timestamps ni rango ADC, y terminan con `dropped=fatal=0`. Cada prueba
restauró exactamente su perfil inicial del candidato (14 bits / 31,25 kHz
y cuadrada habilitada). `acceptance_passed=null` en estos informes significa
que el script de continuidad no evalúa el margen temporal: ese criterio lo
acreditan las instantáneas instrumentadas anteriores.

[Transiciones](resultados/20261004_202100_908703/informe.json): tres ciclos
100 kHz sin DAC → 125 kHz sin DAC → 125 kHz con DAC, nueve etapas sin errores.

[Monitor con USB real](resultados/20261004_202135_362816/informe.json):
V(t), FFT de 1025 bins, heatmap de 119 columnas, trigger/SINGLE y CSV de
507551 filas con incrementos exactos de una muestra y 8 µs. Capturas PNG en
la misma carpeta. Qt se ejecutó en modo offscreen; esto valida adquisición,
análisis y renderizado, sin afirmar una comprobación manual de la pantalla.
V_IN tuvo sólo 45,7 mVpp en la ventana previa al trigger: SINGLE aprobado
no acredita precisión analógica ni que el disparo corresponda al DAC.
La validación analógica de ambos canales sigue pendiente.

[Aceptación consolidada](resultados/aceptacion_p992.json) aprobada.
[Restauración final](resultados/restauracion_final.json): V9 Fast normal,
14 bits / 100 kHz, cuadrada de 2,5 Hz, 298762 pares verificados sin pérdidas
y coincidencia exacta con el perfil guardado. Los 38 archivos originales
conservan sus SHA256. El ciclo queda cerrado; promoción a V11 pendiente.

## Reproducción

### Comprobación analógica

[Ensayo completado y aprobado](ANALOGICO.md): ambos canales recibieron A0
directamente. V9 Fast a 62,5/100 kHz y P992 a 62,5/100/125 kHz, 14 bits,
seno ~2 kHz y 10 segundos por perfil. Esta evidencia reemplaza el pendiente
de comparación de canales para ese estímulo, sin calibración absoluta.

`verificar_analogico.py` adapta el receptor de ensayo existente a V9 Fast
o P992. Requiere confirmar A0 unido directamente a A2 y A3, sin circuito
intermedio y con masa común. Guardará binarios y previews, ajustará una
senoide a cada canal después de desconectar y restaurará el perfil inicial.
Informa amplitud, offset, residuo RMS, frecuencia y diferencia relativa de
fase. El aprobado global exige integridad y comprobación analógica de ambos
canales; no equivale a calibración absoluta con instrumento de referencia.

Con V9 Fast activo, ejecutar primero:

```sh
python experimentos/tasas_spi/opt125/verificar_analogico.py --variant v9_fast --rates 62500 100000 --bits 14 --seconds 10 --frequency 2000 --direct-wiring-confirmed
```

Después de cargar exclusivamente P992 normal, repetir con `--variant p992`
y `--rates 62500 100000 125000`. Restaurar V9 Fast y el perfil guardado al
terminar. La bandera de cableado representa una confirmación física del
usuario; no debe inferirse de que el receptor entregue datos.

### Capturas de integridad y margen

Usar el Python del proyecto para los scripts de medición y el monitor.
Antes de iniciar cualquier variante, detener los otros relays y apps que
usen SPI/GPIO/TCP 8766. `hardware.py start` sólo detiene su propia variante.

1. Iniciar `hardware.py start --variant p992_timing`.
2. Ejecutar `medir_timing.py --variant p992 --rate 125000 --seconds 5 --generator off`.
3. Reiniciar la variante instrumentada y repetir con `--generator on`.
4. Detener `p992_timing`, iniciar `p992` y ejecutar `medir.py` durante 120 s
   sin/con generador; agregar comandos concurrentes mediante `--stress`.
5. Ejecutar `transiciones.py --variant p992` y `probar_monitor.py`.
6. Detener P992, iniciar V9 Fast normal y ejecutar `restaurar_perfil.py`.

La solicitud de snapshot congela la captura instrumentada y cierra el relay;
reiniciarlo antes de cada medición. Los archivos `stream.scp` preservan la
captura binaria. El receptor verifica CRC, secuencia, índices, timestamps,
rango ADC y estado MCU antes de entregar muestras.
