# Telegram Speech Bot Design

## Summary

Нужен Telegram-бот на `aiogram`, который принимает только голосовые сообщения (`voice`), отправляет аудио в сервис ID.SoundWeaver и возвращает пользователю одно итоговое сообщение с результатом распознавания или ошибкой.

Бот должен поддерживать команду `/settings`, где пользователь может включить или выключить разбивку по спикерам. Настройка хранится постоянно в БД и переживает рестарт процесса.

## Goals

- Принимать голосовые сообщения Telegram и преобразовывать их в текст через ID.SoundWeaver API.
- Возвращать ровно одно итоговое сообщение на каждое голосовое сообщение.
- Позволять пользователю управлять опцией diarization через `/settings`.
- Хранить пользовательские настройки в БД.

## Non-Goals

- Поддержка `audio`, `document` или других типов вложений.
- Настройка количества спикеров, `min_speakers` или `max_speakers`.
- Показ промежуточного прогресса пользователю.
- Введение отдельной очереди задач или фоновых воркеров для бота.

## External Contracts

### Telegram

- Бот обрабатывает только сообщения с полем `voice`.
- Для скачивания аудио используется `file_id` и Telegram Bot API через `aiogram`.
- Пользователю отправляется одно финальное текстовое сообщение с результатом или ошибкой.

### ID.SoundWeaver

Поток работы с API:

1. `POST /v1/uploads` с `filename` и `content_type`.
2. `PUT` бинарного тела файла в `upload_url`.
3. `POST /v1/transcriptions` с `upload_id` и, при необходимости, `diarization: true`.
4. Polling `GET /v1/transcriptions/{job_id}` до статуса `completed` или `failed`.

Используемые поля ответа:

- `upload_id`, `upload_url`
- `job_id`, `status`
- `text`
- `utterances`
- `error.code`, `error.message`

## Proposed Architecture

Рекомендуемый вариант: небольшой модульный бот с явным разделением ответственности.

### Modules

- `main.py` или `bot/__main__.py`
  Инициализация конфига, БД, HTTP-клиента, `aiogram`-диспетчера и запуск polling Telegram.
- `bot/handlers/voice.py`
  Обработка `voice` сообщений, вызов сервиса транскрибации, отправка одного финального ответа.
- `bot/handlers/settings.py`
  Обработка `/settings` и callback для переключения diarization.
- `bot/services/soundweaver.py`
  Клиент ID.SoundWeaver API, включая создание upload, загрузку файла, запуск задачи и ожидание результата.
- `bot/repositories/user_settings.py`
  Чтение и запись пользовательских настроек.
- `bot/db/models.py`
  SQLAlchemy-модели или эквивалентный слой описания таблиц.
- `bot/formatters/transcription.py`
  Форматирование текстового ответа пользователю.
- `bot/config.py`
  Загрузка настроек окружения и runtime-параметров.

### Database Model

Таблица `user_settings`:

- `telegram_user_id BIGINT PRIMARY KEY`
- `diarization_enabled BOOLEAN NOT NULL DEFAULT false`
- `created_at TIMESTAMP NOT NULL`
- `updated_at TIMESTAMP NOT NULL`

### Runtime Dependencies

- `aiogram` для Telegram-бота
- HTTP-клиент уровня `aiohttp` или `httpx`
- Библиотека работы с БД через async SQLAlchemy
- PostgreSQL как постоянное хранилище пользовательских настроек

## Message Flow

### Voice Message

1. Пользователь отправляет `voice`.
2. Хендлер извлекает `file_id` и скачивает голосовое сообщение из Telegram.
3. Бот подготавливает имя файла и использует `content_type: audio/ogg`.
4. Бот вызывает `POST /v1/uploads`.
5. Бот делает `PUT` аудиоданных в `upload_url`.
6. Бот получает настройку пользователя `diarization_enabled` из БД.
7. Бот вызывает `POST /v1/transcriptions`:
   - без дополнительных параметров, если diarization выключена;
   - с `diarization: true`, если diarization включена.
8. Бот опрашивает `GET /v1/transcriptions/{job_id}` с фиксированным интервалом.
9. После завершения бот отправляет одно итоговое сообщение:
   - простой текст из `text`, если diarization выключена;
   - форматированный список реплик по `utterances`, если diarization включена и реплики доступны;
   - fallback на `text`, если diarization включена, но `utterances` пуст.

### Settings

1. Пользователь отправляет `/settings`.
2. Бот читает текущее значение `diarization_enabled`.
3. Бот показывает сообщение о текущем состоянии и inline-кнопку переключения.
4. При callback бот делает `upsert` записи пользователя.
5. Бот обновляет сообщение `/settings`, показывая новое состояние.

## Formatting Rules

### Normal Transcription

Если diarization выключена, ответом пользователю является `text` из результата транскрибации.

### Diarized Transcription

Если diarization включена и `utterances` непустой, бот формирует ответ в таком виде:

```text
SPEAKER_00: добрый день
SPEAKER_01: здравствуйте
```

Если понадобятся более дружелюбные подписи, это можно будет поменять в реализации без изменения API-контракта.

### Empty Result

Если сервис вернул `completed`, но `text` пустой и `utterances` пусты, бот отправляет понятное сообщение, что речь не удалось распознать.

## Error Handling

Пользователь получает короткие русскоязычные ошибки без внутренних технических деталей. Подробности остаются в логах.

Сценарии:

- Ошибка скачивания файла из Telegram:
  `Не удалось получить голосовое сообщение. Попробуйте отправить его ещё раз.`
- Ошибка создания upload или загрузки в presigned URL:
  `Не удалось передать аудио в сервис распознавания. Попробуйте позже.`
- Ошибка запуска транскрибации:
  `Не удалось запустить распознавание. Попробуйте позже.`
- Статус задачи `failed`:
  использовать безопасное сообщение на основе `error.message` или обобщённый fallback
  `Не удалось распознать голосовое сообщение.`
- Polling превысил таймаут:
  `Сервис распознавания не завершил обработку вовремя. Попробуйте позже.`

## Configuration

Минимальный набор переменных окружения:

- `BOT_TOKEN`
- `SOUNDWEAVER_BASE_URL`
- `DATABASE_URL`
- `SOUNDWEAVER_POLL_INTERVAL_SEC`
- `SOUNDWEAVER_POLL_TIMEOUT_SEC`

Дополнительно допустимы:

- уровень логирования
- таймауты HTTP-клиента

## Observability

Логи должны покрывать:

- входящее `voice` сообщение и Telegram user id
- создание upload и `upload_id`
- создание transcription job и `job_id`
- финальный статус задачи
- причины сетевых ошибок и ошибок API

Логи не должны включать секреты, bot token или presigned URL целиком.

## Testing Strategy

### Unit Tests

- Форматтер ответа:
  - plain text без diarization
  - diarization с `utterances`
  - diarization включена, но `utterances` пуст
  - completed без распознаваемого текста
- Репозиторий настроек:
  - чтение дефолтного значения для нового пользователя
  - создание настройки
  - обновление настройки
- Клиент SoundWeaver:
  - успешный workflow
  - `failed` job
  - таймаут polling
  - ошибки `POST /v1/uploads`, `PUT upload_url`, `POST /v1/transcriptions`

### Integration-Level Tests

- Обработка `voice` приводит к одному итоговому ответу
- `/settings` показывает текущее значение
- callback `/settings` переключает флаг и сохраняет его в БД

## Implementation Constraints

- Использовать `aiogram`.
- Не вводить промежуточные пользовательские статусы.
- Не поддерживать другие типы медиа кроме `voice`.
- Не вводить настройку количества спикеров.
- Не добавлять отдельную очередь задач, пока этого не требует нагрузка.

## Open Decisions Resolved

- Постоянное хранение настроек: PostgreSQL.
- Поддерживаемый тип входящих сообщений: только `voice`.
- Пользовательский UX: одно итоговое сообщение на одно голосовое сообщение.
- Настройка `/settings`: только включение или выключение diarization.
