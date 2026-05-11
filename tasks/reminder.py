from datetime import date, timedelta
from models.user import User
from models.schedule import Schedule

UZ_DAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
DAY_MAP = {"Monday": "Dushanba", "Tuesday": "Seshanba", "Wednesday": "Chorshanba",
           "Thursday": "Payshanba", "Friday": "Juma", "Saturday": "Shanba", "Sunday": "Yakshanba"}


async def send_daily_reminders(bot):
    from services.hemis_service import create_session, check_login_status, fetch_schedule
    from services.schedule_service import get_cached_week_id
    from services.session_store import user_sessions
    from handlers.users.profile import _hemis_auto_login

    tomorrow = (date.today() + timedelta(days=1)).strftime("%A")
    tomorrow_uz = DAY_MAP.get(tomorrow, tomorrow)

    users = await User.filter(reminder_enabled=True, hemis_login__not_isnull=True)

    for user in users:
        tid = user.telegram_id
        session = user_sessions.get(tid)
        if not session or not check_login_status(session):
            success, session = await _hemis_auto_login(tid)
            if not success:
                continue
        week_id = get_cached_week_id()
        data = fetch_schedule(session, week_id)
        tomorrow_data = [d for d in data if d["day"] == tomorrow_uz]
        if not tomorrow_data:
            try:
                await bot.send_message(tid, f"📅 Ertaga ({tomorrow_uz}) dars yo'q! 🎉")
            except:
                pass
            continue
        text = f"📅 Ertangi dars jadval ({tomorrow_uz}):\n\n"
        for d in tomorrow_data:
            room = f" ({d['room']})" if d['room'] else ""
            text += f"{d['lesson_time']} — {d['subject']}{room}\n"
        try:
            await bot.send_message(tid, text)
        except:
            pass
