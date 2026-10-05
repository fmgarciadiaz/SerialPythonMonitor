# Ensayo MCU interrumpido · 4 de octubre de 2026

Firmware aislado Scope SPI Timing Diagnostic compilado: 103104 bytes de
programa, 157040 bytes de variables, 105104 bytes libres. App independiente
importada; V9 Fast respaldada antes del ensayo en
`respaldos/unoq/osciloscopio_20261004_192442_610957.zip`.

No se obtuvo una instantánea MCU válida. Primer arranque: el contenedor
serialmonitor-usb-stream se creó/inició y fue detenido/eliminado 8 segundos
después, según Docker events. Segundo arranque: la captura de 100 kHz cerró
al recibir 512 bytes FF; CRC recibido FFFFFFFF y calculado 4D3F5134.
[Log de ese intento](generador_activo_100.log). No atribuir estos errores
al atraso sostenido de 125 kHz.

Durante este trabajo las herramientas compartidas incorporaron v10_diag y
el relay cambió sin intervención de este hilo. Se suspendieron nuevos cambios
al Q para aclarar el control concurrente con el usuario. La última app iniciada
por este hilo fue Scope SPI Timing Diagnostic. No se ejecutó aún restauración
normal para evitar interferir con otro controlador de la placa.

Los tiempos MCU todavía están pendientes. La evidencia del diagnóstico
previo de latencias Linux conserva sus límites y no depende de este ensayo.

## Actualización posterior

El usuario confirmó que no había otro ensayo activo y autorizó continuar.
Se obtuvieron dos instantáneas válidas usando un contenedor exclusivo:
[mediciones MCU, límites y restauración](README.md). La interrupción anterior
no tiene autor identificado; ya no bloquea estas mediciones controladas.
