import unittest

from upgr8de.matching import compare_versions, match_offers


class MatchingTests(unittest.TestCase):
    def test_numeric_versions(self):
        self.assertEqual(compare_versions("31.0.15.100", "31.0.15.200"), "newer")
        self.assertEqual(compare_versions("2.1", "2.1.0"), "same")
        self.assertEqual(compare_versions("2.2", "2.1"), "older")

    def test_non_numeric_versions_unknown(self):
        self.assertEqual(compare_versions("1.0-beta", "1.1"), "unknown")
        self.assertEqual(compare_versions(None, "1.1"), "unknown")

    def test_exact_match_only(self):
        devices = [{"name": "GPU", "hardware_ids": [r"PCI\VEN_10DE&DEV_1234"], "driver_version": "1.2"}]
        offers = [
            {"driver_hardware_id": r"PCI\VEN_10DE&DEV_1234", "driver_version": "1.3"},
            {"driver_hardware_id": r"PCI\VEN_10DE&DEV_123", "driver_version": "1.4"},
        ]
        result = match_offers(devices, offers)
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(result["matched"][0]["version_comparison"], "newer")
        self.assertEqual(len(result["unmatched"]), 1)

    def test_missing_id_unmatched(self):
        result = match_offers([], [{"title": "Driver without ID"}])
        self.assertEqual(result["unmatched"][0]["reason"], "missing_hardware_id")

    def test_ambiguous_match_not_assigned(self):
        devices = [
            {"name": "A", "hardware_ids": ["USB\\VID_0001&PID_0002"]},
            {"name": "B", "hardware_ids": ["USB\\VID_0001&PID_0002"]},
        ]
        result = match_offers(devices, [{"driver_hardware_id": "USB\\VID_0001&PID_0002"}])
        self.assertEqual(len(result["matched"]), 0)
        self.assertEqual(result["unmatched"][0]["reason"], "ambiguous_hardware_id")


if __name__ == "__main__":
    unittest.main()
