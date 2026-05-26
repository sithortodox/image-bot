import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import get_settings
from app.db.models import PaymentStatus
from app.db.repository import (
    credit_payment_generations,
    get_payment_by_order_id,
    payment_raw_payload,
    update_payment,
)
from app.db.session import async_session, init_db
from app.logging_setup import setup_logging
from app.services.tbank import verify_notification_token

logger = logging.getLogger("payments")
error_logger = logging.getLogger("errors")

app = FastAPI(title="Image Bot Webhook")


@app.on_event("startup")
async def on_startup() -> None:
    setup_logging()
    await init_db()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/payments/tbank/webhook")
async def tbank_webhook(request: Request) -> PlainTextResponse:
    settings = get_settings()
    try:
        payload = await request.json()
    except Exception:
        error_logger.exception("Invalid webhook JSON")
        return PlainTextResponse("INVALID", status_code=400)

    if not verify_notification_token(payload, settings.tbank_password):
        error_logger.warning("Invalid TBank webhook token: %s", payload.get("OrderId"))
        return PlainTextResponse("INVALID TOKEN", status_code=403)

    order_id = payload.get("OrderId")
    status = payload.get("Status")
    payment_id = payload.get("PaymentId")

    logger.info("Webhook order=%s status=%s", order_id, status)

    if not order_id:
        return PlainTextResponse("OK")

    async with async_session() as session:
        payment = await get_payment_by_order_id(session, order_id)
        if not payment:
            error_logger.warning("Payment not found for order %s", order_id)
            return PlainTextResponse("OK")

        await update_payment(
            session,
            payment,
            payment_id=str(payment_id) if payment_id else payment.payment_id,
            raw_payload=payment_raw_payload(payload),
        )

        if status in {"CONFIRMED", "AUTHORIZED"}:
            credited = await credit_payment_generations(session, payment)
            if credited:
                logger.info(
                    "Credited %s generations for order %s",
                    payment.generations_count,
                    order_id,
                )
        elif status in {"REJECTED", "REVERSED", "REFUNDED", "PARTIAL_REFUNDED"}:
            await update_payment(session, payment, status=PaymentStatus.FAILED)
        elif status == "CANCELED":
            await update_payment(session, payment, status=PaymentStatus.CANCELED)
        else:
            await update_payment(session, payment, status=PaymentStatus.PENDING)

    return PlainTextResponse("OK")
