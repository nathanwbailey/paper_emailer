# Paper Emailer

Daily digest app for sustainable AI papers and articles.

## Run locally

1. Install the package in editable mode with dev extras: `python -m pip install -e ".[dev]"`.
2. Set `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, and `SENDGRID_TO_EMAIL`.
3. Run `paper-emailer --dry-run` to preview the email.
4. Run `paper-emailer --show-email` if you want to print the rendered MIME message.

The digest only includes papers/articles published in the last 14 days.

## Config

You can pass a JSON file with sources:

```json
{
  "sources": [
    {"kind": "arxiv", "value": "sustainable ai", "query": "sustainable ai", "content_type": "paper"},
    {"kind": "search", "value": "sustainable ai", "query": "sustainable ai", "content_type": "article"},
    {"kind": "web", "value": "https://hai.stanford.edu/news/transparency-in-ai-is-on-the-decline", "content_type": "article"}
  ]
}
```

## Deploy without running locally

The simplest hosted option is GitHub Actions:

1. Add the secrets `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, and `SENDGRID_TO_EMAIL` in your repository settings.
2. Commit the workflow in `.github/workflows/daily.yml`.
3. Let the scheduled job run once per day, or trigger it manually from the Actions tab.
4. The workflow caches `.paper_emailer/state.sqlite3` so the app can avoid resending the same items on later runs.
5. The workflow is already guarded against overlapping runs with GitHub Actions concurrency and only requests read access to repository contents.

If you want stronger persistence than a GitHub cache, the next step would be a small VPS with cron or systemd plus a real on-disk state directory.

## Deployment

The next step is a scheduled GitHub Actions workflow that runs the CLI daily and uses SendGrid for delivery.
