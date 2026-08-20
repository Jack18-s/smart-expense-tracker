from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.depends import get_current_user, get_db
from models.user import User
from services.report import get_monthly_report


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/monthly", status_code=status.HTTP_200_OK)
async def monthly_report(
    month: int = Query(...),
    year: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_monthly_report(db, user, month=month, year=year)
