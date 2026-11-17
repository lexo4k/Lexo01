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
        self.assertIn(
            {"module_name": "@minecraft/server-ui", "version": "2.0.0"},
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

    def test_npc_identity_uses_entity_dynamic_properties(self):
        script = (PACK / "scripts" / "main.js").read_text(encoding="utf-8")
        self.assertIn('const NPC_ID_PROPERTY = "aurion:npc_identity"', script)
        self.assertIn("target.getDynamicProperty(NPC_ID_PROPERTY)", script)
        self.assertIn("target.setDynamicProperty(NPC_ID_PROPERTY, created)", script)
        self.assertIn("const npcId = stableNpcIdentity(target)", script)
        # If the entity runtime does not support persistence, the pack labels
        # the fallback as temporary instead of pretending it survives reloads.
        self.assertIn('return "runtime-" + runtimeId', script)

    def test_script_collects_typed_chat_for_identified_npcs(self):
        script = (PACK / "scripts" / "main.js").read_text(encoding="utf-8")
        self.assertIn("world.afterEvents.playerInteractWithEntity.subscribe", script)
        self.assertIn("ModalFormData", script)
        self.assertIn(".textField(\"Sua mensagem\"", script)
        self.assertIn('event_type: "chat"', script)
        self.assertIn("AURION_EVENT ", script)
        self.assertIn("target.nameTag", script)
        self.assertIn("target.id", script)
        self.assertIn("npc_id:", script)
        self.assertIn("npc_type:", script)
        self.assertIn("PLAYER_COOLDOWN_MS", script)


if __name__ == "__main__":
    unittest.main()
