import logging
import datetime
import io
import traceback
import discord
from discord.ext import commands
from load_env import ENV


class LogHandler:
    class LoggingFormatter(logging.Formatter):
        # Colors
        black = "\x1b[30m"
        red = "\x1b[31m"
        green = "\x1b[32m"
        yellow = "\x1b[33m"
        blue = "\x1b[34m"
        gray = "\x1b[38m"
        # Styles
        reset = "\x1b[0m"
        bold = "\x1b[1m"

        COLORS = {
            logging.DEBUG: gray + bold,
            logging.INFO: blue + bold,
            logging.WARNING: yellow + bold,
            logging.ERROR: red,
            logging.CRITICAL: red + bold,
        }

        def format(self, record):
            log_color = self.COLORS[record.levelno]
            format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
            format = format.replace("(black)", self.black + self.bold)
            format = format.replace("(reset)", self.reset)
            format = format.replace("(levelcolor)", log_color)
            format = format.replace("(green)", self.green + self.bold)
            formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
            return formatter.format(record)

    def __init__(
        self, bot: commands.Bot = None, logger_name: str = "discord_bot"
    ) -> None:
        self.logger = logging.getLogger(logger_name)
        self.bot = bot
        self.logger.setLevel(logging.INFO)
        self._setup_handlers()
        self.guild = None
        self.channel = None

    async def initiate_channel(self) -> None:
        if self.channel:
            return
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(int(ENV.OSU_ARENA))
        if not self.guild:
            self.logger.critical("Critical: Guild Not Found!!")
        else:
            self.channel = self.guild.get_channel(int(ENV.BOT_LOGS))
        if not self.channel:
            self.logger.critical("Critical: Bot_Logs Channel Not Found!!")

    def _setup_handlers(self) -> None:
        if self.logger.hasHandlers():
            return
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.LoggingFormatter())
        file_handler = logging.FileHandler(
            filename="discord.log", encoding="utf-8", mode="w"
        )
        file_handler_formatter = logging.Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}",
            "%Y-%m-%d %H:%M:%S",
            style="{",
        )
        file_handler.setFormatter(file_handler_formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    async def report_error(self, location: str, error: Exception, msg: str = None):
        trace = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        log_msg = f"Error in {location} : {error}"
        if msg:
            log_msg += f"\nNote: {msg}"
        self.logger.error(f"{log_msg}\n{trace}")
        if not self.channel:
            return
        embed = discord.Embed(
            title="⚠️ System Error",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        embed.add_field(name="Location", value=f"`{location}`", inline=False)
        embed.add_field(
            name="Message", value=f"```py\n{str(error)[:1000]}```", inline=False
        )

        if len(trace) > 1000:
            with io.BytesIO(trace.encode()) as f:
                await self.channel.send(
                    embed=embed, file=discord.File(f, filename="traceback.txt")
                )
        else:
            embed.add_field(name="Traceback", value=f"```py\n{trace}```", inline=False)
            await self.channel.send(embed=embed)

    async def report_info(self, message: str, title: str = "ℹ️ System Info"):
        self.logger.info(f"{title}: {message}")

        if not self.channel:
            return

        embed = discord.Embed(
            title=title,
            color=discord.Color.blue(),  # Blue for info, Green for success
            timestamp=datetime.datetime.now(datetime.UTC),
        )

        if len(message) > 4000:
            embed.description = "Message too long to display. See attached file."
            with io.BytesIO(message.encode()) as f:
                await self.channel.send(
                    embed=embed, file=discord.File(f, filename="info_log.txt")
                )
        else:
            embed.description = message
            await self.channel.send(embed=embed)

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        if hasattr(ctx.command, "on_error"):
            return
        error = getattr(error, "original", error)
        location = (
            f"Command: {ctx.command.qualified_name if ctx.command else 'Unknown'}"
        )
        await self.report_error(location, error)
        await ctx.send(
            "⚠️ An unexpected error occurred. The developers have been notified."
        )
