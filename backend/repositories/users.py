from models.user import User
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import Depends
from typing import Annotated, Optional, Any
from enum import Enum
from exceptions.users import UserNotFoundError, EmailAlreadyExists



"""
   class User(Base):
    __tablename__="users"
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    username : Mapped[str] = mapped_column(String)
    email : Mapped[str]=mapped_column(String(255), unique = True, index=True, nullable=False)
    password_hash : Mapped[str] = mapped_column(String(255), nullable=False)
    created_at : Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
"""


class UserLookupField(str, Enum):
    ID = "id"
    EMAIL = "email"


FIELD_TO_COLUMN = {
    UserLookupField.ID  : User.id,
    UserLookupField.EMAIL : User.email,
}    

async def get_by_field(db: AsyncSession, field: UserLookupField ,value: Any)-> Optional[User]:
    column = FIELD_TO_COLUMN[field]
    query = select(User).where(column == value)
    result = await db.execute(query)
    user = result.scalars().one_or_none()
    return user
   

async def get_by_field_or_404(db: AsyncSession, field: UserLookupField ,value: Any):
    user = await get_by_field(db, field, value)
    if  user is None:
        raise UserNotFoundError(f"There is no user with {field.value} :{value}")
    return user


async def email_exists(db: AsyncSession, email:str)->bool:
    user = await get_by_field(db, UserLookupField.EMAIL, email) 
    if user is None:
        return False
    else:
        return True    

async def create(db: AsyncSession, *, username: str, email: str, password_hash: str)->Optional[User]:
   if await email_exists(db, email):
         raise EmailAlreadyExists(f"User with {email} already exists")
   user = User(username=username, email=email, password_hash=password_hash)

   try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
   except IntegrityError:
        await db.rollback()
        raise EmailAlreadyExists(f"User with {email} already exists")

   return user
      

async def update_for_user(db: AsyncSession, user: User, **fields):
    ALLOW_UPDATE_FIELDS = ["username","email","password"]
    if "password" in fields.keys():
        from core.security import hash_password

        hashed_password = hash_password(fields["password"])
        fields["password_hash"] = hashed_password
    for key, value in fields.items():
         if key  not in ALLOW_UPDATE_FIELDS:
             continue
         setattr(user, key, value)
    await db.commit()    
    return user    


async def delete_for_user(db:AsyncSession, user: User):
   await db.delete(user)
   await db.commit()
