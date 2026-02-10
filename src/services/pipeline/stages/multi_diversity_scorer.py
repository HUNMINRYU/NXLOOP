"""Multi-Dimensional Diversity Scorer - Author, Topic, Sentiment 차원"""


from services.pipeline.types import Candidate


class DiversityDimension:
    """단일 diversity 차원"""

    def __init__(self, decay: float = 0.7, floor: float = 0.3):
        self.decay = decay
        self.floor = floor
        self._counts: dict[str, int] = {}

    def get_multiplier(self, key: str) -> float:
        count = self._counts.get(key, 0)
        if count == 0:
            self._counts[key] = 1
            return 1.0
        multiplier = (1.0 - self.floor) * (self.decay ** count) + self.floor
        self._counts[key] = count + 1
        return multiplier

    def reset(self) -> None:
        self._counts.clear()


class MultiDiversityScorer:
    """
    3차원 diversity: author, topic, sentiment
    각 차원의 penalty를 곱셈으로 결합
    """

    def __init__(
        self,
        author_decay: float = 0.7,
        author_floor: float = 0.3,
        topic_decay: float = 0.8,
        topic_floor: float = 0.5,
        sentiment_decay: float = 0.9,
        sentiment_floor: float = 0.6,
    ):
        self.author_dim = DiversityDimension(author_decay, author_floor)
        self.topic_dim = DiversityDimension(topic_decay, topic_floor)
        self.sentiment_dim = DiversityDimension(sentiment_decay, sentiment_floor)

    def _get_sentiment_bucket(self, candidate: Candidate) -> str:
        """sentiment_intensity를 3구간으로 버킷화"""
        intensity = candidate.features.sentiment_intensity
        if intensity < 0.33:
            return "low"
        elif intensity < 0.66:
            return "mid"
        return "high"

    def _get_primary_topic(self, candidate: Candidate) -> str:
        """첫 번째 topic 반환 (없으면 'general')"""
        topics = candidate.features.topics
        return topics[0] if topics else "general"

    def apply(self, candidates: list[Candidate]) -> list[Candidate]:
        self.author_dim.reset()
        self.topic_dim.reset()
        self.sentiment_dim.reset()

        for candidate in candidates:
            author_key = candidate.author.username
            topic_key = self._get_primary_topic(candidate)
            sentiment_key = self._get_sentiment_bucket(candidate)

            author_mult = self.author_dim.get_multiplier(author_key)
            topic_mult = self.topic_dim.get_multiplier(topic_key)
            sentiment_mult = self.sentiment_dim.get_multiplier(sentiment_key)

            combined = author_mult * topic_mult * sentiment_mult
            candidate.score.final_score *= combined
            candidate.score.weighted_components["multi_diversity"] = round(combined, 3)

        return sorted(candidates, key=lambda c: c.score.final_score, reverse=True)
