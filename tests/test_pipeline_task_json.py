from datetime import datetime, timezone

from infrastructure.database.models import PipelineTask


def test_pipeline_task_dumps_serializes_datetime():
    payload = {"now": datetime(2026, 2, 10, 5, 50, 16, tzinfo=timezone.utc)}

    # 현재 구현은 datetime을 직렬화하지 못해 TypeError가 발생한다.
    # 이 테스트가 먼저 RED가 된 뒤, dumps를 수정해서 GREEN으로 만든다.
    json_str = PipelineTask.dumps(payload)

    assert "\"now\"" in json_str
    # ISO-8601 형태로 직렬화되는지 간단히 확인
    assert "2026-02-10T05:50:16" in json_str

