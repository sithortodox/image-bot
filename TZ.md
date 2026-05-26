# TZ.md

# ТЗ: Telegram-бот обработки изображений через OpenRouter + оплата Т-Банк

## 1. Цель

Разработать Telegram-бота на Python, который:

- принимает изображение от пользователя;
- отправляет его в OpenRouter API;
- получает результат обработки;
- отправляет пользователю готовую картинку;
- хранит пользователей, лимиты и платежи в SQLite;
- списывает баланс только после успешной генерации;
- принимает оплату через Т-Банк;
- после успешной оплаты автоматически начисляет генерации;
- имеет админ-панель в Telegram;
- удаляет пользовательские изображения после успешной обработки;
- должен быть загружен в GitHub-репозиторий.

---

# 2. Стек

Использовать:

- Python 3.11+
- aiogram 3.x
- aiohttp / httpx
- FastAPI для webhook от Т-Банка
- SQLite
- SQLAlchemy async или aiosqlite
- python-dotenv / pydantic-settings
- Docker + Docker Compose
- GitHub

---

# 3. Основная логика пользователя

## /start

При первом запуске:

1. Создать пользователя в базе.
2. Показать приветствие.
3. Показать баланс генераций.
4. Показать кнопки:

- Загрузить изображение
- Купить генерации
- Мой баланс
- Помощь

---

# 4. Приём изображения

Бот должен принимать:

- photo;
- document, если это изображение.

Поддерживаемые форматы:

- jpg
- jpeg
- png
- webp

Ограничить размер файла через настройку:

```env
MAX_IMAGE_SIZE_MB
```

---

# 5. Проверка баланса

Перед обработкой изображения:

1. Проверить баланс пользователя.
2. Если баланс <= 0 — предложить покупку.
3. Если баланс есть — принять изображение в обработку.
4. Баланс НЕ списывать заранее.

Списание делать только после успешного ответа OpenRouter.

---

# 6. OpenRouter

Создать сервис:

```text
app/services/openrouter.py
```

Функции:

- отправка изображения в OpenRouter;
- получение результата;
- обработка ошибок;
- таймауты;
- fallback на другую бесплатную модель.

Настройки через `.env`:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
OPENROUTER_FALLBACK_MODEL=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Модель должна настраиваться через `.env`.

---

# 7. Хранение файлов

При получении изображения:

1. Скачать файл во временную папку:
   `storage/input/`
2. После успешной генерации удалить исходник.
3. Результат временно сохранить в:
   `storage/output/`
4. После отправки пользователю удалить результат.
5. При ошибке сохранить запись в БД.

---

# 8. SQLite база данных

Файл БД:

```text
data/bot.db
```

## Таблица users

Поля:

- id
- telegram_id
- username
- full_name
- balance
- is_admin
- created_at
- updated_at

---

## Таблица generations

Поля:

- id
- user_id
- status

Статусы:

- pending
- processing
- success
- failed

Дополнительные поля:

- input_file_path
- output_file_path
- error_message
- openrouter_model
- created_at
- updated_at

---

## Таблица payments

Поля:

- id
- user_id
- provider
- order_id
- payment_id
- amount
- generations_count
- status

Статусы:

- created
- pending
- paid
- failed
- canceled

Дополнительные поля:

- raw_payload
- created_at
- updated_at

---

# 9. Пакеты генераций

```python
PACKAGES = {
    "pack_10": {
        "title": "10 генераций",
        "amount": 19900,
        "generations": 10
    },
    "pack_30": {
        "title": "30 генераций",
        "amount": 49900,
        "generations": 30
    },
    "pack_100": {
        "title": "100 генераций",
        "amount": 129900,
        "generations": 100
    }
}
```

---

# 10. Оплата через Т-Банк

Реализовать интеграцию с интернет-эквайрингом Т-Банка.

Переменные `.env`:

```env
TBANK_TERMINAL_KEY=
TBANK_PASSWORD=
TBANK_API_URL=https://securepay.tinkoff.ru/v2
TBANK_NOTIFICATION_URL=
TBANK_SUCCESS_URL=
TBANK_FAIL_URL=
```

---

# 11. FastAPI webhook service

Создать:

```text
app/web/main.py
```

Endpoints:

```text
POST /payments/tbank/webhook
GET /health
```

---

# 12. Админ-панель Telegram

Команда:

```text
/admin
```

Функции:

- начисление генераций;
- списание генераций;
- поиск пользователя;
- статистика;
- просмотр ошибок;
- просмотр платежей.

---

# 13. Асинхронность

Все сетевые операции должны быть async.

---

# 14. Логирование

Файлы:

```text
logs/bot.log
logs/payments.log
logs/errors.log
```

---

# 15. Структура проекта

```text
project/
├── app/
├── data/
├── logs/
├── storage/
├── Dockerfile
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

# 16. Docker

Создать Dockerfile и docker-compose.

---

# 17. README.md

README должен содержать:

- запуск;
- настройка `.env`;
- Docker;
- OpenRouter;
- Т-Банк;
- webhook.

---

# 18. GitHub

После завершения:

```bash
git init
git add .
git commit -m "Initial Telegram bot with OpenRouter and T-Bank payments"
git branch -M main
git remote add origin <GITHUB_REPO_URL>
git push -u origin main
```

---

# 19. Критерии готовности

Проект готов, если:

- бот запускается;
- OpenRouter работает;
- баланс работает;
- оплата работает;
- webhook работает;
- админка работает;
- Docker работает;
- GitHub push выполнен.
