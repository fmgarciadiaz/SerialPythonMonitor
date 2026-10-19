# RADIO+A0 ADC14 — política CPU y envío

Síntoma real: EOF del cliente. Trama67734 aADC14/851063,N1984,ticks188: dropped1,fatal0,cola4 yCRCcorrecto. El relay rechaza la pérdida. Evidencia `diagnosticos/resultados_v17/closed_flow_20261018_121625/`.

Experimento aislado: conservar MCU, relojSPI38,FIFO10 y geometría. Agregar únicamente ADC14 CH1,ticks188/192,N1984 al predicado `scope_cpu_profile`. Activa afinidadCPU2,governorperformance y cola de envíoTCP; no atribuir resultado exclusivamente a afinidad.

No monitor activo. Se recuperó relayexited1 con respaldo, firmwareidéntico42cff220 yADC14/599250,generadorOFF; estado vivo previo no consultable al estar relaycaído. No se afirma restauración exacta de esa sesión fallida.

Campaña:60s baseline599250 con producción,60s candidato851063 y3×120s independientes. Todas RADIO+A0 a40k,volumen,resintonía,Stop. No tolerar pérdidas/underrun. Medir cola y envío por separado; margen>=10%,cola<4,slackpositivo necesarios para holgura. Restaurar relay anterior,política normal,ajustes eidentidad y10scontinuidad al finalizar, también ante fallo. No instalar ni modificar producción automáticamente por un ensayo corto.

Si falla: conservarlog ycomparar; siguiente opcióna estudiar es geometría de nodos mayores,requiereMCU y no se incluye aquí. ADC16 y nuevas tasas14 siguen fuera de alcance.
