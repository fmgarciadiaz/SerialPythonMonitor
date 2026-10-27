# Arduscopio Q: instrucciones de documentación

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
