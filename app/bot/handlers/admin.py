from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import admin_menu_kb
from app.bot.states import AdminStates
from app.db.repository import (
    adjust_balance,
    get_recent_failed_generations,
    get_recent_payments,
    get_stats,
    get_user_by_telegram_id,
    search_users,
)
from app.db.session import async_session

router = Router()


async def _is_admin(telegram_id: int) -> bool:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        return bool(user and user.is_admin)


@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await message.answer("Админ-панель", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with async_session() as session:
        stats = await get_stats(session)
    text = (
        "Статистика:\n"
        f"Пользователей: {stats['users']}\n"
        f"Успешных генераций: {stats['generations_success']}\n"
        f"Ошибок генераций: {stats['generations_failed']}\n"
        f"Оплаченных платежей: {stats['payments_paid']}\n"
        f"Выручка: {stats['total_revenue_kopecks'] // 100} ₽"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "admin:search")
async def admin_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_search)
    await callback.message.answer("Введите telegram_id или @username:")
    await callback.answer()


@router.message(AdminStates.waiting_search)
async def admin_search_process(message: Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return
    async with async_session() as session:
        users = await search_users(session, message.text or "")
    await state.clear()
    if not users:
        await message.answer("Пользователи не найдены.")
        return
    lines = []
    for user in users:
        lines.append(
            f"id={user.id} tg={user.telegram_id} @{user.username or '-'} "
            f"balance={user.balance} admin={user.is_admin}"
        )
    await message.answer("\n".join(lines))


@router.callback_query(F.data == "admin:credit")
async def admin_credit_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_credit)
    await callback.message.answer("Формат: telegram_id количество\nПример: 123456789 5")
    await callback.answer()


@router.message(AdminStates.waiting_credit)
async def admin_credit_process(message: Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("Неверный формат.")
        return
    tg_id = int(parts[0])
    amount = int(parts[1])
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, tg_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return
        user = await adjust_balance(session, user, amount)
    await state.clear()
    await message.answer(f"Начислено {amount}. Новый баланс: {user.balance}")


@router.callback_query(F.data == "admin:debit")
async def admin_debit_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_debit)
    await callback.message.answer("Формат: telegram_id количество\nПример: 123456789 2")
    await callback.answer()


@router.message(AdminStates.waiting_debit)
async def admin_debit_process(message: Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("Неверный формат.")
        return
    tg_id = int(parts[0])
    amount = int(parts[1])
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, tg_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return
        user = await adjust_balance(session, user, -amount)
    await state.clear()
    await message.answer(f"Списано {amount}. Новый баланс: {user.balance}")


@router.callback_query(F.data == "admin:errors")
async def admin_errors(callback: CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with async_session() as session:
        items = await get_recent_failed_generations(session)
    if not items:
        await callback.message.answer("Ошибок нет.")
        await callback.answer()
        return
    lines = []
    for gen in items:
        lines.append(
            f"#{gen.id} user={gen.user_id} {gen.created_at:%Y-%m-%d %H:%M}\n{gen.error_message or '-'}"
        )
    await callback.message.answer("\n\n".join(lines[:10]))
    await callback.answer()


@router.callback_query(F.data == "admin:payments")
async def admin_payments(callback: CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with async_session() as session:
        items = await get_recent_payments(session)
    if not items:
        await callback.message.answer("Платежей нет.")
        await callback.answer()
        return
    lines = []
    for pay in items:
        lines.append(
            f"#{pay.id} order={pay.order_id} user={pay.user_id} "
            f"status={pay.status} amount={pay.amount // 100}₽ gen={pay.generations_count}"
        )
    await callback.message.answer("\n".join(lines[:10]))
    await callback.answer()
