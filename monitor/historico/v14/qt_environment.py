"""Prepare Qt6 plugins on macOS before QApplication is created."""
import os
from pathlib import Path
import stat
import sys


def prepare_platform_plugins():
    """Remove only Finder's hidden flag, which prevents Qt plugin discovery.

    Some local macOS environments reapply UF_HIDDEN to installed libraries.
    Qt's default directory scan then skips valid platform plugins. Permissions,
    signatures, other flags and the platform selection remain untouched.
    """
    if sys.platform != 'darwin':
        return
    from PyQt6 import QtCore
    folder = Path(QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.PluginsPath)) / 'platforms'
    for plugin in (folder.parent, *folder.parent.rglob('*')):
        flags = plugin.stat().st_flags
        if flags & stat.UF_HIDDEN:
            try:
                os.chflags(plugin, flags & ~stat.UF_HIDDEN)
            except OSError as exc:
                raise RuntimeError(f'Qt6 no puede descubrir el plugin oculto {plugin}. '
                                   'Quitar su marca Finder hidden antes de iniciar V14.') from exc
