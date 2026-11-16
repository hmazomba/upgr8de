import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from upgr8de.cli import main
from upgr8de.windows import _as_list


class CLITests(unittest.TestCase):
    def test_empty_driver_list(self):
        self.assertEqual(_as_list(None), [])
        self.assertEqual(_as_list({'DeviceID': 'x'}), [{'DeviceID': 'x'}])

    def test_missing_only_code_28(self):
        records = [
            {'name': 'Missing', 'hardware_id': 'USB\\X', 'missing_driver': True, 'driver_version': None, 'problem_code': 28},
            {'name': 'Broken', 'hardware_id': 'USB\\Y', 'missing_driver': False, 'driver_version': None, 'problem_code': 10},
        ]
        out = io.StringIO()
        with patch('upgr8de.cli.discover', return_value=records), redirect_stdout(out):
            code = main(['missing'])
        self.assertEqual(code, 0)
        self.assertIn('Missing', out.getvalue())
        self.assertNotIn('Broken', out.getvalue())

    def test_scan_lists_devices(self):
        with patch('upgr8de.cli.discover', return_value=[]), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['scan']), 0)


if __name__ == '__main__':
    unittest.main()
