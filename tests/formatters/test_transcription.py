from bot.formatters.transcription import EMPTY_TRANSCRIPTION_MESSAGE, format_transcription_result


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
    assert format_transcription_result(payload, diarization_enabled=False) == EMPTY_TRANSCRIPTION_MESSAGE


def test_returns_empty_result_message_when_diarization_has_only_blank_utterances():
    payload = {
        "text": "",
        "utterances": [
            {"speaker": "SPEAKER_00", "text": "   "},
            {"speaker": "SPEAKER_01", "text": ""},
        ],
    }
    assert format_transcription_result(payload, diarization_enabled=True) == EMPTY_TRANSCRIPTION_MESSAGE
