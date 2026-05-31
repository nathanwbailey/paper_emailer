from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen
import logging
import re
import xml.etree.ElementTree as ET

from .config import SourceConfig
from .models import SourceItem


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def fetch_sources(sources: list[SourceConfig], timeout: int = 20) -> list[SourceItem]:
    items: list[SourceItem] = []
    for source in sources:
        try:
            items.extend(fetch_source(source, timeout=timeout))
        except Exception as error:
            logging.warning("skipping %s source %r: %s", source.kind, source.value, error)
    return items


def fetch_source(source: SourceConfig, timeout: int = 20) -> list[SourceItem]:
    if source.kind == "arxiv":
        query = source.query or source.value
        return fetch_arxiv(query, timeout=timeout, content_type=source.content_type)
    if source.kind == "rss":
        return fetch_rss(source.value, timeout=timeout, content_type=source.content_type)
    if source.kind == "search":
        query = source.query or source.value
        return fetch_web_search(query, timeout=timeout, content_type=source.content_type)
    if source.kind == "web":
        return [fetch_web_page(source.value, timeout=timeout, content_type=source.content_type)]
    raise ValueError(f"Unsupported source kind: {source.kind}")


def fetch_web_search(query: str, timeout: int = 20, content_type: str = "article") -> list[SourceItem]:
    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html = _http_get(search_url, timeout=timeout).decode("utf-8", errors="replace")
    results: list[SourceItem] = []
    for match in re.finditer(
        r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'(?:<a[^>]*class="result__snippet"[^>]*>(.*?)</a>|<div[^>]*class="result__snippet"[^>]*>(.*?)</div>)',
        html,
        flags=re.S,
    ):
        url = _decode_duckduckgo_url(match.group(1))
        title = _strip_tags(match.group(2))
        snippet = _strip_tags(match.group(3) or match.group(4) or "")
        page_item = None
        try:
            page_item = fetch_web_page(url, timeout=timeout, content_type=content_type)
        except Exception:
            page_item = None
        results.append(
            SourceItem(
                title=(page_item.title if page_item and page_item.title else title) or url,
                url=url,
                source="duckduckgo",
                published_at=page_item.published_at if page_item else None,
                summary=(page_item.summary if page_item and page_item.summary else snippet),
                content_type=content_type,
                id=url,
            )
        )
    return results


def fetch_arxiv(query: str, timeout: int = 20, content_type: str = "paper") -> list[SourceItem]:
    # Use query verbatim when it already contains field specifiers (ti:, abs:, cat:),
    # otherwise prefix with all: to search across all fields.
    prefixed = query if (":" in query) else f"all:{query}"
    search_url = (
        "https://export.arxiv.org/api/query?"
        f"search_query={quote_plus(prefixed)}&sortBy=relevance&max_results=50"
    )
    root = ET.fromstring(_http_get(search_url, timeout=timeout))
    items: list[SourceItem] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = _text(entry, "atom:title")
        summary = _text(entry, "atom:summary")
        link = _arxiv_link(entry)
        authors = tuple(
            author.findtext("atom:name", default="", namespaces=ATOM_NS)
            for author in entry.findall("atom:author", ATOM_NS)
        )
        published = _parse_datetime(_text(entry, "atom:published"))
        arxiv_id = _text(entry, "atom:id")
        items.append(
            SourceItem(
                title=title,
                url=link,
                source="arXiv",
                published_at=published,
                summary=summary,
                authors=tuple(author for author in authors if author),
                content_type=content_type,
                id=arxiv_id,
            )
        )
    return items


def fetch_rss(url: str, timeout: int = 20, content_type: str = "article") -> list[SourceItem]:
    root = ET.fromstring(_http_get(url, timeout=timeout))
    if root.tag.endswith("rss"):
        channel = root.find("channel")
        if channel is None:
            return []
        entries = channel.findall("item")
        return [_rss_item(item, content_type) for item in entries]
    entries = root.findall("atom:entry", ATOM_NS)
    return [_atom_item(entry, content_type) for entry in entries]


def fetch_web_page(url: str, timeout: int = 20, content_type: str = "article") -> SourceItem:
    html = _http_get(url, timeout=timeout).decode("utf-8", errors="replace")
    parser = _ArticleHTMLParser()
    parser.feed(html)
    title = parser.title or url
    summary = parser.description or parser.og_description or parser.first_paragraph
    return SourceItem(
        title=title,
        url=url,
        source=parser.site_name or "web",
        published_at=parser.published_at,
        summary=summary,
        content_type=content_type,
        id=url,
    )


def _rss_item(item: ET.Element, content_type: str) -> SourceItem:
    link = _child_text(item, "link")
    title = _child_text(item, "title") or link
    summary = _child_text(item, "description") or _child_text(item, "summary")
    published = _parse_rss_date(_child_text(item, "pubDate"))
    guid = _child_text(item, "guid") or link
    return SourceItem(
        title=title,
        url=link,
        source="rss",
        published_at=published,
        summary=summary,
        content_type=content_type,
        id=guid,
    )


def _atom_item(entry: ET.Element, content_type: str) -> SourceItem:
    title = _text(entry, "atom:title")
    summary = _text(entry, "atom:summary") or _text(entry, "atom:content")
    link = _atom_link(entry)
    published = _parse_datetime(_text(entry, "atom:published") or _text(entry, "atom:updated"))
    return SourceItem(
        title=title,
        url=link,
        source="atom",
        published_at=published,
        summary=summary,
        content_type=content_type,
        id=_text(entry, "atom:id") or link,
    )


def _arxiv_link(entry: ET.Element) -> str:
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("rel") == "alternate":
            return link.attrib.get("href", "")
    return _text(entry, "atom:id")


def _atom_link(entry: ET.Element) -> str:
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("rel") in (None, "alternate"):
            return link.attrib.get("href", "")
    return _text(entry, "atom:id")


def _text(node: ET.Element, path: str) -> str:
    value = node.findtext(path, default="", namespaces=ATOM_NS)
    return (value or "").strip()


def _child_text(node: ET.Element, name: str) -> str:
    child = node.find(name)
    return (child.text or "").strip() if child is not None and child.text else ""


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc)


def _parse_rss_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _http_get(url: str, timeout: int = 20) -> bytes:
    request = Request(url, headers={"User-Agent": "paper-emailer/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except URLError as error:
        raise RuntimeError(f"Failed to fetch {url}: {error}") from error


class _ArticleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self.og_description = ""
        self.site_name = ""
        self.first_paragraph = ""
        self.published_at: datetime | None = None
        self._capture_title = False
        self._capture_paragraph = False
        self._paragraph_parts: list[str] = []
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        if tag == "title":
            self._capture_title = True
        if tag == "p" and not self.first_paragraph:
            self._capture_paragraph = True
            self._paragraph_parts = []
        if tag == "meta":
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            itemprop = attr_map.get("itemprop", "").lower()
            content = attr_map.get("content", "")
            if name == "description" and content:
                self.description = content.strip()
            if prop == "og:description" and content:
                self.og_description = content.strip()
            if prop == "og:site_name" and content:
                self.site_name = content.strip()
            if prop == "og:title" and content and not self.title:
                self.title = content.strip()
            if (
                content
                and (
                    itemprop in {"datepublished", "datecreated", "datemodified"}
                    or name in {"pubdate", "publishdate", "timestamp"}
                    or prop in {"article:published_time", "article:modified_time"}
                )
            ):
                self.published_at = _parse_datetime(content) or self.published_at
        if tag == "time" and not self.published_at:
            datetime_value = attr_map.get("datetime", "")
            if datetime_value:
                self.published_at = _parse_datetime(datetime_value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._capture_title = False
            if not self.title:
                self.title = _normalize_whitespace("".join(self._title_parts))
                self._title_parts = []
        if tag == "p" and self._capture_paragraph and not self.first_paragraph:
            self.first_paragraph = _normalize_whitespace("".join(self._paragraph_parts))
            self._capture_paragraph = False
            self._paragraph_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._title_parts.append(data)
        if self._capture_paragraph:
            self._paragraph_parts.append(data)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _decode_duckduckgo_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
        params = parse_qs(parsed.query)
        if "uddg" in params and params["uddg"]:
            return unquote(params["uddg"][0])
    return url


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()
