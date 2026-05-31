from datetime import datetime, timedelta, timezone

import pytest

from paper_emailer.models import RankedItem, SourceItem
from paper_emailer.state import StateStore


def _make_item(url: str, score: int = 1) -> RankedItem:
    return RankedItem(
        item=SourceItem(title=url, url=url, source="test", id=url),
        score=score,
    )


def test_filter_new_returns_all_when_empty(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    items = [_make_item("https://a.com"), _make_item("https://b.com")]
    assert store.filter_new(items) == items


def test_filter_new_excludes_sent_ids(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    item_a = _make_item("https://a.com")
    item_b = _make_item("https://b.com")
    store.record_sent([item_a], datetime.now(timezone.utc).isoformat())
    result = store.filter_new([item_a, item_b])
    assert result == [item_b]


def test_record_sent_persists(tmp_path):
    db = tmp_path / "state.sqlite3"
    store = StateStore(db)
    item = _make_item("https://a.com")
    store.record_sent([item], datetime.now(timezone.utc).isoformat())
    store2 = StateStore(db)
    assert store2.filter_new([item]) == []


def test_filter_new_empty_input(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    assert store.filter_new([]) == []


def test_prune_removes_old_records(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    item = _make_item("https://old.com")
    old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    store.record_sent([item], old_ts)
    assert store.filter_new([item]) == []
    store.prune(days=90)
    assert store.filter_new([item]) == [item]


def test_prune_keeps_recent_records(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    item = _make_item("https://recent.com")
    store.record_sent([item], datetime.now(timezone.utc).isoformat())
    store.prune(days=90)
    assert store.filter_new([item]) == []
