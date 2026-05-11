import logging
from datetime import datetime
from typing import Optional, List
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from models.user import User
from models.schedule import Schedule
from utils.i18n import get_text
from keyboards.inline.menu import (
    get_schedule_menu_keyboard,
    get_week_pagination_keyboard,
    get_back_keyboard,
)
from services.schedule_service import (
    get_cached_week_id,
    get_prev_week_id,
    get_next_week_id,
    format_week_date_range,
    update_cached_week_id,
)
from services.hemis_service import (
    get_hemis_captcha,
    hemis_login,
    create_session,
    fetch_schedule,
    check_login_status,
    get_current_week_id,
    get_student_group,
)
from services.session_store import user_sessions
from states.user_state import UserState

router = Router()
logger = logging.getLogger(__name__)

UZ_DAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

CACHE_TTL_SECONDS = 3600


def _today_uz_name() -> str:
    return UZ_DAYS[datetime.today().weekday()]


def _schedule_to_dict(s: Schedule) -> dict:
    return {
        "day": s.day,
        "pair_number": s.pair_number,
        "subject": s.subject,
        "teacher": s.teacher,
        "room": s.room,
        "lesson_type": s.lesson_type,
        "lesson_time": s.lesson_time,
    }


def _format_schedule_text(schedules: list, week_id: str = None, language: str = "uz") -> str:
    if week_id:
        date_range = format_week_date_range(week_id, language)
        text = f"{get_text('week_schedule', language)}<b>{date_range}</b>\n\n"
    else:
        today_name = _today_uz_name()
        today_schedules = [s for s in schedules if s["day"] == today_name]
        text = get_text("today_schedule", language)
        if not today_schedules:
            text += get_text("no_classes_today", language)
            return text
        schedules = today_schedules

    if not schedules:
        text += get_text("no_classes_today", language)
        return text

    days: dict = {}
    for s in schedules:
        days.setdefault(s["day"], []).append(s)

    for day in UZ_DAYS:
        if day in days:
            text += f"📅 <b>{day}</b>\n"
            day_schedules = sorted(days[day], key=lambda x: x.get("pair_number", 0))
            for s in day_schedules:
                time = s.get("lesson_time", "")
                subject = s.get("subject", "")
                room = f" ({s['room']})" if s.get("room") else ""
                text += f"{time} — {subject}{room}\n"
            text += "\n"

    return text


async def _ensure_user(tid: int) -> User:
    user, _ = await User.get_or_create(telegram_id=tid)
    return user


async def _get_cached_schedule(user: User, week_id: str) -> Optional[List[dict]]:
    schedules = await Schedule.filter(user=user, week_id=week_id).order_by("pair_number")
    if not schedules:
        return None
    if (datetime.now() - schedules[0].cached_at).total_seconds() > CACHE_TTL_SECONDS:
        return None
    return [_schedule_to_dict(s) for s in schedules]


async def _cache_schedule(user: User, week_id: str, schedules_data: list):
    await Schedule.filter(user=user, week_id=week_id).delete()
    if not schedules_data:
        return
    for s in schedules_data:
        await Schedule.create(
            user=user,
            week_id=week_id,
            day=s.get("day", ""),
            pair_number=s.get("pair_number", 0),
            subject=s.get("subject", ""),
            teacher=s.get("teacher", ""),
            room=s.get("room", ""),
            lesson_type=s.get("lesson_type", ""),
            lesson_time=s.get("lesson_time", ""),
        )


async def _start_captcha_flow(
    message: types.Message,
    state: FSMContext,
    language: str,
    action_type: str,
    week_id: str,
):
    session = create_session()
    csrf, captcha_bytes, cookies = get_hemis_captcha(session)

    if not csrf or not captcha_bytes:
        await message.edit_text(
            get_text("error_loading", language),
            reply_markup=get_back_keyboard(language),
        )
        return

    await state.update_data(
        csrf=csrf,
        cookies=cookies,
        action_type=action_type,
        captcha_week_id=week_id,
        captcha_session=session,
    )

    try:
        await message.delete()
    except Exception:
        pass

    photo = types.BufferedInputFile(captcha_bytes, filename="captcha.jpg")
    await message.answer_photo(
        photo=photo,
        caption=get_text("enter_captcha", language),
    )
    await state.set_state(UserState.waiting_hemis_captcha_schedule)


@router.callback_query(F.data == "menu_schedule")
async def show_schedule_menu(call: types.CallbackQuery):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)

    await call.message.edit_text(
        "📅 <b>" + get_text("btn_schedule", user.language).replace("📅 ", "") + "</b>",
        reply_markup=get_schedule_menu_keyboard(user.language),
    )


@router.callback_query(F.data == "today_schedule")
async def show_today_schedule(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)

    if not user.hemis_login:
        await call.message.edit_text(
            "❌ Avval HEMIS ni ulang! /start",
            reply_markup=get_back_keyboard(user.language),
        )
        return

    await call.message.edit_text(get_text("schedule_loading", user.language))

    week_id = get_cached_week_id()

    cached = await _get_cached_schedule(user, week_id)
    if cached is not None:
        text = _format_schedule_text(cached, week_id=None, language=user.language)
        await call.message.edit_text(text, reply_markup=get_schedule_menu_keyboard(user.language))
        return

    session = user_sessions.get(tid)
    if not session or not check_login_status(session):
        from handlers.users.profile import _hemis_auto_login
        success, session = await _hemis_auto_login(tid)
        if not success:
            await call.message.edit_text(
                get_text("hemis_login_error", user.language),
                reply_markup=get_back_keyboard(user.language),
            )
            return

    schedules_data = fetch_schedule(session, week_id)
    await _cache_schedule(user, week_id, schedules_data)

    text = _format_schedule_text(schedules_data, week_id=None, language=user.language)
    await call.message.edit_text(text, reply_markup=get_schedule_menu_keyboard(user.language))


@router.callback_query(F.data == "week_schedule")
async def show_week_schedule(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)

    if not user.hemis_login:
        await call.message.edit_text(
            "❌ Avval HEMIS ni ulang! /start",
            reply_markup=get_back_keyboard(user.language),
        )
        return

    await call.message.edit_text(get_text("schedule_loading", user.language))

    week_id = get_cached_week_id()

    cached = await _get_cached_schedule(user, week_id)
    if cached is not None:
        await state.update_data(selected_week_id=week_id)
        text = _format_schedule_text(cached, week_id=week_id, language=user.language)
        await call.message.edit_text(text, reply_markup=get_week_pagination_keyboard(user.language, week_id))
        return

    session = user_sessions.get(tid)
    if not session or not check_login_status(session):
        from handlers.users.profile import _hemis_auto_login
        success, session = await _hemis_auto_login(tid)
        if not success:
            await call.message.edit_text(
                get_text("hemis_login_error", user.language),
                reply_markup=get_back_keyboard(user.language),
            )
            return

    schedules_data = fetch_schedule(session, week_id)
    await _cache_schedule(user, week_id, schedules_data)

    await state.update_data(selected_week_id=week_id)
    text = _format_schedule_text(schedules_data, week_id=week_id, language=user.language)
    await call.message.edit_text(text, reply_markup=get_week_pagination_keyboard(user.language, week_id))


@router.callback_query(F.data.startswith("select_week:"))
async def select_week(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)

    week_id = call.data.split(":")[1]

    await call.message.edit_text(get_text("schedule_loading", user.language))

    cached = await _get_cached_schedule(user, week_id)
    if cached is not None:
        await state.update_data(selected_week_id=week_id)
        text = _format_schedule_text(cached, week_id=week_id, language=user.language)
        await call.message.edit_text(text, reply_markup=get_week_pagination_keyboard(user.language, week_id))
        return

    session = user_sessions.get(tid)
    if not session or not check_login_status(session):
        from handlers.users.profile import _hemis_auto_login
        success, session = await _hemis_auto_login(tid)
        if not success:
            await state.update_data(
                action_type="week_select",
                captcha_week_id=week_id,
            )
            await _start_captcha_flow(call.message, state, user.language, "week_select", week_id)
            return

    schedules_data = fetch_schedule(session, week_id)
    await _cache_schedule(user, week_id, schedules_data)

    await state.update_data(selected_week_id=week_id)
    text = _format_schedule_text(schedules_data, week_id=week_id, language=user.language)
    await call.message.edit_text(text, reply_markup=get_week_pagination_keyboard(user.language, week_id))


@router.callback_query(F.data.startswith("update_schedule:"))
async def update_schedule(call: types.CallbackQuery, state: FSMContext):
    week_id = call.data.split(":")[1]
    await call.answer()
    tid = call.from_user.id
    user = await _ensure_user(tid)

    await call.message.edit_text(get_text("schedule_loading", user.language))

    session = user_sessions.get(tid)
    if not session or not check_login_status(session):
        from handlers.users.profile import _hemis_auto_login
        success, session = await _hemis_auto_login(tid)
        if not success:
            await _start_captcha_flow(call.message, state, user.language, "force_update", week_id)
            return

    schedules_data = fetch_schedule(session, week_id)
    await _cache_schedule(user, week_id, schedules_data)

    await state.update_data(selected_week_id=week_id)
    text = _format_schedule_text(schedules_data, week_id=week_id, language=user.language)
    await call.message.edit_text(text, reply_markup=get_week_pagination_keyboard(user.language, week_id))


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    from handlers.users.start import cmd_start
    await cmd_start(call.message)


@router.message(UserState.waiting_hemis_captcha_schedule)
async def process_schedule_captcha(message: types.Message, state: FSMContext):
    tid = message.from_user.id
    user = await _ensure_user(tid)

    data = await state.get_data()
    action_type = data.get("action_type", "week")
    csrf = data.get("csrf")
    cookies_dict = data.get("cookies", {})
    captcha_code = message.text.strip()
    week_id = data.get("captcha_week_id")

    wait_msg = await message.answer(get_text("loading", user.language))

    session = create_session()
    for k, v in cookies_dict.items():
        session.cookies.set(k, v, domain="student.ukiu.uz")

    is_valid, error_msg = hemis_login(session, csrf, user.hemis_login or "", user.hemis_password or "", captcha_code)

    if not is_valid:
        await wait_msg.delete()
        await message.answer(
            f"{error_msg}\n\nQaytadan urinib ko'ring",
            reply_markup=get_back_keyboard(user.language),
        )
        await state.clear()
        return

    user_sessions[tid] = session
    update_cached_week_id(session)

    if not week_id:
        week_id = get_cached_week_id()

    schedules_data = fetch_schedule(session, week_id)
    await _cache_schedule(user, week_id, schedules_data)

    await wait_msg.delete()
    await state.clear()

    if action_type == "today":
        text = _format_schedule_text(schedules_data, week_id=None, language=user.language)
        keyboard = get_schedule_menu_keyboard(user.language)
    else:
        text = _format_schedule_text(schedules_data, week_id=week_id, language=user.language)
        keyboard = get_week_pagination_keyboard(user.language, week_id)

    await message.answer(text, reply_markup=keyboard)
