import logging
import time
from typing import Optional
from datetime import date, timedelta

logger = logging.getLogger(__name__)

_CACHED_WEEK_ID: Optional[str] = None
_CACHED_WEEK_ID_TIME: Optional[float] = None
_WEEK_ID_CACHE_TTL_SECONDS = 3600


def _get_fallback_week_id() -> str:
    return "10844"


def get_cached_week_id() -> str:
    global _CACHED_WEEK_ID
    if _CACHED_WEEK_ID:
        return _CACHED_WEEK_ID
    return _get_fallback_week_id()


def update_cached_week_id(authenticated_session) -> bool:
    global _CACHED_WEEK_ID, _CACHED_WEEK_ID_TIME

    try:
        from services.hemis_service import get_current_week_id
        logger.info("Attempting to update cached week ID with authenticated session...")
        week_id = get_current_week_id(authenticated_session)

        if week_id:
            _CACHED_WEEK_ID = week_id
            _CACHED_WEEK_ID_TIME = time.time()
            logger.info(f"Week ID cache updated: {week_id}")
            return True
        else:
            logger.warning("Failed to detect week ID even with authenticated session")
            return False
    except Exception as e:
        logger.error(f"Error updating week ID cache: {e}")
        return False


def get_prev_week_id(current_week_id: str) -> str:
    try:
        week_num = int(current_week_id)
        return str(week_num - 1)
    except (ValueError, TypeError):
        logger.warning(f"Cannot parse week ID '{current_week_id}' as integer")
        return current_week_id


def get_next_week_id(current_week_id: str) -> str:
    try:
        week_num = int(current_week_id)
        return str(week_num + 1)
    except (ValueError, TypeError):
        logger.warning(f"Cannot parse week ID '{current_week_id}' as integer")
        return current_week_id


def calculate_week_date_range(week_id: str) -> tuple[date, date]:
    try:
        reference_week_id = 10844
        reference_start_date = date(2026, 3, 9)

        current_week_num = int(week_id)
        week_offset = current_week_num - reference_week_id

        start_date = reference_start_date + timedelta(weeks=week_offset)
        end_date = start_date + timedelta(days=5)

        return start_date, end_date
    except (ValueError, TypeError):
        logger.warning(f"Cannot calculate date range for week ID '{week_id}'")
        return date.today(), date.today()


def format_week_date_range(week_id: str, language: str = "uz") -> str:
    start_date, end_date = calculate_week_date_range(week_id)

    if language == "uz":
        months_uz = {
            1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel",
            5: "may", 6: "iyun", 7: "iyul", 8: "avgust",
            9: "sentyabr", 10: "oktyabr", 11: "noyabr", 12: "dekabr",
        }
        start_str = f"{start_date.day}-{months_uz[start_date.month]}"
        end_str = f"{end_date.day}-{months_uz[end_date.month]}"
        return f"{start_str} — {end_str}"
    elif language == "ru":
        months_ru = {
            1: "янв", 2: "фев", 3: "мар", 4: "апр",
            5: "май", 6: "июн", 7: "июл", 8: "авг",
            9: "сен", 10: "окт", 11: "ноя", 12: "дек",
        }
        start_str = f"{start_date.day}-{months_ru[start_date.month]}"
        end_str = f"{end_date.day}-{months_ru[end_date.month]}"
        return f"{start_str} — {end_str}"
    else:
        months_en = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        start_str = f"{months_en[start_date.month - 1]} {start_date.day}"
        end_str = f"{months_en[end_date.month - 1]} {end_date.day}"
        return f"{start_str} — {end_str}"
