from sqlalchemy import select

from bot.db.models import UserSettings


class UserSettingsRepository:
    def __init__(self, session):
        self._session = session

    async def get_diarization_enabled(self, telegram_user_id: int) -> bool:
        stmt = select(UserSettings.diarization_enabled).where(
            UserSettings.telegram_user_id == telegram_user_id
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one_or_none()
        return bool(value) if value is not None else False

    async def set_diarization_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        model = await self._session.get(UserSettings, telegram_user_id)
        if model is None:
            model = UserSettings(
                telegram_user_id=telegram_user_id,
                diarization_enabled=enabled,
            )
            self._session.add(model)
        else:
            model.diarization_enabled = enabled

        await self._session.commit()
