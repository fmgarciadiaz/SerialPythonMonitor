# Arduscopio Q: instrucciones de documentación

## Uso de modelos y ahorro de cuota

Preferencia acordada con el usuario: resolver cada tarea con el modelo de menor
coste disponible que pueda hacerla bien. No asumir precios ni consumo semanal
exactos; dependen del servicio. Esta distribución no exige invocar a todos.

- **Luna:** tareas simples y acotadas: textos, etiquetas, documentación factual,
  inventarios, búsquedas y cambios mecánicos con instrucciones precisas. No
  diseña concurrencia, protocolos, firmware ni recuperaciones del Q.
- **Sol:** ejecutor habitual y coordinador técnico. Implementa, diagnostica,
  ejecuta pruebas pertinentes e integra. Resuelve directamente lo rutinario;
  no crea un agente para cada paso. Es el único dueño del Q durante campañas.
- **Terra:** trabajo de código delimitado que requiera lectura de varios archivos,
  refactorización o revisión técnica independiente. Usarla cuando descargue una
  tarea concreta de Sol; no duplicar por defecto implementación y revisión.
- **Astra:** consulta breve para arquitectura difícil, hipótesis de fallos
  persistentes o decisiones con riesgo importante. Entrega un plan acotado y
  criterios de aceptación; Sol ejecuta. No usar Astra para correr campañas,
  editar rutinariamente, esperar resultados ni supervisar cada paso.

Reglas de ejecución:

1. Un coordinador y, normalmente, como máximo un delegado activo. Paralelizar
   sólo tareas independientes cuando el ahorro justifique el contexto adicional.
2. Delegar con contexto mínimo: objetivo, archivos relevantes, restricciones,
   evidencia actual y criterio de cierre. Evitar heredar todo el historial.
3. Usar esfuerzo bajo en tareas mecánicas y medio en implementación habitual;
   aumentar sólo ante una dificultad concreta. No repetir consultas a Astra
   mientras el plan vigente siga siendo aplicable.
4. Antes de escalar, reunir un caso reproducible y resumir qué se probó y qué
   falta. Una consulta especializada debe responder una pregunta específica.
5. Ejecutar pruebas focalizadas; ampliar sólo por riesgo, cambios nuevos o
   fallos. Reutilizar evidencia válida y no repetir campañas sin hipótesis.
6. Evitar sondeos y mensajes repetidos sin información nueva. Agrupar lecturas
   independientes, limitar salidas y guardar una continuidad breve y vigente.
7. No afirmar que una prueba local demuestra estabilidad física o FPS visibles.
   Mantener respaldos, integridad y restauración del Q aunque se ahorre cuota.
8. Si no se puede seleccionar o delegar a un modelo, indicarlo: no afirmar que
   intervino. Esta pauta no cambia automáticamente el modelo del chat actual.

El nombre visible del programa es **Arduscopio Q**. Conservar los identificadores
técnicos de despliegue y las rutas de Scope V18; no renombrar la pareja aceptada
como parte de cambios de marca.

El README raíz es la landing de presentación del proyecto. Conservar badges, imágenes de cada función del monitor, explicación de los módulos, capacidades, arquitectura y puesta en marcha. Actualizar versiones y cifras sin reemplazar esa presentación por un índice técnico ni eliminar sus imágenes.

El estado de trabajo, pendientes, campañas y diagnósticos se documenta en `docs/`, el plan y la continuidad, y se enlaza desde la landing. Al ordenar archivos, preservar esta distinción y las rutas de las imágenes.

## Parejas de versiones

V17 está congelada con su monitor, firmware y relay del Q. No modificar
`monitor/v17/` ni `arduino/v17/`, ni sobrescribir la app `Scope V17` del Q.
El desarrollo y las nuevas incorporaciones van en `monitor/v18/` y
`arduino/v18/`, con app independiente `Scope V18`. Conservar los respaldos
pareados y sus manifiestos en `respaldos/parejas/`. Las campañas privadas no
habilitan tasas públicas sin aceptación física y restauración verificadas.
