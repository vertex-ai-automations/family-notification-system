import pytest
from app.utils.retry import with_retry


def test_with_retry_returns_value_on_first_success():
    calls = []
    def fn():
        calls.append(1)
        return "ok"
    assert with_retry(fn, attempts=3, base_delay=0) == "ok"
    assert len(calls) == 1


def test_with_retry_succeeds_after_failures():
    calls = []
    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("transient")
        return "recovered"
    assert with_retry(fn, attempts=3, base_delay=0) == "recovered"
    assert len(calls) == 3


def test_with_retry_raises_after_max_attempts():
    calls = []
    def fn():
        calls.append(1)
        raise RuntimeError("permanent")
    with pytest.raises(RuntimeError, match="permanent"):
        with_retry(fn, attempts=3, base_delay=0)
    assert len(calls) == 3
