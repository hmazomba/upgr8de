import json
import unittest
from unittest.mock import patch

from upgr8de.hp import hp_softpaqs
from upgr8de.windows import DiscoveryError


class HPTests(unittest.TestCase):
    @patch("upgr8de.hp.platform.system", return_value="Linux")
    def test_windows_only(self, _):
        with self.assertRaises(DiscoveryError):
            hp_softpaqs("HP")

    @patch("upgr8de.hp.platform.system", return_value="Windows")
    def test_refuse_non_hp(self, _):
        with self.assertRaises(DiscoveryError):
            hp_softpaqs("Lenovo")

    @patch("upgr8de.hp.platform.system", return_value="Windows")
    @patch("upgr8de.hp.subprocess.run")
    def test_parse_metadata(self, run, _):
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps({"packages": [{"id": "sp123", "name": "Test Driver"}]})
        result = hp_softpaqs("HP")
        self.assertEqual(result["packages"][0]["id"], "sp123")
        self.assertFalse(result["verified_for_device"])

    @patch("upgr8de.hp.platform.system", return_value="Windows")
    @patch("upgr8de.hp.subprocess.run")
    def test_failed_catalogue_not_empty_success(self, run, _):
        run.return_value.returncode = 1
        run.return_value.stderr = "HP CMSL is not installed"
        with self.assertRaises(DiscoveryError):
            hp_softpaqs("HP")


if __name__ == "__main__":
    unittest.main()
