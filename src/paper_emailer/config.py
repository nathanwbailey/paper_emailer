from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import os


DEFAULT_KEYWORDS = (
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
    "distillation",
    "quantization",
    "hardware aware",
    "responsible ai",
)


@dataclass(slots=True)
class SourceConfig:
    kind: str
    value: str
    query: str | None = None
    content_type: str = "paper"


@dataclass(slots=True)
class AppConfig:
    sources: list[SourceConfig] = field(default_factory=list)
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS
    state_path: Path = Path(".paper_emailer/state.sqlite3")
    sendgrid_api_key: str = ""
    from_email: str = ""
    from_name: str = "Sustainable AI Digest"
    to_email: str = ""
    dry_run: bool = False
    summarize: bool = False
    openrouter_api_key: str = ""
    summarizer_model: str = "google/gemma-4-31b-it:free"


def load_config(path: str | None = None) -> AppConfig:
    config = AppConfig()
    if path:
        config = _load_json_config(Path(path), config)
    config.sendgrid_api_key = os.environ.get("SENDGRID_API_KEY", config.sendgrid_api_key)
    config.from_email = os.environ.get("SENDGRID_FROM_EMAIL", config.from_email)
    config.from_name = os.environ.get("SENDGRID_FROM_NAME", config.from_name)
    config.to_email = os.environ.get("SENDGRID_TO_EMAIL", config.to_email)
    state_path = os.environ.get("PAPER_EMAILER_STATE_PATH")
    if state_path:
        config.state_path = Path(state_path)
    config.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", config.openrouter_api_key)
    config.summarizer_model = os.environ.get("SUMMARIZER_MODEL", config.summarizer_model)
    if os.environ.get("PAPER_EMAILER_SUMMARIZE", "").lower() in {"1", "true", "yes"}:
        config.summarize = True
    return config


def _load_json_config(path: Path, base: AppConfig) -> AppConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = [SourceConfig(**source) for source in data.get("sources", [])]
    keywords = tuple(data.get("keywords", base.keywords))
    return AppConfig(
        sources=sources,
        keywords=keywords,
        state_path=Path(data.get("state_path", base.state_path)),
        sendgrid_api_key=data.get("sendgrid_api_key", base.sendgrid_api_key),
        from_email=data.get("from_email", base.from_email),
        from_name=data.get("from_name", base.from_name),
        to_email=data.get("to_email", base.to_email),
        dry_run=bool(data.get("dry_run", base.dry_run)),
        summarize=bool(data.get("summarize", base.summarize)),
        openrouter_api_key=data.get("openrouter_api_key", base.openrouter_api_key),
        summarizer_model=data.get("summarizer_model", base.summarizer_model),
    )
