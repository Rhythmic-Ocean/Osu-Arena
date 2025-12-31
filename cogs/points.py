from __future__ import annotations
import discord
from discord.ext import commands
from typing import TYPE_CHECKING
from discord import app_commands

from load_env import ENV
from utils_v2.enums.status import FuncStatus

if TYPE_CHECKING:
    from bot import OsuArena


class Points(commands.Cog):
    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler

    @app_commands.command(
        name="points",
        description="Modify points for any individual player",
    )
    @app_commands.describe(
        player="intended player whose points are to be modified",
        points="Amount to add (use negative numbers to remove)",
    )
    @app_commands.checks.has_any_role(ENV.REQ_ROLE, ENV.REQ_ROLE_POINTS)
    async def points(
        self, interaction: discord.Interaction, player: discord.Member, points: int
    ):
        await interaction.response.defer()

        response = await self.db_handler.check_player_existence_for_points(player.id)

        if response == FuncStatus.EMPTY:
            await interaction.followup.send(
                "Such a player does not exist in the database. If you think this is an error, please report!"
            )
            return

        if response == FuncStatus.ERROR:
            await interaction.followup.send(
                "An internal database error has occured. Error logged. Please report!"
            )
            return

        response2 = await self.db_handler.add_points(points, discord_id=player.id)

        if response2:
            new_seasonal_points = response2.get("new_seasonal_points")
            new_points = response2.get("new_points")

            await interaction.followup.send(
                f"✅ {points} points modification done for <@{player.id}>\n"
                f"Total points : **{new_points}**, Total Seasonal Points : **{new_seasonal_points}**"
            )
        else:
            await interaction.followup.send(
                f"❌ An error occured updating points for <@{player.id}>. Error has been logged, please report!"
            )

    @points.error
    async def points_error(self, interaction: discord.Interaction, error):
        sender = (
            interaction.followup.send
            if interaction.response.is_done()
            else interaction.response.send_message
        )

        if isinstance(error, app_commands.MissingAnyRole):
            await sender(
                "❌ Access Denied. You need one of the allowed roles (admin or speed rank judge).",
                ephemeral=True,
            )
            await self.log_handler.report_info(
                f"<@{interaction.user.id}> tried accessing the command /points"
            )
        else:
            await sender("❌ An unexpected error occurred.", ephemeral=True)
            await self.log_handler.report_error("Points.points_error()", error)


async def setup(bot: OsuArena):
    await bot.add_cog(Points(bot))
