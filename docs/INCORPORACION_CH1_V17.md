# Perfiles CH1 incorporados a V17 — 14/10/2026

Los seis finalistas aislados están instalados en el Q y habilitados en V17.
Cada perfil pasó 60 s y tres arranques independientes de 120 s en producción.
CRC, secuencia, epoch, índices/timestamps, DMA y dropped/fatal permanecieron
sin errores. No se ejecutaron ensayos de 600 s.

| ADC | Perfil | Muestras/s | ticks / nodo | Margen medio envío por etapa | Cola máxima |
|---|---|---:|---|---|---:|
| 10 | Integridad | 1167883,212 | 137 / 5568 | 7,013–7,525% | 3 |
| 10 | Holgura | 1142857,143 | 140 / 2784 | 11,401–11,553% | 3 |
| 12 | Integridad | 981595,092 | 163 / 4608 | 6,875–7,051% | 3 |
| 12 | Holgura | 930232,558 | 172 / 4608 | 11,467–11,559% | 2 |
| 14 | Integridad | 851063,830 | 188 / 1984 | 8,571–8,894% | 4 |
| 14 | Holgura | 833333,333 | 192 / 1984 | 10,012–10,321% | 3 |

Los tres perfiles de holgura cumplen envío medio >=10%, cola <4 y slack >0
en todas las etapas. Los máximos de integridad no cumplen ese conjunto.
También pasó ADC8/1403508 durante 60 s, dual ADC14/363636 durante 10 s y
ADC16/40000 durante 10 s. No son aceptación analógica ni carga RADIO.

Cambios: packing CH1 ADC12 correcto, perfiles exactos con transporte rápido,
validación relay por formato/fronteras autorizada por el usuario y arranque
con cinco segundos de adquisición ADC14/40000 antes del máximo. La prueba
C compara el validador nuevo con el anterior para los seis perfiles,
wrap uint32, extremos y corrupción de payload/metadata/padding/CRC.

Informe y respaldo:
- `diagnosticos/resultados_v17/optimized_integration_20261014_095040/report.json`
- `respaldos/unoq/osciloscopio_20261014_095041_410999.zip`

Firmware instalado SHA256:
`bc150efba8fe229838c65a2dc9945aee020455ce8592c77fefb97772bdac592b`.
Configuración restaurada: ADC10/909090 SPI, generador apagado y todos sus
campos originales. Verificación posterior: 9087712 muestras íntegras en 10 s.
El firmware nuevo permanece instalado. Reiniciar la GUI V17 para cargar
los perfiles y cambios del host. V16 conserva su código previo.
