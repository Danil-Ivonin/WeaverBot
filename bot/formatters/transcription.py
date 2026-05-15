EMPTY_TRANSCRIPTION_MESSAGE = "Не удалось распознать речь в голосовом сообщении."
TELEGRAM_MESSAGE_LIMIT = 4096


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


def split_telegram_message(
    text: str, max_length: int = TELEGRAM_MESSAGE_LIMIT
) -> list[str]:
    if len(text) <= max_length:
        return [text]

    chunks = []
    current = ""

    for line in text.splitlines():
        pending = line if not current else f"{current}\n{line}"
        if len(pending) <= max_length:
            current = pending
            continue

        if current:
            chunks.append(current)
            current = ""

        while len(line) > max_length:
            chunks.append(line[:max_length])
            line = line[max_length:]
        if line:
            current = line

    if current:
        chunks.append(current)

    return chunks or [""]
