from __future__ import annotations
import discord
from typing import TYPE_CHECKING
import re

from load_env import ENV

if TYPE_CHECKING:
    from bot import OsuArena


class ChallengeView(discord.ui.View):
    def __init__(self, challenge_id: int = None):
        super().__init__(timeout=None)
        if challenge_id:
            self.add_buttons(challenge_id)

    def add_buttons(self, challenge_id: int):
        accept_btn = discord.ui.Button(
            label="Accept",
            style=discord.ButtonStyle.success,
            custom_id=f"challenge::{challenge_id}::accept",
        )
        self.add_item(accept_btn)
        decline_btn = discord.ui.Button(
            label="Decline",
            style=discord.ButtonStyle.danger,
            custom_id=f"challenge::{challenge_id}::decline",
        )
        self.add_item(decline_btn)


class DynamicButtons(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"challenge::(?P<cid>\d+)::(?P<action>accept|decline)",
):
    def __init__(self, cid: int, action: str) -> None:
        label = "Accept" if action == "accept" else "Decline"
        style = (
            discord.ButtonStyle.success
            if action == "accept"
            else discord.ButtonStyle.danger
        )
        super().__init__(
            discord.ui.Button(
                label=label, style=style, custom_id=f"challenge::{cid}::{action}"
            )
        )
        self.cid = cid
        self.action = action

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: re.Match[str],
        /,
    ):
        cid = int(match["cid"])
        action = match["action"]
        return cls(cid, action)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        challenge_id = self.cid
        action = self.action
        if action == "accept":
            await self.accept_logic(interaction, challenge_id)
        elif action == "decline":
            await self.decline_logic(interaction, challenge_id)

    async def accept_logic(self, interaction: discord.Interaction, challenge_id: int):
        bot: OsuArena = interaction.client
        result = await bot.db_handler.accept_challenge(challenge_id)

        if not result:
            return await interaction.edit_original_response(
                content="❌ Invalid challenge or one the challengers left the server..",
                view=None,
            )

        challenger_id, challenged_id, for_pp = result

        await interaction.edit_original_response(
            content=f"✅ You accepted the challenge for {for_pp} PP!", view=None
        )

        await self.update_public_log(
            bot,
            challenge_id,
            f"<@{challenger_id}> vs <@{challenged_id}> | {for_pp} PP | Unfinished",
        )

    async def decline_logic(self, interaction: discord.Interaction, challenge_id: int):
        bot: OsuArena = interaction.client
        result = await bot.db_handler.decline_challenge(challenge_id)
        bot: OsuArena = interaction.client
        if not result:
            return await interaction.edit_original_response(
                content="❌ Challenge not found or expired.", view=None
            )

        challenger_id, challenged_id, _ = result

        await interaction.edit_original_response(
            content="🚫 You declined the challenge.", view=None
        )

        await self.update_public_log(
            bot, challenge_id, f"<@{challenger_id}> vs <@{challenged_id}> | Declined"
        )

    async def update_public_log(
        self, bot: OsuArena, challenge_id: int, new_content: str
    ):
        channel = bot.get_channel(ENV.RIVAL_RESULTS_ID)
        if not channel:
            await bot.log_handler.report_error(
                "ChallengeView",
                Exception("Channel Not Found"),
                "Check ENV.RIVAL_RESULTS_ID",
            )
            return

        msg_id = await bot.db_handler.get_msg_id(challenge_id)

        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            except discord.NotFound:
                pass

        await channel.send(content=new_content)
