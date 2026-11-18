import asyncio
import json
import unittest

from cognition import _json_object, think


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


class FakeClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, headers, json):
        self.calls.append(json)
        if len(self.calls) == 1:
            return FakeResponse(json_dumps({
                "understanding": "Criar um plano para estudar",
                "goal": "Plano de estudo",
                "assumptions": [],
                "plan": [{"step": 1, "action": "Separar matérias", "purpose": "Organizar"}],
                "decision": "Começar pela organização",
                "confidence": 1.4,
                "uncertainties": [],
                "approval_required": False,
                "next_action": "Listar matérias",
                "memory_candidates": []
            }))
        return FakeResponse(json_dumps({
            "quality": "adequado",
            "issues": [],
            "improvements": [],
            "safe_next_action": "Listar matérias",
            "approval_required": False
        }))


def json_dumps(value):
    return __import__("json").dumps(value, ensure_ascii=False)


class CognitionTests(unittest.TestCase):
    def test_json_parser_rejects_non_object(self):
        with self.assertRaises(ValueError):
            _json_object("sem json")

    def test_cycle_plans_then_evaluates_and_clamps_confidence(self):
        client = FakeClient()
        result = asyncio.run(think(
            client=client,
            base="https://example.invalid/v1",
            key="test",
            model="test-model",
            goal="Criar um plano para estudar",
            memories=["Prefere instruções diretas"],
            knowledge=[],
            recent_history=[]
        ))
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(result["confidence"], 1.0)
        self.assertEqual(result["evaluation"]["quality"], "adequado")
        self.assertEqual(result["execution_status"], "not_executed")
        self.assertTrue(result["approval_required"])
        self.assertTrue(result["self_review"]["automatic"])
        self.assertFalse(result["self_review"]["revision_attempted"])

    def test_cycle_automatically_revises_a_plan_after_failed_review(self):
        class RepairClient:
            def __init__(self):
                self.calls = 0

            async def post(self, url, headers, json):
                self.calls += 1
                if self.calls == 1:
                    payload = {"understanding":"Criar app","goal":"App funcional",
                        "assumptions":[],"plan":[{"step":1,"action":"Criar","purpose":"Iniciar"}],
                        "decision":"Criar","confidence":0.7,"uncertainties":[],
                        "approval_required":False,"next_action":"Criar","memory_candidates":[]}
                elif self.calls == 2:
                    payload = {"quality":"revisar","issues":["Faltam testes"],
                        "improvements":["Adicionar validação"],"safe_next_action":"Incluir testes",
                        "approval_required":True}
                elif self.calls == 3:
                    payload = {"understanding":"Criar app","goal":"App funcional",
                        "assumptions":[],"plan":[{"step":1,"action":"Criar e testar","purpose":"Validar"}],
                        "decision":"Criar e testar","confidence":0.8,"uncertainties":[],
                        "approval_required":True,"next_action":"Executar testes","memory_candidates":[]}
                else:
                    payload = {"quality":"adequado","issues":[],"improvements":[],
                        "safe_next_action":"Executar testes","approval_required":True}
                return FakeResponse(json_dumps(payload))

        client = RepairClient()
        result = asyncio.run(think(
            client=client, base="https://example.invalid/v1", key="test",
            model="test-model", goal="Criar app", memories=[], knowledge=[],
            recent_history=[]
        ))
        self.assertEqual(client.calls, 4)
        self.assertTrue(result["self_review"]["revision_attempted"])
        self.assertEqual(result["evaluation"]["quality"], "adequado")
        self.assertIn("testar", result["plan"][0]["action"].lower())
        self.assertEqual(result["execution_status"], "not_executed")


if __name__ == "__main__":
    unittest.main()
