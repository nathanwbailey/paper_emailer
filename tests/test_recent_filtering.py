from datetime import datetime, timezone

from paper_emailer.filtering import filter_recent_items
from paper_emailer.models import SourceItem


def test_filter_recent_items_keeps_only_last_two_weeks():
    now = datetime(2026, 5, 25, tzinfo=timezone.utc)
    items = [
        SourceItem(
            title="Recent paper",
            url="https://example.com/recent",
            source="arXiv",
            published_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        ),
        SourceItem(
            title="Old paper",
            url="https://example.com/old",
            source="arXiv",
            published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        ),
        SourceItem(
            title="Unknown date",
            url="https://example.com/unknown",
            source="web",
            published_at=None,
        ),
    ]

    recent = filter_recent_items(items, days=14, now=now)

    assert [item.title for item in recent] == ["Recent paper"]