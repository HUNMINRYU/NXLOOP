from __future__ import annotations

from config.dependencies import ServiceContainer


def test_service_container_provides_pipeline_task_service() -> None:
    container = ServiceContainer(settings=object())

    service = container.pipeline_task_service

    assert service is not None


def test_clear_cache_resets_pipeline_task_service() -> None:
    container = ServiceContainer(settings=object())

    first = container.pipeline_task_service
    container.clear_cache()
    second = container.pipeline_task_service

    assert first is not second
