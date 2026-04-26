import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher

from bot.config import Settings
from bot.db.session import create_session_factory
from bot.handlers.settings import router as settings_router
from bot.handlers.voice import router as voice_router
from bot.services.soundweaver import SoundweaverClient


def main() -> int:
    asyncio.run(run())
    return 0


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

    try:
        await dispatcher.start_polling(
            bot,
            soundweaver_client=soundweaver_client,
            session_factory=session_factory,
        )
    finally:
        await http_client.aclose()
        await bot.session.close()


if __name__ == "__main__":
    raise SystemExit(main())
