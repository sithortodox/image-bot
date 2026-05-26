import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import admin, image, payment, start
from app.config import get_settings
from app.db.session import init_db
from app.logging_setup import setup_logging
from app.services.files import ensure_dirs

logger = logging.getLogger("app")


async def main() -> None:
    setup_logging()
    ensure_dirs()
    await init_db()

    settings = get_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(image.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
