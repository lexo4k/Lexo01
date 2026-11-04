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


if __name__ == "__main__":
    unittest.main()
