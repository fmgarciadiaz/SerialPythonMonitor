## 26/10 · Primera instalación desde Preparar Q

El botón agrega una ruta para un Q sin Scope V18. Implementación autocontenida
en `monitor/v18/q_support/bootstrap.py`, seleccionada por `service.py` sólo
cuando falta la pareja y un inventario explícito confirma el destino vacío.
No considera un fallo genérico de conexión como permiso para sobrescribir.

Antes de importar: propietario único, ausencia de lectores, apps/relays ajenos
activos y colisiones de nombre/carpeta; App CLI con versión y SHA256 del entorno
validado; verificador remoto íntegro; compilación aislada de fuentes aceptadas y
SHA256 exacto del firmware y relay. Luego importa Scope V18, inicia la app,
comprueba caché/BIN, arranca el relay, verifica identidad/fuentes y exige diez
segundos de adquisición continua con salida del generador apagada y WAV inactivo.

Cada fase se registra con intención y resultado. Un fallo conserva `ok=false`:
se detienen únicamente recursos nuevos atribuibles a este intento y se conserva
la instalación fallida para diagnóstico. No se mueve la carpeta si una parada
falla ni se modifica un relay con otra identidad. Una instalación parcial ajena
se rechaza. No se promete restaurar el firmware anterior desconocido de un Q
sin pareja previa. V17 detenida puede permanecer instalada y no se modifica.

Requisitos: sistema UNO Q operativo, ADB autorizado, App CLI compatible y el
entorno Arduino instalado. La operación no instala el sistema operativo del Q
ni controladores del PC. La primera instalación en un Q realmente vacío sigue
pendiente de validación física; las pruebas automatizadas cubren la selección,
orden de operaciones, verificación y fallos. La validación física histórica de
actualizar/restaurar una app existente no certifica este nuevo camino.

## 24/10 · adapter instalado y validado

El backend de producción ya se ejecutó con recibo explícito. El primer intento
revirtió exactamente al detectar un entorno relay distinto; se eliminó la
variable sin uso y el segundo aprobó identidad, fuentes, CPU y recuperación10s.
Usar `python -m tools.prepare_q_v18`; invocación por módulo requerida.
Se genera caché propia de Scope V18 y se exige el BIN aceptado antes del relay.
Fuentes/caché originales quedan respaldadas completas; no se copia caché privada.
Evidencia: `diagnosticos/resultados_v18/production_install_20261024.json`.
Las secciones antiguas siguientes describen las etapas previas del desarrollo.

## 24/10 · receta de producción revisada tras rollback físico

El rehearsal `same_app_restore_20261024_190241_71ed61/report.json` aprobó
restauración exacta de fuentes y caché en la misma app privada, cambio de
binario y recuperación10s. NO prueba traslado de caché entre apps.

Build aislado de fuentes con nombreScopeV18 produjo exactamente el firmware
aceptado `cad37ccd079ff7905863e9f826ba956abe47d13ddeb85634698e44f4930325c7`.
Proof y receipt en `respaldos/parejas/v18_promocion_20261024_191003/`.
La app de producción delQ aún no fue modificada.

Adapter en desarrollo: backupLIVE sólo si fuentes/caché permanecen exactas
antes/después y reconstrucciónstaging probada; sin parada oculta enbackup.
Instalación genera caché NUEVA mediante Board.start normal enScopeV18 y
exigehashMCUaceptado ANTES de arrancar relay. No trasplantar caché privada.
La evidencia de layout se verifica después del arranque, no enprepare.
Rollbackrestaura toda caché original de producción, incluso si fallo dejó
.cache ausente. Sólo tres headers añadidos autorizados y ningún eliminado.
La guarda histórica que sigue abajo queda cerrada hasta review/testsadapter.

# Preparación transaccional de Scope V18

Estado: **motor y contrato para revisión; adapter de producción cerrado**.
`tools/prepare_q_v18.py` muestra el plan por defecto. `--run` exige aceptación
explícita y se detiene sin construir `Board`, abrir ADB ni mutar Q. No hay una
opción para omitir esta guarda. Los tests son puramente inyectados; no prueban
restauración física ni autorizan instalación.

La razón concreta es que falta demostrar cómo la CLI instalada reutiliza el
build exacto al arrancar la misma app. Recuperar fuentes y sólo `sketch.ino.bin`
no demuestra esa propiedad: deben conservarse también ELF, demás artefactos,
metadata y permisos/tiempos que intervengan en la cache. Este documento no
supone flags `--skip-build` o `--skip-sketch`, ni un layout de cache no inspeccionado.

## Alcance fijo

- Fuentes locales: `arduino/v18/oscilloscope` y `arduino/v18/relay`.
- App existente: nombre `Scope V18`, ruta `/home/arduino/ArduinoApps/scope-v18`.
- Relay: `serialmonitor-usb-stream-v18`.
- No crear otra app, importar encima de una identidad no verificada ni usar
  `tools/prepare_q.py`, `tools/usb_stream.py` o autoload como ruta de despliegue.
- Conservar `monitor/v17`, `arduino/v17` y `Scope V17`.
- No actualizar tablas de tasas públicas desde una campaña privada.

## Contrato del adapter pendiente

`execute(backend, acceptance, report, save, allowed_removals)` mantiene
`backend.owner()` durante preflight, captura, preparación, aplicación y rollback.
El adapter real deberá implementar ese contexto con el `board_owner` de V18;
no basta con tomar un lock en un coordinador externo. Cada método tiene un
timeout acotado y cierra su receiver antes de devolver el control a operaciones
administrativas. El journal persiste intent antes de invocarlo y resultado al
terminar. Ninguna operación mutante se reintenta.

| Método | Resultado o garantía obligatoria |
| --- | --- |
| `preflight(acceptance)` | Sólo la app/ruta/serial V18 esperados activos, relay original identificado, puerto sin otro lector. CLI binaria/version y comportamiento de arranque coinciden con un ensayo privado de rollback exacto. Devuelve `production_backend_qualified`, `rollback_rehearsal_verified`, `cached_launcher_verified`. |
| `capture()` | `installed_identity`, inspect de app/relay, governor/scheduler/afinidad originales y `DeviceSnapshot` con SPI, generador OFF y WAV **IDLE**. El capture general permite DONE; este adapter debe exigir IDLE explícitamente. Devuelve manifiesto remoto exacto `app_sources`, `generator_off`, `wav_idle`, `receiver_closed`, `identity_verified`, `source_manifest_verified`. |
| `backup(baseline)` | Export CLI sin modificar la app; ZIP original validado contra manifiesto remoto, archive completo de cache, ELF/BIN originales y binario del mount del relay descargados y hasheados. Copia remota independiente de recuperación. Manifiesto pareado persistido bajo `respaldos/parejas/v18_preparar_<id>/`, con todos los hashes, rutas, inspect, CPU y snapshot. Devuelve `export_verified`, `source_archive_verified`, `full_cache_verified`, `firmware_elf_bin_verified`, `relay_verified`, `paired_manifest_persisted`. |
| `prepare(acceptance, baseline)` | Stage exclusivo con sólo fuentes V18 aceptadas. Compilar allí, antes de parar producción, y exigir SHA256 del firmware igual al binario aceptado. Relay ya compilado: comprobar hash aceptado y copiar a `/home/arduino/.cache/serialmonitor/usb-stream-<relay_digest>/unoq_stream`; rechazar colisión de cache existente con bytes distintos. No compilar relay ni ejecutar apt. No tocar fuentes/cache de la app activa. Devolver `candidate_identity` exacta y las cuatro comprobaciones que exige el motor. |
| `recheck(baseline, backup, prepared)` | Releer identidad, fuentes, estado, ausencia de lector y hashes de todos los respaldos/stages justo antes de mutar producción. Devuelve `baseline_unchanged`, `backups_verified`, `candidate_verified`, `no_other_reader`. |
| `quiesce(baseline)` | Abrir un único receiver, pasar a carga normal según receta probada, guardar CPU inactiva si aún falta, confirmar OFF/IDLE y cerrar el receiver. Desde su intent ya corresponde rollback ante error. |
| `stop_old_relay(baseline)` | Stop sólo por ID original verificado, conservando el container. |
| `rename_old_relay(baseline)` | Renombrar ese ID a un nombre saved único persistido antes del comando. Si el comando falla con efecto desconocido, rollback consulta por ID; no presupone que no ocurrió. |
| `stop_app()` | Detener exclusivamente la misma ruta Scope V18; sólo tras confirmar liberada la propiedad READY del relay. |
| `install_sources(acceptance, changes)` | Push sólo de las fuentes V18 aceptadas. Borrar exclusivamente `changes.remove`, lista que debe coincidir exactamente con `--remove-source`. Rechazar paths absolutos, traversal, symlinks y subárboles excluidos. Verificar manifiesto exacto después del push. |
| `install_cache(prepared)` | Apartar/preservar cache original completa y aplicar el layout del build que el ensayo privado haya probado. No inventar metadatos ni confiar en la existencia de BIN. Verificar firmware/ELF y metadata necesarios antes del arranque. |
| `start_new_app(prepared)` | Un solo arranque de la MISMA app con launcher ya demostrado. Confirmar que utiliza los bytes aceptados y que no hizo una compilación con otra identidad. |
| `start_new_relay(baseline, prepared)` | Crear sólo el container V18 nuevo, con mount al binario aceptado, y conservar el original saved. Persistir ID nuevo. Config/env/mounts/capacidades/CPU siguen una receta explícita revisada. |
| `verify_new(baseline, acceptance, prepared, 10)` | Identidades aceptadas, fuentes exactas, settings originales bajo la identidad nueva, governor/scheduler/afinidad y configuración relay esperados. Receiver continuo >=10 s, dropped/fatal cero y suficientes pares; cerrar antes de inspect final. Todos los booleanos exigidos por el motor y `seconds`. |

Los resultados del adapter deben ser JSON serializables para guardarse sin perder
evidencia. Las comprobaciones booleanas representan verificaciones efectivas;
un adapter no puede completarlas con valores constantes.

## Rollback de la misma app

El rollback privado anterior sólo volvía a arrancar una app original que no se
había modificado. No se reutiliza ese supuesto para esta actualización.

El motor invoca una sola secuencia de recuperación:

1. `stop_new_relay`: observar ID/mounts para confirmar propiedad de esta
   transacción; detener y quitar sólo ese container. `stop_app`: detener V18.
2. `restore_sources`: desde el ZIP original verificado, recuperar archivos
   reemplazados/borrados y quitar exclusivamente `changes.added`. Detectar
   archivos ajenos inesperados antes de borrar; no usar `rm -rf` sobre fuentes.
3. `restore_cache`: recuperar cache original **completa**, artefactos y metadata,
   desde la copia independiente. No sustituirla por un BIN aislado.
4. `verify_original_material`: exigir `sources_exact`, `cache_exact`,
   `firmware_exact`, `relay_exact`. Si falla, el motor no arranca app ni relay.
5. `start_original_app`: una sola vez, usando el launcher ensayado. Después,
   `restore_old_relay` recupera el container original por ID, nombre, inspect y
   mounts; no reconstruye uno aproximadamente equivalente.
6. `restore_cpu` recupera la baseline inactiva antes de reactivar el perfil
   original. `restore_snapshot(baseline, 10)` confirma ADC/generador/transporte,
   continuidad y dropped/fatal cero durante >=10 s. Un `ReceiverLifecycle` puede
   servir aquí, bajo identidad original verificada, sin mantener el socket
   abierto durante inspect u otra administración.
7. `verify_original` confirma identidad original, fuentes exactas, configuración
   original del relay y CPU activa original. Sólo entonces rollback.ok=true.

Si una etapa falla, el informe conserva el punto y el estado incierto. No se
repite la mutación, no se marca restaurado y no se inicia un firmware cuyo
material original no haya podido comprobarse. Los respaldos y el container
original se conservan también después de una instalación exitosa.

## Aceptación explícita

El archivo de aceptación tiene schema 1, version 18, `accepted: true`,
`public_rates_changed: false`, manifiestos completos `sources.app` y
`sources.relay` de las fuentes locales de producción, y tres artefactos:

```json
{
  "schema": 1,
  "version": 18,
  "accepted": true,
  "public_rates_changed": false,
  "sources": {
    "app": {"app.yaml": "SHA256_COMPLETO", "sketch/sketch.ino": "SHA256_COMPLETO"},
    "relay": {"unoq_config_stream.c": "SHA256_COMPLETO"}
  },
  "firmware": {"path": "firmware.bin", "sha256": "SHA256_COMPLETO"},
  "relay": {"path": "relay.bin", "sha256": "SHA256_COMPLETO"},
  "evidence": {
    "path": "physical_acceptance.json",
    "sha256": "SHA256_COMPLETO",
    "physical_acceptance": true,
    "restoration_verified": true
  }
}
```

El ejemplo está abreviado y contiene placeholders inválidos deliberadamente.
Se exige cada archivo real de las fuentes. Las rutas de artefactos se resuelven
respecto del receipt; su existencia no sustituye el hash ni la aceptación.
La compilación de preparación debe volver a producir el hash aceptado. Si el
candidato usaba nombre de app privada, su incorporación a fuentes de producción
debe tener manifiesto explícito y trazable; no se normalizan nombres o hashes
silenciosamente dentro de este preparador.

## Prueba que falta antes de habilitar el adapter

Después de cerrar campañas físicas activas, consultar de forma read-only
`arduino-app-cli version`, `app start --help`, inspect de app y metadata/cache.
Luego usar una app privada independiente con la misma mecánica de actualización:
respaldar, reemplazar/agregar/borrar un archivo de prueba, aplicar cache candidata,
forzar fallo después de cada fase relevante y demostrar restauración exacta
antes de su arranque original. Guardar la CLI binaria/version, launcher real,
manifiestos originales/candidatos/restaurados, ELF/BIN/relay y metadata, journal,
inspect/CPU y recuperación física de 10 s en cada caso requerido.

La habilitación futura requiere revisión del adapter y de esa evidencia;
actualmente ninguna presencia de receipt/archivo habilita producción.

Observación aportada por el coordinador el 2026-10-23: la CLI instalada ofrece
`app start --verbose`, sin flag para omitir build. En la cache de BatchArena
observó `.cache/sketch/` con `sketch.ino.bin`, `.bin-zsk.bin`, `_temp.elf`,
`_debug.elf`, `.elf-zsk.bin`, `_temp.map`, `.map`, `compile_commands.json` y
`build.options.json`; también `app-compose.yaml` y `.venv`. No se infiere de
esa lista que copiar únicamente BIN permita recuperar el mismo arranque.

### Diseño propuesto del ensayo privado de misma app

Arnés independiente implementado en
`experimentos/fs_max_v18/rehearse_same_app_restore.py`, con plan por defecto y
`--run` explícito, helper de archivos `rehearsal_archive.py` y tests puros
`test_same_app_restore.py`. Esta implementación **no lo ejecuta ni habilita
producción**. Usa BatchArena existente, sin cambiar `Hardware` ni registrar
otra app; recupera exactamente sus fuentes originales al finalizar.

1. Un único propietario Q y journal durable. Reusar `Hardware.capture`,
   `prepare` y `restart` una sola vez con receta BatchArena. Guardar la
   transacción externa de restauración de producción antes de preparar la app
   privada. El `finally` exterior siempre invoca `Hardware.restore` tras
   captura exitosa, independientemente del resultado del ensayo privado.
2. Sobre la app privada BatchArena, configurar ADC14/31250, confirmar generador
   OFF y WAV IDLE, tomar baseline privada y cerrar el receiver. Registrar
   identidad MCU/relay, inspect/CPU, manifiesto fuente remoto y metadata.
3. Antes de alterar fuentes, exportar la app privada a ZIP y descargarlo.
   Guardar además fuentes con metadata original y TAR de **toda** `.cache`,
   incluyendo `.venv`, enlaces, modos y mtimes, no sólo `.cache/sketch`.
   Descargar ELF/BIN y relay por separado y verificar hashes. La extracción
   debe estar confinada a una staging propia; validar rutas/enlaces antes de
   restaurar archivos. Guardar una copia remota independiente y una local.
4. Producir una mutación física pequeña y verificable: cambiar sólo
   `halves[1].source==scope_batch2::Source::Idle) k_sleep(K_MSEC(1));`
   por la misma línea con `K_MSEC(2)`. Exigir exactamente una coincidencia.
   Añadir `archivoextra.yml` en la raíz de la app; registrar su
   hash y path en la lista explícita de archivos nuevos. Conservar intactos
   los ancestros y las fuentes locales de BatchArena; mutar sólo una copia
   de ensayo y la app privada identificada.
5. Detener y conservar el relay privado por ID; parar/arrancar **esa misma
   app privada** con `candidate.start()`, sin `Hardware.restart` adicional:
   ese método también arrancaría la app y mezclaría el caso ensayado.
   Arrancar el mismo container relay retenido mediante un helper separado.
   Verificar manifiesto mutado y que el BIN nuevo tenga SHA256 real distinto
   del original. Si no cambia el BIN, el ensayo no es válido. Cerrar receiver
   antes de cada comando administrativo.
6. Detener relay y app privada, recuperar fuentes originales y metadata,
   quitar sólo `archivoextra.yml`, recuperar TAR completo de cache y
   comprobar manifiestos/ELF/BIN originales **antes del arranque**. No usar
   una secuencia que primero arranque y después intente corregir fuentes.
7. Arrancar una sola vez la misma app privada; arrancar su relay retenido.
   Comprobar el SHA256 de firmware original **después** de `app start`, el
   relay original y las fuentes exactas. Si la CLI vuelve a compilar y cambia
   el BIN, no está demostrada recuperación exacta aunque el ADC funcione.
   La posible recompilación y sus outputs forman parte de la evidencia.
8. Bajo identidad privada original verificada, restaurar baseline normal y
   registrar 10 s continuos, dropped/fatal cero, suficientes pares, CPU e
   inspect esperados. Mantener separado el resultado de restauración privada
   del resultado de `Hardware.restore` exterior de producción. Ambos deben
   aprobar para cerrar el ensayo.

El primer ensayo sólo demuestra la ruta completa y el comportamiento real de
la cache. Luego se necesitan fallos inyectados después de push de fuentes,
actualización de cache y arranque de app/relay para calificar el adapter de
producción. El motor ya especifica esa matriz con un backend puro; sus tests
no reemplazan las pruebas físicas.

Comandos de revisión, aún sin ejecutar en esta implementación:

```sh
python3 tools/prepare_q_v18.py
python3 -m unittest tools.test_prepare_q_v18
python3 experimentos/fs_max_v18/rehearse_same_app_restore.py
python3 -m unittest experimentos.fs_max_v18.test_same_app_restore
```

Sólo tras revisión del coordinador y cierre de cualquier campaña activa:

```sh
python3 experimentos/fs_max_v18/rehearse_same_app_restore.py --run
```
