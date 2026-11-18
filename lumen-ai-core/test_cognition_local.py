import unittest
from cognition_local import plan_locally

class LocalPlannerTests(unittest.TestCase):
    def test_returns_steps_without_external_model(self):
        result = plan_locally("Criar e testar um aplicativo")
        self.assertEqual(result["engine"], "nexora-local-planner-v1")
        self.assertEqual(result["execution_status"], "not_executed")
        self.assertGreaterEqual(len(result["plan"]), 2)
        self.assertTrue(result["approval_required"])

    def test_empty_goal_rejected(self):
        with self.assertRaises(ValueError):
            plan_locally("   ")

if __name__ == "__main__":
    unittest.main()
