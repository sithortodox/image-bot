# Telegram Image Bot (OpenRouter + T-Bank)

Telegram-бот на Python для обработки изображений через OpenRouter с оплатой через Т-Банк (Tinkoff Acquiring), SQLite-балансом и админ-панелью в Telegram.

## Возможности

- Приём фото и документов (jpg, jpeg, png, webp)
- Обработка через OpenRouter с fallback-моделью
- Списание баланса только после успешной генерации
- Покупка пакетов генераций через Т-Банк
- Webhook для автоматического начисления после оплаты
- Админ-панель: баланс, статистика, ошибки, платежи
- Docker Compose для бота и webhook-сервиса

## Требования

- Python 3.11+
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- OpenRouter API Key
- Т-Банк интернет-эквайринг (Terminal Key + Password)
- Публичный HTTPS URL для webhook (ngrok, VPS, reverse proxy)

## Быстрый старт (локально)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполните .env
mkdir -p data logs storage/input storage/output
```

### Запуск бота

```bash
python -m app.bot.main
```

### Запуск webhook (FastAPI)

```bash
uvicorn app.web.main:app --host 0.0.0.0 --port 8000
```

Проверка:

```bash
curl http://localhost:8000/health
```

## Настройка `.env`

Скопируйте `.env.example` в `.env` и заполните:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен Telegram-бота |
| `ADMIN_TELEGRAM_IDS` | ID админов через запятую |
| `OPENROUTER_API_KEY` | Ключ OpenRouter |
| `OPENROUTER_MODEL` | Основная модель |
| `OPENROUTER_FALLBACK_MODEL` | Резервная бесплатная модель |
| `OPENROUTER_PROMPT` | Промпт для обработки |
| `MAX_IMAGE_SIZE_MB` | Лимит размера файла |
| `TBANK_TERMINAL_KEY` | Terminal Key Т-Банка |
| `TBANK_PASSWORD` | Пароль терминала |
| `TBANK_NOTIFICATION_URL` | URL webhook, напр. `https://domain.com/payments/tbank/webhook` |
| `TBANK_SUCCESS_URL` | Redirect после успешной оплаты |
| `TBANK_FAIL_URL` | Redirect после ошибки оплаты |

## OpenRouter

Сервис: `app/services/openrouter.py`

- Отправляет изображение в `/chat/completions`
- Таймаут настраивается через `OPENROUTER_TIMEOUT_SEC`
- При ошибке основной модели используется `OPENROUTER_FALLBACK_MODEL`
- Баланс пользователя **не** списывается при ошибке

## Т-Банк

Сервис: `app/services/tbank.py`

- `Init` — создание платежа, возвращает `PaymentURL`
- Подпись запросов и проверка webhook через SHA-256 token
- Пакеты генераций: 10 / 30 / 100 (`app/packages.py`)

### Webhook

Endpoint:

```text
POST /payments/tbank/webhook
```

При статусах `CONFIRMED` / `AUTHORIZED` бот автоматически начисляет генерации на баланс пользователя (идемпотентно — повторное уведомление не дублирует начисление).

В личном кабинете Т-Банка укажите `NotificationURL` = значение `TBANK_NOTIFICATION_URL`.

## Docker

```bash
cp .env.example .env
# заполните .env
docker compose up -d --build
```

Сервисы:

- `bot` — Telegram polling
- `webhook` — FastAPI на порту `WEB_PORT` (по умолчанию 8000)

Логи:

```text
logs/bot.log
logs/payments.log
logs/errors.log
```

База данных:

```text
data/bot.db
```

## Команды бота

| Команда / кнопка | Действие |
|---|---|
| `/start` | Регистрация, меню, баланс |
| `/balance` | Показать баланс |
| `/buy` | Купить генерации |
| `/help` | Справка |
| `/admin` | Админ-панель (только для `ADMIN_TELEGRAM_IDS`) |

## Структура проекта

```text
app/
  bot/          # aiogram handlers
  db/           # SQLAlchemy models + repository
  services/     # OpenRouter, T-Bank, files
  web/          # FastAPI webhook
data/           # SQLite
logs/
storage/        # временные input/output (удаляются после обработки)
```

## GitHub

```bash
git init
git add .
git commit -m "Initial Telegram bot with OpenRouter and T-Bank payments"
git branch -M main
git remote add origin <GITHUB_REPO_URL>
git push -u origin main
```

## Примечания

- Для production рекомендуется HTTPS reverse proxy (nginx/caddy) перед webhook.
- Убедитесь, что модели OpenRouter поддерживают vision/image output для вашего сценария.
- Тестовый терминал Т-Банка используйте до перехода в боевой режим.
