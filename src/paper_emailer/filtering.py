from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections.abc import Iterable

from .config import DEFAULT_KEYWORDS
from .models import RankedItem, SourceItem
from .semantic_scorer import _MIN_SIMILARITY, semantic_score


def filter_recent_items(
    items: Iterable[SourceItem],
    *,
    days: int = 14,
    now: datetime | None = None,
) -> list[SourceItem]:
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(days=days)
    recent: list[SourceItem] = []
    for item in items:
        published_at = item.published_at
        if published_at is None:
            continue
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        if published_at >= cutoff:
            recent.append(item)
    return recent


def rank_items(
    items: Iterable[SourceItem],
    keywords: Iterable[str] = DEFAULT_KEYWORDS,
    threshold: float = _MIN_SIMILARITY,
) -> list[RankedItem]:
    ranked: list[RankedItem] = []
    for item in items:
        score = semantic_score(item)
        if score < threshold:
            continue
        reasons = _keyword_reasons(_item_text(item), keywords)
        ranked.append(RankedItem(item=item, score=score, reasons=tuple(reasons)))
    ranked.sort(key=lambda r: (-r.score, r.item.title.lower()))
    return ranked


def _keyword_reasons(text: str, keywords: Iterable[str]) -> list[str]:
    """Return matched keyword labels for display — not used for scoring."""
    lowered = text.lower()
    return [
        kw.strip().lower()
        for kw in keywords
        if kw.strip() and kw.strip().lower() in lowered
    ]


def _item_text(item: SourceItem) -> str:
    parts = [item.title, item.summary, item.source, " ".join(item.authors)]
    return " ".join(part for part in parts if part)
