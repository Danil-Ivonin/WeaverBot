import pytest

from bot.handlers.voice import build_user_error_message, build_voice_filename


def test_build_voice_filename_uses_message_id():
    assert build_voice_filename(message_id=42) == "voice_42.ogg"


@pytest.mark.parametrize(
    ("error_type", "expected"),
    [
        ("download", "Не удалось получить голосовое сообщение. Попробуйте отправить его ещё раз."),
        ("upload", "Не удалось передать аудио в сервис распознавания. Попробуйте позже."),
        ("transcription", "Не удалось запустить распознавание. Попробуйте позже."),
        ("timeout", "Сервис распознавания не завершил обработку вовремя. Попробуйте позже."),
    ],
)
def test_build_user_error_message(error_type, expected):
    assert build_user_error_message(error_type) == expected
