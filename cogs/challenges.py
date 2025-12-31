from __future__ import annotations
import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, Optional, cast

from load_env import ENV
from utils_v2 import (
    ChallengeFailed,
    UnifiedChallengeView,
    TablesLeagues,
)
from utils_v2.db_handler import DatabaseHandler
from utils_v2.log_handler import LogHandler

if TYPE_CHECKING:
    from bot import OsuArena

MIN_PP = 250
MAX_PP = 750
MAX_ACTIVE_CHALLENGES = 3


class Challenge(commands.Cog):
    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler: DatabaseHandler = self.bot.db_handler
        self.log_handler: LogHandler = self.bot.log_handler

    @app_commands.command(
        name="challenge", description="Challenge a user in your league"
    )
    @app_commands.describe(
        player="Player to challenge", pp="Performance points (250–750)"
    )
    async def challenge(
        self, interaction: discord.Interaction, player: discord.Member, pp: int
    ):
        challenger = cast(discord.Member, interaction.user)
        target = player

        if challenger.id == target.id:
            await interaction.response.send_message(
                "❌ You cannot challenge yourself!", ephemeral=True
            )
            return

        if target.bot:
            await interaction.response.send_message(
                "❌ You cannot challenge a bot!", ephemeral=True
            )
            return

        if not (MIN_PP <= pp <= MAX_PP):
            await interaction.response.send_message(
                f"❌ PP must be between {MIN_PP} and {MAX_PP}.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        exist1, exist2 = await asyncio.gather(
            self.db_handler.check_if_player_exists(challenger.id),
            self.db_handler.check_if_player_exists(target.id),
        )

        if not exist1:
            await interaction.edit_original_response(
                content="⚠️ You are not yet logged into the database. Please try doing /link. If you think this is an error, please contact the mods."
            )
            return

        if not exist2:
            await interaction.edit_original_response(
                content=f"⚠️ <@{target.id}> is not yet logged into the database. Please ask them to try /link. If you think this is an error, please contact the mods."
            )
            return

        # only roles check happen here, database check for shared league happen a bit later
        shared_league = self._find_shared_league(challenger, target)
        if not shared_league:
            await interaction.edit_original_response(
                content="❌ You and the target must have the same League Role to challenge."
            )
            return

        is_eligible = await self._check_eligibility(
            interaction, challenger, target, shared_league
        )
        if not is_eligible:
            return

        try:
            challenge_id = await self.db_handler.log_rivals(
                challenger, target, pp, shared_league
            )
            if challenge_id is None:
                raise Exception("Database returned None for challenge_id")

            await self._distribute_challenge(
                interaction, challenger, target, pp, shared_league, challenge_id
            )

        except Exception as e:
            await self.log_handler.report_error("Challenge.challenge()", e)
            await interaction.edit_original_response(
                content="❌ Internal database error. Please try again later."
            )

    def _find_shared_league(
        self, user1: discord.Member, user2: discord.Member
    ) -> str | None:
        valid_leagues = {t.value.lower() for t in TablesLeagues}

        def get_leagues(m):
            return {r.name.lower() for r in m.roles if r.name.lower() in valid_leagues}

        common = get_leagues(user1).intersection(get_leagues(user2))
        return common.pop().capitalize() if common else None

    async def _check_eligibility(
        self,
        interaction: discord.Interaction,
        p1: discord.Member,
        p2: discord.Member,
        league: str,
    ) -> bool:
        c1_count = await self.db_handler.get_active_challenge_count(p1.id)
        c2_count = await self.db_handler.get_active_challenge_count(p2.id)

        if c1_count is None or c2_count is None:
            raise Exception("Failed to fetch challenge counts")

        if c1_count >= MAX_ACTIVE_CHALLENGES:
            await interaction.edit_original_response(
                content="❌ You already have 3 active/pending challenges."
            )
            return False
        if c2_count >= MAX_ACTIVE_CHALLENGES:
            await interaction.edit_original_response(
                content=f"❌ {p2.mention} already has 3 active/pending challenges."
            )
            return False

        # database check for users happen here, the check is done thru discord_osu table, leagues table are not checked
        if not await self.db_handler.validate_shared_league(p1.id, league):
            await interaction.edit_original_response(
                content="❌ Your database league does not match your role. Contact Admin."
            )
            return False
        if not await self.db_handler.validate_shared_league(p2.id, league):
            await interaction.edit_original_response(
                content=f"❌ {p2.mention}'s database league does not match their role."
            )
            return False

        status = await self.db_handler.check_challenge_eligibility(p1.id, p2.id)
        if status != ChallengeFailed.GOOD:
            msgs = {
                ChallengeFailed.PENDING: f"❌ You already have a pending challenge with {p2.mention}.",
                ChallengeFailed.ONGOING: f"❌ You already have an ongoing challenge with {p2.mention}.",
                ChallengeFailed.TOO_EARLY: "❌ You can only challenge the same player once per day.",
                ChallengeFailed.BAD_LINK: "❌ One of you isn't properly linked in the database.",
            }
            await interaction.edit_original_response(
                content=msgs.get(
                    status, "❌ Challenge failed due to unknown eligibility reason."
                )
            )
            return False

        return True

    async def _distribute_challenge(
        self, interaction, challenger, target, pp, league, challenge_id
    ):
        view = UnifiedChallengeView(bot=self.bot, challenge_id=challenge_id)

        try:
            await target.send(
                f"⚔️ **Challenge Request**\n"
                f"{challenger.display_name} challenged you for **{pp}PP** in **{league}** league.\n"
                f"Do you accept?",
                view=view,
            )
        except discord.Forbidden:
            await self.db_handler.revoke_challenge(challenge_id)
            await interaction.edit_original_response(
                content=f"❌ Challenge failed: {target.mention} has DMs disabled."
            )
            return

        public_msg = await self._announce_publicly(challenger, target, pp, league)

        if public_msg:
            await self.db_handler.store_msg_id(challenge_id, public_msg.id)

        await interaction.edit_original_response(
            content=f"⚔️ {challenger.mention} has challenged {target.mention} for **{pp}PP**!"
        )

    async def _announce_publicly(self, p1, p2, pp, league) -> Optional[discord.Message]:
        """Sends the pending message to the public results channel."""
        guild = self.bot.guild
        if not guild:
            return None

        channel = guild.get_channel(ENV.RIVAL_RESULTS_ID)
        if not channel:
            await self.log_handler.report_error(
                "Challenge._announce_publicly()",
                Exception("Channel Missing"),
                f"ID: {ENV.RIVAL_RESULTS_ID}",
            )
            return None

        try:
            return await channel.send(
                f"🔸 {p1.mention} vs {p2.mention} | **{pp}PP** | {league} | ⏳ Pending..."
            )
        except Exception as e:
            await self.log_handler.report_error("Challenge._announce_publicly()", e)
            return None


async def setup(bot: OsuArena):
    await bot.add_cog(Challenge(bot))
