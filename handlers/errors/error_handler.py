import logging
from aiogram import Router, types

router = Router()
logger = logging.getLogger(__name__)


@router.errors()
async def error_handler(event: types.ErrorEvent):
    logger.error(f"Xatolik: {event.exception}", exc_info=True)
