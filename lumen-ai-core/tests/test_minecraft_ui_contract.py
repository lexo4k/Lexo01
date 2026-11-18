from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "index.html"
ANDROID = ROOT.parent / "lumen-android" / "src" / "main" / "assets" / "index.html"
MAIN_ACTIVITY = ROOT.parent / "lumen-android" / "src" / "main" / "java" / "com" / "lexo" / "lumen" / "MainActivity.kt"
RELAY_CLIENT = ROOT.parent / "lumen-android" / "src" / "main" / "java" / "com" / "lexo" / "lumen" / "MinecraftRelayClient.kt"
BRIDGE_SERVICE = ROOT.parent / "lumen-android" / "src" / "main" / "java" / "com" / "lexo" / "lumen" / "MinecraftBridgeService.kt"
ANDROID_MANIFEST = ROOT.parent / "lumen-android" / "src" / "main" / "AndroidManifest.xml"


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

    def test_android_bridge_keeps_per_npc_memory_and_retryable_local_replies(self):
        activity = MAIN_ACTIVITY.read_text(encoding="utf-8")
        relay_client = RELAY_CLIENT.read_text(encoding="utf-8")
        self.assertIn("npcId: String", relay_client)
        self.assertIn("npcType: String", relay_client)
        self.assertIn("minecraftNpcMemoryKey", activity)
        self.assertIn("aurion_minecraft_memory", activity)
        self.assertIn("aurion_minecraft_outbox", activity)
        self.assertIn("savePendingMinecraftReply(event, answer)", activity)
        self.assertIn("loadPendingMinecraftReply(event)", activity)
        self.assertIn("event.npcId", activity)

    def test_ui_states_bedrock_server_requirement(self):
        web = WEB.read_text(encoding="utf-8")
        self.assertIn("Bedrock Dedicated Server", web)
        self.assertIn("Realms", web)
        self.assertIn("modelo GGUF", web)

    def test_minecraft_bridge_uses_foreground_service_when_game_takes_focus(self):
        activity = MAIN_ACTIVITY.read_text(encoding="utf-8")
        service = BRIDGE_SERVICE.read_text(encoding="utf-8")
        manifest = ANDROID_MANIFEST.read_text(encoding="utf-8")
        self.assertIn("startForegroundService(intent)", activity)
        self.assertIn("minecraft_service_expired", activity)
        pause_block = activity.split("override fun onPause()", 1)[1].split("override fun onStop()", 1)[0]
        self.assertNotIn("pauseMinecraftAssistant()", pause_block)
        self.assertIn("startForeground(", service)
        self.assertIn("override fun onTimeout(startId: Int, fgsType: Int)", service)
        self.assertIn('android:foregroundServiceType="dataSync"', manifest)
        self.assertIn("FOREGROUND_SERVICE_DATA_SYNC", manifest)


if __name__ == "__main__":
    unittest.main()
