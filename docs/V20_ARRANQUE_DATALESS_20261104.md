# V20: arranque bloqueado al materializar archivos locales

Se inspeccionó el proceso real del usuario, PID23037, ejecutando Python3.13
con `monitor/v20/app.py`. Llevaba más de un minuto, CPU0%, sin llegar a crear
la GUI. La [muestra anterior](../diagnosticos/resultados_v20/startup_hang_20261104/user_python_23037.sample.txt)
registró889/889 muestras del hilo principal en importación y
`FileIO.readall → read`. `lsof` identificó FD3 leyendo
`monitor/v20/radio_am.py`; macOS marcaba ese archivo `compressed,dataless`.
El bloqueo estaba antes del event loop y de cualquier conexión al Q.

Se solicitó materialización por la API oficial de macOS
`NSFileManager.startDownloadingUbiquitousItemAtURL`, sin editar contenido ni
reiniciar el proceso. Tras solicitar el primer archivo su flag dataless
desapareció y el mismo PID avanzó hacia otros imports. Se inventariaron336
archivos del árbol V20 (5,3MB);193 seguían dataless. Las193 solicitudes
individuales fueron aceptadas; el control final confirmó0archivos dataless.
No se tocaron históricos, Arduino ni preferencias de sincronización.

La [muestra posterior](../diagnosticos/resultados_v20/startup_hang_20261104/user_python_23037_after.sample.txt)
del mismo proceso registró827muestras en `QApplication.exec → QEventLoop.exec
→ NSApplication.run`: la app completó sus imports y entró al bucle GUI.
No hubo kill, reset ni otro lanzamiento. No se conectó al Q ni se probó la
conexión del usuario. La consulta auxiliar de ventanas CoreGraphics falló
por conversión de JXA; la confirmación procede de la pila real, no de esa
consulta ni de una captura visual.

[Informe e inventarios antes/después](../diagnosticos/resultados_v20/startup_hang_20261104/report.json)
conservan rutas, tamaños, flags y respuestas del sistema. Los SHA de app,
panel y journal coinciden con el smoke anterior. No se modificó código.
El volumen mostraba98% de ocupación y12GiB disponibles; eso no prueba por
qué se descargaron los archivos del almacenamiento local.

Para evitar recurrencia conviene mantener descargada permanentemente la
carpeta del proyecto mediante Finder, o planificar su ubicación en una carpeta
local fuera de la gestión bajo demanda. No se cambió esa preferencia ni se
movió el proyecto en este bloque. La configuración VSCode predeterminada aún
apunta aV19, pero este proceso ejecutaba V20 directamente; no fue la causa
del bloqueo observado.
