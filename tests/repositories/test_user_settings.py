import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db.base import Base
from bot.repositories.user_settings import UserSettingsRepository


@pytest.mark.asyncio
async def test_returns_disabled_by_default():
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
