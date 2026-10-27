# Arduscopio Q · pareja Arduino UNO Q

La pareja actual es **[Scope V18](v18/README.md)**: MCU STM32 y relay Linux.
Preparar Q se ejecuta desde el monitor V18; Conectar usa lo instalado.

```sh
python tools/unoq.py status --version v18
python -m monitor.v18.q_support.service --serial SERIAL --report diagnosticos/preparar_v18.json
```

El preparador verifica la instalación aceptada o actualiza una pareja existente
con backup y rollback. No selecciona firmware de otra versión. V17 permanece
congelada y detenida; V16 y anteriores están en `historico/`.

[Guía actual](../docs/GUIA_V18.md) · [Arquitectura](../docs/ARQUITECTURA_V18.md) ·
[Histórico](historico/README.md) · [Catálogo](apps_catalogo.json).
