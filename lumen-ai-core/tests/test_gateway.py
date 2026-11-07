import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

import app


class NEXORAGatewayTests(unittest.TestCase):
    def test_chat_image_validator_accepts_supported_image(self):
        item = app.ChatIn(
            message="Descreva",
            image_data_url="data:image/png;base64,ZmFrZQ==",
        )
        self.assertTrue(item.image_data_url.startswith("data:image/png;base64,"))

    def test_chat_image_validator_rejects_unsupported_image(self):
        with self.assertRaises(ValidationError):
            app.ChatIn(
                message="Descreva",
                image_data_url="data:image/svg+xml;base64,ZmFrZQ==",
            )

    def test_gateway_request_schema_accepts_chat_completion(self):
        item = app.GatewayChatIn(
            model="alpha/example-model",
            messages=[{"role": "user", "content": "Olá"}],
        )
        self.assertEqual(item.model, "alpha/example-model")
        self.assertFalse(item.stream)

    def test_provider_registry_resolves_allowlisted_model(self):
        env = {
            "NEXORA_PROVIDERS": (
                '{"alpha":{"base_url":"https://provider.example/v1",'
                '"api_key_env":"TEST_PROVIDER_KEY","models":["model-a"]}}'
            ),
            "TEST_PROVIDER_KEY": "test-secret",
            "NEXORA_DEFAULT_PROVIDER": "alpha",
        }
        with patch.dict(os.environ, env, clear=False):
            provider_name, model_name, provider = app.resolve_gateway_model("alpha/model-a")
        self.assertEqual(provider_name, "alpha")
        self.assertEqual(model_name, "model-a")
        self.assertEqual(provider["api_key"], "test-secret")

    def test_provider_registry_rejects_unlisted_model(self):
        env = {
            "NEXORA_PROVIDERS": (
                '{"alpha":{"base_url":"https://provider.example/v1",'
                '"api_key_env":"TEST_PROVIDER_KEY","models":["model-a"]}}'
            ),
            "TEST_PROVIDER_KEY": "test-secret",
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(HTTPException) as caught:
                app.resolve_gateway_model("alpha/model-b")
        self.assertEqual(caught.exception.status_code, 404)

    def test_provider_registry_rejects_unimplemented_protocol(self):
        env = {
            "NEXORA_PROVIDERS": (
                '{"alpha":{"base_url":"https://provider.example/v1",'
                '"api_key_env":"TEST_PROVIDER_KEY","models":["model-a"],'
                '"protocol":"native-custom"}}'
            ),
            "TEST_PROVIDER_KEY": "test-secret",
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(HTTPException) as caught:
                app.resolve_gateway_model("alpha/model-a")
        self.assertEqual(caught.exception.status_code, 501)


if __name__ == "__main__":
    unittest.main()
