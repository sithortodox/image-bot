import json
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Generation, GenerationStatus, Payment, PaymentStatus, User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.username = username
        user.full_name = full_name
        await session.commit()
        await session.refresh(user)
        return user

    admin_ids = get_settings().admin_ids
    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        balance=0,
        is_admin=telegram_id in admin_ids,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def search_users(session: AsyncSession, query: str, limit: int = 10) -> list[User]:
    q = query.strip().lstrip("@")
    stmt = select(User)
    if q.isdigit():
        stmt = stmt.where(User.telegram_id == int(q))
    else:
        stmt = stmt.where(User.username.ilike(f"%{q}%"))
    result = await session.execute(stmt.limit(limit))
    return list(result.scalars().all())


async def adjust_balance(session: AsyncSession, user: User, delta: int) -> User:
    user.balance = max(0, user.balance + delta)
    await session.commit()
    await session.refresh(user)
    return user


async def create_generation(
    session: AsyncSession,
    user_id: int,
    input_file_path: str,
) -> Generation:
    gen = Generation(
        user_id=user_id,
        status=GenerationStatus.PENDING,
        input_file_path=input_file_path,
    )
    session.add(gen)
    await session.commit()
    await session.refresh(gen)
    return gen


async def update_generation(
    session: AsyncSession,
    generation: Generation,
    **kwargs,
) -> Generation:
    for key, value in kwargs.items():
        setattr(generation, key, value)
    generation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(generation)
    return generation


async def deduct_balance_on_success(session: AsyncSession, user: User) -> bool:
    if user.balance <= 0:
        return False
    user.balance -= 1
    await session.commit()
    await session.refresh(user)
    return True


async def create_payment(
    session: AsyncSession,
    user_id: int,
    order_id: str,
    amount: int,
    generations_count: int,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        provider="tbank",
        order_id=order_id,
        amount=amount,
        generations_count=generations_count,
        status=PaymentStatus.CREATED,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment_by_order_id(session: AsyncSession, order_id: str) -> Payment | None:
    result = await session.execute(select(Payment).where(Payment.order_id == order_id))
    return result.scalar_one_or_none()


async def update_payment(
    session: AsyncSession,
    payment: Payment,
    **kwargs,
) -> Payment:
    for key, value in kwargs.items():
        setattr(payment, key, value)
    payment.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(payment)
    return payment


async def credit_payment_generations(session: AsyncSession, payment: Payment) -> bool:
    if payment.status == PaymentStatus.PAID:
        return False
    user = await get_user_by_id(session, payment.user_id)
    if not user:
        return False
    user.balance += payment.generations_count
    payment.status = PaymentStatus.PAID
    await session.commit()
    return True


async def get_stats(session: AsyncSession) -> dict:
    users_count = await session.scalar(select(func.count()).select_from(User))
    gens_success = await session.scalar(
        select(func.count())
        .select_from(Generation)
        .where(Generation.status == GenerationStatus.SUCCESS)
    )
    gens_failed = await session.scalar(
        select(func.count())
        .select_from(Generation)
        .where(Generation.status == GenerationStatus.FAILED)
    )
    payments_paid = await session.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.PAID)
    )
    total_revenue = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.PAID
        )
    )
    return {
        "users": users_count or 0,
        "generations_success": gens_success or 0,
        "generations_failed": gens_failed or 0,
        "payments_paid": payments_paid or 0,
        "total_revenue_kopecks": total_revenue or 0,
    }


async def get_recent_failed_generations(
    session: AsyncSession, limit: int = 10
) -> list[Generation]:
    result = await session.execute(
        select(Generation)
        .where(Generation.status == GenerationStatus.FAILED)
        .order_by(desc(Generation.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_recent_payments(session: AsyncSession, limit: int = 10) -> list[Payment]:
    result = await session.execute(
        select(Payment).order_by(desc(Payment.created_at)).limit(limit)
    )
    return list(result.scalars().all())


def payment_raw_payload(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)
