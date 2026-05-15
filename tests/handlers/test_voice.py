import pytest
import httpx

from bot.handlers.voice import (
    MAX_LOGGED_RESPONSE_BODY_CHARS,
    build_user_error_message,
    build_voice_filename,
    format_http_error_for_log,
)


def test_build_voice_filename_uses_message_id():
    assert build_voice_filename(message_id=42) == "voice_42.ogg"


@pytest.mark.parametrize(
    ("error_type", "expected"),
    [
        (
            "download",
            "Не удалось получить голосовое сообщение. Попробуйте отправить его ещё раз.",
        ),
        (
            "upload",
            "Не удалось передать аудио в сервис распознавания. Попробуйте позже.",
        ),
        ("transcription", "Не удалось запустить распознавание. Попробуйте позже."),
        (
            "timeout",
            "Сервис распознавания не завершил обработку вовремя. Попробуйте позже.",
        ),
    ],
)
def test_build_user_error_message(error_type, expected):
    assert build_user_error_message(error_type) == expected


def test_format_http_error_for_log_includes_response_details():
    request = httpx.Request("POST", "http://localhost:8000/v1/uploads")
    response = httpx.Response(
        503,
        request=request,
        headers={"content-type": "application/json"},
        json={"detail": "storage unavailable"},
    )
    exc = httpx.HTTPStatusError("boom", request=request, response=response)

    details = format_http_error_for_log(exc)

    assert "method=POST" in details
    assert "url=http://localhost:8000/v1/uploads" in details
    assert "status_code=503" in details
    assert "content_type=application/json" in details
    assert "storage unavailable" in details


def test_format_http_error_for_log_truncates_long_response_body():
    request = httpx.Request("POST", "http://localhost:8000/v1/uploads")
    response = httpx.Response(
        503,
        request=request,
        text="x" * (MAX_LOGGED_RESPONSE_BODY_CHARS + 1),
    )
    exc = httpx.HTTPStatusError("boom", request=request, response=response)

    details = format_http_error_for_log(exc)

    assert ("x" * (MAX_LOGGED_RESPONSE_BODY_CHARS + 1)) not in details
    assert "response_body='" + ("x" * MAX_LOGGED_RESPONSE_BODY_CHARS) + "..." in details
