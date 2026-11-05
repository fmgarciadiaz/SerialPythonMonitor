# Versiones, parejas y respaldos

Arduscopio Q usa el monitor PySide6 V19 y la pareja independiente **Scope V19**.
El 27/10/2026 se instaló desde cero en el Q; firmware y relay coinciden con el
recibo V19. La recuperación inicial sostuvo 10,03 s sin pérdidas y el smoke de
GUI dibujó FFT con la ventana expuesta, sin encender A0, y cerró restaurando la
salida. La aceptación cubre esa pareja y ADC8 CH1/1,860 MS/s; no califica todos
los bits, tasas, modos ni la respuesta analógica. Consultar el inventario antes
de volver a operar el Q.

| Elemento | Ubicación | Estado |
|---|---|---|
| Monitor de escritorio activo | [monitor/v19](../monitor/v19/README.md) | PySide6; código y dependencias propios |
| Pareja activa del Q | [Scope V19](../arduino/v19/README.md) | Instalada; hashes del recibo verificados; adquisición inicial y GUI smoke aprobados |
| Pareja anterior | [Scope V18](../arduino/v18/README.md) | Se conserva intacta y asociada a monitor/v18; no modificar |
| Snapshot de fuentes y artefactos V18 | [respaldo pareado](../respaldos/parejas/v18_archivo_host_20261027/manifest.json) | Hashes preservados; sin cambio de firmware al migrar el host |
| Monitor anterior | [monitor/v18](../monitor/v18/README.md) | Se conserva en su ruta junto con su firmware |
| Monitor congelado | [monitor/v17](../monitor/v17/README.md) | No modificar |
| Pareja congelada | [arduino/v17](../arduino/v17/README.md) | No modificar |
| Respaldo pareado V17 | [manifiesto](../respaldos/parejas/v17_20261023_000325/manifest.json) | Fuentes verificadas contra el árbol congelado |

[Recibo V19, alcance y preparación](PREPARAR_Q_V19.md). El inventario del Q del
27/10/2026 confirmó Scope V19, `scope-v19-main-1` y
`serialmonitor-usb-stream-v19` como única pareja activa; V18 aparece sin
inicializar, V17 detenida y cuatro relays guardados V18 detenidos. Los recibos y binarios V18 se conservan en
`monitor/v19/q_support/v18_reference/` solo como referencia histórica; no
autorizan instalar Scope V19. El despliegue V19 usa su recibo propio.

V17 y V18 permanecen en sus ubicaciones actuales: mover las parejas aceptadas
y sus manifiestos rompería las rutas de respaldo y recuperación. La carpeta
`arduino/v19` es el nuevo espacio de trabajo de firmware; los cambios futuros
de V19 se hacen allí.

[Validación del host y límites](PYSIDE_V19_COMPARACION.md) ·
[Arquitectura del sistema](ARQUITECTURA_V19.md) ·
[Índice técnico](README.md) · [Historia](HISTORIA.md).
