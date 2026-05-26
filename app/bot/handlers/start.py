from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.keyboards import main_menu_kb
from app.db.repository import get_or_create_user
from app.db.session import async_session

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        balance = user.balance

    text = (
        "Привет! Я бот для обработки изображений через OpenRouter.\n\n"
        f"Ваш баланс: {balance} генераций.\n\n"
        "Отправьте фото или изображение-документ, либо выберите действие в меню."
    )
    await message.answer(text, reply_markup=main_menu_kb())


@router.message(F.text == "Мой баланс")
@router.message(Command("balance"))
async def show_balance(message: Message) -> None:
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
    await message.answer(f"Ваш баланс: {user.balance} генераций.")


@router.message(F.text == "Помощь")
@router.message(Command("help"))
async def show_help(message: Message) -> None:
    await message.answer(
        "Как пользоваться:\n"
        "1. Нажмите «Загрузить изображение» или отправьте фото/файл (jpg, png, webp).\n"
        "2. Дождитесь обработки — баланс спишется только после успешной генерации.\n"
        "3. Купите пакет генераций через «Купить генерации».\n\n"
        "Команды: /start, /balance, /buy, /help, /admin"
    )
