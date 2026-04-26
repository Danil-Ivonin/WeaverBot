from bot.handlers.settings import SETTINGS_TOGGLE_CALLBACK, render_settings_text
from bot.keyboards.settings import build_settings_keyboard


def test_render_settings_text_for_enabled_flag():
    assert render_settings_text(True) == "Разбивка по спикерам: включена"


def test_build_settings_keyboard_for_enabled_flag():
    keyboard = build_settings_keyboard(True)

    button = keyboard.inline_keyboard[0][0]

    assert button.text == "Выключить разбивку по спикерам"
    assert button.callback_data == SETTINGS_TOGGLE_CALLBACK


def test_build_settings_keyboard_for_disabled_flag():
    keyboard = build_settings_keyboard(False)

    button = keyboard.inline_keyboard[0][0]

    assert button.text == "Включить разбивку по спикерам"
    assert button.callback_data == SETTINGS_TOGGLE_CALLBACK
