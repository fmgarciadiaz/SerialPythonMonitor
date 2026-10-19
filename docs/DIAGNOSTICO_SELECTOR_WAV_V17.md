# Selector WAV con ADC8/1,6 MHz — 19/10/2026

Sin cambios de producción/firmware. Selector original conservado.

1. `wav_selection_20261019_120357/report.json`: adquisición física 22 s por
   caso, RADIO OFF/ON, callback completo posterior a selección con ruta
   imperial.wav inyectada: 2,45/1,42 ms, sin errores, GUI máxima46/81 ms.
2. `wav_selection_20261019_120519/report.json`: Cocoa, diálogo nativo original
   abierto, intento de selección automatizada sin aceptación efectiva y
   cancelación automática a6 s. RADIO OFF reprodujo “Entrega GUI atrasada:
   presupuesto de muestras/tiempo/memoria excedido”, GUI máxima1058 ms.
   RADIO ON no falló en ese intento, GUI máxima356 ms y18 lotes retenidos.
   No presentar esto como carga exitosa del archivo: metadata=null en ambos.

La adquisición puede detenerse mientras el selector nativo está abierto;
la lectura de imperial.wav no es necesaria para reproducir este fallo.
Todavía no está corregido y no se demuestra que sea la única causa.
Una corrección conservando selector debe evitar adquisición sin atención
GUI durante su apertura (por ejemplo pausa/reanudación explícita) y verificar
restauración de RADIO/generador/grabación; no subir el presupuesto para ocultar
una pausa arbitraria. No se implementó esta corrección en este bloque.

Q restaurado a la configuración previa ADC8/597014, generador OFF, identidad
de firmware idéntica; captura posterior5 s sin dropped/fatal. Informes bajo
`diagnosticos/resultados_v17`. Diagnóstico `diagnosticos/probar_selector_wav_v17.py`.


## Selector no modal solicitado: incorporado

`monitor/v17/app.py`: QFileDialog de Qt no nativo, WindowModality.NonModal,
sin exec ni bucle modal; abre directamente ROOT/audios (carpeta existente).
Una única instancia por ventana y limpieza al cerrar; metadatos se aplican
al aceptar. No se pausa adquisición, no se alteran presupuestos ni firmware.

Validación Cocoa física `wav_selection_20261019_120839/report.json`: 16 s por
caso, ADC8/1600000, RADIO OFF/ON, apertura real del selector y escritura del
nombre imperial.wav en fileNameEdit, aceptación efectiva, metadatos correctos.
Sin errores; GUI máxima130/121 ms, pendientes pico4/4; 21.721.824 y21.562.848
muestras recibidas. No incluye Play/A0 ni aceptación sostenida global.
Q restaurado ADC8/597014 generador OFF, firmware idéntico, recuperación5 s
sin dropped/fatal. El intento120735 mantuvo adquisición pero no aceptó archivo
por fallo de automatización: conservar evidencia, no contarlo como carga válida.
Diagnóstico reproducible: `diagnosticos/probar_selector_wav_no_modal_v17.py`.
