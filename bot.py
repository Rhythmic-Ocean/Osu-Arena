import os
import sys

import discord
from discord.ext import commands
from load_env import ENV
from osu import AsynchronousClient


from supabase._async.client import AsyncClient
import asyncio

from utils_v2 import ErrorHandler, DatabaseHandler
from utils_v2.osuapi_handler import OsuAPI_Handler


intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class OsuArena(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )
        self.error_handler = ErrorHandler(self)
        self.logger = self.error_handler.logger

        self.db_handler = None
        self.supabase_client = None
        self.osu_client = None
        self.osuapi_handler = None

    async def setup_hook(self) -> None:
        self.logger.info(f"Logged in as {self.user.name}")

        self.supabase_client = await self.setup_supabase_client()
        self.osu_client = await self.setup_osu_client()

        self.db_handler = DatabaseHandler(self, self.supabase_client)
        self.osuapi_handler = OsuAPI_Handler(self, self.osu_client)

        await self.load_cogs()

        self.tree.error(self.error_handler.on_command_error)

    async def on_ready(self) -> None:
        await self.error_handler.initiate_channel()
        self.logger.info("-------------------")
        await self.error_handler.report_info("Bot is Ready and Online!")

    async def load_cogs(self) -> None:
        self.logger.info("-------------------")
        self.logger.info("Loading extensions (COGS)")
        cogs_path = os.path.join(os.path.dirname(__file__), "cogs")
        for file in os.listdir(cogs_path):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    self.logger.info(f"Successfully loaded extension {extension}")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extension {extension}\n{exception}"
                    )
        self.logger.info("-------------------")

    async def setup_supabase_client(self) -> AsyncClient:
        SUPABASE_URL = ENV.SUPABASE_URL
        SUPABASE_KEY = ENV.SUPABASE_KEY
        max_tries = 3

        self.logger.info("-------------------")
        self.logger.info("Creating Supabase Client....")

        for i in range(max_tries):
            try:
                supabase_client = await AsyncClient.create(
                    supabase_key=SUPABASE_KEY, supabase_url=SUPABASE_URL
                )
                self.logger.info("Supabase client created successfully")
                self.logger.info("-------------------")
                return supabase_client
            except Exception as e:
                if i == max_tries - 1:
                    self.logger.critical(
                        f"CRITICAL FAILURE: Supabase Client creation failed after {max_tries} attempts.\n"
                        f"Error: {e}\n"
                        "Shutting down..."
                    )
                    sys.exit(1)
                else:
                    self.logger.error(
                        f"Supabase Client creation failed (Attempt {i + 1}/{max_tries}).\n"
                        f"Error: {e}\n"
                        "Retrying in 5 seconds..."
                    )
                    await asyncio.sleep(5)

    async def setup_osu_client(self) -> AsynchronousClient:
        OSU_CLIENT_ID = int(ENV.OSU_CLIENT_ID)
        OSU_CLIENT_SECRET = ENV.OSU_CLIENT_SECRET
        REDIRECT_URL = ENV.REDIRECT_URL
        max_tries = 3

        self.logger.info("-------------------")
        self.logger.info("Creating Osu Client....")

        for i in range(max_tries):
            try:
                osu_client = AsynchronousClient.from_credentials(
                    OSU_CLIENT_ID, OSU_CLIENT_SECRET, REDIRECT_URL
                )
                self.logger.info("Osu client created successfully")
                self.logger.info("-------------------")
                return osu_client
            except Exception as e:
                if i == max_tries - 1:
                    self.logger.critical(
                        f"CRITICAL FAILURE: Osu Client creation failed after {max_tries} attempts.\n"
                        f"Error: {e}\n"
                        "Shutting down..."
                    )
                    sys.exit(1)
                else:
                    self.logger.error(
                        f"Osu Client creation failed (Attempt {i + 1}/{max_tries}).\n"
                        f"Error: {e}\n"
                        "Retrying in 5 seconds..."
                    )
                    await asyncio.sleep(5)

    @property
    def guild(self) -> discord.Guild | None:
        return self.get_guild(ENV.OSU_ARENA)


if __name__ == "__main__":
    bot = OsuArena()
    bot.run(ENV.DISCORD_TOKEN)
