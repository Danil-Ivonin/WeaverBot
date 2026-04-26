# Telegram Speech Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an `aiogram` Telegram bot that accepts `voice` messages, sends audio to ID.SoundWeaver, returns one final transcription result or error, and lets users toggle speaker diarization in `/settings` with persistent PostgreSQL-backed storage.

**Architecture:** Use a small modular async Python app. Keep Telegram handlers, SoundWeaver API integration, formatting, config, and persistence separate so the message flow stays easy to test. Prefer direct dependency injection during startup instead of hidden globals.

**Tech Stack:** Python 3.12+, `aiogram`, `httpx`, `SQLAlchemy` async, PostgreSQL, `pytest`, `pytest-asyncio`, `respx`

---

## Planned File Structure

### Create

- `pyproject.toml`
- `bot/__init__.py`
- `bot/__main__.py`
- `bot/config.py`
- `bot/keyboards/settings.py`
- `bot/handlers/__init__.py`
- `bot/handlers/settings.py`
- `bot/handlers/voice.py`
- `bot/services/__init__.py`
- `bot/services/soundweaver.py`
- `bot/repositories/__init__.py`
- `bot/repositories/user_settings.py`
- `bot/db/__init__.py`
- `bot/db/base.py`
- `bot/db/models.py`
- `bot/db/session.py`
- `bot/formatters/__init__.py`
- `bot/formatters/transcription.py`
- `tests/conftest.py`
- `tests/test_config.py`
- `tests/formatters/test_transcription.py`
- `tests/repositories/test_user_settings.py`
- `tests/services/test_soundweaver.py`
- `tests/handlers/test_settings.py`
- `tests/handlers/test_voice.py`
- `.env.example`
- `README.md`

### Modify

- `main.py`

### Responsibility Notes

- `bot/__main__.py` is the actual application entrypoint.
- `main.py` remains a thin compatibility shim that calls `bot.__main__.main()`.
- `bot/config.py` owns environment parsing and defaults.
- `bot/db/*` owns engine/session/model setup only.
- `bot/repositories/user_settings.py` owns SQL operations for the single settings table.
- `bot/services/soundweaver.py` owns the full external API workflow and timeout handling.
- `bot/handlers/*` stay thin and orchestrate dependencies.
- `bot/formatters/transcription.py` owns user-facing response shaping.

### Task 1: Bootstrap Project Skeleton And Dependency Metadata

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `bot/__init__.py`
- Create: `bot/handlers/__init__.py`
- Create: `bot/services/__init__.py`
- Create: `bot/repositories/__init__.py`
- Create: `bot/db/__init__.py`
- Create: `bot/formatters/__init__.py`
- Modify: `main.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing config smoke test**

```python
from bot.config import Settings


def test_settings_builds_from_values():
    settings = Settings(
        bot_token="token",
        soundweaver_base_url="http://localhost:8000",
        database_url="postgresql+asyncpg://user:pass@localhost/db",
    )

    assert settings.bot_token == "token"
    assert settings.soundweaver_poll_interval_sec == 2.0
    assert settings.soundweaver_poll_timeout_sec == 120.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py::test_settings_builds_from_values -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bot'` or missing `Settings`

- [ ] **Step 3: Add project metadata, dependencies, package markers, and compatibility entrypoint**

```toml
[project]
name = "weaverbot"
version = "0.1.0"
description = "Telegram speech-to-text bot for ID.SoundWeaver"
requires-python = ">=3.12"
dependencies = [
  "aiogram>=3.18.0,<4.0.0",
  "httpx>=0.28.0,<0.29.0",
  "pydantic>=2.11.0,<3.0.0",
  "pydantic-settings>=2.8.0,<3.0.0",
  "sqlalchemy>=2.0.39,<3.0.0",
  "asyncpg>=0.30.0,<0.31.0",
  "greenlet>=3.1.0,<4.0.0",
]

[project.optional-dependencies]
dev = [
  "aiosqlite>=0.21.0,<0.22.0",
  "pytest>=8.3.0,<9.0.0",
  "pytest-asyncio>=0.26.0,<0.27.0",
  "respx>=0.22.0,<0.23.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```python
# main.py
from bot.__main__ import main


if __name__ == "__main__":
    main()
```

```dotenv
# .env.example
BOT_TOKEN=123456:telegram-token
SOUNDWEAVER_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/weaverbot
SOUNDWEAVER_POLL_INTERVAL_SEC=2
SOUNDWEAVER_POLL_TIMEOUT_SEC=120
LOG_LEVEL=INFO
```

```python
# bot/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

- [ ] **Step 4: Add the initial `Settings` implementation**

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    soundweaver_base_url: str
    database_url: str
    soundweaver_poll_interval_sec: float = Field(default=2.0, gt=0)
    soundweaver_poll_timeout_sec: float = Field(default=120.0, gt=0)
    log_level: str = "INFO"
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_config.py::test_settings_builds_from_values -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example main.py bot/__init__.py bot/handlers/__init__.py bot/services/__init__.py bot/repositories/__init__.py bot/db/__init__.py bot/formatters/__init__.py bot/config.py tests/test_config.py
git commit -m "chore: bootstrap telegram bot package"
```

### Task 2: Add Transcription Formatting Rules

**Files:**
- Create: `bot/formatters/transcription.py`
- Test: `tests/formatters/test_transcription.py`

- [ ] **Step 1: Write failing formatter tests**

```python
from bot.formatters.transcription import format_transcription_result


def test_formats_plain_text_when_diarization_disabled():
    payload = {"text": "пример распознанного текста", "utterances": []}
    assert format_transcription_result(payload, diarization_enabled=False) == "пример распознанного текста"


def test_formats_utterances_when_diarization_enabled():
    payload = {
        "text": "полный текст записи",
        "utterances": [
            {"speaker": "SPEAKER_00", "text": "добрый день"},
            {"speaker": "SPEAKER_01", "text": "здравствуйте"},
        ],
    }
    assert format_transcription_result(payload, diarization_enabled=True) == (
        "SPEAKER_00: добрый день\n"
        "SPEAKER_01: здравствуйте"
    )


def test_falls_back_to_text_when_utterances_are_empty():
    payload = {"text": "полный текст записи", "utterances": []}
    assert format_transcription_result(payload, diarization_enabled=True) == "полный текст записи"


def test_returns_empty_result_message_when_service_has_no_text():
    payload = {"text": "", "utterances": []}
    assert format_transcription_result(payload, diarization_enabled=False) == (
        "Не удалось распознать речь в голосовом сообщении."
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/formatters/test_transcription.py -v`
Expected: FAIL with missing formatter module or function

- [ ] **Step 3: Implement the formatter**

```python
EMPTY_TRANSCRIPTION_MESSAGE = "Не удалось распознать речь в голосовом сообщении."


def format_transcription_result(payload: dict, diarization_enabled: bool) -> str:
    text = (payload.get("text") or "").strip()
    utterances = payload.get("utterances") or []

    if diarization_enabled and utterances:
        lines = []
        for utterance in utterances:
            speaker = utterance.get("speaker") or "SPEAKER"
            utterance_text = (utterance.get("text") or "").strip()
            if utterance_text:
                lines.append(f"{speaker}: {utterance_text}")
        if lines:
            return "\n".join(lines)

    if text:
        return text

    return EMPTY_TRANSCRIPTION_MESSAGE
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/formatters/test_transcription.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add bot/formatters/transcription.py tests/formatters/test_transcription.py
git commit -m "feat: add transcription formatter"
```

### Task 3: Add Database Model And User Settings Repository

**Files:**
- Create: `bot/db/base.py`
- Create: `bot/db/models.py`
- Create: `bot/db/session.py`
- Create: `bot/repositories/user_settings.py`
- Test: `tests/repositories/test_user_settings.py`

- [ ] **Step 1: Write failing repository tests**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db.base import Base
from bot.repositories.user_settings import UserSettingsRepository


@pytest.mark.asyncio
async def test_returns_disabled_by_default():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        assert await repo.get_diarization_enabled(1001) is False


@pytest.mark.asyncio
async def test_upsert_updates_existing_setting():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        await repo.set_diarization_enabled(1001, True)
        await repo.set_diarization_enabled(1001, False)
        assert await repo.get_diarization_enabled(1001) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/repositories/test_user_settings.py -v`
Expected: FAIL with missing DB base, model, or repository

- [ ] **Step 3: Implement database base and model**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

```python
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    diarization_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
```

- [ ] **Step 4: Implement the repository**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/repositories/test_user_settings.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add bot/db/base.py bot/db/models.py bot/db/session.py bot/repositories/user_settings.py tests/repositories/test_user_settings.py
git commit -m "feat: add user settings persistence"
```

### Task 4: Add SoundWeaver Client Workflow

**Files:**
- Create: `bot/services/soundweaver.py`
- Test: `tests/services/test_soundweaver.py`

- [ ] **Step 1: Write failing service tests**

```python
import httpx
import pytest
import respx

from bot.services.soundweaver import SoundweaverClient, SoundweaverJobFailedError, SoundweaverTimeoutError


@pytest.mark.asyncio
@respx.mock
async def test_transcribe_voice_success():
    respx.post("http://localhost:8000/v1/uploads").mock(
        return_value=httpx.Response(
            200,
            json={
                "upload_id": "upload-1",
                "upload_url": "http://storage.local/upload-1",
                "method": "PUT",
                "expires_in_sec": 900,
            },
        )
    )
    respx.put("http://storage.local/upload-1").mock(return_value=httpx.Response(200))
    respx.post("http://localhost:8000/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"job_id": "job-1", "status": "queued"})
    )
    respx.get("http://localhost:8000/v1/transcriptions/job-1").mock(
        side_effect=[
            httpx.Response(200, json={"job_id": "job-1", "status": "processing"}),
            httpx.Response(
                200,
                json={
                    "job_id": "job-1",
                    "status": "completed",
                    "text": "пример распознанного текста",
                    "utterances": [],
                    "error": None,
                },
            ),
        ]
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 1.0)
        result = await client.transcribe_voice(
            filename="voice.ogg",
            content_type="audio/ogg",
            audio_bytes=b"abc",
            diarization_enabled=False,
        )

    assert result["status"] == "completed"
    assert result["text"] == "пример распознанного текста"


@pytest.mark.asyncio
@respx.mock
async def test_raises_on_failed_job():
    respx.post("http://localhost:8000/v1/uploads").mock(
        return_value=httpx.Response(
            200,
            json={"upload_id": "upload-1", "upload_url": "http://storage.local/upload-1", "method": "PUT", "expires_in_sec": 900},
        )
    )
    respx.put("http://storage.local/upload-1").mock(return_value=httpx.Response(200))
    respx.post("http://localhost:8000/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"job_id": "job-1", "status": "queued"})
    )
    respx.get("http://localhost:8000/v1/transcriptions/job-1").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "failed",
                "text": None,
                "utterances": None,
                "error": {"code": "asr_failed", "message": "Task failed"},
            },
        )
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 1.0)
        with pytest.raises(SoundweaverJobFailedError):
            await client.transcribe_voice(
                filename="voice.ogg",
                content_type="audio/ogg",
                audio_bytes=b"abc",
                diarization_enabled=True,
            )


@pytest.mark.asyncio
@respx.mock
async def test_raises_on_timeout():
    respx.post("http://localhost:8000/v1/uploads").mock(
        return_value=httpx.Response(
            200,
            json={"upload_id": "upload-1", "upload_url": "http://storage.local/upload-1", "method": "PUT", "expires_in_sec": 900},
        )
    )
    respx.put("http://storage.local/upload-1").mock(return_value=httpx.Response(200))
    respx.post("http://localhost:8000/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"job_id": "job-1", "status": "queued"})
    )
    respx.get("http://localhost:8000/v1/transcriptions/job-1").mock(
        return_value=httpx.Response(200, json={"job_id": "job-1", "status": "processing"})
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 0.0)
        with pytest.raises(SoundweaverTimeoutError):
            await client.transcribe_voice(
                filename="voice.ogg",
                content_type="audio/ogg",
                audio_bytes=b"abc",
                diarization_enabled=False,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/services/test_soundweaver.py -v`
Expected: FAIL with missing `SoundweaverClient` or related exceptions

- [ ] **Step 3: Implement the SoundWeaver client**

```python
import asyncio
from time import monotonic

import httpx


class SoundweaverError(Exception):
    pass


class SoundweaverJobFailedError(SoundweaverError):
    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("error", {}).get("message", "Task failed"))


class SoundweaverTimeoutError(SoundweaverError):
    pass


class SoundweaverClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str, poll_interval_sec: float, poll_timeout_sec: float):
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._poll_interval_sec = poll_interval_sec
        self._poll_timeout_sec = poll_timeout_sec

    async def transcribe_voice(
        self,
        *,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
        diarization_enabled: bool,
    ) -> dict:
        upload_response = await self._http_client.post(
            f"{self._base_url}/v1/uploads",
            json={"filename": filename, "content_type": content_type},
        )
        upload_response.raise_for_status()
        upload_payload = upload_response.json()

        put_response = await self._http_client.put(
            upload_payload["upload_url"],
            content=audio_bytes,
            headers={"Content-Type": content_type},
        )
        put_response.raise_for_status()

        transcription_payload = {"upload_id": upload_payload["upload_id"]}
        if diarization_enabled:
            transcription_payload["diarization"] = True

        job_response = await self._http_client.post(
            f"{self._base_url}/v1/transcriptions",
            json=transcription_payload,
        )
        job_response.raise_for_status()
        job_id = job_response.json()["job_id"]

        started_at = monotonic()
        while True:
            status_response = await self._http_client.get(f"{self._base_url}/v1/transcriptions/{job_id}")
            status_response.raise_for_status()
            payload = status_response.json()
            status = payload["status"]

            if status == "completed":
                return payload
            if status == "failed":
                raise SoundweaverJobFailedError(payload)
            if monotonic() - started_at >= self._poll_timeout_sec:
                raise SoundweaverTimeoutError(f"Polling exceeded {self._poll_timeout_sec} seconds")
            await asyncio.sleep(self._poll_interval_sec)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/services/test_soundweaver.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add bot/services/soundweaver.py tests/services/test_soundweaver.py
git commit -m "feat: add soundweaver transcription client"
```

### Task 5: Add `/settings` Keyboard And Handler

**Files:**
- Create: `bot/keyboards/settings.py`
- Create: `bot/handlers/settings.py`
- Test: `tests/handlers/test_settings.py`

- [ ] **Step 1: Write failing settings handler tests**

```python
import pytest
from aiogram.types import CallbackQuery, Message, User
from unittest.mock import AsyncMock

from bot.handlers.settings import render_settings_text, toggle_diarization_value


def test_render_settings_text_for_enabled_flag():
    assert render_settings_text(True) == "Разбивка по спикерам: включена"


def test_toggle_diarization_value_flips_flag():
    assert toggle_diarization_value(True) is False
    assert toggle_diarization_value(False) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/handlers/test_settings.py -v`
Expected: FAIL with missing settings handler helpers

- [ ] **Step 3: Implement settings keyboard and handler helpers**

```python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_settings_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    label = "Выключить разбивку по спикерам" if enabled else "Включить разбивку по спикерам"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data="settings:toggle_diarization")]]
    )
```

```python
def render_settings_text(enabled: bool) -> str:
    status = "включена" if enabled else "выключена"
    return f"Разбивка по спикерам: {status}"


def toggle_diarization_value(enabled: bool) -> bool:
    return not enabled
```

- [ ] **Step 4: Expand handler implementation around repository-backed commands**

```python
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.keyboards.settings import build_settings_keyboard
from bot.repositories.user_settings import UserSettingsRepository

router = Router()


@router.message(Command("settings"))
async def settings_command(message: Message, session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        enabled = await repo.get_diarization_enabled(message.from_user.id)
    await message.answer(render_settings_text(enabled), reply_markup=build_settings_keyboard(enabled))


@router.callback_query(F.data == "settings:toggle_diarization")
async def toggle_settings(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        repo = UserSettingsRepository(session)
        enabled = await repo.get_diarization_enabled(callback.from_user.id)
        new_value = toggle_diarization_value(enabled)
        await repo.set_diarization_enabled(callback.from_user.id, new_value)
    await callback.message.edit_text(
        render_settings_text(new_value),
        reply_markup=build_settings_keyboard(new_value),
    )
    await callback.answer()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/handlers/test_settings.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add bot/keyboards/settings.py bot/handlers/settings.py tests/handlers/test_settings.py
git commit -m "feat: add settings toggle handler"
```

### Task 6: Add Voice Handler And Application Wiring

**Files:**
- Create: `bot/__main__.py`
- Create: `bot/handlers/voice.py`
- Test: `tests/conftest.py`
- Test: `tests/handlers/test_voice.py`

- [ ] **Step 1: Write failing voice flow tests**

```python
import pytest

from bot.formatters.transcription import EMPTY_TRANSCRIPTION_MESSAGE
from bot.handlers.voice import build_voice_filename


def test_build_voice_filename_uses_message_id():
    assert build_voice_filename(message_id=42) == "voice_42.ogg"
```

```python
import pytest

from bot.handlers.voice import build_user_error_message


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/handlers/test_voice.py -v`
Expected: FAIL with missing voice handler helpers

- [ ] **Step 3: Implement helper logic for filenames and user-facing errors**

```python
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
```

- [ ] **Step 4: Implement the voice handler and bot startup**

```python
from io import BytesIO
import logging

import httpx
from aiogram import Bot, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.formatters.transcription import format_transcription_result
from bot.repositories.user_settings import UserSettingsRepository
from bot.services.soundweaver import SoundweaverClient, SoundweaverJobFailedError, SoundweaverTimeoutError

router = Router()
logger = logging.getLogger(__name__)


@router.message(lambda message: bool(message.voice))
async def handle_voice(
    message: Message,
    bot: Bot,
    soundweaver_client: SoundweaverClient,
    session_factory: async_sessionmaker,
) -> None:
    async with session_factory() as session:
        user_settings_repo = UserSettingsRepository(session)
        diarization_enabled = await user_settings_repo.get_diarization_enabled(message.from_user.id)

    try:
        file = await bot.get_file(message.voice.file_id)
        buffer = BytesIO()
        await bot.download(file, destination=buffer)
        audio_bytes = buffer.getvalue()
    except Exception:
        logger.exception("Failed to download telegram voice", extra={"user_id": message.from_user.id})
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
        logger.exception("Soundweaver HTTP error", extra={"status_code": exc.response.status_code})
        status_code = exc.response.status_code
        if exc.request.url.path == "/v1/uploads" or exc.request.method == "PUT":
            await message.answer(build_user_error_message("upload"))
        elif status_code in {404, 409, 422} or exc.request.url.path == "/v1/transcriptions":
            await message.answer(build_user_error_message("transcription"))
        else:
            await message.answer(build_user_error_message("failed"))
        return

    await message.answer(format_transcription_result(payload, diarization_enabled))
```

```python
import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher

from bot.config import Settings
from bot.db.session import create_session_factory
from bot.handlers.settings import router as settings_router
from bot.handlers.voice import router as voice_router
from bot.services.soundweaver import SoundweaverClient


def main() -> None:
    asyncio.run(run())


async def run() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.log_level)

    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(settings_router)
    dispatcher.include_router(voice_router)

    http_client = httpx.AsyncClient(timeout=30.0)
    session_factory = create_session_factory(settings.database_url)
    soundweaver_client = SoundweaverClient(
        http_client,
        settings.soundweaver_base_url,
        settings.soundweaver_poll_interval_sec,
        settings.soundweaver_poll_timeout_sec,
    )

    dispatcher["soundweaver_client"] = soundweaver_client
    dispatcher["session_factory"] = session_factory

    try:
        await dispatcher.start_polling(bot)
    finally:
        await http_client.aclose()
        await bot.session.close()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/handlers/test_voice.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add bot/__main__.py bot/handlers/voice.py tests/conftest.py tests/handlers/test_voice.py
git commit -m "feat: add voice transcription flow"
```

### Task 7: Add Repository/Handler Integration Tests And Final Docs

**Files:**
- Modify: `tests/handlers/test_settings.py`
- Modify: `tests/handlers/test_voice.py`
- Create: `README.md`

- [ ] **Step 1: Add failing integration-oriented tests for `/settings` and one final voice reply**

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers.settings import toggle_settings
from bot.handlers.voice import handle_voice


@pytest.mark.asyncio
async def test_settings_callback_updates_persisted_value(fake_session_factory):
    callback = AsyncMock()
    callback.from_user.id = 1001
    callback.message = AsyncMock()

    await toggle_settings(callback, fake_session_factory)

    callback.message.edit_text.assert_awaited_once()
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_voice_flow_returns_single_final_message_text(fake_session_factory):
    message = AsyncMock()
    message.from_user.id = 1001
    message.message_id = 42
    message.voice.file_id = "voice-file"

    bot = AsyncMock()
    bot.get_file.return_value = SimpleNamespace(file_path="voices/voice.ogg")

    soundweaver_client = AsyncMock()
    soundweaver_client.transcribe_voice.return_value = {
        "status": "completed",
        "text": "пример распознанного текста",
        "utterances": [],
    }

    await handle_voice(message, bot, soundweaver_client, fake_session_factory)

    message.answer.assert_awaited_once_with("пример распознанного текста")
```

- [ ] **Step 2: Run tests to verify they fail or remain incomplete**

Run: `uv run pytest tests/handlers/test_settings.py tests/handlers/test_voice.py -v`
Expected: FAIL because `fake_session_factory` fixture and session-backed handler plumbing are not implemented yet

- [ ] **Step 3: Replace shallow tests with dependency-backed assertions and add usage docs**

```markdown
# README.md
# WeaverBot

Telegram-бот на `aiogram`, который принимает голосовые сообщения и отправляет их в ID.SoundWeaver для распознавания.

## Environment

- `BOT_TOKEN`
- `SOUNDWEAVER_BASE_URL`
- `DATABASE_URL`
- `SOUNDWEAVER_POLL_INTERVAL_SEC`
- `SOUNDWEAVER_POLL_TIMEOUT_SEC`

## Run

    uv sync
    uv run python -m bot

## Test

    uv run pytest -q
```

```python
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers.settings import settings_command
from bot.handlers.voice import handle_voice
from bot.services.soundweaver import SoundweaverTimeoutError


@pytest.fixture
def fake_session_factory():
    @asynccontextmanager
    async def factory():
        yield SimpleNamespace()

    return factory


@pytest.mark.asyncio
async def test_settings_command_renders_current_value(fake_session_factory, monkeypatch):
    message = AsyncMock()
    message.from_user.id = 1001

    class FakeRepo:
        async def get_diarization_enabled(self, telegram_user_id: int) -> bool:
            return False

    monkeypatch.setattr("bot.handlers.settings.UserSettingsRepository", lambda session: FakeRepo())

    await settings_command(message, fake_session_factory)

    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_voice_handler_timeout_returns_single_error(fake_session_factory, monkeypatch):
    message = AsyncMock()
    message.from_user.id = 1001
    message.message_id = 77
    message.voice.file_id = "voice-file"

    bot = AsyncMock()
    bot.get_file.return_value = SimpleNamespace(file_path="voices/voice.ogg")
    soundweaver_client = AsyncMock()
    soundweaver_client.transcribe_voice.side_effect = SoundweaverTimeoutError("timeout")

    class FakeRepo:
        async def get_diarization_enabled(self, telegram_user_id: int) -> bool:
            return False

    monkeypatch.setattr("bot.handlers.voice.UserSettingsRepository", lambda session: FakeRepo())

    await handle_voice(message, bot, soundweaver_client, fake_session_factory)

    message.answer.assert_awaited_once_with(
        "Сервис распознавания не завершил обработку вовремя. Попробуйте позже."
    )
```

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest -q`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add tests/handlers/test_settings.py tests/handlers/test_voice.py README.md
git commit -m "test: cover handler flows and document bot usage"
```

### Task 8: Final Manual Verification

**Files:**
- Modify: none
- Test: local runtime only

- [ ] **Step 1: Start PostgreSQL and provide environment values**

```bash
export BOT_TOKEN=123456:telegram-token
export SOUNDWEAVER_BASE_URL=http://localhost:8000
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/weaverbot
export SOUNDWEAVER_POLL_INTERVAL_SEC=2
export SOUNDWEAVER_POLL_TIMEOUT_SEC=120
```

- [ ] **Step 2: Run the full test suite before manual checks**

Run: `uv run pytest -q`
Expected: all tests pass

- [ ] **Step 3: Start the bot**

Run: `uv run python -m bot`
Expected: process starts without import/config errors and begins Telegram polling

- [ ] **Step 4: Manually verify the main user flows**

```text
1. Send /settings and confirm the bot shows the current diarization state.
2. Tap the inline button and confirm the message updates to the opposite state.
3. Send one voice message with diarization off and confirm one reply containing plain text.
4. Enable diarization, send another voice message, and confirm one reply containing speaker-prefixed lines or plain text fallback.
5. Temporarily point SOUNDWEAVER_BASE_URL to an invalid endpoint and confirm one reply with a user-friendly error.
```

- [ ] **Step 5: Commit the finished implementation**

```bash
git add .
git commit -m "feat: implement telegram speech bot"
```
