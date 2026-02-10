"""API Response 스키마"""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ScheduleResponse(BaseModel):
    """스케줄 조회 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None

    gcp_job_id: str
    cron_expression: str
    timezone: str

    product_name: str
    config: dict[str, Any] | None = None
    enabled: bool
    version: int = 1

    last_executed_at: datetime | None
    next_execution_at: datetime | None

    created_at: datetime
    updated_at: datetime

    @field_validator("config", mode="before")
    @classmethod
    def parse_config_json(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return None
