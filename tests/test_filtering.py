from paper_emailer.filtering import rank_items
from paper_emailer.models import SourceItem


def test_rank_items_filters_and_scores_sustainable_ai_terms():
    items = [
        SourceItem(
            title="Carbon footprint of training large language models",
            url="https://example.com/a",
            source="arXiv",
            summary="This paper studies energy use and carbon emissions.",
        ),
        SourceItem(
            title="A generic machine learning paper",
            url="https://example.com/b",
            source="arXiv",
            summary="Nothing relevant here.",
        ),
    ]

    ranked = rank_items(items)

    assert len(ranked) == 1
    assert ranked[0].item.title.startswith("Carbon footprint")
    assert "carbon footprint" in ranked[0].reasons
