from models.categories import Category
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, delete
from typing import List, Optional
from exceptions.categories import CategoryAlreadyExists



"""
class Category(Base):
    __tablename__="categories"
    __table_args__= (
        UniqueConstraint("user_id", "name", name="userid__name_constraint"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
"""


async def list_for_user(db: AsyncSession, user: User)->List[Category]:
    query = select(Category).where(Category.user_id == user.id).order_by(Category.name)
    result = await db.execute(query)
    return result.scalars().all()


async def get_for_user(db: AsyncSession, user: User, category_id:int) -> Optional[Category]:
    query = select(Category).where(and_(Category.id == category_id, Category.user_id == user.id))
    result = await db.execute(query)
    return result.scalars().one_or_none()


async def get_by_name_for_user(db: AsyncSession, user: User, category_name:str)->Optional[Category]:
    query = select(Category).where(and_(Category.user_id == user.id, Category.name == category_name))
    result = await db.execute(query)
    return result.scalars().one_or_none()

async def create_for_user(db: AsyncSession, user: User, name:str, description:str) -> Optional[Category]:
    if await get_by_name_for_user(db, user, name):
        raise CategoryAlreadyExists(f"Category with '{name}' already exists")
    category = Category(user_id=user.id, name=name, description=description)
    try:
        db.add(category)
        await db.commit()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise CategoryAlreadyExists(f"Category with '{name}' already exists")

    return category


#Optional stuff

async def delete_for_user(db: AsyncSession, user: User, category_id:str):
    query = delete(Category).where(and_(Category.id == category_id, Category.user_id == user.id))
    await db.execute(query)
    await db.commit()


async def update_for_user(db: AsyncSession, user: User, category_id : int, **fields):
    ALLOW_UPDATE_FIELDS = ["name", "description"]
    category = await get_for_user(db, user, category_id)
    if category is None:
        return None

    if "name" in fields:
        existing = await get_by_name_for_user(db, user, fields["name"])
        if existing is not None and existing.id != category.id:
            raise CategoryAlreadyExists(f"Category with '{fields['name']}' already exists")

    for key, value in fields.items():
        if key not in ALLOW_UPDATE_FIELDS:
            continue
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return category

