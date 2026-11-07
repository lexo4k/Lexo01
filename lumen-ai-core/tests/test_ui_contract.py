from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UiContractTests(unittest.TestCase):
    def test_android_bundle_matches_web_interface(self):
        web = (ROOT / "index.html").read_text(encoding="utf-8")
        android = (ROOT.parent / "lumen-android" / "src" / "main" / "assets" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(web, android)

    def test_offline_workspace_and_local_commands_are_present(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for marker in (
            'id="home"',
            'id="chat"',
            'id="memory"',
            'id="tasks"',
            'id="knowledge"',
            'id="settings"',
            '<section id="home" class="screen active">',
            'Olá. Sou o LÚMEN.',
            'function localCommand(msg)',
            'function loadConfig()',
            'saved.url==="https://lumen-ai-core.vercel.app"',
            'busque|procure|procurar|pesquisar|pesquise',
            'planejar|plano',
            'function exportData()',
            'function handleImport(e)',
            'id="researchMode"',
            'id="thinkMode"',
            'function startVoiceInput()',
            'function speakLastAnswer()',
            'function selectImage(event)',
            'async function syncWorkspace()',
            'await syncWorkspace()',
            'function setMode(mode)',
            'api("/api/research"',
            'api("/api/think"',
            'image_data_url:imageData',
            'PESQUISA NA WEB',
            'PLANEJAMENTO COGNITIVO',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)

    def test_connected_model_takes_priority_over_offline_shortcuts(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("const modelReady=Boolean(connected&&apiCaps&&apiCaps.chat&&apiCaps.chat.configured)", html)
        self.assertIn("const command=(!modelReady&&msg)?localCommand(msg):null", html)

    def test_cloud_knowledge_delete_endpoint_exists(self):
        backend = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('@app.delete("/api/knowledge/{knowledge_id}"', backend)
        self.assertIn('DELETE FROM knowledge WHERE id=?', backend)

    def test_android_voice_permission_is_user_gated(self):
        manifest = (ROOT.parent / "lumen-android" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
        activity = (ROOT.parent / "lumen-android" / "src" / "main" / "java" / "com" / "lexo" / "lumen" / "MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn('android.permission.RECORD_AUDIO', manifest)
        self.assertIn('override fun onPermissionRequest', activity)
        self.assertIn('request.resources.all { it == PermissionRequest.RESOURCE_AUDIO_CAPTURE }', activity)
        self.assertIn('requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO)', activity)

    def test_no_fake_default_server_hostname(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('url:"https://lumen-ai-core.vercel.app"', html)
        self.assertIn("lumen-ai-core-git-lumen-ai-core-unk-studio.vercel.app", html)

    def test_embedded_javascript_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed in this test environment")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.DOTALL)
        self.assertTrue(scripts, "No inline application script found")
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as source:
            source.write("\\n".join(scripts))
            source.flush()
            result = subprocess.run([node, "--check", source.name], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
