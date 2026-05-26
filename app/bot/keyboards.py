from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.packages import PACKAGES


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Загрузить изображение")],
            [KeyboardButton(text="Купить генерации"), KeyboardButton(text="Мой баланс")],
            [KeyboardButton(text="Помощь")],
        ],
        resize_keyboard=True,
    )


def packages_kb() -> InlineKeyboardMarkup:
    rows = []
    for pack_id, pack in PACKAGES.items():
        amount_rub = pack["amount"] // 100
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{pack['title']} — {amount_rub} ₽",
                    callback_data=f"buy:{pack_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="Поиск пользователя", callback_data="admin:search")],
            [
                InlineKeyboardButton(
                    text="Начислить генерации", callback_data="admin:credit"
                ),
                InlineKeyboardButton(text="Списать генерации", callback_data="admin:debit"),
            ],
            [InlineKeyboardButton(text="Ошибки генераций", callback_data="admin:errors")],
            [InlineKeyboardButton(text="Последние платежи", callback_data="admin:payments")],
        ]
    )
