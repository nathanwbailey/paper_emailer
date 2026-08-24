from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import logging

from .config import AppConfig, SourceConfig, load_config
from .emailer import SendGridCreditExceededError, build_digest_email, send_sendgrid
from .filtering import rank_items
from .models import Digest
from .sources import fetch_sources
from .state import StateStore
from .summarizer import summarize_items


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Daily sustainable AI paper digest")
    parser.add_argument("--config", help="Path to JSON config file", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Render locally without sending")
    parser.add_argument("--show-email", action="store_true", help="Print the rendered email")
    parser.add_argument("--summarize", action="store_true", help="Summarize items via LLM (off by default)")
    return parser


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args()
    config = load_config(args.config)
    if args.dry_run:
        config.dry_run = True
    if args.summarize:
        config.summarize = True

    if not config.dry_run:
        if not config.sendgrid_api_key:
            raise SystemExit("SENDGRID_API_KEY is required")
        if not config.from_email or not config.to_email:
            raise SystemExit("SENDGRID_FROM_EMAIL and SENDGRID_TO_EMAIL are required")

    if not config.sources:
        config.sources = [
            # broad concept queries
            SourceConfig(kind="arxiv", value="sustainable ai", query="sustainable ai", content_type="paper"),
            SourceConfig(kind="arxiv", value="green ai", query="green ai computing", content_type="paper"),
            # title-targeted: catches vocabulary arXiv-concept queries miss
            SourceConfig(kind="arxiv", value="ti:energy AND ti:LLM", query="ti:energy AND ti:LLM", content_type="paper"),
            SourceConfig(kind="arxiv", value="ti:carbon AND ti:footprint", query="ti:carbon AND ti:footprint", content_type="paper"),
            SourceConfig(kind="arxiv", value="ti:energy AND ti:efficient AND ti:neural", query="ti:energy AND ti:efficient AND ti:neural", content_type="paper"),
            # cs.CY = Computers and Society — where environmental impact papers are classified
            SourceConfig(kind="arxiv", value="cat:cs.CY AND (abs:energy OR abs:carbon OR abs:sustainability)", query="cat:cs.CY AND (abs:energy OR abs:carbon OR abs:sustainability)", content_type="paper"),
            # web search for news/articles
            SourceConfig(kind="search", value="sustainable ai research", query="sustainable ai research", content_type="article"),
        ]

    logging.info("fetching from %d source(s)", len(config.sources))
    items = fetch_sources(config.sources)
    logging.info("%d item(s) fetched", len(items))
    ranked = rank_items(items, config.keywords)
    logging.info("%d item(s) after ranking", len(ranked))
    state = StateStore(config.state_path)
    new_items = state.filter_new(ranked)
    logging.info("%d new item(s) to send", len(new_items))
    if config.summarize:
        new_items = summarize_items(new_items, config.openrouter_api_key, config.summarizer_model)
    digest = Digest(items=tuple(new_items))

    message = build_digest_email(digest, config.from_email, config.to_email, config.from_name)
    if args.show_email or config.dry_run:
        print(message.as_string())

    if config.dry_run:
        return 0

    try:
        send_sendgrid(message, config.sendgrid_api_key)
    except SendGridCreditExceededError as error:
        logging.warning("skipping send: SendGrid credits exceeded (%s)", error)
        return 0
    if new_items:
        state.record_sent(new_items, datetime.now(timezone.utc).isoformat())
    state.prune()
    return 0
