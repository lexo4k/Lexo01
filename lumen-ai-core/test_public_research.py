import unittest
from public_research import ResultsParser


class PublicResearchParserTests(unittest.TestCase):
    def test_extracts_secure_result_links(self):
        html = """
        <div class="result">
          <a class="result__a" href="https://example.org/article">Example article</a>
          <a class="result__snippet">A short search result description.</a>
        </div>
        <div class="result">
          <a class="result__a" href="javascript:alert(1)">Unsafe result</a>
        </div>
        """
        parser = ResultsParser()
        parser.feed(html)
        self.assertEqual(len(parser.items), 1)
        self.assertEqual(parser.items[0]["title"], "Example article")
        self.assertEqual(parser.items[0]["url"], "https://example.org/article")

    def test_decodes_duckduckgo_redirect(self):
        parser = ResultsParser()
        parser.feed('<a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fx">Link</a>')
        self.assertEqual(parser.items[0]["url"], "https://example.org/x")


if __name__ == "__main__":
    unittest.main()
