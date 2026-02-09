from services.ctr_ranker_metrics import ndcg_at_k, spearman_corr, top1_hit


def test_spearman_corr_perfect_positive():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [10.0, 20.0, 30.0, 40.0]
    assert abs(spearman_corr(a, b) - 1.0) < 1e-9


def test_spearman_corr_perfect_negative():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [40.0, 30.0, 20.0, 10.0]
    assert abs(spearman_corr(a, b) - (-1.0)) < 1e-9


def test_top1_hit_matches_best_item():
    pred = [0.1, 0.2, 0.05]
    true = [0.0, 1.0, 0.5]
    assert top1_hit(pred, true) == 1.0


def test_ndcg_at_k_in_range():
    pred = [0.1, 0.2, 0.05, 0.9]
    true = [0.0, 1.0, 0.5, 2.0]
    v = ndcg_at_k(pred, true, k=3)
    assert 0.0 <= v <= 1.0

