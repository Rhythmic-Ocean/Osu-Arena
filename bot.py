import os
import platform
import sys

import discord
from discord.ext import commands
from load_env import ENV


from supabase._async.client import AsyncClient
import asyncio

from utils_v2 import ErrorHandler


intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class OsuArena(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=None,
            intents=intents,
            help_command=None,
        )

        self.error_handler = ErrorHandler(self)
        self.logger = self.error_handler.logger
        self.bot_prefix = None

    async def setup_supabase_client(self) -> AsyncClient:
        SUPABASE_URL = ENV.SUPABASE_URL
        SUPABASE_KEY = ENV.SUPABASE_KEY
        supabase_client = None
        max_tries = 3
        for i in range(max_tries):
            try:
                supabase_client = await AsyncClient.create(
                    supabase_key=SUPABASE_KEY, supabase_url=SUPABASE_URL
                )
                self.logger.info("Supabase client created successfully")
                return supabase_client
            except Exception as e:
                if i == max_tries - 1:
                    await self.error_handler.report_error(
                        "OsuArena.setup_supabase_client()",
                        e,
                        "Critical Failure: Supabase Client creation failed.\n Shutting the bot down.",
                    )
                    sys.exit(1)
                await self.error_handler.report_error(
                    "OsuArena.setup_supabase_client()",
                    e,
                    f"Supabase Client creation failed.\n Tries : {i + 1}.\n Retrying in 5 secs",
                )
                await asyncio.sleep(5)

    async def load_cogs(self) -> None:
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

    async def setup_hook(self) -> None:
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(
            f"Running on: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------")
        self.logger.info("Creating Supabase Client....")
        self.supabase_client = await self.setup_supabase_client()
        await self.load_cogs()
        self.tree.error(self.error_handler.on_app_command_error)

    async def on_ready(self) -> None:
        await self.error_handler.initiate_channel()
        self.logger.info("-------------------")
        self.logger.info("Bot is Ready and Error Handler is active.")
        self.logger.info("-------------------")


bot = OsuArena()
bot.run(ENV.DISCORD_TOKEN)
