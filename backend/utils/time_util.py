import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class TimeUtil:
    @classmethod
    def get_elapsed_time(
        cls, func: Callable[..., T], *args, **kwargs
    ) -> tuple[T, float]:
        start = float(time.monotonic())
        result = func(*args, **kwargs)
        end = float(time.monotonic())
        return result, end - start

    @classmethod
    async def get_elapsed_time_async(
        cls, func: Callable[..., Awaitable[T]], *args, **kwargs
    ) -> tuple[T, float]:
        """异步版本的计时方法"""
        start = float(time.monotonic())
        result = await func(*args, **kwargs)
        end = float(time.monotonic())
        return result, end - start
