#!/bin/bash
export PYTHONPATH=src
# 가상 환경이 활성화되지 않은 상태라면 대비하여 경로 지정 실행
./.venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000
