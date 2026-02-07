from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import secrets

from infrastructure.database.models import Team, User, UserSession
from utils.logger import (
    log_info,
    log_input_data,
    log_output_data,
    log_stage_end,
    log_stage_fail,
    log_stage_start,
    log_warning,
)


class AuthService:
    def __init__(
        self, secret: str, expire_hours: int, algorithm: str = "HS256"
    ) -> None:
        self._secret = secret
        self._expire_hours = expire_hours
        self._algorithm = algorithm
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # 서버 세션 TTL(안전장치). 쿠키는 브라우저 종료 시 사라지게 운용한다.
        self.session_expire_hours = 8

    def hash_password(self, plain: str) -> str:
        trimmed = plain.encode("utf-8")[:72]
        return self._pwd_context.hash(trimmed)

    def verify_password(self, plain: str, hashed: str) -> bool:
        trimmed = plain.encode("utf-8")[:72]
        return self._pwd_context.verify(trimmed, hashed)

    def _create_token(self, user: User) -> str:
        """테스트/내부용 JWT 생성 (role 포함)."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "email": str(user.email),
            "role": str(user.role),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=self._expire_hours)).timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str) -> dict[str, Any]:
        """JWT 검증 후 payload 반환."""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            if not isinstance(payload, dict):
                raise HTTPException(status_code=401, detail="Invalid token payload")
            return payload
        except JWTError as e:
            raise HTTPException(status_code=401, detail="Invalid token") from e




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

        return {"user": user}

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

        return {"user": user}

    def new_csrf_token(self) -> str:
        # 256-bit random token (urlsafe)
        return secrets.token_urlsafe(32)

    async def create_session(self, session: AsyncSession, user: User) -> UserSession:
        now = datetime.now(timezone.utc)
        sid = secrets.token_urlsafe(32)
        sess = UserSession(
            id=sid,
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(hours=self.session_expire_hours),
            revoked_at=None,
        )
        session.add(sess)
        await session.commit()
        return sess

    async def get_user_by_session_id(self, session: AsyncSession, session_id: str) -> User:
        now = datetime.now(timezone.utc)
        sess = await session.get(UserSession, session_id)
        if not sess:
            raise HTTPException(status_code=401, detail="Invalid session")
        if sess.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Session revoked")
        # Handle timezone-naive expires_at from legacy data
        expires = sess.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= now:
            raise HTTPException(status_code=401, detail="Session expired")
        user = await session.get(User, sess.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session")
        return user

    async def delete_session(self, session: AsyncSession, session_id: str) -> None:
        sess = await session.get(UserSession, session_id)
        if not sess:
            return
        sess.revoked_at = datetime.now(timezone.utc)
        await session.commit()

    async def logout(self, session: AsyncSession) -> dict[str, Any]:
        """로그아웃 처리 및 로그 기록 (세션은 엔드포인트에서 delete_session으로 처리)."""
        log_stage_start("로그아웃", "사용자 세션 종료")
        log_stage_end("로그아웃", "로그아웃 완료")
        return {"message": "로그아웃 완료"}


