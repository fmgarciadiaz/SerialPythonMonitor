# Campaña guardada antes de implementar Generador Radio

ADC10 y ADC12 completaron60s +3×120s con integridad/holgura y sus controles
normales. Ver checkpoint_before_radio.json y qualification_20261017_021922/report.json.
ADC14 pasó screening60s y control normal; la primera120s fue interrumpida
por pedido del usuario. No se considera aceptación deADC14.
ADC16CH1 conserva su prueba local de formato, sin tasa física nueva.

Tras SIGINT, el finally restauró relay y firmware originales, ADC8/1600000
y generador apagado con campos previos. Verificación10s:15.990.912muestras,
dropped=fatal=0. La campaña no se reanuda automáticamente: el usuario pidió
implementar ahora Generador Radio separado de Radio Test.
