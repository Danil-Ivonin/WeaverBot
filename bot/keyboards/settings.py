from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_settings_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    label = (
        "Выключить разбивку по спикерам"
        if enabled
        else "Включить разбивку по спикерам"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data="settings:toggle_diarization",
                )
            ]
        ]
    )
