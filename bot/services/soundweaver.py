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
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        poll_interval_sec: float,
        poll_timeout_sec: float,
    ):
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
            status_response = await self._http_client.get(
                f"{self._base_url}/v1/transcriptions/{job_id}"
            )
            status_response.raise_for_status()
            payload = status_response.json()
            status = payload["status"]

            if status == "completed":
                return payload
            if status == "failed":
                raise SoundweaverJobFailedError(payload)
            if monotonic() - started_at >= self._poll_timeout_sec:
                raise SoundweaverTimeoutError(
                    f"Polling exceeded {self._poll_timeout_sec} seconds"
                )
            await asyncio.sleep(self._poll_interval_sec)
