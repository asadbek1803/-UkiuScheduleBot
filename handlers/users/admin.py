import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from models.user import User
from models.schedule import Schedule
from keyboards.inline.menu import get_admin_menu_markup, are_you_sure_markup
from states.user_state import AdminState
from filters.admin import IsBotAdminFilter
from data.config import ADMINS

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command('admin'), IsBotAdminFilter())
async def admin_panel(message: types.Message):
    text = """
🔐 <b>ADMIN PANEL</b>

• /allusers - Barcha foydalanuvchilar
• /stats - Statistika
• /reklama - Reklama yuborish
• /cleandb - Bazani tozalash
"""
    await message.answer(text, reply_markup=get_admin_menu_markup())


@router.callback_query(F.data == 'admin_allusers')
async def admin_allusers_callback(call: types.CallbackQuery):
    await call.answer()
    await get_all_users_handler(call.message)


@router.message(Command('allusers'), IsBotAdminFilter())
async def get_all_users(message: types.Message):
    await get_all_users_handler(message)


async def get_all_users_handler(message: types.Message):
    total = await User.all().count()
    if total == 0:
        await message.answer("❌ Foydalanuvchilar topilmadi.")
        return

    text = f"👥 <b>Barcha foydalanuvchilar: {total}</b>\n\n"
    users = await User.all().limit(20)
    for idx, user in enumerate(users, 1):
        connected = "✅" if user.hemis_login else "❌"
        group = user.group_name or "—"
        text += f"{idx}. <code>{user.telegram_id}</code> | HEMIS:{connected} | {group}\n"

    if total > 20:
        text += f"\n... va yana {total - 20} ta"

    await message.answer(text)


@router.callback_query(F.data == 'admin_stats')
async def admin_stats_callback(call: types.CallbackQuery):
    await call.answer()
    await stats_handler(call.message)


@router.message(Command('stats'), IsBotAdminFilter())
async def stats(message: types.Message):
    await stats_handler(message)


async def stats_handler(message: types.Message):
    total = await User.all().count()
    connected = await User.filter(hemis_login__not_isnull=True).count()
    reminders = await User.filter(reminder_enabled=True).count()

    text = f"""
📊 <b>Bot statistikasi</b>

👥 Jami: {total}
🔗 HEMIS ulangan: {connected}
🔔 Eslatma yoqilgan: {reminders}
"""
    await message.answer(text)


@router.callback_query(F.data == 'admin_reklama')
async def admin_reklama_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer("📢 Reklama uchun post yuboring:")
    await state.set_state(AdminState.ask_ad_content)


@router.message(Command('reklama'), IsBotAdminFilter())
async def ask_ad_content(message: types.Message, state: FSMContext):
    await message.answer("📢 Reklama uchun post yuboring:")
    await state.set_state(AdminState.ask_ad_content)


@router.message(AdminState.ask_ad_content, IsBotAdminFilter())
async def send_ad_to_users(message: types.Message, state: FSMContext):
    try:
        await message.answer("⏳ Reklama yuborilmoqda...")
        user_ids = await User.all().values_list('telegram_id', flat=True)
        total = len(user_ids)
        success = 0
        failed = 0

        for tid in user_ids:
            try:
                if message.photo:
                    await message.bot.send_photo(
                        chat_id=tid,
                        photo=message.photo[-1].file_id,
                        caption=message.caption or "",
                    )
                elif message.video:
                    await message.bot.send_video(
                        chat_id=tid,
                        video=message.video.file_id,
                        caption=message.caption or "",
                    )
                elif message.document:
                    await message.bot.send_document(
                        chat_id=tid,
                        document=message.document.file_id,
                        caption=message.caption or "",
                    )
                elif message.animation:
                    await message.bot.send_animation(
                        chat_id=tid,
                        animation=message.animation.file_id,
                        caption=message.caption or "",
                    )
                else:
                    await message.bot.send_message(
                        chat_id=tid,
                        text=message.text or message.caption or "",
                        entities=message.entities or message.caption_entities,
                    )
                success += 1
            except Exception:
                failed += 1

        await message.answer(
            f"✅ Reklama yuborildi\n\n✅ Muvaffaqiyatli: {success}\n❌ Xatolik: {failed}\n📊 Jami: {total}"
        )
        await state.clear()

    except Exception as e:
        logger.exception(f"Reklama xatoligi: {e}")
        await message.answer(f"❌ Xatolik: {str(e)}")
        await state.clear()


@router.callback_query(F.data == 'admin_cleandb')
async def admin_cleandb_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    msg = await call.message.answer(
        "⚠️ <b>EHTIYOT!</b>\n\nHaqiqatdan ham bazani tozalab yubormoqchimisiz?",
        reply_markup=are_you_sure_markup,
    )
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(AdminState.are_you_sure)


@router.message(Command('cleandb'), IsBotAdminFilter())
async def ask_are_you_sure(message: types.Message, state: FSMContext):
    msg = await message.reply(
        "⚠️ <b>EHTIYOT!</b>\n\nHaqiqatdan ham bazani tozalab yubormoqchimisiz?",
        reply_markup=are_you_sure_markup,
    )
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(AdminState.are_you_sure)


@router.callback_query(AdminState.are_you_sure, IsBotAdminFilter())
async def clean_db(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    if call.data == 'yes':
        count = await User.all().count()
        await User.all().delete()
        await Schedule.all().delete()
        await call.message.edit_text(f"✅ Baza tozalandi. O'chirilgan: {count} ta foydalanuvchi")
    else:
        await call.message.edit_text("❌ Amal bekor qilindi.")
    await state.clear()
