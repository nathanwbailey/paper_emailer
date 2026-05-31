from __future__ import annotations

import dataclasses
import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import RankedItem, SourceItem


DEFAULT_MODEL = "google/gemma-4-31b-it:free"
_FALLBACK_MODELS = (
    "deepseek/deepseek-v4-flash:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
)
_INTER_REQUEST_DELAY = 2.0
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 5.0


def summarize_items(
    items: list[RankedItem],
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> list[RankedItem]:
    if not items or not api_key:
        return items
    result: list[RankedItem] = []
    for i, ranked in enumerate(items):
        if i > 0:
            time.sleep(_INTER_REQUEST_DELAY)
        try:
            summary = _call_with_fallbacks(ranked.item, api_key, model)
            new_item = dataclasses.replace(ranked.item, summary=summary)
            result.append(dataclasses.replace(ranked, item=new_item))
            logging.info("summarized %r", ranked.item.title[:60])
        except Exception as error:
            logging.warning("summarization failed for %r: %s", ranked.item.title[:60], error)
            result.append(ranked)
    return result


def _call_with_fallbacks(item: SourceItem, api_key: str, model: str) -> str:
    models_to_try = [model, *_FALLBACK_MODELS]
    last_error: Exception = RuntimeError("no models configured")
    for candidate in models_to_try:
        try:
            return _call_openrouter_with_retry(item, api_key, candidate)
        except Exception as error:
            logging.warning("model %r failed for %r: %s", candidate, item.title[:60], error)
            last_error = error
    raise last_error


def _call_openrouter_with_retry(item: SourceItem, api_key: str, model: str) -> str:
    delay = _RETRY_BASE_DELAY
    for attempt in range(_MAX_RETRIES):
        try:
            return _call_openrouter(item, api_key, model)
        except RuntimeError as error:
            if "429" in str(error) and attempt < _MAX_RETRIES - 1:
                logging.warning("rate limited, retrying in %.0fs (attempt %d/%d)", delay, attempt + 1, _MAX_RETRIES)
                time.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError("unreachable")


def _call_openrouter(item: SourceItem, api_key: str, model: str) -> str:
    existing = item.summary or "None provided"
    prompt = (
        "Summarize the following research paper or article in 2-3 clear sentences. "
        "Focus on the key contribution and its relevance to sustainable or energy-efficient AI. "
        "Be concise and factual.\n\n"
        f"Title: {item.title}\n\nExisting abstract/summary: {existing}"
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 350,
    }
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/nathanwbailey/paper_emailer",
            "User-Agent": "paper-emailer/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"OpenRouter connection error: {error.reason}") from error
