import json
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import packages_kb
from app.db.models import PaymentStatus
from app.db.repository import create_payment, get_or_create_user, update_payment
from app.db.session import async_session
from app.packages import PACKAGES
from app.services.tbank import TBankError, TBankService

logger = logging.getLogger("payments")

router = Router()


@router.message(F.text == "Купить генерации")
@router.message(Command("buy"))
async def show_packages(message: Message) -> None:
    lines = ["Выберите пакет генераций:"]
    for pack in PACKAGES.values():
        lines.append(f"• {pack['title']} — {pack['amount'] // 100} ₽")
    await message.answer("\n".join(lines), reply_markup=packages_kb())


@router.callback_query(F.data.startswith("buy:"))
async def buy_package(callback: CallbackQuery) -> None:
    pack_id = callback.data.split(":", 1)[1]
    pack = PACKAGES.get(pack_id)
    if not pack:
        await callback.answer("Пакет не найден", show_alert=True)
        return

    async with async_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
        )
        tbank = TBankService()
        order_id = tbank.new_order_id(user.id, pack_id)
        payment = await create_payment(
            session,
            user_id=user.id,
            order_id=order_id,
            amount=pack["amount"],
            generations_count=pack["generations"],
        )

        try:
            result = await tbank.init_payment(
                amount=pack["amount"],
                order_id=order_id,
                description=pack["title"],
            )
        except TBankError as exc:
            await update_payment(
                session,
                payment,
                status=PaymentStatus.FAILED,
                raw_payload=json.dumps({"error": str(exc)}, ensure_ascii=False),
            )
            await callback.message.answer(f"Не удалось создать платёж: {exc}")
            await callback.answer()
            return

        payment_id = str(result.get("PaymentId", ""))
        payment_url = result.get("PaymentURL")
        await update_payment(
            session,
            payment,
            payment_id=payment_id or None,
            status=PaymentStatus.PENDING,
            raw_payload=json.dumps(result, ensure_ascii=False),
        )

    if not payment_url:
        await callback.message.answer("Платёж создан, но ссылка на оплату не получена.")
        await callback.answer()
        return

    await callback.message.answer(
        f"Оплата: {pack['title']}\n"
        f"Сумма: {pack['amount'] // 100} ₽\n\n"
        f"Перейдите по ссылке для оплаты:\n{payment_url}\n\n"
        "После успешной оплаты генерации начислятся автоматически."
    )
    await callback.answer()
