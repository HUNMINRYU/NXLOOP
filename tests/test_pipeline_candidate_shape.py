from __future__ import annotations

from datetime import datetime

from services.pipeline.types import AuthorInfo, Candidate


def test_candidate_accepts_title_category_and_metadata() -> None:
    candidate = Candidate(
        id="c1",
        title="Hello",
        content="World",
        author=AuthorInfo(username="u1"),
        created_at=datetime.now(),
        like_count=0,
        category="general",
    )

    # pipeline stages expect these attributes to exist
    assert candidate.title == "Hello"
    assert candidate.category == "general"
    assert isinstance(candidate.metadata, dict)

