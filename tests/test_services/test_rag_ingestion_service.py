from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.models import PipelineResult
from services.rag_ingestion_service import RagIngestionService


def _make_service_with_settings():
    rag_client = MagicMock()
    rag_client.is_configured = MagicMock(return_value=True)
    rag_client.upsert_documents = AsyncMock(return_value=1)

    service = RagIngestionService(rag_client=rag_client)
    # 테스트 환경에서는 Settings를 최소 형태로 주입한다.
    service._settings = SimpleNamespace(  # type: ignore[attr-defined]
        rag_data_stores={},
        gcp=SimpleNamespace(data_store_id="test-data-store"),
        app=SimpleNamespace(
            rag_ingestion_max_retries=1,
            rag_ingestion_backoff_seconds=0.0,
            rag_ingestion_jitter_seconds=0.0,
        ),
    )
    return service, rag_client


@pytest.mark.asyncio
async def test_rag_ingestion_ingest_pipeline_result_async_awaits_upsert_documents():
    service, rag_client = _make_service_with_settings()
    result = PipelineResult(
        success=True,
        product_name="벅스델타",
        strategy={"summary": "ok", "hook_suggestions": ["hook"]},
    )

    ingested = await service.ingest_pipeline_result_async(result)  # type: ignore[attr-defined]
    assert ingested == 1
    rag_client.upsert_documents.assert_awaited()


def test_rag_ingestion_ingest_pipeline_result_sync_runs_async_upsert_documents():
    service, rag_client = _make_service_with_settings()
    result = PipelineResult(
        success=True,
        product_name="벅스델타",
        strategy={"summary": "ok", "hook_suggestions": ["hook"]},
    )

    ingested = service.ingest_pipeline_result(result)
    assert ingested == 1
    # sync wrapper 내부에서 event loop를 생성해 async upsert를 수행해야 한다.
    rag_client.upsert_documents.assert_awaited()

