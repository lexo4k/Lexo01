import unittest

from symbolic_engine import calculate_arithmetic, inspect_symbols


class SymbolicEngineTests(unittest.TestCase):
    def test_recognizes_ascii_letters_digits_and_punctuation(self):
        sample = "0123456789 AaZz @[]{}() .,:;!?+-=*/"
        result = inspect_symbols(sample)
        self.assertGreaterEqual(result["counts"]["digits"], 10)
        self.assertGreaterEqual(result["counts"]["letters"], 4)
        self.assertGreater(result["counts"]["punctuation"], 0)
        self.assertGreater(result["counts"]["operators"], 0)
        self.assertEqual(result["unmatched_open_delimiters"], 0)
        self.assertEqual(result["unmatched_close_delimiters"], 0)

    def test_handles_utf8_accents_and_symbols(self):
        sample = "ação, coração, € ☀️ 漢字"
        result = inspect_symbols(sample)
        self.assertGreater(result["utf8_bytes"], result["length_characters"])
        self.assertGreater(result["counts"]["symbols"], 0)
        self.assertGreater(result["counts"]["letters"], 0)

    def test_detects_unbalanced_delimiters(self):
        result = inspect_symbols("([x)]}")
        self.assertGreater(result["unmatched_close_delimiters"], 0)
        self.assertGreater(result["unmatched_open_delimiters"], 0)

    def test_calculates_basic_arithmetic(self):
        self.assertEqual(calculate_arithmetic("(12 + 8) * 3")["result"], 60)
        self.assertEqual(calculate_arithmetic("17 // 5")["result"], 3)

    def test_rejects_code_execution_and_unsafe_expressions(self):
        for expression in ("__import__('os').system('echo unsafe')", "2 ** 100"):
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    calculate_arithmetic(expression)

    def test_rejects_division_by_zero(self):
        with self.assertRaises(ValueError):
            calculate_arithmetic("9 / 0")


if __name__ == "__main__":
    unittest.main()
