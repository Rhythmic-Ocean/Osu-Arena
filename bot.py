import logging
import os

import discord
from discord.ext import commands
from load_env import ENV


from utils_v2 import (
    LogHandler,
    DatabaseHandler,
    InitExterns,
    ChallengeView,
    DynamicButtons,
)


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
        self.log_handler = LogHandler()
        self.logger = self.log_handler.logger

        self.db_handler = None
        self.supabase_client = None
        self.osu_client = None
        self.osu_auth = None

    async def setup_hook(self) -> None:
        self.logger.info(f"Logged in as {self.user.name}")
        self.add_view(ChallengeView())

        self.add_dynamic_items(DynamicButtons)
        await self.init_externs()
        self.db_handler = DatabaseHandler(self.log_handler, self.supabase_client)

        await self.load_cogs()

        self.tree.on_error = self.on_tree_error

    async def on_ready(self) -> None:
        self.logger.info("-------------------")
        await self.log_handler.report_info("Bot is Ready and Online!")
        try:
            target_guild = discord.Object(id=ENV.OSU_ARENA)

            self.tree.copy_global_to(guild=target_guild)

            synced = await self.tree.sync(guild=target_guild)

            await self.log_handler.report_info(
                f"Synced {len(synced)} commands to guild {ENV.OSU_ARENA}!",
                "Commands Synced",
            )
        except Exception as e:
            self.log_handler.report_error("OsuArena.on_ready()", e)

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

    async def init_externs(self) -> None:
        init_obj = InitExterns(self.log_handler)
        self.osu_auth = await init_obj.setup_osu_auth(
            ENV.AUTH_ID, ENV.AUTH_TOKEN, ENV.REDIRECT_URL
        )
        self.supabase_client = await init_obj.setup_supabase_client(
            ENV.SUPABASE_URL, ENV.SUPABASE_KEY
        )
        self.osu_client = await init_obj.setup_osu_client(self.osu_auth)

    @property
    def guild(self) -> discord.Guild | None:
        return self.get_guild(ENV.OSU_ARENA)

    async def on_tree_error(
        self, interaction: discord.Interaction, error: commands.CommandError
    ):
        error = getattr(error, "original", error)
        location = f"Slash Command: /{interaction.command.name if interaction.command else 'Unknown'}"
        await self.log_handler.report_error(location, error)

        msg = "⚠️ An unexpected error occurred."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    async def close(self) -> None:
        if self.log_handler:
            try:
                await self.log_handler.report_info("Bot is closing")
            except Exception as e:
                self.logger.error(f"Failed to report shutdown: {e}")
        await super().close()


if __name__ == "__main__":
    bot = OsuArena()
    bot.run(ENV.DISCORD_TOKEN, log_level=logging.DEBUG)
