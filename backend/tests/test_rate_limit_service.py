import pytest

from backend.app.services.rate_limit_service import (
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    check_rate_limit,
    reset_rate_limit,
)


@pytest.fixture(autouse=True)
def clean_rate_limit_history() -> None:
    reset_rate_limit()

    yield

    reset_rate_limit()


def test_first_request_is_allowed() -> None:
    result = check_rate_limit(
        "session-first",
        current_time=1000.0,
    )

    assert result.allowed is True
    assert result.limit == RATE_LIMIT_REQUESTS
    assert result.remaining == RATE_LIMIT_REQUESTS - 1
    assert result.retry_after_seconds == 0


def test_first_ten_requests_are_allowed() -> None:
    results = [
        check_rate_limit(
            "session-ten",
            current_time=1000.0,
        )
        for _ in range(RATE_LIMIT_REQUESTS)
    ]

    assert all(result.allowed for result in results)
    assert results[-1].remaining == 0
    assert results[-1].retry_after_seconds == 0


def test_eleventh_request_is_rejected() -> None:
    identifier = "session-eleven"

    for _ in range(RATE_LIMIT_REQUESTS):
        check_rate_limit(
            identifier,
            current_time=1000.0,
        )

    result = check_rate_limit(
        identifier,
        current_time=1000.0,
    )

    assert result.allowed is False
    assert result.limit == RATE_LIMIT_REQUESTS
    assert result.remaining == 0
    assert (
        result.retry_after_seconds
        == RATE_LIMIT_WINDOW_SECONDS
    )


def test_requests_are_isolated_by_identifier() -> None:
    for _ in range(RATE_LIMIT_REQUESTS):
        check_rate_limit(
            "session-full",
            current_time=1000.0,
        )

    other_result = check_rate_limit(
        "session-other",
        current_time=1000.0,
    )

    assert other_result.allowed is True
    assert other_result.remaining == RATE_LIMIT_REQUESTS - 1


def test_request_is_allowed_after_window_expires() -> None:
    identifier = "session-expired"

    for _ in range(RATE_LIMIT_REQUESTS):
        check_rate_limit(
            identifier,
            current_time=1000.0,
        )

    blocked_result = check_rate_limit(
        identifier,
        current_time=1059.0,
    )

    allowed_result = check_rate_limit(
        identifier,
        current_time=1060.0,
    )

    assert blocked_result.allowed is False
    assert blocked_result.retry_after_seconds == 1

    assert allowed_result.allowed is True
    assert allowed_result.remaining == RATE_LIMIT_REQUESTS - 1
    assert allowed_result.retry_after_seconds == 0


def test_reset_one_identifier() -> None:
    identifier = "session-reset"

    for _ in range(RATE_LIMIT_REQUESTS):
        check_rate_limit(
            identifier,
            current_time=1000.0,
        )

    reset_rate_limit(identifier)

    result = check_rate_limit(
        identifier,
        current_time=1000.0,
    )

    assert result.allowed is True
    assert result.remaining == RATE_LIMIT_REQUESTS - 1


def test_reset_all_identifiers() -> None:
    for identifier in ("session-a", "session-b"):
        for _ in range(RATE_LIMIT_REQUESTS):
            check_rate_limit(
                identifier,
                current_time=1000.0,
            )

    reset_rate_limit()

    result_a = check_rate_limit(
        "session-a",
        current_time=1000.0,
    )
    result_b = check_rate_limit(
        "session-b",
        current_time=1000.0,
    )

    assert result_a.allowed is True
    assert result_b.allowed is True
