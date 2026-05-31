from unittest.mock import patch

from paper_emailer.filtering import rank_items
from paper_emailer.models import SourceItem


def _item(title: str, summary: str = "") -> SourceItem:
    return SourceItem(title=title, url=f"https://example.com/{title}", source="arXiv", summary=summary)


def test_rank_items_includes_relevant_papers():
    relevant = _item("Carbon footprint of training large language models", "energy use and carbon emissions")
    irrelevant = _item("A generic machine learning paper", "nothing relevant here")

    scores = {relevant: 0.92, irrelevant: 0.50}

    with patch("paper_emailer.filtering.semantic_score", side_effect=lambda item: scores[item]):
        ranked = rank_items([relevant, irrelevant])

    assert len(ranked) == 1
    assert ranked[0].item.title.startswith("Carbon footprint")


def test_rank_items_sorted_by_score_descending():
    high = _item("Energy efficient AI", "reduces carbon emissions")
    low = _item("Sustainable AI basics", "green computing")

    scores = {high: 0.90, low: 0.80}

    with patch("paper_emailer.filtering.semantic_score", side_effect=lambda item: scores[item]):
        ranked = rank_items([low, high])

    assert ranked[0].item == high
    assert ranked[1].item == low


def test_rank_items_keyword_reasons_populated():
    item = _item("Carbon footprint of AI", "energy efficient neural networks")

    with patch("paper_emailer.filtering.semantic_score", return_value=0.90):
        ranked = rank_items([item])

    assert "carbon footprint" in ranked[0].reasons
    assert "energy efficient" in ranked[0].reasons


def test_rank_items_empty_input():
    with patch("paper_emailer.filtering.semantic_score", return_value=0.95):
        ranked = rank_items([])
    assert ranked == []


def test_rank_items_all_below_threshold():
    items = [_item("Unrelated paper A"), _item("Unrelated paper B")]
    with patch("paper_emailer.filtering.semantic_score", return_value=0.50):
        ranked = rank_items(items)
    assert ranked == []
