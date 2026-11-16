import os
import tempfile
import unittest
from unittest.mock import patch

from upgr8de.agent import AgentError, config, read_job, submit_background


class AgentTests(unittest.TestCase):
    @patch.dict(os.environ, {"UPGR8DE_AI_MODEL": "test-model", "UPGR8DE_AI_API_KEY": "fake", "UPGR8DE_AI_BASE_URL": "https://api.example.com/v1"})
    def test_config(self):
        self.assertEqual(config()["model"], "test-model")

    @patch.dict(os.environ, {"UPGR8DE_AI_MODEL": "test", "UPGR8DE_AI_API_KEY": "fake", "UPGR8DE_AI_BASE_URL": "http://remote.example/v1"})
    def test_http_rejected(self):
        with self.assertRaises(AgentError):
            config()

    @patch.dict(os.environ, {"UPGR8DE_AI_MODEL": "test", "UPGR8DE_AI_API_KEY": "fake", "UPGR8DE_AI_BASE_URL": "https://api.example.com/v1"})
    @patch("upgr8de.agent.subprocess.Popen")
    def test_submit_and_poll(self, popen):
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ, {"UPGR8DE_JOB_DIR": root}):
                result = submit_background({"matched": []})
                self.assertEqual(read_job(result["job_id"])["status"], "queued")
                popen.assert_called_once()

    def test_invalid_job_id(self):
        with self.assertRaises(AgentError):
            read_job("../../secret")


if __name__ == "__main__":
    unittest.main()
