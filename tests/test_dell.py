import unittest
from unittest.mock import patch

from upgr8de.dell import parse_catalogue, dell_driver_packs
from upgr8de.windows import DiscoveryError


class DellTests(unittest.TestCase):
    def test_model_match(self):
        xml = b'<Catalog><DriverPackage path="FOLDER/driver.cab"><SupportedSystems><Brand><Model name="Latitude 5420"/></Brand></SupportedSystems></DriverPackage></Catalog>'
        results = parse_catalogue(xml, "Latitude 5420")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://downloads.dell.com/FOLDER/driver.cab")

    def test_other_model_not_matched(self):
        xml = b'<Catalog><DriverPackage path="driver.cab"><Model name="Latitude 5420"/></DriverPackage></Catalog>'
        self.assertEqual(parse_catalogue(xml, "Latitude 5430"), [])

    def test_traversal_rejected(self):
        xml = b'<Catalog><DriverPackage path="../driver.cab"><Model name="Latitude 5420"/></DriverPackage></Catalog>'
        self.assertEqual(parse_catalogue(xml, "Latitude 5420"), [])

    def test_dtd_rejected(self):
        with self.assertRaises(DiscoveryError):
            parse_catalogue(b'<!DOCTYPE Catalog><Catalog/>', "Test")

    @patch("upgr8de.dell.platform.system", return_value="Windows")
    def test_non_dell_rejected(self, _):
        with self.assertRaises(DiscoveryError):
            dell_driver_packs("HP", "ProBook")


if __name__ == "__main__":
    unittest.main()
