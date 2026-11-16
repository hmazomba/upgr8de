import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from upgr8de.catalogue import CatalogueError, candidates, load_catalogue, verify_file


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = {
            "vendor": "Example OEM", "model": "Model X",
            "hardware_id": r"PCI\VEN_8086&DEV_1234", "version": "2.0",
            "os": "Windows 11", "architecture": "x64",
            "url": "https://example.com/driver.zip", "sha256": "a" * 64,
        }

    def test_valid_catalogue(self):
        path = self.root / "catalogue.json"
        path.write_text(json.dumps({"schema_version": 1, "packages": [self.package]}))
        self.assertEqual(len(load_catalogue(str(path))), 1)

    def test_reject_http(self):
        path = self.root / "catalogue.json"
        entry = dict(self.package, url="http://example.com/driver.zip")
        path.write_text(json.dumps({"schema_version": 1, "packages": [entry]}))
        with self.assertRaises(CatalogueError):
            load_catalogue(str(path))

    def test_exact_model_os_arch_and_id(self):
        devices = [{"name": "GPU", "hardware_ids": [self.package["hardware_id"]], "driver_version": "1.0"}]
        found = candidates(devices, [self.package], model="Model X", os_name="Windows 11", architecture="x64")
        self.assertEqual(found[0]["comparison"], "newer")
        self.assertEqual(candidates(devices, [self.package], model="Model Y", os_name="Windows 11", architecture="x64"), [])

    def test_local_hash(self):
        path = self.root / "driver.bin"
        path.write_bytes(b"driver data")
        digest = hashlib.sha256(b"driver data").hexdigest()
        self.assertTrue(verify_file(str(path), digest)["matches"])
        self.assertFalse(verify_file(str(path), "0" * 64)["matches"])


if __name__ == "__main__":
    unittest.main()
