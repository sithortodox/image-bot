from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_search = State()
    waiting_credit = State()
    waiting_debit = State()
