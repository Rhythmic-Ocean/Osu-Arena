import asyncio
import functools
from utils_v2 import LogHandler

log_handler = LogHandler("error_logging")


async def handle_error(location: str = "Unknown", msg: str = None):
    async def report_error(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as error:
                await log_handler.report_error(location, error, msg)

        return wrapper


@handle_error(location="test.smthing", msg="smthing_smthing")
async def smthing(string: str):
    raise Exception(string)


if __name__ == "__main__":
    asyncio.run(smthing("hello"))
