# Barrido máximo V16 con dos canales

Campaña física v2 cerrada el 12/10/2026 después de incorporar y verificar CH1.
Reporte: `sweep.json` (`ok=true`, `restored=true`); registros: `sweep_v2.log`
y `resume_finalists.log`. [Resultados y límites](RESULTADOS.md), nueve perfiles
aceptados y auditoría `acceptance_audit.json`. Nueve perfiles dual incorporados
y verificados en producción, conservando cinco CH1: `production_acceptance.json`.
ADC10/12 no retuvieron ≥10% de margen integrado; etiquetas reconciliadas.
El dueño host y caffeinate terminaron; parámetros originales restaurados.

La campaña anterior, rechazada por una discrepancia de capacidad de trama ADC8,
se conserva en `full_frame_geometry_failure/`. La corrección se verificó con
el constructor MCU real, relay y ambos decodificadores para las cinco resoluciones.

Orden: cerrar CH1, incorporar y verificar la integración real; luego guardar el
perfil y respaldo de ese V16 y ejecutar esta variante aislada con dueño único.
Usar caffeinate -i -s y control de deriva pared/monotónico.

Resoluciones: 8, 10, 12, 14 y 16 bits. Dos entradas por disparo; las tasas se
reportan por canal. Los 16 bits usan el oversampling ×16 existente. ADC/DAC
mantienen el kernel de 54 MHz y cada disparo conserva su timestamp TIM5 a160 MHz.

Kind20 transporta ambos valores compactos, índices, época y métricas de cola,
copia, envío y margen hasta sobrescritura. No reducir validación DMA/timestamps.
Pruebas cortas con al menos128 nodos; refinamiento en ticks enteros; aceptación
60s + tres arranques independientes de120s +600s para cada perfil incorporado.
Buscar máximo íntegro y máximo con margen por separado. Restaurar exactamente
ADC, salida y generador; informar integridad de restauración aparte.

Cota de exploración:156 ticks para ADC8/10/12/14,2048 para ADC16.
En16 bits se incluyen disparos deliberadamente más rápidos que el tiempo
esperado de la secuencia; los timestamps y la propiedad DMA deben rechazarlos
si se omiten conversiones. Esto no cambia el reloj ADC ni la salida DAC.
No llamar a esa cota un máximo físico. ST DS13086 rev10, tablas104/105:
https://www.st.com/resource/en/datasheet/dm00639779.pdf
ADC1 admite hasta55 MHz; tCONV=(ts+N+3)/fADC, ts mínimo5 ciclos.
El esquema de16 bits hace16 subconversiones de14 bits por cada canal.
El ensayo acepta integridad de transporte/adquisición; precisión analógica,
asentamiento y ENOB necesitan evidencia analógica independiente.

Los nodos están alineados a16 pares y a tramas completas para no perder
capacidad por padding: ADC8 1728/3456/3888, ADC10 1392/2784/4176,
ADC12 1152/2304/4032, ADC14 992/1984/3968, ADC16 864/1728/3456.
Máximo4176 pares: arrays y validadores comparten ese límite. La variante
experimental preserva las aceptaciones CH1 y cabe con sus buffers aislados.
