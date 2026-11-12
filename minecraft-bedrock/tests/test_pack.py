import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "behavior-pack"


class BehaviorPackContractTests(unittest.TestCase):
    def test_manifest_uses_stable_server_api_and_no_client_network_api(self):
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        dependencies = manifest["dependencies"]
        self.assertIn(
            {"module_name": "@minecraft/server", "version": "2.0.0"},
            dependencies,
        )
        self.assertFalse(any(item.get("module_name") == "@minecraft/server-net" for item in dependencies))
        self.assertEqual(manifest["header"]["min_engine_version"], [1, 26, 60])

    def test_pack_uuids_are_unique_and_script_entry_exists(self):
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        uuids = [manifest["header"]["uuid"]] + [module["uuid"] for module in manifest["modules"]]
        self.assertEqual(len(uuids), len(set(uuids)))
        self.assertTrue(re.fullmatch(r"[0-9a-f-]{36}", manifest["header"]["uuid"]))
        entry = PACK / manifest["modules"][1]["entry"]
        self.assertTrue(entry.is_file())

    def test_script_emits_only_identified_npc_interactions(self):
        script = (PACK / "scripts" / "main.js").read_text(encoding="utf-8")
        self.assertIn("world.afterEvents.playerInteractWithEntity.subscribe", script)
        self.assertIn("AURION_EVENT ", script)
        self.assertIn("target.nameTag", script)
        self.assertIn("PLAYER_COOLDOWN_MS", script)


if __name__ == "__main__":
    unittest.main()
