import unittest

from memory_wormhole import compress_text, decompress_text, fingerprint, select_relevant, storage_metrics


class MemoryWormholeTests(unittest.TestCase):
    def test_compression_is_lossless(self):
        original = ("AURION memória persistente. " * 400) + "🌌"
        packed = compress_text(original)
        self.assertEqual(decompress_text(packed), original)
        self.assertLess(packed["compressed_bytes"], packed["original_bytes"])

    def test_retrieval_prefers_relevant_and_deduplicates(self):
        records = [
            {"id": 1, "title": "Futebol", "content": "Treino de lateral esquerdo e preparação física."},
            {"id": 2, "title": "Receitas", "content": "Como preparar tacacá e açaí."},
            {"id": 3, "title": "Futebol duplicado", "content": "Treino de lateral esquerdo e preparação física."},
        ]
        found = select_relevant(records, "treino de futebol lateral", limit=5)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], 1)

    def test_context_budget_preserves_full_selected_records(self):
        records = [
            {"title": "Projeto AURION", "content": "memória " * 40},
            {"title": "Projeto AURION", "content": "memória " * 40},
        ]
        found = select_relevant(records, "projeto memória", max_chars=1000)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["content"].startswith("memória"))

    def test_fingerprint_normalizes_whitespace_and_case(self):
        self.assertEqual(fingerprint("AURION   AI"), fingerprint("aurion ai"))

    def test_storage_metrics_counts_generator(self):
        metrics = storage_metrics(x for x in ["alpha", "beta"])
        self.assertEqual(metrics["records"], 2)
        self.assertTrue(metrics["lossless"])


if __name__ == "__main__":
    unittest.main()
