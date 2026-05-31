from __future__ import annotations

from email.message import EmailMessage
from html import escape
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import Digest, RankedItem


def build_digest_email(digest: Digest, from_email: str, to_email: str, from_name: str) -> EmailMessage:
    subject = _subject_for_digest(digest)
    html = _render_html(digest)
    text = _render_text(digest)

    message = EmailMessage()
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def send_sendgrid(message: EmailMessage, api_key: str) -> None:
    payload = {
        "personalizations": [{"to": [{"email": message["To"]}]}],
        "from": _parse_from_header(message["From"]),
        "subject": message["Subject"],
        "content": [
            {"type": "text/plain", "value": message.get_body(preferencelist=("plain",)).get_content()},
            {"type": "text/html", "value": message.get_body(preferencelist=("html",)).get_content()},
        ],
    }
    request = Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "paper-emailer/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            response.read()
        logging.info("email sent via sendgrid")
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"SendGrid request failed: HTTP {error.code} {error.reason} — {body}") from error
    except URLError as error:
        raise RuntimeError(f"SendGrid request failed: {error.reason}") from error


def _subject_for_digest(digest: Digest) -> str:
    count = len(digest.items)
    if count == 1:
        return "1 new sustainable AI paper/article"
    return f"{count} new sustainable AI papers/articles"


def _render_html(digest: Digest) -> str:
    if not digest.items:
        return _html_page("No new sustainable AI items today", "No matching papers or articles were found today.")
    rows = []
    for ranked in digest.items:
        rows.append(_render_item_html(ranked))
    return _html_page(
        "Today's sustainable AI digest",
        "",
        extra_html="".join(rows),
    )


def _render_text(digest: Digest) -> str:
    lines = ["Sustainable AI digest", ""]
    if not digest.items:
        lines.append("No matching papers or articles were found today.")
        return "\n".join(lines)
    for ranked in digest.items:
        lines.append(f"- {ranked.item.title} ({ranked.item.source})")
        lines.append(f"  {ranked.item.url}")
        if ranked.reasons:
            lines.append(f"  matched: {', '.join(ranked.reasons)}")
    return "\n".join(lines)


def _render_item_html(ranked: RankedItem) -> str:
    reasons = ", ".join(escape(reason) for reason in ranked.reasons)
    authors = escape(", ".join(ranked.item.authors)) if ranked.item.authors else ""
    summary = escape(ranked.item.summary) if ranked.item.summary else ""
    return f"""
    <div class="card">
      <div class="meta">{escape(ranked.item.source)} · relevance {ranked.score:.0%}</div>
      <h2><a href="{escape(ranked.item.url)}">{escape(ranked.item.title)}</a></h2>
      {f'<div class="authors">{authors}</div>' if authors else ''}
      {f'<p>{summary}</p>' if summary else ''}
      {f'<div class="reasons">Matched: {reasons}</div>' if reasons else ''}
    </div>
    """


def _html_page(title: str, message: str, extra_html: str = "") -> str:
    body = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <style>
          body {{ margin: 0; padding: 0; background: #f4f7fb; color: #172033; font-family: Arial, sans-serif; }}
          .wrap {{ max-width: 760px; margin: 0 auto; padding: 32px 16px; }}
          .panel {{ background: #ffffff; border-radius: 18px; padding: 28px; box-shadow: 0 10px 32px rgba(18, 39, 74, 0.08); }}
          h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.2; }}
          .intro {{ color: #5d6b82; font-size: 15px; line-height: 1.6; margin-bottom: 24px; }}
          .card {{ border: 1px solid #e6ebf2; border-radius: 14px; padding: 18px; margin: 16px 0; background: #fbfcfe; }}
          .card h2 {{ margin: 8px 0; font-size: 20px; line-height: 1.35; }}
          .card a {{ color: #153b77; text-decoration: none; }}
          .meta, .authors, .reasons {{ color: #627089; font-size: 13px; line-height: 1.5; }}
          p {{ margin: 12px 0 0; font-size: 14px; line-height: 1.6; color: #24324a; }}
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="panel">
            <h1>{escape(title)}</h1>
            <div class="intro">{escape(message)}</div>
            {extra_html}
          </div>
        </div>
      </body>
    </html>
    """
    return body


def _parse_from_header(header: str) -> dict[str, str]:
    if "<" in header and ">" in header:
        name, email = header.split("<", 1)
        return {"email": email.rstrip(">"), "name": name.strip()}
    return {"email": header, "name": ""}
