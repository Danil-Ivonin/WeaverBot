from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import UserSettings


class UserSettingsRepository:
    def __init__(self, session: AsyncSession):
        self._session: AsyncSession = session

    async def get_diarization_enabled(self, telegram_user_id: int) -> bool:
        stmt = select(UserSettings.diarization_enabled).where(
            UserSettings.telegram_user_id == telegram_user_id
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one_or_none()
        return bool(value) if value is not None else False

    async def set_diarization_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        values = {"telegram_user_id": telegram_user_id}
        if enabled:
            values["diarization_enabled"] = True

        dialect_name = self._session.get_bind().dialect.name
        if dialect_name == "postgresql":
            stmt = postgresql_insert(UserSettings)
        elif dialect_name == "sqlite":
            stmt = sqlite_insert(UserSettings)
        else:
            raise ValueError(f"Unsupported SQL dialect for upsert: {dialect_name}")

        stmt = stmt.values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserSettings.telegram_user_id],
            set_={
                "diarization_enabled": enabled,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()
