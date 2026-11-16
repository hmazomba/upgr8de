import json
import unittest
from unittest.mock import patch

from upgr8de.oem import detect_system
from upgr8de.windows import DiscoveryError


class OEMTests(unittest.TestCase):
    @patch("upgr8de.oem.platform.system", return_value="Linux")
    def test_windows_required(self, _):
        with self.assertRaises(DiscoveryError):
            detect_system()

    @patch("upgr8de.oem.platform.system", return_value="Windows")
    @patch("upgr8de.oem.subprocess.run")
    def test_detects_model_without_serial(self, run, _):
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps({
            "manufacturer": "HP", "model": "ProBook 430 G8",
            "os_caption": "Windows 11", "architecture": "64-bit",
        })
        result = detect_system()
        self.assertEqual(result["model"], "ProBook 430 G8")
        self.assertNotIn("serial_number", result)
        self.assertNotIn("uuid", result)

    @patch("upgr8de.oem.platform.system", return_value="Windows")
    @patch("upgr8de.oem.subprocess.run")
    def test_bad_response_fails(self, run, _):
        run.return_value.returncode = 0
        run.return_value.stdout = "not-json"
        with self.assertRaises(DiscoveryError):
            detect_system()


if __name__ == "__main__":
    unittest.main()
