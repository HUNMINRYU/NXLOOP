from pathlib import Path

COMPONENT_PATH = Path("frontend/src/components/PipelineSlugClient.tsx")


def _read_component() -> str:
    return COMPONENT_PATH.read_text(encoding="utf-8")


def test_ctr_ranking_call_is_guarded_by_pipeline_result_readiness() -> None:
    source = _read_component()
    assert "pipeline.pipelineResult?.task_id !== taskId" in source
    assert "pipeline.pipelineResult?.status !== 'success'" in source


def test_ctr_404_error_is_silently_ignored() -> None:
    source = _read_component()
    assert "const status =" in source
    assert "status === 404" in source


def test_ctr_auth_error_is_silently_ignored() -> None:
    source = _read_component()
    assert "status === 401" in source
    assert "status === 403" in source


def test_ctr_ranking_uses_partial_failure_tolerant_parallel_calls() -> None:
    source = _read_component()
    assert "Promise.allSettled" in source
    assert "if (r.status === 'fulfilled')" in source


def test_selected_output_sync_effect_reacts_to_selected_value_changes() -> None:
    source = _read_component()
    assert "selectedOutputs?.thumbnail?.url" in source
    assert "selectedOutputs?.video?.url" in source
