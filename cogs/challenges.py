from __future__ import annotations

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

if TYPE_CHECKING:
    from bot import OsuArena

MIN_PP = 250
MAX_PP = 750
MAX_ACTIVE_CHALLENGES = 3


class Challenge(commands.Cog):
    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler

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

        shared_league = self._find_shared_league(challenger, target)
        if not shared_league:
            await interaction.followup.send(
                "❌ You and the target must have the same League Role to challenge.",
                ephemeral=True,
            )
            return

        is_eligible = await self._check_eligibility(
            interaction, challenger, target, shared_league
        )
        if not is_eligible:
            return

        try:
            challenge_id = await self.db_handler.log_rivals(
                challenger.id, target.id, pp, shared_league
            )
            if challenge_id is None:
                raise Exception("Database returned None for challenge_id")

            await self._distribute_challenge(
                interaction, challenger, target, pp, shared_league, challenge_id
            )

        except Exception as e:
            await self.log_handler.report_error("Challenge Command", e)
            await interaction.followup.send(
                "❌ Internal database error. Please try again later.", ephemeral=True
            )

    def _find_shared_league(
        self, user1: discord.Member, user2: discord.Member
    ) -> str | None:
        """Returns the league name common to both users, or None."""
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
        """Performs all DB checks. Returns True if challenge can proceed, False if error sent."""

        c1_count = await self.db_handler.get_active_challenge_count(p1.id)
        c2_count = await self.db_handler.get_active_challenge_count(p2.id)

        if c1_count is None or c2_count is None:
            raise Exception("Failed to fetch challenge counts")

        if c1_count >= MAX_ACTIVE_CHALLENGES:
            await interaction.followup.send(
                "❌ You already have 3 active/pending challenges.", ephemeral=True
            )
            return False
        if c2_count >= MAX_ACTIVE_CHALLENGES:
            await interaction.followup.send(
                f"❌ {p2.mention} already has 3 active/pending challenges.",
                ephemeral=True,
            )
            return False

        if not await self.db_handler.validate_user_league(p1.id, league):
            await interaction.followup.send(
                "❌ Your database league does not match your role. Contact Admin.",
                ephemeral=True,
            )
            return False
        if not await self.db_handler.validate_user_league(p2.id, league):
            await interaction.followup.send(
                f"❌ {p2.mention}'s database league does not match their role.",
                ephemeral=True,
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
            await interaction.followup.send(
                msgs.get(
                    status, "❌ Challenge failed due to unknown eligibility reason."
                ),
                ephemeral=True,
            )
            return False

        return True

    async def _distribute_challenge(
        self, interaction, challenger, target, pp, league, challenge_id
    ):
        """Handles the DM, Public Announcement, and User Feedback."""

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
            await interaction.followup.send(
                f"❌ Challenge failed: {target.mention} has DMs disabled.",
                ephemeral=True,
            )
            return

        public_msg = await self._announce_publicly(challenger, target, pp, league)

        if public_msg:
            await self.db_handler.store_msg_id(challenge_id, public_msg.id)

        await interaction.followup.send(
            f"⚔️ {challenger.mention} has challenged {target.mention} for **{pp}PP**!"
        )

    async def _announce_publicly(self, p1, p2, pp, league) -> Optional[discord.Message]:
        """Sends the pending message to the public results channel."""
        guild = self.bot.guild
        if not guild:
            return None

        channel = guild.get_channel(ENV.RIVAL_RESULTS_ID)
        if not channel:
            await self.log_handler.report_error(
                "Challenge Announcement",
                Exception("Channel Missing"),
                f"ID: {ENV.RIVAL_RESULTS_ID}",
            )
            return None

        try:
            return await channel.send(
                f"🔸 {p1.mention} vs {p2.mention} | **{pp}PP** | {league} | ⏳ Pending..."
            )
        except Exception as e:
            await self.log_handler.report_error("Challenge Announcement", e)
            return None


async def setup(bot: OsuArena):
    await bot.add_cog(Challenge(bot))
