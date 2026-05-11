import time
from typing import Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slow_mode_delay: float = 0.5):
        self.slow_mode_delay = slow_mode_delay
        self.user_timeouts = {}

    async def __call__(
        self,
        handler: Callable[[Message, dict], Awaitable],
        event: Message,
        data: dict
    ):
        user_id = event.from_user.id
        current_time = time.time()
        last_time = self.user_timeouts.get(user_id, 0)
        if current_time - last_time < self.slow_mode_delay:
            return
        self.user_timeouts[user_id] = current_time
        return await handler(event, data)
