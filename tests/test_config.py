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
