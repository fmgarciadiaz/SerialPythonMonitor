"""Compatibility entry; implementation lives entirely in monitor.v18."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if str(root) not in sys.path: sys.path.insert(0,str(root))
from monitor.v18.q_support import prepare as implementation
if __name__ == "__main__":
    raise SystemExit(implementation.main())
else:
    sys.modules[__name__] = implementation
