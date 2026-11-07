import os
import tempfile
import unittest
from unittest import mock
from fastapi.testclient import TestClient

tmp = tempfile.TemporaryDirectory()
os.environ["LUMEN_DB_PATH"] = os.path.join(tmp.name, "test.db")
os.environ["LUMEN_ACCESS_TOKEN"] = "test-token"
from app import app, execute_agent_tool

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token"}

    def test_health_is_public(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["app"], "LÚMEN AI CORE")
        self.assertFalse(response.json()["model_connected"])
        self.assertIn(response.json()["storage_backend"], ("sqlite", "postgresql"))


    def test_android_origin_cors_preflight(self):
        response = self.client.options(
            "/api/overview",
            headers={
                "Origin": "null",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "*")

    def test_memory_persists_and_lists(self):
        saved = self.client.post("/api/memories", headers=self.headers,
                                 json={"content": "Preferência de teste", "category": "teste"})
        self.assertEqual(saved.status_code, 200)
        items = self.client.get("/api/memories", headers=self.headers).json()
        self.assertTrue(any(x["content"] == "Preferência de teste" for x in items))

    def test_invalid_token_is_rejected(self):
        response = self.client.get("/api/overview", headers={"Authorization": "Bearer errado"})
        self.assertEqual(response.status_code, 401)

    def test_tasks_can_be_created_and_completed(self):
        created = self.client.post("/api/tasks", headers=self.headers,
                                   json={"title": "Validar MVP"})
        task_id = created.json()["id"]
        updated = self.client.patch(f"/api/tasks/{task_id}", headers=self.headers,
                                    json={"status": "concluída"})
        self.assertEqual(updated.status_code, 200)

    def test_agent_tools_save_memory_create_and_list_tasks(self):
        saved = execute_agent_tool("save_memory", {"content": "Gosta de respostas objetivas", "category": "preferencia"})
        self.assertTrue(saved["saved"])
        task = execute_agent_tool("create_task", {"title": "Revisar o núcleo LÚMEN", "details": "Adicionar ferramentas locais"})
        self.assertEqual(task["status"], "pendente")
        listed = execute_agent_tool("list_tasks", {})
        self.assertTrue(any(item["title"] == "Revisar o núcleo LÚMEN" for item in listed["tasks"]))

    def test_agent_tool_memory_search(self):
        execute_agent_tool("save_memory", {"content": "Prefere interface em português", "category": "preferencia"})
        result = execute_agent_tool("search_memory", {"query": "interface em português"})
        self.assertTrue(any("interface em português" in item["content"] for item in result["memories"]))

    def test_agent_tool_rejects_unknown_tool(self):
        result = execute_agent_tool("run_shell", {})
        self.assertFalse(result["ok"])

    def test_web_research_requires_provider_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            response = self.client.post("/api/research", headers=self.headers,
                                        json={"query": "notícias sobre ciência"})
        self.assertEqual(response.status_code, 503)

    def test_pwa_assets_are_served(self):
        self.assertEqual(self.client.get("/manifest.webmanifest").status_code, 200)
        self.assertEqual(self.client.get("/sw.js").status_code, 200)
        self.assertEqual(self.client.get("/icon.svg").status_code, 200)

    def test_capabilities_are_protected_and_explicit(self):
        response = self.client.get("/api/capabilities", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("web_research", response.json())
        self.assertFalse(response.json()["ads"]["implemented"])

    def test_image_mime_is_validated(self):
        response = self.client.post("/api/chat", headers=self.headers,
                                    json={"message": "teste", "image_data_url": "data:text/html;base64,abc"})
        self.assertEqual(response.status_code, 422)

    def test_conversation_history_endpoint_is_protected_and_empty(self):
        response = self.client.get("/api/conversations", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_conversation_history_requires_token(self):
        response = self.client.get("/api/conversations")
        self.assertEqual(response.status_code, 401)

if __name__ == "__main__":
    unittest.main()
