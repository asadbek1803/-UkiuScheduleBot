from data.config import ADMINS


async def on_startup_notify(bot):
    for admin in ADMINS:
        try:
            await bot.send_message(int(admin), "✅ Bot ishga tushdi!")
        except:
            pass
