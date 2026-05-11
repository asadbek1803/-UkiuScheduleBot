from aiogram import Router


def setup_routers() -> Router:
    from .users import start, schedule, profile, feedback, admin
    from .errors import error_handler

    router = Router()
    router.include_routers(
        start.router, schedule.router, profile.router,
        feedback.router, admin.router, error_handler.router
    )
    return router
