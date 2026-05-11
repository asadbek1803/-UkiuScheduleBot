import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from models.user import get_user, get_or_create_user, update_user
from utils.i18n import get_text
from keyboards.inline.menu import get_profile_keyboard, get_back_keyboard, get_main_keyboard
from states.user_state import UserState
from services.hemis_service import (
    get_hemis_captcha,
    hemis_login,
    create_session,
    check_login_status,
    get_student_group,
)
from services.schedule_service import update_cached_week_id
from services.session_store import user_sessions

router = Router()
logger = logging.getLogger(__name__)


async def _hemis_auto_login(tid: int) -> tuple:
    try:
        user = await get_user(tid)
        if not user or not user.hemis_login or not user.hemis_password:
            return False, None
        session = create_session()
        csrf, captcha_bytes, cookies = get_hemis_captcha(session)
        if not csrf or not captcha_bytes:
            return False, None
        captcha_code = "0000"
        success, error = hemis_login(session, csrf, user.hemis_login, user.hemis_password, captcha_code)
        if success:
            user_sessions[tid] = session
            return True, session
        return False, None
    except Exception:
        return False, None


async def _ensure_user(tid: int):
    user, _ = await get_or_create_user(tid)
    return user


@router.callback_query(F.data == "menu_profile")
async def show_profile(call: types.CallbackQuery):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)

    connected = bool(user.hemis_login)
    group = user.group_name or "—"

    text = (
        f"<b>{get_text('btn_profile', user.language)}</b>\n\n"
        f"ID: <code>{tid}</code>\n"
        f"Guruh: {group}\n"
        f"HEMIS: {'✅' if connected else '❌'}"
    )

    await call.message.edit_text(
        text,
        reply_markup=get_profile_keyboard(user.language, connected, user.reminder_enabled),
    )


@router.callback_query(F.data == "connect_hemis")
async def connect_hemis(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)

    msg = await call.message.edit_text(
        get_text("enter_hemis_login", user.language),
        reply_markup=get_back_keyboard(user.language),
    )
    await state.update_data(flow_message_id=msg.message_id)
    await state.set_state(UserState.waiting_hemis_login)


@router.message(UserState.waiting_hemis_login)
async def process_login(message: types.Message, state: FSMContext):
    data = await state.get_data()
    login = message.text.strip()
    flow_msg = data.get("flow_message_id")

    try:
        await message.delete()
    except:
        pass

    try:
        await message.bot.delete_message(message.chat.id, flow_msg)
    except:
        pass

    await state.update_data(hemis_login=login)
    ask_password = await message.answer("🔐 HEMIS parolini kiriting:")
    await state.update_data(flow_message_id=ask_password.message_id)
    await state.set_state(UserState.waiting_hemis_password)


@router.message(UserState.waiting_hemis_password)
async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    password = message.text.strip()
    flow_msg = data.get("flow_message_id")

    try:
        await message.delete()
    except:
        pass

    try:
        await message.bot.delete_message(message.chat.id, flow_msg)
    except:
        pass

    await state.update_data(hemis_password=password)

    session = create_session()
    csrf, captcha_bytes, cookies = get_hemis_captcha(session)

    if not csrf or not captcha_bytes:
        await message.answer("❌ Captcha yuklanmadi")
        await state.clear()
        return

    await state.update_data(csrf=csrf, cookies=cookies)

    photo = types.BufferedInputFile(captcha_bytes, filename="captcha.jpg")
    captcha_msg = await message.answer_photo(
        photo,
        caption="🧩 Captcha kodini kiriting:",
    )
    await state.update_data(captcha_message_id=captcha_msg.message_id)
    await state.set_state(UserState.waiting_hemis_captcha)


@router.message(UserState.waiting_hemis_captcha)
async def process_captcha(message: types.Message, state: FSMContext):
    tid = message.from_user.id
    user = await _ensure_user(tid)

    data = await state.get_data()
    login = data.get("hemis_login")
    password = data.get("hemis_password")
    csrf = data.get("csrf")
    cookies = data.get("cookies")
    captcha_msg_id = data.get("captcha_message_id")
    captcha_code = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    try:
        await message.bot.delete_message(message.chat.id, captcha_msg_id)
    except:
        pass

    wait = await message.answer("⏳ HEMIS ga ulanmoqda...")

    session = create_session()
    for k, v in cookies.items():
        session.cookies.set(k, v, domain="student.ukiu.uz")

    is_valid, error = hemis_login(session, csrf, login, password, captcha_code)

    if not is_valid:
        await wait.edit_text("❌ Login yoki captcha xato")
        await state.clear()
        return

    user_sessions[tid] = session
    update_cached_week_id(session)
    group_name = get_student_group(session)

    await update_user(tid, hemis_login=login, hemis_password=password, group_name=group_name)

    await wait.delete()

    await message.answer(
        get_text("hemis_connected", user.language),
        reply_markup=get_profile_keyboard(user.language, True, user.reminder_enabled),
    )

    await state.clear()


@router.callback_query(F.data == "disconnect_hemis")
async def disconnect_hemis(call: types.CallbackQuery):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)

    await update_user(tid, hemis_login=None, hemis_password=None, group_name=None, reminder_enabled=False)

    if tid in user_sessions:
        del user_sessions[tid]

    await call.message.edit_text(
        get_text("hemis_disconnected", user.language),
        reply_markup=get_profile_keyboard(user.language, False, False),
    )


@router.callback_query(F.data == "reminder_enable")
async def reminder_enable(call: types.CallbackQuery):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)
    await update_user(tid, reminder_enabled=True)

    await call.message.edit_text(
        get_text("reminder_enabled_text", user.language),
        reply_markup=get_profile_keyboard(user.language, True, True),
    )


@router.callback_query(F.data == "reminder_disable")
async def reminder_disable(call: types.CallbackQuery):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)
    await update_user(tid, reminder_enabled=False)

    await call.message.edit_text(
        get_text("reminder_disabled_text", user.language),
        reply_markup=get_profile_keyboard(user.language, True, False),
    )
