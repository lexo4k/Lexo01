import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import serve


class OwnModelServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.client = TestClient(serve.app)
        self.checkpoint = mock.patch.object(serve, "CHECKPOINT", Path(self.temp.name) / "missing.pt")
        self.checkpoint.start()
        self.token = mock.patch.object(serve, "ACCESS_TOKEN", "test-own-model-token")
        self.token.start()
        serve._model = None
        serve._load_error = None

    def tearDown(self):
        self.checkpoint.stop()
        self.token.stop()
        serve._model = None
        self.temp.cleanup()

    def test_health_does_not_claim_missing_checkpoint_is_ready(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "not_ready")
        self.assertFalse(response.json()["checkpoint_present"])
        self.assertTrue(response.json()["own_weights"])

    def test_generate_requires_authentication(self):
        response = self.client.post("/generate", json={"prompt": "NEXORA"})
        self.assertEqual(response.status_code, 401)

    def test_generate_refuses_to_fake_an_unavailable_own_model(self):
        response = self.client.post(
            "/generate",
            headers={"X-Model-Token": "test-own-model-token"},
            json={"prompt": "NEXORA"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("checkpoint", response.json()["detail"])

    def test_generate_validates_prompt(self):
        response = self.client.post(
            "/generate",
            headers={"X-Model-Token": "test-own-model-token"},
            json={"prompt": ""},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
