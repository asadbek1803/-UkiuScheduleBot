from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from models.user import get_user, get_or_create_user, update_user
from utils.i18n import get_text
from keyboards.inline.menu import get_main_keyboard, get_language_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    tid = message.from_user.id
    user, created = await get_or_create_user(
        tid,
        defaults={
            "username": message.from_user.username,
            "full_name": message.from_user.full_name,
        },
    )
    if created:
        await message.answer(
            get_text("select_language", "uz"),
            reply_markup=get_language_keyboard(),
        )
        return
    await message.answer(
        get_text("welcome", user.language),
        reply_markup=get_main_keyboard(user.language),
    )


@router.callback_query(F.data.startswith("set_lang:"))
async def set_language(call: types.CallbackQuery):
    lang = call.data.split(":")[1]
    tid = call.from_user.id
    await update_user(tid, language=lang)
    await call.message.edit_text(
        get_text("language_changed", lang),
        reply_markup=get_main_keyboard(lang),
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    user = await get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await message.answer(
        get_text("help_text", lang),
    )
