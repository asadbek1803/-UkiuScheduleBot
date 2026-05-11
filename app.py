import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from data.config import BOT_TOKEN
from tasks.cleanup import delete_old_schedules
from tasks.reminder import send_daily_reminders
from db_utils.tortoise import init_db, close_db

logger = logging.getLogger(__name__)


def setup_handlers(dispatcher: Dispatcher) -> None:
    from handlers import setup_routers
    dispatcher.include_router(setup_routers())


def setup_middlewares(dispatcher: Dispatcher) -> None:
    from middlewares.throttling import ThrottlingMiddleware
    dispatcher.message.middleware(ThrottlingMiddleware(slow_mode_delay=0.5))


async def on_startup(bot: Bot) -> None:
    await init_db()

    from utils.set_bot_commands import set_default_commands
    from utils.notify_admins import on_startup_notify

    await bot.delete_webhook(drop_pending_updates=True)
    await on_startup_notify(bot)
    await set_default_commands(bot)

    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    scheduler.add_job(
        delete_old_schedules,
        trigger="cron",
        hour=3,
        minute=0,
        id="cleanup_old_schedules",
        replace_existing=True,
    )

    scheduler.add_job(
        send_daily_reminders,
        trigger="cron",
        hour=20,
        minute=0,
        args=[bot],
        id="daily_reminders",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler ishga tushdi")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Bot to'xtatilmoqda")
    await close_db()
    await bot.session.close()


def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    setup_handlers(dp)
    setup_middlewares(dp)

    asyncio.run(dp.start_polling(bot, close_bot_session=True))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped!")
