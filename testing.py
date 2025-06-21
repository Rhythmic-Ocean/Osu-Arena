import asyncio
from core import update_rival_table

async def main():
    await update_rival_table()

asyncio.run(main())