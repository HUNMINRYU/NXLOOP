"""Bloom Filter - 메모리 효율적인 중복 탐지"""

import hashlib
import math
from collections.abc import Iterable


class BloomFilter:
    """
    Bloom Filter 구현 (bitarray 대신 bytearray 사용으로 외부 의존성 제거)
    Configurable false positive rate로 메모리 효율적 중복 탐지
    """

    def __init__(self, expected_items: int = 10000, fp_rate: float = 0.01):
        """
        Args:
            expected_items: 예상 항목 수
            fp_rate: 허용 false positive 비율 (기본 1%)
        """
        self.expected_items = max(expected_items, 1)
        self.fp_rate = fp_rate

        # 최적 비트 수 계산: m = -(n * ln(p)) / (ln(2)^2)
        self.size = max(
            int(-expected_items * math.log(fp_rate) / (math.log(2) ** 2)), 64
        )
        # 최적 해시 함수 수: k = (m/n) * ln(2)
        self.num_hashes = max(int((self.size / expected_items) * math.log(2)), 1)

        self._bits = bytearray((self.size + 7) // 8)
        self._count = 0

    def _get_bit(self, index: int) -> bool:
        byte_idx = index // 8
        bit_idx = index % 8
        return bool(self._bits[byte_idx] & (1 << bit_idx))

    def _set_bit(self, index: int) -> None:
        byte_idx = index // 8
        bit_idx = index % 8
        self._bits[byte_idx] |= 1 << bit_idx

    def _hash_positions(self, item: str) -> list[int]:
        """Double hashing으로 k개의 해시 위치 생성"""
        h1 = int(hashlib.md5(item.encode("utf-8")).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode("utf-8")).hexdigest(), 16)
        return [(h1 + i * h2) % self.size for i in range(self.num_hashes)]

    def add(self, item: str) -> None:
        """항목 추가"""
        for pos in self._hash_positions(item):
            self._set_bit(pos)
        self._count += 1

    def contains(self, item: str) -> bool:
        """항목 존재 여부 확인 (false positive 가능, false negative 불가)"""
        return all(self._get_bit(pos) for pos in self._hash_positions(item))

    def bulk_add(self, items: Iterable[str]) -> None:
        """여러 항목 일괄 추가"""
        for item in items:
            self.add(item)

    @property
    def count(self) -> int:
        return self._count

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    def __len__(self) -> int:
        return self._count
