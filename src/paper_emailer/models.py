from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class SourceItem:
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    summary: str = ""
    authors: tuple[str, ...] = ()
    content_type: str = "paper"
    id: str | None = None

    def normalized_id(self) -> str:
        return self.id or self.url or self.title.lower().strip()


@dataclass(frozen=True, slots=True)
class RankedItem:
    item: SourceItem
    score: float
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Digest:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    items: tuple[RankedItem, ...] = ()
