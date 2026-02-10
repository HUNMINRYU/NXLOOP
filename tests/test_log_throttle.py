from __future__ import annotations

import pytest

from utils import log_throttle


@pytest.fixture(autouse=True)
def _reset_throttle_state():
    log_throttle._reset_for_tests()
    yield
    log_throttle._reset_for_tests()


def test_should_log_throttled_first_call_is_true_then_false_within_interval():
    key = "pipeline_status:task-1"
    assert log_throttle.should_log_throttled(key, interval_sec=10.0, now=100.0) is True
    assert log_throttle.should_log_throttled(key, interval_sec=10.0, now=105.0) is False


def test_should_log_throttled_becomes_true_after_interval():
    key = "pipeline_status:task-1"
    assert log_throttle.should_log_throttled(key, interval_sec=10.0, now=100.0) is True
    assert log_throttle.should_log_throttled(key, interval_sec=10.0, now=110.0) is True


def test_should_log_throttled_isolated_per_key():
    assert log_throttle.should_log_throttled("k1", interval_sec=10.0, now=100.0) is True
    assert log_throttle.should_log_throttled("k2", interval_sec=10.0, now=100.0) is True
    assert (
        log_throttle.should_log_throttled("k1", interval_sec=10.0, now=105.0) is False
    )
    assert (
        log_throttle.should_log_throttled("k2", interval_sec=10.0, now=105.0) is False
    )


def test_should_log_throttled_interval_zero_or_less_always_true():
    key = "any"
    assert log_throttle.should_log_throttled(key, interval_sec=0.0, now=100.0) is True
    assert log_throttle.should_log_throttled(key, interval_sec=-1.0, now=100.0) is True
