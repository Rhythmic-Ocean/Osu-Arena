import logging
import datetime
import io
import traceback
import discord
from load_env import ENV
import aiohttp


class LogHandler:
    class LoggingFormatter(logging.Formatter):
        black = "\x1b[30m"
        red = "\x1b[31m"
        green = "\x1b[32m"
        yellow = "\x1b[33m"
        blue = "\x1b[34m"
        gray = "\x1b[38m"

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

    def __init__(self, logger_name: str = "discord_bot") -> None:
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        self._setup_handlers()
        self.webhook_url = ENV.LOGS_WEBHOOK

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

        if not self.webhook_url:
            self.logger.critical(
                "CRITICAL : WEBHOOOK URL NOT FOUND! CANNOT REPORT ERRORS TO SERVER!"
            )
            return

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(self.webhook_url, session=session)
            embed = discord.Embed(
                title="⚠️ System Error",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.add_field(name="Location", value=f"`{location}`", inline=False)
            embed.add_field(
                name="Message", value=f"```py\n{str(error)[:1000]}```", inline=False
            )
            if msg:
                embed.add_field(name="Note :", value=f"\n{msg}")

            if len(trace) > 1000:
                with io.BytesIO(trace.encode()) as f:
                    await webhook.send(
                        embed=embed,
                        file=discord.File(f, filename="traceback.txt"),
                        username="OsuArena Error",
                    )
            else:
                embed.add_field(
                    name="Traceback", value=f"```py\n{trace}```", inline=False
                )
                await webhook.send(embed=embed, username="OsuArena Error")

    async def report_info(self, message: str, title: str = "ℹ️ System Info"):
        if hasattr(self, "logger"):
            self.logger.info(f"{title}: {message}")
        else:
            print(f"{title}: {message}")

        if not self.webhook_url:
            return

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(self.webhook_url, session=session)

            embed = discord.Embed(
                title=title,
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )

            if len(message) > 4000:
                embed.description = "Message too long to display. See attached file."
                with io.BytesIO(message.encode()) as f:
                    await webhook.send(
                        embed=embed,
                        file=discord.File(f, filename="info_log.txt"),
                        username="OsuArena Info",
                    )
            else:
                embed.description = message
                await webhook.send(embed=embed, username="OsuArena Info")
