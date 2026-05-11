import logging
from datetime import datetime, timedelta
from models.schedule import delete_old_schedules

logger = logging.getLogger(__name__)


async def delete_old_schedules():
    cutoff = datetime.now() - timedelta(days=7)
    deleted = await delete_old_schedules(cutoff)
    if deleted:
        logger.info(f"Tozalandi: {deleted} eski jadval yozuvi")
