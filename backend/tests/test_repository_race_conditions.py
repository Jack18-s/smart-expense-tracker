"""
Regression tests for repositories.users.create() and
repositories.categories.create_for_user().

Both functions do an application-level "does this already exist" check
before inserting, then rely on the database's unique constraint as a
backstop for the race-condition case (two requests creating the same
email/category name at almost the same instant). Previously, if that
backstop actually fired (an IntegrityError on commit), both functions
caught it, rolled back, and returned the in-memory ORM object anyway --
an object that was never persisted (no id, no created_at) and does not
represent a real row in the database.

Since the API layer's response_model (UserOut / CategoryOut) declares
`id` as a required int, returning that unpersisted object meant the
endpoint would blow up with a 500 Internal Server Error on the rare
race, instead of the clean 409 Conflict these functions already raise
for the common (non-race) duplicate case.

These tests reproduce the bug by faking a session whose commit() raises
IntegrityError, and assert the functions now raise the same "already
exists" exception used elsewhere instead of returning a phantom object.
"""

import asyncio

import pytest
from sqlalchemy.exc import IntegrityError

from exceptions.categories import CategoryAlreadyExists
from exceptions.users import EmailAlreadyExists
from repositories import categories as categories_repo
from repositories import users as users_repo


class _FakeScalars:
    def __init__(self, value):
        self._value = value

    def one_or_none(self):
        return self._value


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return _FakeScalars(self._value)


class _FakeSession:
    """Minimal async-session stand-in.

    execute() always reports "nothing found yet" (so the application-level
    pre-check passes), then commit() raises IntegrityError to simulate a
    concurrent insert winning the race between the pre-check and this
    request's own insert.
    """

    def __init__(self):
        self.added = []
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, *args, **kwargs):
        return _FakeResult(None)

    async def commit(self):
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    async def refresh(self, obj):  # pragma: no cover - not reached on this path
        pass

    async def rollback(self):
        self.rolled_back = True


class _FakeUser:
    id = 1


def test_users_create_raises_on_integrity_error_instead_of_returning_unpersisted_user():
    db = _FakeSession()

    async def _run():
        await users_repo.create(
            db,
            username="jai",
            email="jai@example.com",
            password_hash="hashed",
        )

    with pytest.raises(EmailAlreadyExists):
        asyncio.run(_run())

    assert db.rolled_back is True


def test_categories_create_raises_on_integrity_error_instead_of_returning_unpersisted_category():
    db = _FakeSession()
    user = _FakeUser()

    async def _run():
        await categories_repo.create_for_user(db, user, "Food", "Meals and groceries")

    with pytest.raises(CategoryAlreadyExists):
        asyncio.run(_run())

    assert db.rolled_back is True
