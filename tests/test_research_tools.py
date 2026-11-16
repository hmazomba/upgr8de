import unittest
from unittest.mock import patch

from upgr8de.research_tools import collect_oem_evidence, download_candidate


class ResearchToolsTests(unittest.TestCase):
    def test_unsupported_oem_reports_gap(self):
        result = collect_oem_evidence({"manufacturer": "Lenovo", "model": "ThinkPad"})
        self.assertFalse(result["catalogue_checked"])
        self.assertEqual(result["packages"], [])

    @patch("upgr8de.research_tools.dell_driver_packs")
    def test_dell_catalogue_evidence_is_not_device_verified(self, fetch):
        fetch.return_value = {"packages": [{
            "url": "https://downloads.dell.com/driver.cab", "release_id": "ABC"
        }]}
        result = collect_oem_evidence({"manufacturer": "Dell", "model": "Latitude 5420"})
        self.assertEqual(len(result["packages"]), 1)
        self.assertFalse(result["packages"][0]["device_match"])
        self.assertFalse(result["packages"][0]["os_match"])

    def test_ai_cannot_download_without_approval(self):
        with self.assertRaises(PermissionError):
            download_candidate({"url": "https://downloads.dell.com/driver.cab"}, ".")

    def test_unverified_candidate_cannot_download_even_with_approval(self):
        with self.assertRaises(ValueError):
            download_candidate({"status": "model_match_only"}, ".", approved=True)


if __name__ == "__main__":
    unittest.main()
