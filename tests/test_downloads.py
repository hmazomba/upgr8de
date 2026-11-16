import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from upgr8de.downloads import DownloadError, download_package, validate_source


class FakeResponse:
    headers = {"Content-Length": "6"}

    def __init__(self):
        self.data = [b"driver", b""]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _):
        return self.data.pop(0)


class DownloadsTests(unittest.TestCase):
    def test_four_vendor_hosts(self):
        urls = [
            ("dell", "https://downloads.dell.com/FOLDER/driver.cab"),
            ("hp", "https://ftp.hp.com/pub/driver.exe"),
            ("lenovo", "https://download.lenovo.com/driver.zip"),
            ("asus", "https://dlcdnets.asus.com/pub/driver.exe"),
        ]
        for vendor, url in urls:
            self.assertTrue(validate_source(url, vendor))

    def test_reject_non_oem(self):
        with self.assertRaises(DownloadError):
            validate_source("https://evil.example/driver.exe", "dell")

    def test_reject_credentials_and_redirect_hosts(self):
        with self.assertRaises(DownloadError):
            validate_source("https://downloads.dell.com@evil.example/file.exe", "dell")
        with self.assertRaises(DownloadError):
            validate_source("http://downloads.dell.com/driver.exe", "dell")

    @patch("upgr8de.downloads.urllib.request.build_opener")
    def test_download_hash_verified(self, opener):
        opener.return_value.open.return_value = FakeResponse()
        with tempfile.TemporaryDirectory() as directory:
            expected = hashlib.sha256(b"driver").hexdigest()
            result = download_package("https://downloads.dell.com/driver.cab", "dell", directory, sha256=expected)
            self.assertTrue(result["hash_verified"])
            self.assertEqual(Path(result["path"]).read_bytes(), b"driver")

    @patch("upgr8de.downloads.urllib.request.build_opener")
    def test_hash_mismatch_no_output(self, opener):
        opener.return_value.open.return_value = FakeResponse()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(DownloadError):
                download_package("https://downloads.dell.com/driver.cab", "dell", directory, sha256="0" * 64)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
