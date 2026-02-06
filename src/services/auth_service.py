from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Team, User
from utils.logger import (
    get_logger,
    log_info,
    log_input_data,
    log_output_data,
    log_stage_end,
    log_stage_fail,
    log_stage_start,
    log_warning,
)

logger = get_logger(__name__)


class AuthService:
    def __init__(
        self, secret: str, expire_hours: int, algorithm: str = "HS256"
    ) -> None:
        self._secret = secret
        self._expire_hours = expire_hours
        self._algorithm = algorithm
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, plain: str) -> str:
        trimmed = plain.encode("utf-8")[:72]
        return self._pwd_context.hash(trimmed)

    def verify_password(self, plain: str, hashed: str) -> bool:
        trimmed = plain.encode("utf-8")[:72]
        return self._pwd_context.verify(trimmed, hashed)

    def _create_token(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.email,
            "uid": user.id,
            "role": getattr(user, "role", "editor"),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=self._expire_hours)).timestamp()),
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        log_info(f"   🔑 JWT 토큰 생성: 사용자 {user.email}, 만료: {self._expire_hours}시간")
        return token

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            log_info(f"   ✅ 토큰 검증 성공: 사용자 {payload.get('sub', 'N/A')}")
            return payload
        except JWTError as exc:
            log_warning(f"   ⚠️ 토큰 검증 실패: {exc}")
            raise HTTPException(status_code=401, detail="Invalid token") from exc

    async def signup(
        self,
        session: AsyncSession,
        name: str,
        email: str,
        password: str,
        team_name: str | None = None,
        job_title: str | None = None,
        phone_number: str | None = None,
    ) -> dict[str, Any]:
        log_stage_start("회원가입", f"사용자: {email}")
        log_input_data("이름", name)
        log_input_data("이메일", email)
        log_input_data("팀", team_name or "없음")
        log_input_data("직책", job_title or "없음")

        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            log_stage_fail("회원가입", "유효하지 않은 이메일 형식")
            raise HTTPException(status_code=400, detail="Invalid email")

        exists = await session.scalar(
            select(User).where(User.email == normalized_email)
        )
        if exists:
            log_stage_fail("회원가입", f"이미 존재하는 사용자: {normalized_email}")
            raise HTTPException(status_code=409, detail="User already exists")

        # Team 처리
        team_id = None
        if team_name:
            team = await session.scalar(select(Team).where(Team.name == team_name))
            if not team:
                team = Team(name=team_name)
                session.add(team)
                await session.flush()
                log_info(f"   🏢 새 팀 생성: {team_name}")
            team_id = team.id

        # 첫 가입자 체크
        user_count = await session.scalar(select(func.count()).select_from(User))
        initial_role = "admin" if user_count == 0 else "editor"

        if initial_role == "admin":
            log_info("   👑 첫 번째 사용자 - admin 권한 부여")
        else:
            log_info(f"   👤 일반 사용자 - {initial_role} 권한 부여")

        user = User(
            name=name,
            email=normalized_email,
            password=self.hash_password(password),
            role=initial_role,
            team_id=team_id,
            job_title=job_title,
            phone_number=phone_number,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        log_output_data("사용자 ID", user.id)
        log_output_data("권한", initial_role)
        log_stage_end("회원가입", f"사용자 {normalized_email} 등록 완료")

        return {"token": self._create_token(user)}

    async def login(
        self, session: AsyncSession, email: str, password: str
    ) -> dict[str, Any]:
        log_stage_start("로그인", f"사용자: {email}")

        normalized_email = email.strip().lower()
        log_input_data("이메일", normalized_email)

        user = await session.scalar(select(User).where(User.email == normalized_email))

        if not user:
            log_stage_fail("로그인", f"존재하지 않는 사용자: {normalized_email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not self.verify_password(password, user.password):
            log_stage_fail("로그인", f"비밀번호 불일치: {normalized_email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        log_output_data("사용자 ID", user.id)
        log_output_data("사용자 이름", user.name)
        log_output_data("권한", user.role)
        log_stage_end("로그인", f"사용자 {normalized_email} 로그인 성공")

        return {"token": self._create_token(user)}

    async def get_current_user(self, session: AsyncSession, token: str) -> User:
        log_info("   🔍 현재 사용자 조회 시작")

        payload = self.verify_token(token)
        user_id = payload.get("uid")

        if not user_id:
            log_warning("   ⚠️ 토큰에 사용자 ID 없음")
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await session.get(User, user_id)

        if not user:
            log_warning(f"   ⚠️ 사용자 ID {user_id} 찾을 수 없음")
            raise HTTPException(status_code=401, detail="Invalid token")

        log_info(f"   ✅ 현재 사용자: {user.email} (권한: {user.role})")
        return user

    async def logout(
        self,
        session: AsyncSession,
        token: str | None = None,
    ) -> dict[str, Any]:
        """로그아웃 처리 및 로그 기록"""
        log_stage_start("로그아웃", "사용자 세션 종료")

        user_email = "알 수 없음"
        user_role = "알 수 없음"

        if token:
            try:
                payload = self.verify_token(token)
                user_email = payload.get("sub", "알 수 없음")
                user_id = payload.get("uid")
                user_role = payload.get("role", "알 수 없음")

                if user_id:
                    user = await session.get(User, user_id)
                    if user:
                        user_email = user.email
                        user_role = user.role

                log_output_data("사용자 이메일", user_email)
                log_output_data("사용자 권한", user_role)
            except Exception as e:
                log_warning(f"   ⚠️ 토큰 검증 실패 (만료된 토큰으로 로그아웃): {e}")
        else:
            log_warning("   ⚠️ 토큰 없이 로그아웃 요청 (클라이언트 측 세션 삭제)")

        log_stage_end("로그아웃", f"사용자 {user_email} 로그아웃 완료")

        return {"message": "로그아웃 완료", "email": user_email}


