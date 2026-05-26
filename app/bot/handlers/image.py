import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.types import FSInputFile, Message
from sqlalchemy import select

from app.bot.keyboards import main_menu_kb, packages_kb
from app.config import get_settings
from app.db.models import Generation, GenerationStatus
from app.db.repository import (
    create_generation,
    deduct_balance_on_success,
    get_or_create_user,
    update_generation,
)
from app.db.session import async_session
from app.services.files import input_path, is_allowed_image, output_path, safe_remove
from app.services.openrouter import OpenRouterError, OpenRouterService

logger = logging.getLogger("app")
error_logger = logging.getLogger("errors")

router = Router()


async def _download_telegram_file(bot: Bot, file_id: str, dest: Path) -> None:
    file = await bot.get_file(file_id)
    if not file.file_path:
        raise ValueError("Не удалось получить файл из Telegram")
    await bot.download_file(file.file_path, destination=dest)


@router.message(F.text == "Загрузить изображение")
async def upload_hint(message: Message) -> None:
    await message.answer("Отправьте фото или файл изображения (jpg, jpeg, png, webp).")


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot) -> None:
    photo = message.photo[-1]
    settings = get_settings()
    if photo.file_size and photo.file_size > settings.max_image_size_bytes:
        await message.answer(
            f"Файл слишком большой. Максимум: {settings.max_image_size_mb} МБ."
        )
        return
    await _process_image_message(message, bot, photo.file_id, ".jpg")


@router.message(F.document)
async def handle_document(message: Message, bot: Bot) -> None:
    doc = message.document
    if not doc or not is_allowed_image(doc.file_name):
        await message.answer("Поддерживаются только jpg, jpeg, png, webp.")
        return
    settings = get_settings()
    if doc.file_size and doc.file_size > settings.max_image_size_bytes:
        await message.answer(
            f"Файл слишком большой. Максимум: {settings.max_image_size_mb} МБ."
        )
        return
    ext = Path(doc.file_name or ".jpg").suffix.lower()
    await _process_image_message(message, bot, doc.file_id, ext)


async def _process_image_message(
    message: Message, bot: Bot, file_id: str, ext: str
) -> None:
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        if user.balance <= 0:
            await message.answer(
                "Недостаточно генераций. Купите пакет, чтобы продолжить.",
                reply_markup=packages_kb(),
            )
            return

    status_msg = await message.answer("Изображение принято. Обрабатываю…")

    in_path = input_path(ext)
    out_path = output_path(".png")
    generation_id: int | None = None
    remaining_balance = 0

    try:
        await _download_telegram_file(bot, file_id, in_path)

        async with async_session() as session:
            user = await get_or_create_user(
                session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
            )
            gen = await create_generation(session, user.id, str(in_path))
            generation_id = gen.id
            await update_generation(session, gen, status=GenerationStatus.PROCESSING)

        service = OpenRouterService()
        model_used = await service.process_image(in_path, out_path)

        async with async_session() as session:
            user = await get_or_create_user(
                session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
            )
            if user.balance <= 0:
                await status_msg.edit_text("Недостаточно генераций для списания.")
                return

            if not await deduct_balance_on_success(session, user):
                await status_msg.edit_text("Не удалось списать баланс.")
                return

            remaining_balance = user.balance

            if generation_id:
                result = await session.execute(
                    select(Generation).where(Generation.id == generation_id)
                )
                gen = result.scalar_one()
                await update_generation(
                    session,
                    gen,
                    status=GenerationStatus.SUCCESS,
                    output_file_path=str(out_path),
                    openrouter_model=model_used,
                )

        await bot.send_photo(
            chat_id=message.chat.id,
            photo=FSInputFile(out_path),
            caption=f"Готово! Осталось генераций: {remaining_balance}",
            reply_markup=main_menu_kb(),
        )
        await status_msg.delete()

    except OpenRouterError as exc:
        error_logger.exception("OpenRouter error: %s", exc)
        await _mark_failed(generation_id, str(exc))
        await status_msg.edit_text(f"Ошибка обработки: {exc}")
    except Exception:
        error_logger.exception("Image processing error")
        await _mark_failed(generation_id, "Internal error")
        await status_msg.edit_text("Произошла ошибка при обработке изображения.")
    finally:
        safe_remove(in_path)
        safe_remove(out_path)


async def _mark_failed(generation_id: int | None, error: str) -> None:
    if not generation_id:
        return
    async with async_session() as session:
        result = await session.execute(
            select(Generation).where(Generation.id == generation_id)
        )
        gen = result.scalar_one_or_none()
        if gen:
            await update_generation(
                session,
                gen,
                status=GenerationStatus.FAILED,
                error_message=error[:2000],
            )
