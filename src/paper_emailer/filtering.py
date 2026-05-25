from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections.abc import Iterable

from .models import RankedItem, SourceItem


DEFAULT_PHRASES = (
    "sustainable ai",
    "green ai",
    "energy efficient",
    "energy efficiency",
    "carbon footprint",
    "carbon emissions",
    "low power",
    "efficient training",
    "efficient inference",
    "model compression",
    "hardware aware",
    "quantization",
    "distillation",
    "responsible ai",
)


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


def rank_items(items: Iterable[SourceItem], keywords: Iterable[str] = DEFAULT_PHRASES) -> list[RankedItem]:
    ranked: list[RankedItem] = []
    for item in items:
        text = _item_text(item)
        score, reasons = _score_text(text, keywords)
        if score > 0:
            ranked.append(RankedItem(item=item, score=score, reasons=tuple(reasons)))
    ranked.sort(key=lambda ranked_item: (-ranked_item.score, ranked_item.item.title.lower()))
    return ranked


def _score_text(text: str, keywords: Iterable[str]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    lowered = text.lower()
    for keyword in keywords:
        keyword = keyword.strip().lower()
        if not keyword:
            continue
        hits = lowered.count(keyword)
        if hits:
            score += len(keyword.replace(" ", "")) + (hits - 1)
            reasons.append(keyword)
    if any(term in lowered for term in ("energy", "carbon", "emission", "power", "efficient")):
        score += 1
    return score, reasons


def _item_text(item: SourceItem) -> str:
    parts = [item.title, item.summary, item.source, " ".join(item.authors)]
    return " ".join(part for part in parts if part)
