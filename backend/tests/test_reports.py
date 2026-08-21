import datetime
from unittest.mock import AsyncMock, patch

import pytest

from api.v1.endpoints import reports as report_endpoints
from services.report import _get_month_bounds, get_monthly_report


def test_monthly_report_returns_service_payload(client, db_session, test_user):
    expected = {
        "month": 3,
        "year": 2026,
        "month_summary": {"total_expenses": 2, "total_amount": 70.0},
        "category_breakdown": [],
        "top_5_categories": [],
        "expenses": [],
        "start_at": "2026-03-01T00:00:00+00:00",
        "end_at": "2026-03-31T23:59:59.999999+00:00",
    }

    with patch.object(
        report_endpoints,
        "get_monthly_report",
        AsyncMock(return_value=expected),
    ) as get_monthly_report_mock:
        response = client.get("/api/v1/reports/monthly", params={"month": 3})

    assert response.status_code == 200
    assert response.json() == expected
    get_monthly_report_mock.assert_awaited_once_with(
        db_session, test_user, month=3, year=None
    )


def test_monthly_report_accepts_explicit_year(client, db_session, test_user):
    expected = {
        "month": 12,
        "year": 2020,
        "month_summary": {"total_expenses": 0, "total_amount": 0.0},
        "category_breakdown": [],
        "top_5_categories": [],
        "expenses": [],
        "start_at": "2020-12-01T00:00:00+00:00",
        "end_at": "2020-12-31T23:59:59.999999+00:00",
    }

    with patch.object(
        report_endpoints,
        "get_monthly_report",
        AsyncMock(return_value=expected),
    ) as get_monthly_report_mock:
        response = client.get(
            "/api/v1/reports/monthly", params={"month": 12, "year": 2020}
        )

    assert response.status_code == 200
    assert response.json() == expected
    get_monthly_report_mock.assert_awaited_once_with(
        db_session, test_user, month=12, year=2020
    )


def test_monthly_report_validates_required_query(client):
    response = client.get("/api/v1/reports/monthly")

    assert response.status_code == 422


# --- Regression coverage for the year-handling bug in _get_month_bounds ---
# Previously, _get_month_bounds always used the *current* calendar year and
# ignored any requested year entirely, so historical reports silently
# returned bounds for the wrong year.

def test_get_month_bounds_uses_explicit_year_not_current_year():
    start_at, end_at = _get_month_bounds(month=6, year=2021)

    assert start_at == datetime.datetime(2021, 6, 1, 0, 0, 0, tzinfo=datetime.UTC)
    assert end_at == datetime.datetime(
        2021, 6, 30, 23, 59, 59, 999999, tzinfo=datetime.UTC
    )


def test_get_month_bounds_defaults_to_current_year_when_omitted():
    start_at, _ = _get_month_bounds(month=1)
    assert start_at.year == datetime.datetime.now(datetime.UTC).year


def test_get_month_bounds_handles_december_year_boundary():
    start_at, end_at = _get_month_bounds(month=12, year=2023)

    assert start_at == datetime.datetime(2023, 12, 1, 0, 0, 0, tzinfo=datetime.UTC)
    assert end_at.year == 2023
    assert end_at.month == 12
    assert end_at.day == 31


def test_get_month_bounds_rejects_invalid_year():
    with pytest.raises(ValueError):
        _get_month_bounds(month=5, year=0)


@pytest.mark.asyncio
async def test_get_monthly_report_uses_requested_year_for_bounds():
    # A user querying June for a past year should get bounds scoped to that
    # year, not silently coerced to the current year.
    class _FakeUser:
        id = 1

    with patch(
        "services.report.expenses_repo.list_for_user", AsyncMock(return_value=[])
    ), patch(
        "services.report.categories_repo.list_for_user", AsyncMock(return_value=[])
    ):
        report = await get_monthly_report(
            db=object(), user=_FakeUser(), month=6, year=2019
        )

    assert report["year"] == 2019
    assert report["start_at"].startswith("2019-06-01")
    assert report["end_at"].startswith("2019-06-30")
