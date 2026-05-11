import logging
from datetime import datetime, timedelta
from models.schedule import Schedule

logger = logging.getLogger(__name__)


async def delete_old_schedules():
    cutoff = datetime.now() - timedelta(days=7)
    deleted = await Schedule.filter(cached_at__lt=cutoff).delete()
    if deleted:
        logger.info(f"Tozalandi: {deleted} eski jadval yozuvi")
