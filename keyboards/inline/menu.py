from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.i18n import get_text


def get_main_keyboard(language: str = "uz") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("btn_schedule", language),
                callback_data="menu_schedule"
            ),
            InlineKeyboardButton(
                text=get_text("btn_profile", language),
                callback_data="menu_profile"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("btn_feedback", language),
                callback_data="menu_feedback"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedule_menu_keyboard(language: str = "uz") -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(
            text=get_text("btn_today_schedule", language),
            callback_data="today_schedule"
        )],
        [InlineKeyboardButton(
            text=get_text("btn_week_schedule", language),
            callback_data="week_schedule"
        )],
        [InlineKeyboardButton(
            text=get_text("btn_back", language),
            callback_data="back_to_menu"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_week_pagination_keyboard(language: str = "uz", week_id: str = None) -> InlineKeyboardMarkup:
    from services.schedule_service import get_prev_week_id, get_next_week_id, format_week_date_range

    keyboard = []

    if week_id:
        prev_week = get_prev_week_id(week_id)
        next_week = get_next_week_id(week_id)
        prev_date_range = format_week_date_range(prev_week, language)
        next_date_range = format_week_date_range(next_week, language)

        keyboard.append([
            InlineKeyboardButton(
                text=f"⬅️ {prev_date_range}",
                callback_data=f"select_week:{prev_week}"
            ),
            InlineKeyboardButton(
                text=f"{next_date_range} ➡️",
                callback_data=f"select_week:{next_week}"
            ),
        ])

        keyboard.append([
            InlineKeyboardButton(
                text=get_text("btn_update_schedule", language),
                callback_data=f"update_schedule:{week_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text=get_text("btn_back", language),
            callback_data="menu_schedule"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_profile_keyboard(language: str = "uz", connected: bool = False, reminder: bool = False) -> InlineKeyboardMarkup:
    buttons = []

    if connected:
        buttons.append([
            InlineKeyboardButton(
                text=get_text("btn_disconnect_hemis", language),
                callback_data="disconnect_hemis"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text=get_text("btn_reminder_disable" if reminder else "btn_reminder_enable", language),
                callback_data="reminder_disable" if reminder else "reminder_enable"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text=get_text("btn_connect_hemis", language),
                callback_data="connect_hemis"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text=get_text("btn_back", language),
            callback_data="back_to_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard(language: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=get_text("btn_back", language),
            callback_data="back_to_menu"
        )
    ]])


def get_admin_menu_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data='admin_allusers'),
            InlineKeyboardButton(text="📊 Statistika", callback_data='admin_stats'),
        ],
        [
            InlineKeyboardButton(text="📢 Reklama", callback_data='admin_reklama'),
            InlineKeyboardButton(text="🗑️ Tozalash", callback_data='admin_cleandb'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


are_you_sure_markup = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✅ Ha", callback_data='yes'),
    InlineKeyboardButton(text="❌ Yo'q", callback_data='no'),
]])


def get_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("lang_uzbek", "uz"),
                callback_data="set_lang:uz"
            ),
            InlineKeyboardButton(
                text=get_text("lang_english", "en"),
                callback_data="set_lang:en"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("lang_russian", "ru"),
                callback_data="set_lang:ru"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
