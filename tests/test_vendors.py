import unittest

from upgr8de.vendors import parse_hardware_id, support_candidates


class VendorTests(unittest.TestCase):
    def test_pci_hardware_id(self):
        self.assertEqual(parse_hardware_id(r"PCI\VEN_8086&DEV_9A49&SUBSYS_1234"), {
            "bus": "PCI", "vendor_id": "8086", "device_id": "9A49",
        })

    def test_usb_hardware_id(self):
        parsed = parse_hardware_id(r"USB\VID_046D&PID_C534")
        self.assertEqual(parsed["vendor_id"], "046D")
        self.assertEqual(parsed["device_id"], "C534")

    def test_invalid_id_not_guessed(self):
        self.assertEqual(parse_hardware_id("PCI\\VEN_123&DEV_9999")["bus"], "unknown")

    def test_official_portal_not_claimed_as_update(self):
        result = support_candidates({
            "name": "Graphics adapter",
            "hardware_id": r"PCI\VEN_10DE&DEV_1C82",
            "driver_version": "1.0",
        }, oem="Dell Inc.")
        self.assertEqual(result["update_status"], "not_checked")
        self.assertIsNone(result["verified_package"])
        self.assertEqual(result["sources"][0]["role"], "computer_oem")
        self.assertEqual(result["sources"][1]["name"], "NVIDIA")

    def test_unknown_vendor_returns_no_download(self):
        result = support_candidates({"name": "Unknown", "hardware_id": r"PCI\VEN_FFFF&DEV_0001"})
        self.assertEqual(result["sources"], [])


if __name__ == "__main__":
    unittest.main()
