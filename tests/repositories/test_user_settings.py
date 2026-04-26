import importlib
import sys

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def test_db_package_import_registers_user_settings_model():
    for module_name in ("bot.db.models", "bot.db.base", "bot.db"):
        sys.modules.pop(module_name, None)

    db = importlib.import_module("bot.db")

    assert "user_settings" in db.Base.metadata.tables


@pytest.mark.asyncio
async def test_returns_disabled_by_default():
    from bot.db import Base
    from bot.repositories.user_settings import UserSettingsRepository

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        assert await repo.get_diarization_enabled(1001) is False


@pytest.mark.asyncio
async def test_upsert_updates_existing_setting():
    from bot.db import Base
    from bot.repositories.user_settings import UserSettingsRepository

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        await repo.set_diarization_enabled(1001, True)
        await repo.set_diarization_enabled(1001, False)
        assert await repo.get_diarization_enabled(1001) is False


@pytest.mark.asyncio
async def test_first_write_false_uses_default_disabled_value():
    from bot.db import Base
    from bot.repositories.user_settings import UserSettingsRepository

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        await repo.set_diarization_enabled(1002, False)
        assert await repo.get_diarization_enabled(1002) is False


@pytest.mark.asyncio
async def test_postgresql_upsert_branch_generates_conflict_update_statement():
    from bot.repositories.user_settings import UserSettingsRepository

    class _FakeSession:
        def __init__(self):
            self.statement = None
            self.committed = False

        def get_bind(self):
            class _Bind:
                dialect = postgresql.dialect()

            return _Bind()

        async def execute(self, statement):
            self.statement = statement

        async def commit(self):
            self.committed = True

    session = _FakeSession()
    repo = UserSettingsRepository(session)

    await repo.set_diarization_enabled(1003, True)

    sql = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()

    assert "insert into user_settings" in sql
    assert "on conflict (telegram_user_id) do update set" in sql
    assert "diarization_enabled = true" in sql
    assert "updated_at = now()" in sql
    assert session.committed is True
