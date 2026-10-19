# Continuidad · 19/10/2026

La pareja activa es **V17**. Leer primero el [estado actual](docs/ESTADO_ACTUAL_V17.md) y el [plan vigente](Plan%20de%20trabajo.md).

## Último trabajo

Nuevo corte real RADIO/A0 a ADC8/1,6 MS/s (18:39:17): DAC UNDERRUN, fuente sin error ni hits de lazo. Se incorporó registro acotado de huecos DSP/chunks y pausas de transporte, con tasa de salida explícita. No se cambiaron reservas ni política de entrega. [Seguimiento y pruebas](docs/DIAGNOSTICO_RADIO_A0_ADC8_1600_V17.md). Causa todavía abierta.

Se ordenó documentación sin cambiar la lógica: el README anterior y los registros acumulados se conservaron en `docs/historico`. Las fuentes activas siguen en sus rutas; experimentos, capturas y respaldos se mantienen.

Q: sólo Scope V17 como app de usuario, activa. V16 y Send1400 se retiraron después de exportar/verificar ZIP y SHA256. Los ejemplos Arduino se conservan. Firmware antes/después idéntico: `96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`. [Limpieza](diagnosticos/resultados_v17/cleanup_apps_20261019_160438.json).

## Retomar Bode

El usuario confirmó **CH1 = antena**. El par predeterminado CH1→CH2 no puede medir correctamente el estímulo de A0 en ese cableado. Última conexión confirmada de A0 era CH2/A3; reconfirmar si se cambia el montaje.

Se corrigió Pulso/Sweep para detectar el estímulo usando la referencia seleccionada. Sweep CH2/CH2 produjo curvas físicas válidas. Tonos y Pulso no quedaron validados por esos ensayos. Los selectores se ampliaron a 150 kHz para Tonos/Sweep/Chirp y 200 kHz para Pulso, con límite final <0,45×Fs; comprobación local de límites/intermedias correcta, no validación física de Bode a esos extremos.

## Incidencias abiertas

GUI atrasada en RADIO/Scan, cortes variables WAV y aceptación global RADIO/A0 continúan abiertas. No incorporar candidatos aislados sólo porque pasaron una corrida. Ver el plan y los informes enlazados desde el estado actual.

Herramientas CLI: indicar V17 explícitamente, porque el valor predeterminado V16 se conserva por compatibilidad. La limpieza no cambió configuración ADC/DAC ni reinició V17. Comprobar propietario antes de operar Q.

[Registro anterior completo](docs/historico/CONTINUIDAD_ACUMULADA_20261019.md).
