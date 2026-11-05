# V20: limpieza y verificación de arranque (4/11)

Se terminó de eliminar `.venv-v19Pyside`, entorno local de pruebas que no
figuraba en los lanzadores actuales ni tenía procesos activos. El conda
habitual `Python_3_13_DataScience` se conservó. El primer borrado tuvo un
residuo de directorio no vacío; el segundo confirmó ausencia del entorno.
El inventario previo registraba aproximadamente 931,5 MB asignados; no es
una medición del espacio libre efectivamente recuperado en APFS.

En el Q se quitaron 45 contenedores detenidos `serialmonitor-usb-stream-v20-evidence-*`
y 88 directorios de caché que contenían únicamente un binario de relay
(6.515.400 bytes). Se excluyeron los montajes de todos los contenedores
conservados. El relay activo V20 mantuvo su SHA antes y después. No se
modificaron apps de ArduinoApps, biblioteca App Lab, firmware, fuentes ni
respaldos de versiones. Se conservaron los contenedores guardados por versión.

La prueba de ventana real importó en 2,49 s, mostró ventana en 4,52 s y
confirmó bucle GUI activo; cerró normalmente sin conectar al Q. Esto no
reproduce todas las demoras intermitentes del usuario.

Volvieron a encontrarse archivos V20 dataless después de la recuperación
anterior. Se solicitaron 151 descargas mediante la API oficial de macOS;
las 151 fueron aceptadas, y el control posterior dio cero archivos V20
dataless. No se cambió la preferencia de mantener descargado permanentemente.
La persistencia local depende del proveedor de archivos y esa preferencia.

El lanzador principal de VS Code todavía abría V19. Ahora ejecuta
`monitor/v20/app.py` con el mismo conda habitual. Los lanzadores de archivo
se conservaron, y el JSON anterior está respaldado en
`respaldos/host/v20_before_launch_cleanup_20261104/launch.json`.

Los inventarios, selecciones exactas y resultados están en
[`diagnosticos/limpieza_20261104`](../diagnosticos/limpieza_20261104/).
La verificación física de conexión se registra por separado en
[`normal_reconnect_cleanup_20261104/report.json`](../diagnosticos/resultados_v20/normal_reconnect_cleanup_20261104/report.json).

Resultado físico: dos conexiones normales ADC14/40 kHz dual, 10 s de
adquisición cada una, desconexión y cierre PASS. Ambas restauraciones
confirmadas durante al menos 10 s, sin errores, e identidad antes/después
igual. Ningún proceso de prueba quedó activo.
