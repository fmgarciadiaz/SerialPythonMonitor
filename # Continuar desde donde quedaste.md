# Continuidad · 19/10/2026

La pareja activa es **V17**. Leer primero el [estado actual](docs/ESTADO_ACTUAL_V17.md) y el [plan vigente](Plan%20de%20trabajo.md).

## Última actualización · landing y estabilidad RADIO/WAV

- README raíz recuperado como presentación completa: badges, imágenes por función, módulos y arquitectura; actualizado a V17. Regla permanente en `AGENTS.md` y memoria, por pedido explícito del usuario. No volver a reemplazar la landing por un índice técnico.
- WAV incorporado: dos chunks PCM en vuelo al reproducir, capacidad anunciada hasta 30 bloques, ACK atendidos entre tramas. La combinación pasó 3×120 s ADC16/76226→50 kHz; las variantes parciales fallidas siguen descartadas. Con producción pasaron seek/Stop/replay/EOF/reinicio. ADC14/100000→50 kHz pasó 60 s; luego SIGBUS en cierre Qt/SIP de Python, ya con Q restaurado (no underrun durante captura).
- RADIO: transición de estación con rampa 5 ms a neutral y 20 ms de entrada. Se conserva explícitamente como transición la duración de audio de sintonía anterior descartado, sólo dentro de sesión/reloj iguales. Control antes/después, 120 s y 58 resintonías: reserva mínima host 0→7670 muestras; sin cortes ni dropped/fatal. No equivale a aceptación global de todos los perfiles.
- Sweep/Chirp: saltos de inicio/fin medidos físicamente, hasta 1,62/0,74 V en este caso; suavizado de firmware sigue pendiente. No se cambió firmware.
- Resultado y evidencias: [RADIO/WAV y clics](docs/ESTABILIDAD_RADIO_WAV_CLICS_V17.md). Q restaurado a ADC8/1,6 MS/s y generador OFF, mismo firmware. Reiniciar monitor para cargar cambios host; no hace falta Preparar Q.

## Trabajo anterior

Se corrigió el orden de ACK del generador: el bloque ADC acumulado se publica antes y se respeta el executor DSP. Regresión antes/después reproducida. Tonos CH2/CH2 pasó 5/5 puntos entre 20 y 1000 Hz con asentamiento 200 ms; Sweep dibuja; Pulso sigue sin detectar estímulo con 1 y 10 ms. Ver [Bode](docs/DIAGNOSTICO_BODE_SIN_CURVAS_V17.md). RADIO sin A0 demodula y dibuja en prueba local a 8 bits/1,6 MS/s; salida por parlantes PC no implementada.

Nuevo corte real RADIO/A0 a ADC8/1,6 MS/s (18:39:17): DAC UNDERRUN, fuente sin error ni hits de lazo. Se incorporó registro acotado de huecos DSP/chunks y pausas de transporte, con tasa de salida explícita. No se cambiaron reservas ni política de entrega. [Seguimiento y pruebas](docs/DIAGNOSTICO_RADIO_A0_ADC8_1600_V17.md). Causa todavía abierta.

Se ordenó documentación sin cambiar la lógica: el README anterior y los registros acumulados se conservaron en `docs/historico`. Las fuentes activas siguen en sus rutas; experimentos, capturas y respaldos se mantienen.

Q: sólo Scope V17 como app de usuario, activa. V16 y Send1400 se retiraron después de exportar/verificar ZIP y SHA256. Los ejemplos Arduino se conservan. Firmware antes/después idéntico: `96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`. [Limpieza](diagnosticos/resultados_v17/cleanup_apps_20261019_160438.json).

## Retomar Bode

El usuario confirmó **CH1 = antena**. El par predeterminado CH1→CH2 no puede medir correctamente el estímulo de A0 en ese cableado. Última conexión confirmada de A0 era CH2/A3; reconfirmar si se cambia el montaje.

Se corrigió Pulso/Sweep para detectar el estímulo usando la referencia seleccionada. Sweep CH2/CH2 produjo curvas físicas válidas. El seguimiento posterior validó Tonos sólo a 20–1000 Hz con 200 ms de asentamiento; Pulso continúa pendiente. Los selectores se ampliaron a 150 kHz para Tonos/Sweep/Chirp y 200 kHz para Pulso, con límite final <0,45×Fs; comprobación local de límites/intermedias correcta, no validación física de Bode a esos extremos.

## Incidencias abiertas

GUI atrasada en RADIO/Scan, cortes variables WAV y aceptación global RADIO/A0 continúan abiertas. No incorporar candidatos aislados sólo porque pasaron una corrida. Ver el plan y los informes enlazados desde el estado actual.

Herramientas CLI: indicar V17 explícitamente, porque el valor predeterminado V16 se conserva por compatibilidad. La limpieza no cambió configuración ADC/DAC ni reinició V17. Comprobar propietario antes de operar Q.

[Registro anterior completo](docs/historico/CONTINUIDAD_ACUMULADA_20261019.md).

Control final del cambio de orden: RADIO/A0 ADC8/1,6 MS/s durante 60 s, Python 3.13, sin cortes, con restauración y firmware idéntico. Q libre, generador OFF. No cerrar incidencias intermitentes por este control.
