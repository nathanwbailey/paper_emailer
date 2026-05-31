import json
from unittest.mock import MagicMock, patch

from paper_emailer.models import RankedItem, SourceItem
from paper_emailer.summarizer import summarize_items


def _make_item(title: str = "A paper", summary: str = "Original summary") -> RankedItem:
    return RankedItem(
        item=SourceItem(title=title, url="https://example.com", source="arXiv", summary=summary),
        score=5,
    )


def _mock_response(text: str) -> MagicMock:
    payload = json.dumps({"choices": [{"message": {"content": text}}]}).encode()
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = payload
    return mock


def test_summarize_replaces_summary():
    item = _make_item()
    with patch("paper_emailer.summarizer.urlopen", return_value=_mock_response("New summary.")):
        result = summarize_items([item], api_key="key")
    assert result[0].item.summary == "New summary."


def test_summarize_preserves_score_and_reasons():
    item = RankedItem(
        item=SourceItem(title="T", url="u", source="s"),
        score=10,
        reasons=("efficient training",),
    )
    with patch("paper_emailer.summarizer.urlopen", return_value=_mock_response("Summary.")):
        result = summarize_items([item], api_key="key")
    assert result[0].score == 10
    assert result[0].reasons == ("efficient training",)


def test_summarize_skipped_when_no_api_key():
    item = _make_item(summary="Keep this")
    result = summarize_items([item], api_key="")
    assert result[0].item.summary == "Keep this"


def test_summarize_falls_back_on_error():
    item = _make_item(summary="Original")
    with patch("paper_emailer.summarizer.urlopen", side_effect=Exception("boom")):
        result = summarize_items([item], api_key="key")
    assert result[0].item.summary == "Original"


def test_summarize_empty_list():
    assert summarize_items([], api_key="key") == []
