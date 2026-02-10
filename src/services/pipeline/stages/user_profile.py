"""User Profile - 제품/채널별 선호도 학습"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UserProfile:
    """사용자 선호 프로필"""

    product_id: str = ""
    preferred_features: dict[str, float] = field(default_factory=dict)
    topic_affinities: dict[str, float] = field(default_factory=dict)
    interaction_count: int = 0


class UserProfileManager:
    """
    DB에서 프로필 로드/저장, 과거 선택 결과로부터 선호도 학습.
    DB 세션은 외부에서 주입.
    """

    def __init__(self, db_session: Any = None):
        self._db = db_session
        # DB 없이도 in-memory로 동작 (테스트/개발용)
        self._cache: dict[str, UserProfile] = {}

    async def load_profile(self, product_id: str) -> UserProfile | None:
        """프로필 로드 (DB 우선, 없으면 캐시)"""
        if product_id in self._cache:
            return self._cache[product_id]

        if self._db is not None:
            try:
                return await self._load_from_db(product_id)
            except Exception as e:
                logger.warning(f"프로필 DB 로드 실패: {e}")

        return None

    async def save_profile(self, profile: UserProfile) -> None:
        """프로필 저장"""
        self._cache[profile.product_id] = profile

        if self._db is not None:
            try:
                await self._save_to_db(profile)
            except Exception as e:
                logger.warning(f"프로필 DB 저장 실패: {e}")

    def learn_from_selections(
        self,
        profile: UserProfile,
        selected_features: list[dict[str, float]],
        learning_rate: float = 0.1,
    ) -> UserProfile:
        """선택된 결과로부터 선호도 학습 (exponential moving average)"""
        if not selected_features:
            return profile

        for feat_dict in selected_features:
            for feat_name, feat_value in feat_dict.items():
                if feat_name in ("keywords", "topics"):
                    continue
                current = profile.preferred_features.get(feat_name, 0.0)
                profile.preferred_features[feat_name] = (
                    current * (1 - learning_rate) + feat_value * learning_rate
                )

        profile.interaction_count += 1
        return profile

    async def _load_from_db(self, product_id: str) -> UserProfile | None:
        """DB에서 프로필 로드"""
        from sqlalchemy import select

        from infrastructure.database.models import UserProfileModel

        stmt = select(UserProfileModel).where(
            UserProfileModel.product_id == product_id
        )
        result = await self._db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return UserProfile(
            product_id=row.product_id,
            preferred_features=json.loads(row.preferences_json or "{}"),
            topic_affinities=json.loads(row.topic_affinities_json or "{}"),
            interaction_count=row.interaction_count,
        )

    async def _save_to_db(self, profile: UserProfile) -> None:
        """DB에 프로필 저장 (upsert)"""
        from sqlalchemy import select

        from infrastructure.database.models import UserProfileModel

        stmt = select(UserProfileModel).where(
            UserProfileModel.product_id == profile.product_id
        )
        result = await self._db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            row = UserProfileModel(product_id=profile.product_id)
            self._db.add(row)

        row.preferences_json = json.dumps(profile.preferred_features)
        row.topic_affinities_json = json.dumps(profile.topic_affinities)
        row.interaction_count = profile.interaction_count
        await self._db.commit()
