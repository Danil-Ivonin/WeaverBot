from io import BytesIO
import logging

import httpx
from aiogram import Bot, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.formatters.transcription import format_transcription_result
from bot.repositories.user_settings import UserSettingsRepository
from bot.services.soundweaver import (
    SoundweaverClient,
    SoundweaverJobFailedError,
    SoundweaverTimeoutError,
)

router = Router()
logger = logging.getLogger(__name__)

DOWNLOAD_ERROR = "Не удалось получить голосовое сообщение. Попробуйте отправить его ещё раз."
UPLOAD_ERROR = "Не удалось передать аудио в сервис распознавания. Попробуйте позже."
TRANSCRIPTION_START_ERROR = "Не удалось запустить распознавание. Попробуйте позже."
TIMEOUT_ERROR = "Сервис распознавания не завершил обработку вовремя. Попробуйте позже."
FAILED_TRANSCRIPTION_ERROR = "Не удалось распознать голосовое сообщение."


def build_voice_filename(message_id: int) -> str:
    return f"voice_{message_id}.ogg"


def build_user_error_message(error_type: str) -> str:
    mapping = {
        "download": DOWNLOAD_ERROR,
        "upload": UPLOAD_ERROR,
        "transcription": TRANSCRIPTION_START_ERROR,
        "timeout": TIMEOUT_ERROR,
        "failed": FAILED_TRANSCRIPTION_ERROR,
    }
    return mapping[error_type]


@router.message(lambda message: bool(message.voice))
async def handle_voice(
    message: Message,
    bot: Bot,
    soundweaver_client: SoundweaverClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user_settings_repo = UserSettingsRepository(session)
        diarization_enabled = await user_settings_repo.get_diarization_enabled(
            message.from_user.id
        )

    try:
        file = await bot.get_file(message.voice.file_id)
        buffer = BytesIO()
        await bot.download(file, destination=buffer)
        audio_bytes = buffer.getvalue()
    except Exception:
        logger.exception(
            "Failed to download telegram voice",
            extra={"user_id": message.from_user.id},
        )
        await message.answer(build_user_error_message("download"))
        return

    try:
        payload = await soundweaver_client.transcribe_voice(
            filename=build_voice_filename(message.message_id),
            content_type="audio/ogg",
            audio_bytes=audio_bytes,
            diarization_enabled=diarization_enabled,
        )
    except SoundweaverTimeoutError:
        await message.answer(build_user_error_message("timeout"))
        return
    except SoundweaverJobFailedError:
        await message.answer(build_user_error_message("failed"))
        return
    except httpx.HTTPStatusError as exc:
        logger.exception(
            "Soundweaver HTTP error",
            extra={"status_code": exc.response.status_code},
        )
        status_code = exc.response.status_code
        if exc.request.url.path == "/v1/uploads" or exc.request.method == "PUT":
            await message.answer(build_user_error_message("upload"))
        elif status_code in {404, 409, 422} or exc.request.url.path == "/v1/transcriptions":
            await message.answer(build_user_error_message("transcription"))
        else:
            await message.answer(build_user_error_message("failed"))
        return

    await message.answer(format_transcription_result(payload, diarization_enabled))
