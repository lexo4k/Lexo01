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
            'Olá. Sou o AURION.',
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
            'api("/api/research/public"',
            'api("/api/think"',
            'image_data_url:imageData',
            'PESQUISA NA WEB',
            'PLANEJAMENTO COGNITIVO',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)

    def test_local_tools_run_before_model_inference_in_both_modes(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("const command=(!modelReady&&msg)?localCommand(msg):null;", html)
        self.assertNotIn("const command=(!modelReady&&!nativeLocalReady&&msg)?localCommand(msg):null;", html)
        self.assertIn("No modo offline, execute ferramentas locais", html)

    def test_offline_agent_executes_compound_local_task_requests(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Executor local de tarefas compostas", html)
        self.assertIn("Criada pelo executor local AURION", html)
        self.assertIn("Pendentes primeiro", html)
        self.assertIn("tarefas concluidas", html)

    def test_on_device_model_has_priority_and_receives_local_context(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("const nativeLocalReady=Boolean(window.AurionNative&&(localModelState()===" + '"ready"' + "||localModelState()===" + '"downloaded"' + "))", html)
        self.assertIn("if(nativeLocalReady&&!modelReady&&activeMode!==", html)
        self.assertIn("MEMÓRIAS RELEVANTES:", html)
        self.assertIn("BASE DE CONHECIMENTO:", html)
        self.assertIn("TAREFAS EM ABERTO:", html)

    def test_cloud_knowledge_delete_endpoint_exists(self):
        backend = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('@app.delete("/api/knowledge/{knowledge_id}"', backend)
        self.assertIn('DELETE FROM knowledge WHERE id=?', backend)

    def test_chat_ui_exposes_explicit_learning_feedback(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("function rateExperience(index,rating)", html)
        self.assertIn("rateExperience('+i+',5)", html)
        self.assertIn("rateExperience('+i+',2)", html)
        self.assertIn('api("/api/experiences"', html)
        self.assertIn("feedbackSaved", html)

    def test_android_has_practical_default_and_optional_larger_local_model(self):
        activity = (ROOT.parent / "lumen-android" / "src" / "main" / "java" / "com" / "lexo" / "lumen" / "MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn('"qwen-1.5b" to LocalModelProfile', activity)
        self.assertIn('"qwen-3b" to LocalModelProfile', activity)
        self.assertIn('Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf', activity)
        self.assertIn('getString("model_id", "qwen-1.5b")', activity)
        self.assertIn('history.takeLast(1800)', activity)
        self.assertIn('maxTokens = selectedProfile().maxTokens', activity)

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
