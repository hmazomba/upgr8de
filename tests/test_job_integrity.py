import tempfile
import unittest
from unittest.mock import patch

from upgr8de.job_integrity import seal, verify


class JobIntegrityTests(unittest.TestCase):
    def test_seal_and_detect_candidate_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("upgr8de.job_integrity.job_root", return_value=__import__("pathlib").Path(directory)):
                job = {"id": "job1", "verified_candidates": [{"sha256": "a" * 64}],
                       "catalogue_sha256": "b" * 64}
                seal(job)
                self.assertTrue(verify(job))
                job["verified_candidates"][0]["sha256"] = "c" * 64
                self.assertFalse(verify(job))

    def test_missing_seal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("upgr8de.job_integrity.job_root", return_value=__import__("pathlib").Path(directory)):
                self.assertFalse(verify({"id": "job2", "verified_candidates": []}))
