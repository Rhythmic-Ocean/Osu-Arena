from __future__ import annotations
import discord
from discord.ext import commands
from typing import TYPE_CHECKING
from discord import app_commands

from load_env import ENV

if TYPE_CHECKING:
    from bot import OsuArena


class Revoke(commands.Cog):
    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler

    @app_commands.command(
        name="revoke_challenge",
        description="Revoke a pending challenge",
    )
    @app_commands.describe(player="Player to revoke challenge with")
    async def revoke_challenge(
        self, interaction: discord.Interaction, player: discord.Member
    ):
        await interaction.response.defer()

        challenger = interaction.user
        challenged = player

        challenge_id = await self.db_handler.check_matching_challenges(
            challenger.id, challenged.id
        )

        if not challenge_id:
            await interaction.followup.send(
                "❌ Request Failed. No such challenge exists!"
            )
            return

        msg_id = await self.db_handler.get_msg_id(challenge_id)
        revoke_success = await self.db_handler.revoke_challenge(challenge_id)

        if not revoke_success:
            await interaction.followup.send(
                "❌ The challenge was found but could not be revoked. Please report!"
            )
            await self.log_handler.report_error(
                "Revoke.revoke_challenge()",
                Exception(f"Could not revoke challenge {challenge_id}"),
                f"Could not revoke challenge {challenge_id} upon <@{challenger.id}>'s request",
            )
            return

        guild = interaction.guild
        channel = guild.get_channel(ENV.RIVAL_RESULTS_ID)

        revoke_content = f"<@{challenger.id}> vs <@{challenged.id}> | Revoked"

        if channel:
            msg = None

            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                except discord.NotFound:
                    msg = None
                except discord.HTTPException as e:
                    await self.log_handler.report_error("Fetch Message Error", e)

            if msg:
                await msg.edit(content=revoke_content)
            else:
                await channel.send(content=revoke_content)

            await interaction.followup.send(
                f"Your challenge with <@{challenged.id}> has been successfully revoked!"
            )
            return

        else:
            error = Exception(
                f"Rival result channel not found for announcement : {revoke_content}"
            )
            await self.log_handler.report_error("Revoke.revoke_challenge()", error)
            await interaction.followup.send(
                "Your challenge has been internally revoked but the announcement could not be made! Error Logged"
            )
