#!/bin/sh
# Arduscopio Q host; uses the independent Scope V20 identity (v20Gemini).
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON="/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python"

if [ ! -x "$PYTHON" ]; then
  printf '%s\n' "No encuentro el Python 3.13 configurado para este proyecto: $PYTHON" >&2
  exit 127
fi

cd "$ROOT"
export PYQTGRAPH_QT_LIB=PySide6
exec "$PYTHON" -m monitor.v20 --gui "$@"

