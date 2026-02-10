from pydantic import BaseModel, ValidationError


def test_summarize_validation_error_includes_loc_and_msg():
    from services.pipeline_runner import summarize_validation_error

    class M(BaseModel):
        youtube_count: int

    try:
        M(youtube_count="nope")
    except ValidationError as e:
        summary = summarize_validation_error(e)
        assert "youtube_count" in summary
        assert "Invalid pipeline config" in summary
    else:
        raise AssertionError("expected ValidationError")

