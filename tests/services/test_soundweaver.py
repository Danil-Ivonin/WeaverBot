import asyncio
from time import monotonic

import httpx
import pytest
import respx

from bot.services.soundweaver import (
    SoundweaverClient,
    SoundweaverError,
    SoundweaverJobFailedError,
    SoundweaverTimeoutError,
)


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
async def test_raises_controlled_error_on_failed_job_with_malformed_error_payload():
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
        return_value=httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "failed",
                "text": None,
                "utterances": None,
                "error": None,
            },
        )
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 1.0)
        with pytest.raises(SoundweaverJobFailedError, match="Task failed"):
            await client.transcribe_voice(
                filename="voice.ogg",
                content_type="audio/ogg",
                audio_bytes=b"abc",
                diarization_enabled=True,
            )


@pytest.mark.asyncio
@respx.mock
async def test_raises_controlled_error_on_failed_job_with_null_error_message():
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
        return_value=httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "failed",
                "text": None,
                "utterances": None,
                "error": {"message": None},
            },
        )
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 1.0)
        with pytest.raises(SoundweaverJobFailedError, match="Task failed"):
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


@pytest.mark.asyncio
@respx.mock
async def test_raises_on_timeout_when_status_request_stalls():
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

    async def slow_status_response(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.2)
        return httpx.Response(200, json={"job_id": "job-1", "status": "processing"})

    respx.get("http://localhost:8000/v1/transcriptions/job-1").mock(
        side_effect=slow_status_response
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 0.01)
        started_at = monotonic()
        with pytest.raises(SoundweaverTimeoutError):
            await client.transcribe_voice(
                filename="voice.ogg",
                content_type="audio/ogg",
                audio_bytes=b"abc",
                diarization_enabled=False,
            )

    assert monotonic() - started_at < 0.1


@pytest.mark.asyncio
@respx.mock
async def test_raises_on_upload_http_failure():
    respx.post("http://localhost:8000/v1/uploads").mock(
        return_value=httpx.Response(500, json={"detail": "broken"})
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 1.0)
        with pytest.raises(httpx.HTTPStatusError):
            await client.transcribe_voice(
                filename="voice.ogg",
                content_type="audio/ogg",
                audio_bytes=b"abc",
                diarization_enabled=False,
            )


@pytest.mark.asyncio
@respx.mock
async def test_raises_on_storage_upload_http_failure():
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
    respx.put("http://storage.local/upload-1").mock(
        return_value=httpx.Response(500, json={"detail": "broken"})
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 1.0)
        with pytest.raises(httpx.HTTPStatusError):
            await client.transcribe_voice(
                filename="voice.ogg",
                content_type="audio/ogg",
                audio_bytes=b"abc",
                diarization_enabled=False,
            )


@pytest.mark.asyncio
@respx.mock
async def test_raises_on_transcription_create_http_failure():
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
        return_value=httpx.Response(502, json={"detail": "broken"})
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 1.0)
        with pytest.raises(httpx.HTTPStatusError):
            await client.transcribe_voice(
                filename="voice.ogg",
                content_type="audio/ogg",
                audio_bytes=b"abc",
                diarization_enabled=False,
            )


@pytest.mark.asyncio
@respx.mock
async def test_raises_soundweaver_error_on_missing_upload_payload_field():
    respx.post("http://localhost:8000/v1/uploads").mock(
        return_value=httpx.Response(200, json={"upload_id": "upload-1"})
    )

    async with httpx.AsyncClient() as http_client:
        client = SoundweaverClient(http_client, "http://localhost:8000", 0.0, 1.0)
        with pytest.raises(SoundweaverError, match="upload_url"):
            await client.transcribe_voice(
                filename="voice.ogg",
                content_type="audio/ogg",
                audio_bytes=b"abc",
                diarization_enabled=False,
            )
