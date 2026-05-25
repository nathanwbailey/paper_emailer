from paper_emailer.sources import fetch_web_page
from paper_emailer.sources import fetch_web_search


def test_fetch_web_page_parses_title_and_summary(monkeypatch):
    html = b"""
    <html>
      <head>
        <title>Transparency in AI is on the decline</title>
        <meta name="description" content="A report on transparency." />
        <meta property="article:published_time" content="2026-05-20T10:15:00Z" />
      </head>
      <body><p>First paragraph summary.</p></body>
    </html>
    """

    def fake_get(url: str, timeout: int = 20) -> bytes:
        return html

    monkeypatch.setattr("paper_emailer.sources._http_get", fake_get)

    item = fetch_web_page("https://example.com/article")

    assert item.title == "Transparency in AI is on the decline"
    assert item.summary == "A report on transparency."
    assert item.published_at is not None


def test_fetch_web_search_parses_result_links(monkeypatch):
    search_html = b"""
    <html>
      <body>
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fblog%2Fpost">Transparency in AI is on the decline</a>
        <div class="result__snippet">A short article about transparency.</div>
      </body>
    </html>
    """
    article_html = b"""
    <html>
      <head>
        <title>Transparency in AI is on the decline</title>
        <meta property="article:published_time" content="2026-05-22T09:00:00Z" />
      </head>
      <body><p>Article body.</p></body>
    </html>
    """

    def fake_get(url: str, timeout: int = 20) -> bytes:
        if "duckduckgo.com" in url:
            return search_html
        return article_html

    monkeypatch.setattr("paper_emailer.sources._http_get", fake_get)

    items = fetch_web_search("transparency in ai")

    assert len(items) == 1
    assert items[0].url == "https://example.com/blog/post"
    assert items[0].summary == "Article body."
    assert items[0].published_at is not None
