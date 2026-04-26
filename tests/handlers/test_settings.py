import pytest

from bot.handlers.settings import render_settings_text, toggle_diarization_value


def test_render_settings_text_for_enabled_flag():
    assert render_settings_text(True) == "Разбивка по спикерам: включена"


def test_toggle_diarization_value_flips_flag():
    assert toggle_diarization_value(True) is False
    assert toggle_diarization_value(False) is True
