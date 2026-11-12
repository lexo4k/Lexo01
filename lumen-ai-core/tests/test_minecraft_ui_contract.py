from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "index.html"
ANDROID = ROOT.parent / "lumen-android" / "src" / "main" / "assets" / "index.html"


class MinecraftUiContractTests(unittest.TestCase):
    def test_android_and_core_interfaces_expose_real_pairing_bridge(self):
        web = WEB.read_text(encoding="utf-8")
        android = ANDROID.read_text(encoding="utf-8")
        self.assertEqual(web, android)
        for expected in (
            'id="minecraftRelayUrl"',
            'id="minecraftConnect"',
            'id="minecraftPairingCode"',
            'id="minecraftStop"',
            "onMinecraftPairingStarted",
            "startMinecraftAssistant",
            "getMinecraftRelayUrl",
        ):
            self.assertIn(expected, web)

    def test_ui_states_bedrock_server_requirement(self):
        web = WEB.read_text(encoding="utf-8")
        self.assertIn("Bedrock Dedicated Server", web)
        self.assertIn("Realms", web)
        self.assertIn("modelo GGUF", web)


if __name__ == "__main__":
    unittest.main()
