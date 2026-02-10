#!/bin/bash
# Nexloop Backend Startup Script

# 프로젝트 루트 권한 보장 및 필수 디렉토리 생성
mkdir -p data outputs

# PYTHONPATH 설정 (src 내부를 루트 패키지로 인식하도록 설정)
export PYTHONPATH=$(pwd)/src

echo "------------------------------------------------"
echo "🚀 Nexloop 백엔드를 시작합니다..."
echo "📂 DB 경로: $(pwd)/data/auth.db"
echo "🌐 주소: http://0.0.0.0:8000"
echo "------------------------------------------------"

# 가상 환경 우선 실행, 없으면 시스템 uvicorn 사용
if [ -f "./.venv/bin/uvicorn" ]; then
    ./.venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000
else
    uvicorn app:app --reload --host 0.0.0.0 --port 8000
fi
