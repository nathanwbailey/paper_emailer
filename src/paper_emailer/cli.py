from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone

from .config import AppConfig, SourceConfig, load_config
from .emailer import build_digest_email, send_sendgrid
from .filtering import filter_recent_items, rank_items
from .models import Digest
from .sources import fetch_sources
from .state import StateStore


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Daily sustainable AI paper digest")
    parser.add_argument("--config", help="Path to JSON config file", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Render locally without sending")
    parser.add_argument("--show-email", action="store_true", help="Print the rendered email")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    if args.dry_run:
        config.dry_run = True
    if not config.sources:
        config.sources = [
            SourceConfig(kind="arxiv", value="sustainable ai", query="sustainable ai", content_type="paper"),
            SourceConfig(kind="search", value="sustainable ai", query="sustainable ai", content_type="article"),
        ]

    items = fetch_sources(config.sources)
    items = filter_recent_items(items, days=14)
    ranked = rank_items(items, config.keywords)
    state = StateStore(config.state_path)
    new_items = state.filter_new(ranked)
    digest = Digest(items=tuple(new_items))

    message = build_digest_email(digest, config.from_email, config.to_email, config.from_name)
    if args.show_email or config.dry_run:
        print(message.as_string())

    if config.dry_run:
        return 0

    if not config.sendgrid_api_key:
        raise SystemExit("SENDGRID_API_KEY is required")
    if not config.from_email or not config.to_email:
        raise SystemExit("SENDGRID_FROM_EMAIL and SENDGRID_TO_EMAIL are required")

    if digest.items:
        send_sendgrid(message, config.sendgrid_api_key)
        state.record_sent(new_items, datetime.now(timezone.utc).isoformat())
    return 0
