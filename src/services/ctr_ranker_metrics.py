from __future__ import annotations

import math


def _ranks(values: list[float]) -> list[float]:
    """
    평균 순위(ties -> average rank)로 변환한다.
    rank는 1..n (값이 클수록 rank가 작아지도록: 내림차순)
    """
    n = len(values)
    if n == 0:
        return []

    indexed = list(enumerate(values))
    indexed.sort(key=lambda x: x[1], reverse=True)

    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        v = indexed[i][1]
        while j < n and indexed[j][1] == v:
            j += 1
        # i..j-1 are ties, assign average rank (1-indexed)
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = avg
        i = j
    return ranks


def spearman_corr(a: list[float], b: list[float]) -> float:
    """
    Spearman rank correlation (ties는 평균 순위로 처리).
    """
    if not a or len(a) != len(b):
        return 0.0

    ra = _ranks(a)
    rb = _ranks(b)

    n = len(ra)
    mean_a = sum(ra) / n
    mean_b = sum(rb) / n

    num = sum((x - mean_a) * (y - mean_b) for x, y in zip(ra, rb, strict=True))
    den_a = math.sqrt(sum((x - mean_a) ** 2 for x in ra))
    den_b = math.sqrt(sum((y - mean_b) ** 2 for y in rb))
    if den_a == 0.0 or den_b == 0.0:
        return 0.0
    return float(num / (den_a * den_b))


def top1_hit(pred_scores: list[float], true_scores: list[float]) -> float:
    """
    pred의 top1 아이템이 true의 top1과 일치하면 1.0, 아니면 0.0.
    (동률은 가장 먼저 등장한 인덱스를 사용)
    """
    if not pred_scores or len(pred_scores) != len(true_scores):
        return 0.0
    pred_i = max(range(len(pred_scores)), key=lambda i: pred_scores[i])
    true_i = max(range(len(true_scores)), key=lambda i: true_scores[i])
    return 1.0 if pred_i == true_i else 0.0


def ndcg_at_k(pred_scores: list[float], true_scores: list[float], k: int = 10) -> float:
    """
    점수 기반 NDCG@K.
    true_scores를 relevance로 사용(연속값 허용).
    """
    if not pred_scores or len(pred_scores) != len(true_scores) or k <= 0:
        return 0.0

    n = len(pred_scores)
    kk = min(k, n)

    pred_order = sorted(range(n), key=lambda i: pred_scores[i], reverse=True)[:kk]
    ideal_order = sorted(range(n), key=lambda i: true_scores[i], reverse=True)[:kk]

    def dcg(order: list[int]) -> float:
        s = 0.0
        for rank, idx in enumerate(order):
            rel = float(true_scores[idx])
            # 표준 DCG 변형: (2^rel - 1) / log2(rank+2)
            s += (2.0**rel - 1.0) / math.log2(rank + 2)
        return s

    dcg_val = dcg(pred_order)
    idcg_val = dcg(ideal_order)
    if idcg_val == 0.0:
        return 0.0
    return float(dcg_val / idcg_val)

