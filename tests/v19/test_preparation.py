import ast
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from monitor.v19.q_support import service
from monitor.v19.q_support.prepare import load_acceptance


class PreparationTests(TestCase):
    def test_gui_preparation_uses_selected_device_and_blocks_live_capture(self):
        from PySide6.QtWidgets import QApplication
        from monitor.v19.app import SerialMonitorWindow
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

    def test_v19_receipt_is_hash_bound_and_does_not_promote_rates(self):
        accepted=load_acceptance(service.RECEIPT)
        receipt=json.loads(service.RECEIPT.read_text())
        self.assertEqual(receipt['version'],19)
        self.assertTrue(receipt['accepted'])
        self.assertFalse(receipt['public_rates_changed'])
        self.assertEqual(accepted['candidate_identity']['firmware_sha256'],
                         '37f049fa029ad62a10767c56dc586b2c3697f8d250a0b8a7396570ce8e0c7060')
        self.assertEqual(accepted['candidate_identity']['relay_sha256'],
                         '27da0bc4860401df27eef50429f2ec881bfd3b51b1893d1fe3bacb9e922f56ae')
        self.assertTrue(receipt['evidence']['physical_acceptance'])
        self.assertTrue(receipt['evidence']['restoration_verified'])
        evidence=json.loads((service.RECEIPT.parent/receipt['evidence']['path']).read_text())
        self.assertTrue(evidence['manual_gui_acceptance_pending'])

    def test_versioned_runtime_has_no_external_project_imports(self):
        root=Path(__file__).resolve().parents[2]/'monitor/v19'
        violations=[]
        for path in root.rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                names=([node.module or ''] if isinstance(node,ast.ImportFrom) else
                       [a.name for a in node.names] if isinstance(node,ast.Import) else [])
                for name in names:
                    if name.startswith(('monitor.','tools','transport','experimentos')) and not name.startswith('monitor.v19'):
                        violations.append((str(path.relative_to(root)),node.lineno,name))
        self.assertEqual(violations,[])
