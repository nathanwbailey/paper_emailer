from paper_emailer.emailer import build_digest_email
from paper_emailer.models import Digest, RankedItem, SourceItem


def test_build_digest_email_contains_branding_and_item_link():
    item = RankedItem(
        item=SourceItem(
            title="Efficient training for sustainable AI",
            url="https://example.com/paper",
            source="arXiv",
            summary="An efficient training approach.",
        ),
        score=12,
        reasons=("efficient training", "sustainable ai"),
    )
    digest = Digest(items=(item,))

    message = build_digest_email(digest, "from@example.com", "to@example.com", "Digest")

    assert message["Subject"] == "1 new sustainable AI paper/article"
    assert "Efficient training for sustainable AI" in message.get_body(preferencelist=("html",)).get_content()
    assert "https://example.com/paper" in message.get_body(preferencelist=("plain",)).get_content()
