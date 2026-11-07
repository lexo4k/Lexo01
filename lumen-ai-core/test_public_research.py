import unittest
from unittest.mock import AsyncMock, patch
from public_research import ResultsParser, search_nearby


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

    def test_search_nearby_builds_osm_results_with_distance_and_map_link(self):
        class FakeResponse:
            def raise_for_status(self):
                return None
            def json(self):
                return {"elements": [{"type": "node", "lat": -23.55060, "lon": -46.63340, "tags": {"name": "Farmácia Teste", "amenity": "pharmacy", "addr:street": "Rua Central"}}]}
        async def run_search():
            client = AsyncMock()
            client.post.return_value = FakeResponse()
            context = AsyncMock()
            context.__aenter__.return_value = client
            context.__aexit__.return_value = False
            with patch("public_research.httpx.AsyncClient", return_value=context):
                result = await search_nearby("farmácia", -23.55052, -46.63331)
            client.post.assert_awaited_once()
            request_data = client.post.await_args.kwargs["data"]["data"]
            self.assertIn('["amenity"="pharmacy"]', request_data)
            self.assertEqual(result[0]["title"], "Farmácia Teste")
            self.assertIn("km", result[0]["snippet"])
            self.assertIn("openstreetmap.org", result[0]["url"])
        import asyncio
        asyncio.run(run_search())


if __name__ == "__main__":
    unittest.main()
