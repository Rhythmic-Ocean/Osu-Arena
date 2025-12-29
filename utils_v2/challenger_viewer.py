from __future__ import annotations
import discord
from typing import TYPE_CHECKING

from load_env import ENV

if TYPE_CHECKING:
    from bot import OsuArena


class UnifiedChallengeView(discord.ui.View):
    def __init__(self, bot: OsuArena, challenge_id: int = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler

        if challenge_id:
            self.add_buttons(challenge_id)

    def add_buttons(self, challenge_id: int):
        accept_btn = discord.ui.Button(
            label="Accept",
            style=discord.ButtonStyle.success,
            custom_id=f"challenge::{challenge_id}::accept",
        )
        accept_btn.callback = self.handle_click
        self.add_item(accept_btn)

        decline_btn = discord.ui.Button(
            label="Decline",
            style=discord.ButtonStyle.danger,
            custom_id=f"challenge::{challenge_id}::decline",
        )
        decline_btn.callback = self.handle_click
        self.add_item(decline_btn)

    async def handle_click(self, interaction: discord.Interaction):
        custom_id = interaction.custom_id

        try:
            _, challenge_id_str, action = custom_id.split("::")
            challenge_id = int(challenge_id_str)
        except Exception as error:
            await self.log_handler.report_error(
                "UnifiedChallengeView.handle_click()", error, f"Bad ID: {custom_id}"
            )
            return await interaction.response.edit_message(
                content="❌ Error parsing ID.", view=None
            )

        if action == "accept":
            await self.accept_logic(interaction, challenge_id)
        elif action == "decline":
            await self.decline_logic(interaction, challenge_id)

    async def accept_logic(self, interaction: discord.Interaction, challenge_id: int):
        result = await self.db_handler.accept_challenge(challenge_id)

        if not result:
            return await interaction.response.edit_message(
                content="❌ Challenge not found or expired.", view=None
            )

        challenger_id, challenged_id, for_pp = result

        await interaction.response.edit_message(
            content=f"✅ You accepted the challenge for {for_pp} PP!", view=None
        )

        await self.update_public_log(
            challenge_id,
            f"<@{challenger_id}> vs <@{challenged_id}> | {for_pp} PP | Unfinished",
        )

    async def decline_logic(self, interaction: discord.Interaction, challenge_id: int):
        result = await self.db_handler.decline_challenge(challenge_id)

        if not result:
            return await interaction.response.edit_message(
                content="❌ Challenge not found or expired.", view=None
            )

        challenger_id, challenged_id, _ = result

        await interaction.response.edit_message(
            content="🚫 You declined the challenge.", view=None
        )

        await self.update_public_log(
            challenge_id, f"<@{challenger_id}> vs <@{challenged_id}> | Declined"
        )

    async def update_public_log(self, challenge_id: int, new_content: str):
        """Helper to find the log message and edit it, or send a new one."""
        channel = self.bot.get_channel(ENV.RIVAL_RESULTS_ID)
        if not channel:
            await self.log_handler.report_error(
                "UnifiedChallengeView",
                Exception("Channel Not Found"),
                "Check ENV.RIVAL_RESULTS_ID",
            )
            return

        msg_id = await self.db_handler.get_msg_id(challenge_id)

        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(content=new_content)
                return
            except discord.NotFound:
                pass

        await channel.send(content=new_content)
