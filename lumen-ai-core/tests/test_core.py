import os
import tempfile
import unittest
from unittest import mock
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

tmp = tempfile.TemporaryDirectory()
os.environ["LUMEN_DB_PATH"] = os.path.join(tmp.name, "test.db")
os.environ["LUMEN_ACCESS_TOKEN"] = "test-token"
from app import app, execute_agent_tool, tool_mutation_authorized

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer test-token"}

    def test_agent_web_research_returns_source_links(self):
        from app import execute_agent_research
        with mock.patch("app.search_web", new=AsyncMock(return_value=[
            {"title": "Documentação oficial", "url": "https://example.test/docs", "snippet": "Trecho relevante."}
        ])):
            import asyncio
            result = asyncio.run(execute_agent_research({"query": "documentação de IA"}))
        self.assertTrue(result["ok"])
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["sources"][0]["url"], "https://example.test/docs")

    def test_agent_web_research_rejects_empty_query(self):
        from app import execute_agent_research
        import asyncio
        result = asyncio.run(execute_agent_research({"query": "  "}))
        self.assertFalse(result["ok"])

    def test_video_study_archives_researched_principles(self):
        from app import search_web
        with mock.patch("app.search_web", new=AsyncMock(return_value=[
            {"title": "Guia de vídeo", "url": "https://example.test/video", "snippet": "Enquadramento e continuidade."}
        ])):
            response = self.client.post("/api/video/study", headers=self.headers, json={
                "topic": "Como planejar vídeos gerados por IA"
            })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["studied"])
        self.assertFalse(payload["model_weights_changed"])
        self.assertGreaterEqual(len(payload["sources"]), 1)
        self.assertIn("continuidade", payload["principles"][3].lower())

    def test_video_test_requires_study_and_returns_storyboard_not_fake_video(self):
        from app import db
        with db() as con:
            con.execute("DELETE FROM knowledge WHERE title='Vídeo IA: princípios de criação'")
        response = self.client.post("/api/video/test", headers=self.headers, json={
            "idea": "Um robô explorando uma floresta luminosa"
        })
        self.assertEqual(response.status_code, 409)
        from app import search_web
        with mock.patch("app.search_web", new=AsyncMock(return_value=[
            {"title": "Guia de vídeo", "url": "https://example.test/video", "snippet": "Enquadramento e continuidade."}
        ])):
            study = self.client.post("/api/video/study", headers=self.headers, json={
                "topic": "Como planejar vídeos gerados por IA"
            })
        self.assertEqual(study.status_code, 200)
        result = self.client.post("/api/video/test", headers=self.headers, json={
            "idea": "Um robô explorando uma floresta luminosa"
        })
        self.assertEqual(result.status_code, 200)
        payload = result.json()
        self.assertTrue(payload["created"])
        self.assertFalse(payload["rendered_video"])
        self.assertEqual(len(payload["shots"]), 3)
        self.assertIn("continuidade", payload["video_prompt"].lower())

    def test_learning_experience_requires_positive_rating_and_lesson_for_reuse(self):
        response = self.client.post("/api/experiences", headers=self.headers, json={
            "user_message": "Explique como organizar tarefas",
            "assistant_answer": "Separe por prioridade e prazo.",
            "rating": 5,
            "lesson": "A pessoa prefere passos curtos e priorizados."
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "useful")
        self.assertTrue(response.json()["used_as_learning_context"])

    def test_low_rated_experience_is_stored_for_review_not_reused(self):
        response = self.client.post("/api/experiences", headers=self.headers, json={
            "user_message": "Faça um plano",
            "assistant_answer": "Resposta inadequada",
            "rating": 2,
            "correction": "A resposta não atendeu ao pedido."
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "review")
        self.assertFalse(response.json()["used_as_learning_context"])

    def test_learning_experience_endpoint_requires_authentication(self):
        response = self.client.post("/api/experiences", json={
            "user_message": "Teste",
            "assistant_answer": "Teste",
            "rating": 5,
            "lesson": "Teste"
        })
        self.assertEqual(response.status_code, 401)

    def test_model_config_accepts_generic_provider_credentials(self):
        from app import model_config
        with mock.patch.dict(os.environ, {
            "LUMEN_MODEL_API_KEY": "generic-test-key",
            "LUMEN_MODEL_BASE_URL": "https://example.test/v1",
            "LUMEN_MODEL_NAME": "test-chat-model",
            "OPENAI_API_KEY": "",
            "OPENAI_BASE_URL": "",
            "OPENAI_MODEL": "",
            "OPENROUTER_API_KEY": "",
            "GROQ_API_KEY": "",
            "TOGETHER_API_KEY": "",
        }, clear=False):
            config = model_config()
        self.assertEqual(config["api_key"], "generic-test-key")
        self.assertEqual(config["base_url"], "https://example.test/v1")
        self.assertEqual(config["model"], "test-chat-model")

    def test_model_config_auto_detects_openrouter(self):
        from app import model_config
        with mock.patch.dict(os.environ, {
            "LUMEN_MODEL_API_KEY": "",
            "LUMEN_MODEL_BASE_URL": "",
            "OPENAI_API_KEY": "",
            "OPENAI_BASE_URL": "",
            "OPENROUTER_API_KEY": "router-test-key",
            "GROQ_API_KEY": "",
            "TOGETHER_API_KEY": "",
        }, clear=False):
            config = model_config()
        self.assertEqual(config["api_key"], "router-test-key")
        self.assertEqual(config["base_url"], "https://openrouter.ai/api/v1")

    def test_model_config_supports_self_hosted_ollama_without_api_key(self):
        from app import model_config, model_is_configured
        with mock.patch.dict(os.environ, {
            "LUMEN_MODEL_API_KEY": "",
            "OPENAI_API_KEY": "",
            "OPENROUTER_API_KEY": "",
            "GROQ_API_KEY": "",
            "TOGETHER_API_KEY": "",
            "LUMEN_MODEL_BASE_URL": "http://ollama.internal:11434/v1",
            "OPENAI_BASE_URL": "",
            "LUMEN_MODEL_NAME": "",
            "OPENAI_MODEL": "",
        }, clear=False):
            config = model_config()
            self.assertEqual(config["provider"], "ollama")
            self.assertEqual(config["model"], "llama3.2")
            self.assertEqual(config["api_key"], "ollama-local")
            self.assertTrue(model_is_configured())

    def test_health_is_public(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["app"], "AURION AI")
        self.assertFalse(response.json()["model_connected"])
        self.assertIn(response.json()["storage_backend"], ("sqlite_ephemeral", "sqlite_persistent_disk", "postgresql"))


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

    def test_agent_can_archive_knowledge_and_complete_task(self):
        task = execute_agent_tool("create_task", {"title": "Testar agente"})
        archived = execute_agent_tool("save_knowledge", {"title": "Nota técnica", "content": "Conteúdo de teste"})
        completed = execute_agent_tool("complete_task", {"task_id": task["id"]})
        overview = execute_agent_tool("get_overview", {})
        self.assertTrue(archived["saved"])
        self.assertTrue(completed["ok"])
        self.assertGreaterEqual(overview["knowledge"], 1)
        self.assertGreaterEqual(overview["completed_tasks"], 1)

    def test_agent_tool_rejects_unknown_tool(self):
        result = execute_agent_tool("run_shell", {})
        self.assertFalse(result["ok"])

    def test_agent_mutations_require_explicit_user_intent(self):
        self.assertTrue(tool_mutation_authorized("save_memory", "Guarde isso na minha memória: prefiro português."))
        self.assertTrue(tool_mutation_authorized("create_task", "Crie uma tarefa para revisar o projeto."))
        self.assertTrue(tool_mutation_authorized("save_knowledge", "Registre esta nota no conhecimento."))
        self.assertTrue(tool_mutation_authorized("complete_task", "Marque a tarefa como concluída."))
        self.assertFalse(tool_mutation_authorized("save_memory", "Qual é a sua opinião sobre isso?"))
        self.assertFalse(tool_mutation_authorized("create_task", "Explique como organizar minhas tarefas."))
        self.assertFalse(tool_mutation_authorized("save_knowledge", "Resuma esse assunto para mim."))
        self.assertFalse(tool_mutation_authorized("complete_task", "Quais tarefas estão abertas?"))

    def test_agent_mutation_authorization_is_not_granted_to_read_tools(self):
        self.assertFalse(tool_mutation_authorized("list_tasks", "Liste minhas tarefas."))

    @mock.patch("app.search_nearby", new_callable=AsyncMock)
    def test_public_research_is_available_without_access_token_and_uses_gps_coordinates(self, search):
        search.return_value = [{"title": "Lugares próximos", "url": "https://example.org/places", "snippet": "Resultado de teste"}]
        response = self.client.post("/api/research/public", json={
            "query": "cafés",
            "latitude": -23.55052,
            "longitude": -46.63331
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["location_used"])
        search.assert_awaited_once_with("cafés", -23.55052, -46.63331, limit=8)

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
        self.assertTrue(response.json()["agent_tools"]["implemented"])
        self.assertIn("save_knowledge", response.json()["agent_tools"]["available_tools"])
        self.assertIn("web_research", response.json()["agent_tools"]["available_tools"])
        self.assertIn("get_capabilities", response.json()["agent_tools"]["available_tools"])
        self.assertFalse(response.json()["ads"]["implemented"])

    def test_agent_capabilities_tool_reports_features_without_secrets(self):
        result = execute_agent_tool("get_capabilities", {})
        self.assertTrue(result["ok"])
        self.assertTrue(result["web_research"])
        self.assertTrue(result["persistent_memory"])
        self.assertNotIn("api_key", result)


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
