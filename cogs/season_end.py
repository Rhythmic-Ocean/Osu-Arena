from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING
from load_env import ENV
from utils_v2.enums.status import FuncStatus
from utils_v2.enums.tables import TablesLeagues
from utils_v2 import ResetConfirmView

if TYPE_CHECKING:
    from bot import OsuArena


class SeasonEnd(commands.Cog):
    GUILD = discord.Object(ENV.OSU_ARENA)

    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler

    @app_commands.command(
        name="season_end",
        description="End current season with backups (Admin Only)",
    )
    @app_commands.guilds(GUILD)
    @app_commands.checks.has_any_role(ENV.REQ_ROLE)
    async def season_end(self, interaction: discord.Interaction):
        if not await self._get_confirmation(interaction):
            return

        try:
            current_season = await self._step_archive_season(interaction)
            if not current_season:
                return

            if not await self._step_update_points(interaction):
                return

            if not await self._step_backup_points(interaction, current_season):
                return

            if not await self._step_backup_leagues(interaction, current_season):
                return
            await interaction.followup.send(
                "**Success!** All tables have been archived, use /archive command to see the final result.\n"
                f"🏁**Season {current_season}** has ended!"
            )

            guild = self.bot.guild
            channel = guild.get_channel(ENV.BOT_UPDATES)
            try:
                await channel.send(
                    f"🏁 **Season {current_season}** has ended! The final table for this season has being archived. 📜"
                )
            except Exception as e:
                await self.log_handler.report_error(
                    "Failed announcement for season end!", e
                )

        except Exception as e:
            await self.log_handler.report_error("Season Restart Critical Failure", e)
            await interaction.edit_original_response(
                content="❌ **CRITICAL ERROR** during restart sequence. Check logs."
            )

    async def _get_confirmation(self, interaction: discord.Interaction) -> bool:
        await interaction.response.defer(ephemeral=False)

        view = ResetConfirmView(interaction)
        await interaction.edit_original_response(
            content=(
                "⚠️ **WARNING** ⚠️\n"
                "You are about to **END THE CURRENT SEASON**.\n"
                "Are you sure you want to proceed?"
            ),
            view=view,
        )

        await view.wait()

        if view.value is None:
            await interaction.edit_original_response(
                content="❌ **Timed out.** Operation cancelled.", view=None
            )
            return False
        elif not view.value:
            return False

        return True

    async def _step_archive_season(
        self, interaction: discord.Interaction
    ) -> str | None:
        """Phase 1: Check if there's an ongoing season and mark it as Archived"""
        current = await self.db_handler.get_current_season()
        if not current:
            await interaction.followup.send(
                "❌ No ongoing season found. Season Close Cancelled"
            )
            return None

        success = await self.db_handler.mark_season_archived(current)
        if not success:
            await interaction.followup.send(
                f"❌ Failed to mark Season {current} as archived."
            )
            return None

        await interaction.followup.send(f"✅ Ending **Season {current}**.")
        return current

    async def _step_update_points(self, interaction: discord.Interaction) -> bool:
        """Phase 2: Finalize point calculations."""
        await interaction.followup.send("⏳ Updating end-of-season points...")
        try:
            response = await self.db_handler.seasonal_point_update()
            if response is FuncStatus.GOOD:
                await interaction.followup.send("✅ End-of-season points distributed.")
                return True
            raise Exception("Failed at phase 2, got error from seasonal_point_update()")
        except Exception as error:
            await self.log_handler.report_error(
                "SeasonManagement._step_update_points()", error
            )
            await interaction.followup.send(
                "❌ Error updating points. Error has been logged."
            )
            return False

    async def _step_backup_points(
        self, interaction: discord.Interaction, season: str
    ) -> bool:
        """Phase 3: Backup points to history."""
        await interaction.followup.send("⏳ Backing up seasonal points...")
        try:
            response = await self.db_handler.backup_seasonal_points(season)
            if response is FuncStatus.GOOD:
                await interaction.followup.send("✅ Seasonal points backed up.")
                return True
            raise Exception(
                "Error at phase 3. Got error response from backup_seasonal_points()"
            )
        except Exception as e:
            await self.log_handler.report_error(
                "SeasonManagement._step_backup_points()", e
            )
            await interaction.followup.send(f"❌ Error backing up points: {e}")
            return False

    async def _step_backup_leagues(
        self, interaction: discord.Interaction, season: str
    ) -> bool:
        """Phase 4: Duplicate league tables."""
        for league in [leag for leag in TablesLeagues]:
            msg = await interaction.followup.send(
                f"⏳ Processing **{league} League**..."
            )
            response1 = await self.db_handler.duplicate_table(league, season)
            if response1 == FuncStatus.ERROR:
                await msg.edit(
                    content=f"❌ Error duplicating {league}. Stopped at {league}_{season}."
                )
                return False
            await msg.edit(content=f"✅ **{league.capitalize()} League**: Backed up")

        return True

    @season_end.error
    async def session_restart_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(
                "❌ **Access Denied.** Admin role required.", ephemeral=True
            )
            await self.log_handler.report_info(
                f"<@{interaction.user.id}> tried accessing the command season_restart"
            )
        else:
            await self.log_handler.report_error("session_restart_error()", error)
            await interaction.followup.send(
                "❌ An unexpected error occurred.", ephemeral=True
            )


async def setup(bot: OsuArena):
    await bot.add_cog(SeasonEnd(bot))
