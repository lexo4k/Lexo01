import unittest
import torch
from model import LumenGPT, encode, decode

class LumenModelTests(unittest.TestCase):
    def test_utf8_round_trip(self):
        text = "LÚMEN aprende português."
        self.assertEqual(decode(encode(text)), text)

    def test_logits_and_loss(self):
        model = LumenGPT(width=32, layers=1, heads=2, context=16, dropout=0.0)
        x = torch.randint(0, 257, (2, 12))
        y = torch.randint(0, 257, (2, 12))
        logits, loss = model(x, y)
        self.assertEqual(tuple(logits.shape), (2, 12, 257))
        self.assertTrue(torch.isfinite(loss).item())

    def test_rejects_context_overflow(self):
        model = LumenGPT(width=32, layers=1, heads=2, context=8)
        with self.assertRaises(ValueError):
            model(torch.zeros((1, 9), dtype=torch.long))

if __name__ == "__main__":
    unittest.main()
