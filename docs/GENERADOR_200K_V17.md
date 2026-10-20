# Generador ampliado V17 — instalado 19/10/2026

Seno:0,1Hz–150kHz. Cuadrada:0,1Hz–200kHz. Resto:0,1Hz–50kHz.
Entrada numérica de frecuencias intermedias con resolución de0,001Hz en el
contrato; frecuencia efectiva redondeada por el timer. Dialeslogarítmicos y
frecuenciafinal ajustan el máximo según onda. RadioTest conserva su contrato.

## Validación

- MediciónA0→CH2/A3:17casoscortos,intermedias62500/73333/87500/112500/123456/
  137500Hzentreotras. Resultados analógicos en
  experimentos/generador_200k_v17/probe_20261019_144937/RESULTADOS.md.
- probe_20261019_145935:3arranquesporonda de120s cadauno a seno150k/cuadrada200k,
  ADC8dual632411, dropped/fatal0. Capturaanalógica alinicio de cada tramo;
  estosintervalosprueban adquisición conjunta sostenida,noTHDcontinuo.
- deployment_20261019_151624:señalCH2yestadoRUNNINGconfirmados alfinalde60s
  adicionales poronda. Sweep/Chirp62500↔150000Hz correctos enambossentidos.
-11pruebaslocales deGUI/contrato/RADIOTest/autogain/WAVcorrectas ypruebaC++
  detemporización/límites correcta.

Seno150k usa6puntos/ciclo:real~149812,7Hz,fundamental0,964Vpp frente1,017Vpp
seno25k para1Vppnominal. Mayordistorsión/residual a frecuenciasaltas;
no presentarlo como generador calibrado niTHDcertificado. Cuadrada200k
verificada en frecuencia,noflancoscalibrados. Dutyvariableaaltasfrecuencias
redondeado a pocos puntos; campaña física fue50%.

## Instalación y cierre

Firmware instalado SHA256:96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9.
Relay actualizado con límites poronda coincidentes con host yMCU.
Ajustespreviosrestaurados:True. ADC8/
1600000,generadorOFF. Recuperación10s:
15991776muestras,dropped/fatal0. Qlibre.
Respaldoprevio:/Users/fmgarciadiaz/Documents/Development/Electronica/0Fergd/SerialPythonMonitor/respaldos/unoq/osciloscopio_20261019_151625_317279.zip.

Primerintento151406seinterrumpió para corregir un contratoPythonimportadoantes
depublicarfuentes;rollbackrestaurófuentespero verificacióndealtaFS cerróflujo.
Recuperaciónposterior verificada conidentidadoriginaly10s15991776sin errores.
Segundo intento151624usa procesoPythonnuevo para comprobaciónfísica,terminó
ok/installed/restored=true. Conservar informes delintento interrumpido.

ReiniciarV17para usar nuevos límites.

## Transitorios en Sweep/Chirp

Los extremos de los barridos pueden producir clics por saltos de nivel. Se midieron en A0→CH2 sin modificar firmware; el suavizado sigue pendiente. Ver [medición y seguimiento](ESTABILIDAD_RADIO_WAV_CLICS_V17.md). No confundir la frecuencia verificada con una garantía de ausencia de transitorios.
