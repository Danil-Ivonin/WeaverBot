import asyncio
from time import monotonic

import httpx


class SoundweaverError(Exception):
    pass


class SoundweaverJobFailedError(SoundweaverError):
    def __init__(self, payload: dict):
        self.payload = payload
        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            raw_message = error_payload.get("message")
            if isinstance(raw_message, str) and raw_message:
                message = raw_message
            else:
                message = "Task failed"
        else:
            message = "Task failed"
        super().__init__(message)


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

    @staticmethod
    def _response_payload(response: httpx.Response, context: str) -> dict:
        try:
            payload = response.json()
        except ValueError as exc:
            raise SoundweaverError(f"{context} returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise SoundweaverError(f"{context} returned unexpected payload type")
        return payload

    @staticmethod
    def _require_field(payload: dict, field_name: str, context: str):
        try:
            return payload[field_name]
        except KeyError as exc:
            raise SoundweaverError(
                f"{context} response missing required field '{field_name}'"
            ) from exc

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
        upload_payload = self._response_payload(upload_response, "Upload creation")

        put_response = await self._http_client.put(
            self._require_field(upload_payload, "upload_url", "Upload creation"),
            content=audio_bytes,
            headers={"Content-Type": content_type},
        )
        put_response.raise_for_status()

        transcription_payload = {
            "upload_id": self._require_field(
                upload_payload, "upload_id", "Upload creation"
            )
        }
        if diarization_enabled:
            transcription_payload["diarization"] = True

        job_response = await self._http_client.post(
            f"{self._base_url}/v1/transcriptions",
            json=transcription_payload,
        )
        job_response.raise_for_status()
        job_payload = self._response_payload(job_response, "Transcription creation")
        job_id = self._require_field(job_payload, "job_id", "Transcription creation")

        deadline = monotonic() + self._poll_timeout_sec
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise SoundweaverTimeoutError(
                    f"Polling exceeded {self._poll_timeout_sec} seconds"
                )

            try:
                status_response = await asyncio.wait_for(
                    self._http_client.get(f"{self._base_url}/v1/transcriptions/{job_id}"),
                    timeout=remaining,
                )
            except asyncio.TimeoutError as exc:
                raise SoundweaverTimeoutError(
                    f"Polling exceeded {self._poll_timeout_sec} seconds"
                ) from exc

            status_response.raise_for_status()
            payload = self._response_payload(status_response, "Transcription status")
            status = self._require_field(payload, "status", "Transcription status")

            if status == "completed":
                return payload
            if status == "failed":
                raise SoundweaverJobFailedError(payload)

            remaining = deadline - monotonic()
            if remaining <= 0:
                raise SoundweaverTimeoutError(
                    f"Polling exceeded {self._poll_timeout_sec} seconds"
                )
            await asyncio.sleep(min(self._poll_interval_sec, remaining))
