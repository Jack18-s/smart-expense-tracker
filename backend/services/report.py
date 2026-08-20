import calendar
import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.expense import Expense
from models.user import User
from repositories import categories as categories_repo
from repositories import expenses as expenses_repo


def _get_month_bounds(
    month: int, year: int | None = None
) -> tuple[datetime.datetime, datetime.datetime]:
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")

    resolved_year = datetime.datetime.now(datetime.UTC).year if year is None else year
    if resolved_year < 1:
        raise ValueError("year must be >= 1")

    _, num_days = calendar.monthrange(resolved_year, month)

    start_at = datetime.datetime(resolved_year, month, 1, 0, 0, 0, tzinfo=datetime.UTC)
    end_at = datetime.datetime(
        resolved_year,
        month,
        num_days,
        23,
        59,
        59,
        999999,
        tzinfo=datetime.UTC,
    )
    return start_at, end_at


def month_summary(monthly_expenses: list[Expense]) -> dict:
    total_amount = sum(expense.amount for expense in monthly_expenses)
    return {
        "total_expenses": len(monthly_expenses),
        "total_amount": total_amount,
    }


def category_breakdown(monthly_expenses: list[Expense], category_lookup: dict[int, str]) -> list[dict]:
    breakdown_by_category: dict[int, dict] = {}

    for expense in monthly_expenses:
        category_id = expense.category_id
        if category_id not in breakdown_by_category:
            breakdown_by_category[category_id] = {
                "category_id": category_id,
                "category_name": category_lookup.get(category_id),
                "total_amount": 0.0,
                "total_expenses": 0,
            }

        breakdown_by_category[category_id]["total_amount"] += expense.amount
        breakdown_by_category[category_id]["total_expenses"] += 1

    return sorted(
        breakdown_by_category.values(),
        key=lambda item: item["total_amount"],
        reverse=True,
    )


def top_5_categories(category_totals: list[dict]) -> list[dict]:
    return category_totals[:5]


async def get_monthly_report(
    db: AsyncSession, user: User, *, month: int, year: int | None = None
) -> dict:
    start_at, end_at = _get_month_bounds(month, year)

    monthly_expenses = await expenses_repo.list_for_user(
        db,
        user,
        from_date=start_at,
        to_date=end_at,
        sort="-occurred_at",
    )
    user_categories = await categories_repo.list_for_user(db, user)

    category_lookup = {category.id: category.name for category in user_categories}
    expense_items = []

    for expense in monthly_expenses:
        expense_items.append(
            {
                "id": expense.id,
                "category_id": expense.category_id,
                "category_name": category_lookup.get(expense.category_id),
                "amount": expense.amount,
                "occurred_at": expense.occurred_at.isoformat(),
                "title": expense.title,
                "note": expense.note,
            }
        )

    monthly_summary = month_summary(monthly_expenses)
    categories_total = category_breakdown(monthly_expenses, category_lookup)
    top_categories = top_5_categories(categories_total)

    report = {
        "month": month,
        "year": start_at.year,
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "month_summary": monthly_summary,
        "category_breakdown": categories_total,
        "top_5_categories": top_categories,
        "expenses": expense_items,
    }
    return report
