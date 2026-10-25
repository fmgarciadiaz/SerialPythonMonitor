import ast
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from monitor.v18.q_support import service
from monitor.v18.q_support.prepare import load_acceptance


class PreparationTests(TestCase):
    def test_gui_preparation_uses_selected_device_and_blocks_live_capture(self):
        from PyQt6.QtWidgets import QApplication
        from monitor.v18.app import SerialMonitorWindow
        app=QApplication.instance() or QApplication([])
        window=SerialMonitorWindow()
        try:
            self.assertTrue(window.prepare_q_button.isEnabled())
            window.port_combo.addItem('Q elegido','chosen-q')
            window.port_combo.setCurrentIndex(window.port_combo.count()-1)
            with patch.object(window,'_begin_q_preparation') as begin:
                window.prepare_q()
                begin.assert_called_once_with('chosen-q')
                window.serial_worker=Mock()
                window.prepare_q()
                self.assertEqual(begin.call_count,1)
                window.serial_worker=None
        finally:
            window.close()

    def test_accepted_pair_verifies_without_redeploying(self):
        import tempfile
        acceptance=load_acceptance(service.RECEIPT)
        identity=dict(board_serial='1060031107',app='scope-v18-main-1',
                      **acceptance['candidate_identity'])
        backend=Mock()
        from contextlib import nullcontext
        backend.owner.side_effect=nullcontext
        backend.capture.return_value={'app_sources':acceptance['sources']['app']}
        backend._recover.return_value=dict(snapshot_equal=True,continuous=True,integrity_ok=True,seconds=10)
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(service,'ProductionBackend',return_value=backend), \
             patch.object(service,'installed_identity',return_value=identity), \
             patch.object(service,'execute') as deploy:
            result=service.prepare('1060031107',Path(folder)/'report.json')
        self.assertTrue(result['ok'])
        self.assertEqual(result['action'],'verified')
        deploy.assert_not_called()
        backend._recover.assert_called_once_with(identity,10)

    def test_versioned_runtime_has_no_external_project_imports(self):
        root=Path(__file__).resolve().parents[2]/'monitor/v18'
        violations=[]
        for path in root.rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                names=([node.module or ''] if isinstance(node,ast.ImportFrom) else
                       [a.name for a in node.names] if isinstance(node,ast.Import) else [])
                for name in names:
                    if name.startswith(('monitor.','tools','transport','experimentos')) and not name.startswith('monitor.v18'):
                        violations.append((str(path.relative_to(root)),node.lineno,name))
        self.assertEqual(violations,[])
