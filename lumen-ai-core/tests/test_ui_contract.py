from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT.parent / "lumen-android"
ACTIVITY = ANDROID / "src/main/java/com/lexo/lumen/MainActivity.kt"
HTML = ROOT / "index.html"


class UiContractTests(unittest.TestCase):
    def test_android_bundle_matches_rebuilt_web_interface(self):
        self.assertEqual(HTML.read_text(encoding="utf-8"),
                         (ANDROID / "src/main/assets/index.html").read_text(encoding="utf-8"))

    def test_rebuilt_interface_is_a_single_conversation_screen(self):
        html = HTML.read_text(encoding="utf-8")
        for marker in ('<title>AURION</title>', 'id="messages"', 'id="message"',
                       'id="voice"', 'id="send"', 'id="settings"',
                       'id="modelStatus"', 'function send()', 'function aurionStartupCheck()'):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)
        for removed in ('id="home"', 'id="memory"', 'id="tasks"', 'id="knowledge"',
                        'id="researchMode"', 'id="thinkMode"', 'id="video"',
                        'id="imageLab"', 'id="bottomNav"'):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, html)

    def test_native_local_model_setup_and_inference_are_connected(self):
        html = HTML.read_text(encoding="utf-8")
        activity = ACTIVITY.read_text(encoding="utf-8")
        for marker in ('window.AurionNative.sendLocalMessage(text,context,requestId)',
                       'window.AurionNative.confirmModelDownload()',
                       'window.AurionNative.chooseDownloadedModel()',
                       'window.AurionNative.resumeAuthorizedModelSetup()',
                       'window.onAurionNativeAnswer=function(answer,failed,id)'):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)
        for marker in ('@JavascriptInterface fun sendLocalMessage(prompt: String, history: String, requestId: String)',
                       '@JavascriptInterface fun resumeAuthorizedModelSetup()',
                       '@JavascriptInterface fun confirmModelDownload()',
                       'private fun modelMemoryBlockReason(modelBytes: Long)',
                       'validateGgufHeader(modelFile)',
                       'Llama.complete('):
            with self.subTest(marker=marker):
                self.assertIn(marker, activity)

    def test_voice_and_speech_callbacks_remain_wired(self):
        html = HTML.read_text(encoding="utf-8")
        activity = ACTIVITY.read_text(encoding="utf-8")
        self.assertIn('window.AurionNative.startVoiceRecognition()', html)
        self.assertIn('window.onAurionVoiceResult=function(text,error)', html)
        self.assertIn('window.AurionNative.stopSpeaking()', html)
        self.assertIn('createOnDeviceSpeechRecognizer', activity)
        self.assertIn('TextToSpeech', activity)

    def test_model_download_is_wifi_only_and_resumable(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        self.assertIn('Download bloqueado para proteger seus dados móveis', activity)
        self.assertIn('setRequestProperty("Range", "bytes=', activity)
        self.assertIn('putBoolean("model_download_authorized", true)', activity)
        self.assertIn('getString("model_id", "qwen-0.5b")', activity)

    def test_manifest_has_network_and_user_gated_microphone(self):
        manifest = (ANDROID / "src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        activity = ACTIVITY.read_text(encoding="utf-8")
        self.assertIn('android.permission.INTERNET', manifest)
        self.assertIn('android.permission.RECORD_AUDIO', manifest)
        self.assertIn('override fun onPermissionRequest', activity)
        self.assertIn('requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO)', activity)

    def test_embedded_javascript_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed in this test environment")
        html = HTML.read_text(encoding="utf-8")
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.I | re.S)
        self.assertTrue(scripts, "No inline application JavaScript block found")
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as source:
            source.write("\\n".join(scripts))
            source.flush()
            result = subprocess.run([node, "--check", source.name], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
