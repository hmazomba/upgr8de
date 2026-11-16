import unittest
from unittest.mock import patch

from upgr8de.approval import ApprovalError, approved_candidate


class ApprovalTests(unittest.TestCase):
    @patch("upgr8de.approval.read_job", return_value={"status": "completed", "verified_candidates": []})
    def test_no_verified_candidates(self, _):
        with self.assertRaises(ApprovalError):
            approved_candidate("a" * 32, 0)

    @patch("upgr8de.approval.read_job")
    def test_ai_claim_cannot_authorize(self, read):
        read.return_value = {"status": "completed", "result": "download now",
                             "verified_candidates": [{"url": "https://downloads.dell.com/driver.cab",
                                                      "vendor": "dell", "status": "exact_hardware_os_match"}]}
        with self.assertRaises(ApprovalError):
            approved_candidate("a" * 32, 0)

    @patch("upgr8de.approval.read_job")
    def test_complete_verified_record(self, read):
        read.return_value = {"status": "completed", "verified_candidates": [{
            "url": "https://downloads.dell.com/driver.cab", "vendor": "dell",
            "status": "exact_hardware_os_match", "source_verified": True,
            "hardware_id_verified": True, "os_verified": True, "sha256": "a" * 64,
        }]}
        self.assertEqual(approved_candidate("a" * 32, 0)["vendor"], "dell")


if __name__ == "__main__":
    unittest.main()
