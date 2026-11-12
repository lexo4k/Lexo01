import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aurion_bds_host as host


class HostBridgeTests(unittest.TestCase):
    def test_extracts_real_interaction_marker_from_prefixed_bds_log(self):
        event = {
            "event_id": "aurion-mn0abc-1-x7y8z9",
            "event_type": "interaction",
            "player": "Player One",
            "npc": "Aldeão da Vila",
            "message": "",
            "world_id": "aurion-bds-world",
        }
        line = "[2026-11-12 12:00:00 INFO] [Script Engine] " + host.EVENT_MARKER + json.dumps(event, ensure_ascii=False)
        self.assertEqual(host.extract_event(line), event)

    def test_ignores_lines_without_marker(self):
        self.assertIsNone(host.extract_event("[INFO] Server started"))

    def test_rejects_malformed_or_unsupported_events(self):
        with self.assertRaises(ValueError):
            host.extract_event("[INFO] " + host.EVENT_MARKER + "{broken")
        with self.assertRaises(ValueError):
            host.validate_game_event({
                "event_id": "aurion-invalid-01",
                "event_type": "chat",
                "player": "Player",
                "npc": "Villager",
            })

    def test_tellraw_escapes_untrusted_dialogue_as_json(self):
        command = host.build_tellraw_command("Player One", "Guia", 'Olá "viajante"\\nBem-vindo!')
        self.assertTrue(command.startswith('tellraw @a[name="Player One"] '))
        payload_text = command.split(" ", 2)[2]
        payload = json.loads(payload_text)
        self.assertEqual(payload["rawtext"][0]["text"], '§bGuia§r §7»§r Olá "viajante"\\nBem-vindo!')
        self.assertNotIn("\n", command)

    def test_relay_requires_https_and_rejects_query_strings(self):
        self.assertEqual(host.normalize_relay_url("https://relay.example/"), "https://relay.example")
        with self.assertRaises(ValueError):
            host.normalize_relay_url("http://relay.example")
        with self.assertRaises(ValueError):
            host.normalize_relay_url("https://relay.example?token=secret")

    def test_credentials_are_written_privately_and_bound_to_relay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials.json"
            host.save_credentials(path, "https://relay.example/", "session-1", "s" * 48)
            loaded = host.load_credentials(path, "https://relay.example")
            self.assertEqual(loaded["session_id"], "session-1")
            self.assertEqual(loaded["server_token"], "s" * 48)
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                host.load_credentials(path, "https://other.example")

    def test_claim_pairing_sends_code_without_exposing_server_token(self):
        response = {"session_id": "session-2", "server_token": "t" * 48}
        with patch.object(host, "request_json", return_value=response) as request:
            result = host.claim_pairing("https://relay.example", "12345678")
        self.assertEqual(result["session_id"], "session-2")
        self.assertEqual(result["server_token"], "t" * 48)
        request.assert_called_once_with(
            "https://relay.example", "/v1/pair/claim", method="POST",
            payload={"pairing_code": "12345678"},
        )
        with self.assertRaises(ValueError):
            host.claim_pairing("https://relay.example", "1234")


if __name__ == "__main__":
    unittest.main()
