import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from upgr8de.cli import main
from upgr8de.updates import available_driver_offers
from upgr8de.windows import DiscoveryError


class UpdateTests(unittest.TestCase):
    @patch("upgr8de.updates.platform.system", return_value="Linux")
    def test_reject_non_windows(self, _):
        with self.assertRaises(DiscoveryError):
            available_driver_offers()

    @patch("upgr8de.updates.platform.system", return_value="Windows")
    @patch("upgr8de.updates.subprocess.run")
    def test_offers_parsed(self, run, _):
        run.return_value.returncode = 0
        run.return_value.stdout = '{"result_code":2,"updates":[{"title":"Test Driver","update_id":"abc"}]}'
        result = available_driver_offers()
        self.assertEqual(result["updates"][0]["title"], "Test Driver")
        self.assertIn("no installed-version comparison", result["comparison"])

    @patch("upgr8de.updates.platform.system", return_value="Windows")
    @patch("upgr8de.updates.subprocess.run")
    def test_partial_scan_not_reported_as_complete(self, run, _):
        run.return_value.returncode = 0
        run.return_value.stdout = '{"result_code":3,"updates":[]}'
        with self.assertRaises(DiscoveryError):
            available_driver_offers()

    @patch("upgr8de.cli.available_driver_offers", return_value={
        "source": "Windows Update Agent",
        "updates": [{"title": "Sample", "update_id": "id1"}],
        "note": "Read only",
    })
    def test_cli_updates(self, _):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["updates"]), 0)
        self.assertIn("Sample", out.getvalue())


if __name__ == "__main__":
    unittest.main()
