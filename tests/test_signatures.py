import json
import unittest
from unittest.mock import patch

from upgr8de.signatures import inspect_signature
from upgr8de.windows import DiscoveryError


class SignatureTests(unittest.TestCase):
    @patch("upgr8de.signatures.platform.system", return_value="Linux")
    def test_requires_windows(self, _):
        with self.assertRaises(DiscoveryError):
            inspect_signature("driver.exe")

    @patch("upgr8de.signatures.platform.system", return_value="Windows")
    @patch("upgr8de.signatures.Path")
    @patch("upgr8de.signatures.subprocess.run")
    def test_valid_signature_not_oem_approval(self, run, path, _):
        path.return_value.resolve.return_value.is_file.return_value = True
        path.return_value.resolve.return_value.__str__.return_value = "C:\\driver.exe"
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps({"status": "Valid", "signer_subject": "CN=Example"})
        result = inspect_signature("driver.exe")
        self.assertTrue(result["signature_valid"])
        self.assertEqual(result["publisher_authorized"], "not_checked")

    @patch("upgr8de.signatures.platform.system", return_value="Windows")
    @patch("upgr8de.signatures.Path")
    @patch("upgr8de.signatures.subprocess.run")
    def test_unsigned_is_not_valid(self, run, path, _):
        path.return_value.resolve.return_value.is_file.return_value = True
        run.return_value.returncode = 0
        run.return_value.stdout = '{"status":"NotSigned"}'
        self.assertFalse(inspect_signature("driver.exe")["signature_valid"])


if __name__ == "__main__":
    unittest.main()
