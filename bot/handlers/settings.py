from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.keyboards.settings import SETTINGS_TOGGLE_CALLBACK, build_settings_keyboard
from bot.repositories.user_settings import UserSettingsRepository

router = Router()


def render_settings_text(enabled: bool) -> str:
    status = "включена" if enabled else "выключена"
    return f"Разбивка по спикерам: {status}"

@router.message(Command("settings"))
async def settings_command(
    message: Message,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        enabled = await repo.get_diarization_enabled(message.from_user.id)

    await message.answer(
        render_settings_text(enabled),
        reply_markup=build_settings_keyboard(enabled),
    )


@router.callback_query(F.data == SETTINGS_TOGGLE_CALLBACK)
async def toggle_settings(
    callback: CallbackQuery,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        new_value = await repo.toggle_diarization_enabled(callback.from_user.id)

    await callback.message.edit_text(
        render_settings_text(new_value),
        reply_markup=build_settings_keyboard(new_value),
    )
    await callback.answer()
