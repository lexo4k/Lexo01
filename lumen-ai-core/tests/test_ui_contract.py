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
            '<section id="chat" class="screen active">',
            'Olá. Sou o LÚMEN.',
            'function localCommand(msg)',
            'function loadConfig()',
            'saved.url==="https://lumen-ai-core.vercel.app"',
            'buscar|pesquisar|procurar',
            'planejar|plano',
            'function exportData()',
            'function handleImport(e)',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)

    def test_no_fake_default_server_hostname(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("lumen-ai-core.vercel.app", html)
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
