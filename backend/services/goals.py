from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from repositories import expenses as expenses_repo
from repositories import goals as goals_repo


def _validate_goal_id(goal_id: int) -> None:
    if goal_id <= 0:
        raise ValueError("goal_id must be > 0")


def _validate_goal_limit(goal_limit: float) -> None:
    if goal_limit is None:
        raise ValueError("goal_limit is required")
    if goal_limit <= 0:
        raise ValueError("goal_limit must be > 0")


def _validate_month(month: int) -> None:
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")


def _resolve_year(year: Optional[int]) -> int:
    resolved = datetime.datetime.now(datetime.UTC).year if year is None else year
    if resolved < 1:
        raise ValueError("year must be >= 1")
    return resolved


async def set_monthly_goals(
    db: AsyncSession,
    *,
    user: User,
    goal_limit: float,
    goal_id: int | None = None,
):
    """
    Set a monthly goal.
    - If goal_id is omitted, creates a new goal.
    - If goal_id is provided, updates the existing goal for that user.
    """
    _validate_goal_limit(goal_limit)

    if goal_id is None:
        return await goals_repo.create_for_user(db, user, goal_limit)

    _validate_goal_id(goal_id)
    return await goals_repo.update_for_user(db, user, goal_id, goal_limit=goal_limit)


async def get_monthly_goals(
    db: AsyncSession,
    *,
    user: User,
    goal_id: int | None = None,
):
    if goal_id is None:
        return await goals_repo.get_latest_for_user(db, user)

    _validate_goal_id(goal_id)
    return await goals_repo.get_for_user(db, user, goal_id)


async def get_monthly_progress(
    db: AsyncSession,
    *,
    user: User,
    month: int,
    goal_id: int | None = None,
    year: int | None = None,
) -> Optional[dict]:
    """
    Calculate monthly goal progress.
    Uses expense repository monthly total and returns goal/expense difference.
    """
    _validate_month(month)
    target_year = _resolve_year(year)

    goal = await get_monthly_goals(db, user=user, goal_id=goal_id)
    if goal is None:
        return None

    total_expense = await expenses_repo.total_amount_for_month(
        db,
        user,
        month=month,
        year=target_year,
    )
    difference = goal.goal_limit - total_expense

    return {
        "goal_id": goal.id,
        "month": month,
        "year": target_year,
        "goal_limit": goal.goal_limit,
        "total_expense": total_expense,
        "difference": difference,
    }
