"""Prepare Qt6 plugins on macOS before QApplication is created."""
import os
from pathlib import Path
import stat
import sys
_prepared=False


def prepare_platform_plugins():
    """Remove only Finder's hidden flag, which prevents Qt plugin discovery.

    Some local macOS environments reapply UF_HIDDEN to installed libraries.
    Qt's default directory scan then skips valid platform plugins. Permissions,
    signatures, other flags and the platform selection remain untouched.
    """
    global _prepared
    if _prepared or sys.platform != 'darwin':
        return
    from PySide6 import QtCore
    if QtCore.QLocale().language()==QtCore.QLocale.Language.C:
        # This PySide macOS build reports C under LANG=C.UTF-8, whereas the
        # PyQt build reads the user's AppleLocale. Preserve that same setting.
        import subprocess
        try:
            result=subprocess.run(['/usr/bin/defaults','read','-g','AppleLocale'],
                                  capture_output=True,text=True,timeout=2)
            if result.returncode==0:
                locale=QtCore.QLocale(result.stdout.strip())
                if locale.language()!=QtCore.QLocale.Language.C:QtCore.QLocale.setDefault(locale)
        except (OSError,subprocess.TimeoutExpired):
            pass  # Keep Qt's locale if the OS preference cannot be read.
    folder = Path(QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.PluginsPath))
    # Only plugin families used by the widget application. Do this once per
    # process; imports of Bode/spectrum must not rescan the entire Qt install.
    paths=[folder]
    for name in ('platforms','imageformats','iconengines','styles'):
        child=folder/name
        if child.is_dir():paths.extend((child,*child.iterdir()))
    for plugin in paths:
        flags = plugin.stat().st_flags
        if flags & stat.UF_HIDDEN:
            try:
                os.chflags(plugin, flags & ~stat.UF_HIDDEN)
            except OSError as exc:
                raise RuntimeError(f'Qt6 no puede descubrir el plugin oculto {plugin}. '
                                   'Quitar su marca Finder hidden antes de iniciar V19.') from exc
    _prepared=True
