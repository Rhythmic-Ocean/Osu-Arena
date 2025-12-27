import discord
from discord import app_commands
from discord.ext import commands
from bot import OsuArena
from load_env import ENV
from utils_v2.enums import ChallengeStatus
from utils_v2.enums.tables import TablesLeagues
from utils_v2 import ChallengeView

MIN_PP = 250
MAX_PP = 750


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
        challenger = interaction.user
        challenged = player.user

        if challenger.id == challenged.id:
            await interaction.response.send_message(
                "❌ You cannot challenge yourself!", ephemeral=True
            )
            return

        if not (MIN_PP <= pp <= MAX_PP):
            await interaction.response.send_message(
                f"❌ PP must be between {MIN_PP} and {MAX_PP}.", ephemeral=True
            )
            return

        await interaction.response.defer()

        shared_league = self._find_shared_league(challenger, challenged)

        if not shared_league:
            await interaction.followup.send(
                "❌ You and the target must have the same League Role to challenge."
            )
            return

        try:
            if await self.db_handler.get_active_challenge_count(challenger.id) >= 3:
                await interaction.followup.send(
                    "❌ You already have 3 active/pending challenges.", ephemeral=True
                )
                return

            if await self.db_handler.get_active_challenge_count(player.id) >= 3:
                await interaction.followup.send(
                    f"❌ {player.mention} already has 3 active/pending challenges.",
                    ephemeral=True,
                )
                return

            if not await self.db_handler.validate_user_league(
                challenger.id, shared_league
            ):
                await interaction.followup.send(
                    "❌ Your database league does not match your role. Contact Admin.",
                    ephemeral=True,
                )
                return

            if not await self.db_handler.validate_user_league(player.id, shared_league):
                await interaction.followup.send(
                    f"❌ {player.mention}'s database league does not match their role.",
                    ephemeral=True,
                )
                return

            eligibility_code = await self.db_handler.check_challenge_eligibility(
                challenger.id, player.id
            )
            if eligibility_code != 0:
                await self._handle_eligibility_error(
                    interaction, eligibility_code, player
                )
                return

        except Exception as e:
            await self.log_handler.report_error("Challenge Command Logic", e)
            await interaction.followup.send(
                "❌ Internal database error. Please try again later.", ephemeral=True
            )
            return

        try:
            challenge_id = await self.db_handler.create_challenge(
                challenger_id=challenger.id,
                challenged_id=player.id,
                league=shared_league,
                pp=pp,
            )
        except Exception as e:
            await self.log_handler.report_error("Create Challenge DB", e)
            await interaction.followup.send("❌ Failed to create challenge record.")
            return

        await self._process_challenge_flow(
            interaction, challenger, player, pp, shared_league, challenge_id
        )

    def _find_shared_league(
        self, challenger: discord.Member, challenged: discord.Member
    ) -> str | None:
        valid_leagues = {t.value.lower() for t in TablesLeagues}

        user1_leagues = {
            r.name.lower() for r in challenger.roles if r.name.lower() in valid_leagues
        }
        user2_leagues = {
            r.name.lower() for r in challenged.roles if r.name.lower() in valid_leagues
        }

        common = user1_leagues.intersection(user2_leagues)
        return common.pop().capitalize() if common else None

    async def _handle_eligibility_error(self, interaction, code, player):
        messages = {
            2: f"❌ You already have a pending challenge with {player.mention}.",
            3: f"❌ You already have an ongoing challenge with {player.mention}.",
            4: "❌ You can only challenge the same player once per day.",
            5: "❌ One of you isn't properly linked in the database.",
        }
        msg = messages.get(code, "❌ Challenge not allowed (Unknown Reason).")
        await interaction.followup.send(msg, ephemeral=True)

    async def _process_challenge_flow(
        self, interaction, challenger, player, pp, league, challenge_id
    ):
        """Handles DMs, Waiting, and Result Logic."""

        await interaction.followup.send(
            f"⚔️ {challenger.mention} has challenged {player.mention} for **{pp}PP**!"
        )

        view = ChallengeView(target_user=player)
        try:
            await player.send(
                f"⚔️ **Challenge Request**\n{challenger.display_name} challenged you for **{pp}PP** in **{league}** league.\nDo you accept?",
                view=view,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Challenge failed: {player.mention} has DMs disabled."
            )
            await self.db_handler.delete_challenge(challenge_id)
            return

        results_channel = self.bot.get_channel(ENV.RIVAL_RESULTS_ID)
        public_msg = None
        if results_channel:
            try:
                public_msg = await results_channel.send(
                    f"🔸 {challenger.mention} vs {player.mention} | **{pp}PP** | {league} | ⏳ Pending..."
                )
                await self.db_handler.set_challenge_msg_id(challenge_id, public_msg.id)
            except Exception as e:
                self.bot.logger.warning(f"Could not post to results channel: {e}")

        await view.wait()

        if view.response is None:
            await self._finalize_challenge(
                challenge_id,
                ChallengeStatus.CANCELLED,
                public_msg,
                f"{challenger.mention} vs {player.mention} | ⏱️ Revoked (Timeout)",
            )
            await interaction.followup.send(
                f"⏱️ Challenge to {player.display_name} timed out."
            )

        elif view.response is True:
            await self._finalize_challenge(
                challenge_id,
                ChallengeStatus.ACCEPTED,
                public_msg,
                f"{challenger.mention} vs {player.mention} | **{pp}PP** | ⚔️ **UNFINISHED**",
            )
            await interaction.followup.send(
                f"✅ {player.mention} accepted the challenge!"
            )

        else:
            await self._finalize_challenge(
                challenge_id,
                ChallengeStatus.DECLINED,
                public_msg,
                f"{challenger.mention} vs {player.mention} | ❌ Declined",
            )
            await interaction.followup.send(
                f"🚫 {player.display_name} declined the challenge."
            )

    async def _finalize_challenge(self, c_id, status, msg, content):
        """Updates DB and edits the public message."""
        try:
            if status == ChallengeStatus.CANCELLED:
                await self.db_handler.delete_challenge(c_id)
            else:
                await self.db_handler.update_challenge_status(c_id, status)

            if msg:
                await msg.edit(content=content)
        except Exception as e:
            self.bot.logger.error(f"Failed to finalize challenge {c_id}: {e}")


async def setup(bot: OsuArena):
    await bot.add_cog(Challenge(bot))
