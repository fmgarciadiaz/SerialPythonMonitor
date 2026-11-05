import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from PySide6 import QtCore
from monitor.v19 import qt_environment


class QtEnvironmentTests(unittest.TestCase):
    def test_plugin_repair_is_once_per_process_and_does_not_walk_unrelated_plugins(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('platforms','imageformats','unused'):
                (root/name).mkdir();(root/name/'plugin.dylib').touch()
            old=qt_environment._prepared
            try:
                qt_environment._prepared=False
                with patch.object(qt_environment.sys,'platform','darwin'), \
                     patch.object(QtCore.QLibraryInfo,'path',return_value=directory) as location, \
                     patch.object(Path,'rglob',side_effect=AssertionError('global scan')), \
                     patch.object(qt_environment.os,'chflags'):
                    qt_environment.prepare_platform_plugins()
                    qt_environment.prepare_platform_plugins()
                    self.assertEqual(location.call_count,1)
            finally:qt_environment._prepared=old
