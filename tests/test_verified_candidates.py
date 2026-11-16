import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from upgr8de.verified_candidates import verified_catalogue_candidates, VerificationError

class VerifiedCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "catalogue.json"
        self.pkg = {"vendor":"dell","model":"Latitude 5420","hardware_id":"PCI\\VEN_1234&DEV_5678","version":"2.0.0","os":"Windows 11","architecture":"64-bit","url":"https://downloads.dell.com/driver.cab","sha256":"a"*64}
        self.devices = [{"name":"Test","hardware_ids":["PCI\\VEN_1234&DEV_5678"],"driver_version":"1.0.0"}]
        self.system = {"manufacturer":"Dell","model":"Latitude 5420","os_caption":"Windows 11","architecture":"64-bit"}

    def tearDown(self):
        self.tmp.cleanup()

    def run_match(self):
        self.path.write_text(json.dumps({"schema_version":1,"packages":[self.pkg]}))
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        return verified_catalogue_candidates(str(self.path),digest,self.devices,self.system)

    def test_match(self):
        self.assertEqual(len(self.run_match()),1)

    def test_hardware_mismatch(self):
        self.devices[0]["hardware_ids"] = ["OTHER"]
        self.assertEqual(self.run_match(),[])

    def test_os_mismatch(self):
        self.system["os_caption"] = "Windows 10"
        self.assertEqual(self.run_match(),[])

    def test_vendor_mismatch(self):
        self.system["manufacturer"] = "HP"
        self.assertEqual(self.run_match(),[])

    def test_older_version(self):
        self.devices[0]["driver_version"] = "3.0.0"
        self.assertEqual(self.run_match(),[])

    def test_bad_digest(self):
        self.path.write_text(json.dumps({"schema_version":1,"packages":[self.pkg]}))
        with self.assertRaises(VerificationError):
            verified_catalogue_candidates(str(self.path),"0"*64,self.devices,self.system)
