import json
from unittest.mock import MagicMock, patch

import pytest

from paper_emailer.cli import main
from paper_emailer.emailer import SendGridCreditExceededError
from paper_emailer.models import RankedItem, SourceItem


def test_dry_run_exits_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("PAPER_EMAILER_STATE_PATH", str(tmp_path / "state.sqlite3"))
    with patch("paper_emailer.cli.fetch_sources", return_value=[]), \
         patch("paper_emailer.cli.send_sendgrid") as mock_send:
        result = main.__wrapped__() if hasattr(main, "__wrapped__") else _run_main(["--dry-run"])
    assert result == 0
    mock_send.assert_not_called()


def _run_main(args: list[str]) -> int:
    import sys
    sys.argv = ["paper-emailer"] + args
    return main()


def test_missing_api_key_exits_early(tmp_path, monkeypatch):
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "from@example.com")
    monkeypatch.setenv("SENDGRID_TO_EMAIL", "to@example.com")
    monkeypatch.setenv("PAPER_EMAILER_STATE_PATH", str(tmp_path / "state.sqlite3"))
    with patch("paper_emailer.cli.fetch_sources") as mock_fetch:
        with pytest.raises(SystemExit):
            _run_main([])
        mock_fetch.assert_not_called()


def test_missing_to_email_exits_early(tmp_path, monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "key")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "from@example.com")
    monkeypatch.delenv("SENDGRID_TO_EMAIL", raising=False)
    monkeypatch.setenv("PAPER_EMAILER_STATE_PATH", str(tmp_path / "state.sqlite3"))
    with patch("paper_emailer.cli.fetch_sources") as mock_fetch:
        with pytest.raises(SystemExit):
            _run_main([])
        mock_fetch.assert_not_called()


def test_json_config_loaded(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "sources": [{"kind": "arxiv", "value": "green ai", "content_type": "paper"}],
        "from_email": "from@example.com",
        "to_email": "to@example.com",
        "dry_run": True,
    }))
    monkeypatch.setenv("PAPER_EMAILER_STATE_PATH", str(tmp_path / "state.sqlite3"))
    with patch("paper_emailer.cli.fetch_sources", return_value=[]) as mock_fetch, \
         patch("paper_emailer.cli.send_sendgrid"):
        result = _run_main(["--config", str(cfg), "--dry-run"])
    assert result == 0
    call_sources = mock_fetch.call_args[0][0]
    assert len(call_sources) == 1
    assert call_sources[0].kind == "arxiv"
    assert call_sources[0].value == "green ai"


def test_email_sent_even_with_no_new_items(tmp_path, monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "key")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "from@example.com")
    monkeypatch.setenv("SENDGRID_TO_EMAIL", "to@example.com")
    monkeypatch.setenv("PAPER_EMAILER_STATE_PATH", str(tmp_path / "state.sqlite3"))
    with patch("paper_emailer.cli.fetch_sources", return_value=[]), \
         patch("paper_emailer.cli.send_sendgrid") as mock_send:
        result = _run_main([])
    assert result == 0
    mock_send.assert_called_once()


def test_sendgrid_credit_exhausted_returns_zero_without_recording_state(tmp_path, monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "key")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "from@example.com")
    monkeypatch.setenv("SENDGRID_TO_EMAIL", "to@example.com")
    monkeypatch.setenv("PAPER_EMAILER_STATE_PATH", str(tmp_path / "state.sqlite3"))
    ranked = RankedItem(item=SourceItem(title="t", url="https://example.com", source="arXiv"), score=0.9)
    mock_state = MagicMock()
    mock_state.filter_new.return_value = [ranked]
    with patch("paper_emailer.cli.fetch_sources", return_value=[ranked.item]), \
         patch("paper_emailer.cli.rank_items", return_value=[ranked]), \
         patch("paper_emailer.cli.StateStore", return_value=mock_state), \
         patch("paper_emailer.cli.send_sendgrid", side_effect=SendGridCreditExceededError("Maximum credits exceeded")):
        result = _run_main([])
    assert result == 0
    mock_state.record_sent.assert_not_called()
