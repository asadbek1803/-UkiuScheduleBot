from aiogram.fsm.state import StatesGroup, State


class UserState(StatesGroup):
    waiting_hemis_login = State()
    waiting_hemis_password = State()
    waiting_hemis_captcha = State()
    waiting_hemis_captcha_schedule = State()
    waiting_feedback = State()


class AdminState(StatesGroup):
    are_you_sure = State()
    ask_ad_content = State()
    add_admin = State()
    remove_admin = State()
    reply_user = State()
