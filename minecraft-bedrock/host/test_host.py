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
            "npc_id": "entity-7f31",
            "npc_type": "minecraft:villager",
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
                "event_type": "teleport",
                "player": "Player",
                "npc": "Villager",
            })

    def test_accepts_real_player_chat_event_from_bedrock_form(self):
        event = {
            "event_id": "aurion-chat-001-a1b2c3",
            "event_type": "chat",
            "player": "Player One",
            "npc": "Guia",
            "npc_id": "entity-7f31",
            "npc_type": "minecraft:npc",
            "message": "Onde encontro a vila?",
            "world_id": "aurion-bds-world",
        }
        self.assertEqual(host.validate_game_event(event), event)

    def test_tellraw_escapes_untrusted_dialogue_as_json(self):
        command = host.build_tellraw_command("Player One", "Guia", 'Olá "viajante"\\nBem-vindo!')
        self.assertTrue(command.startswith('tellraw @a[name="Player One"] '))
        payload_text = command.split("] ", 1)[1]
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

    def test_bds_script_console_logging_is_enabled_and_original_config_is_backed_up(self):
        with tempfile.TemporaryDirectory() as directory:
            server_dir = Path(directory)
            properties = server_dir / "server.properties"
            original = (
                "# keep comments and unrelated settings\r\n"
                "server-name=World One\r\n"
                "content-log-console-output-enabled=false\r\n"
                "content-log-level=error\r\n"
                "online-mode=true\r\n"
            )
            properties.write_bytes(original.encode("utf-8"))

            backup = host.configure_script_console_logging(server_dir)

            self.assertIsNotNone(backup)
            self.assertEqual(backup.read_bytes(), original.encode("utf-8"))
            updated = properties.read_text(encoding="utf-8")
            self.assertIn("# keep comments and unrelated settings", updated)
            self.assertIn("server-name=World One", updated)
            self.assertIn("content-log-console-output-enabled=true", updated)
            self.assertIn("content-log-level=warning", updated)
            self.assertIn("online-mode=true", updated)
            self.assertNotIn("content-log-console-output-enabled=false", updated)
            self.assertNotIn("content-log-level=error", updated)

    def test_bds_script_console_logging_configuration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            server_dir = Path(directory)
            properties = server_dir / "server.properties"
            configured = (
                "server-name=World One\n"
                "content-log-console-output-enabled=true\n"
                "content-log-level=warning\n"
            )
            properties.write_text(configured, encoding="utf-8")

            self.assertIsNone(host.configure_script_console_logging(server_dir))
            self.assertEqual(properties.read_text(encoding="utf-8"), configured)
            self.assertEqual(list(server_dir.glob("server.properties.aurion-backup-*")), [])

    def test_bds_script_console_logging_requires_server_properties(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                host.configure_script_console_logging(Path(directory))

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
