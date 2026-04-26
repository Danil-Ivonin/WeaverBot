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
