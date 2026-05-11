from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from models.user import User
from data.config import ADMINS
from states.user_state import UserState
from keyboards.inline.menu import get_back_keyboard, get_main_keyboard

router = Router()


@router.callback_query(F.data == "menu_feedback")
async def feedback_start(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    tid = call.from_user.id
    user = await User.get_or_none(telegram_id=tid)
    lang = user.language if user else "uz"
    await call.message.edit_text(
        "💬 Taklif yoki murojjatingizni yozib yuboring:",
        reply_markup=get_back_keyboard(lang)
    )
    await state.set_state(UserState.waiting_feedback)


@router.message(UserState.waiting_feedback)
async def feedback_process(message: types.Message, state: FSMContext):
    await state.clear()
    tid = message.from_user.id
    user = await User.get_or_none(telegram_id=tid)
    lang = user.language if user else "uz"
    msg = message.text or message.caption or ""
    for admin_id in ADMINS:
        try:
            await message.bot.send_message(
                int(admin_id),
                f"💬 Yangi taklif/murojjat\n\n👤 {message.from_user.full_name}\n🆔 {tid}\n📝 {msg}"
            )
        except:
            pass
    from utils.i18n import get_text
    await message.answer(get_text("feedback_sent", lang), reply_markup=get_main_keyboard(lang))
