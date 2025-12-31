from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, Any
from load_env import ENV
from utils_v2.enums.status import FuncStatus
from utils_v2.enums.tables import TablesLeagues
from utils_v2.enums.tables_internals import DiscordOsuColumn
from utils_v2 import ResetConfirmView

if TYPE_CHECKING:
    from bot import OsuArena


class SeasonManagement(commands.Cog):
    GUILD = discord.Object(ENV.OSU_ARENA)

    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler

    @app_commands.command(
        name="season_restart",
        description="End current season with backups (Admin Only)",
    )
    @app_commands.guilds(GUILD)
    @app_commands.checks.has_any_role(ENV.REQ_ROLE)
    async def season_restart(self, interaction: discord.Interaction):
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

            if not await self._step_reset_points(interaction):
                return

            if not await self._step_backup_leagues(interaction, current_season):
                return

            await self._step_migrate_roles(interaction)

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
                "This will archive data, reset points, and move players.\n\n"
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
                "❌ No ongoing season found. Restart Cancelled"
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

    async def _step_reset_points(self, interaction: discord.Interaction) -> bool:
        """Phase 4: Reset points for the new season."""
        await interaction.followup.send("⏳ Resetting seasonal points...")
        try:
            response = await self.db_handler.reset_seasonal_points()
            if response is FuncStatus.GOOD:
                await interaction.followup.send("✅ Seasonal points reset.")
                return True
            raise Exception(
                "Error at phase 4. Got error response from reset_seasonal_points()"
            )
        except Exception as e:
            await self.log_handler.report_error(
                "SeasonManagement._step_reset_points", e
            )
            await interaction.followup.send(f"❌ Error resetting points: {e}")
            return False

    async def _step_backup_leagues(
        self, interaction: discord.Interaction, season: str
    ) -> bool:
        """Phase 5: Duplicate league tables and re-initiate."""
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
            response2 = await self.db_handler.update_init_pp(league)
            if response2 == FuncStatus.ERROR:
                await msg.edit(content=f"❌ Error initializing pp for {league}")
                return False
            await msg.edit(
                content=f"✅ **{league.capitalize()} League**: Backed up & Season Reinitiated."
            )

        return True

    async def _step_migrate_roles(self, interaction: discord.Interaction):
        """Phase 6: Move players to their new leagues based on DB stats."""
        await interaction.followup.send("⏳ Starting Player Role Migration...")

        try:
            players_data = await self.db_handler.update_leagues()

            await self._process_role_changes(interaction, players_data)

            await interaction.followup.send(
                "🎉 **Success!** All players reassigned.\n"
                "🏆 Good luck to all players in the new season!"
            )
        except Exception as e:
            await self.log_handler.report_error(
                "SeasonManagement._step_migrate_roles()", e
            )
            await interaction.followup.send(
                "❌ Critical Error updating leagues. Please refer to log."
            )

    async def _process_role_changes(
        self, interaction: discord.Interaction, players_data: list[dict[str, Any]]
    ):
        guild = interaction.guild
        role_cache = {role.name: role for role in guild.roles}

        for player_record in players_data:
            discord_id = int(player_record[DiscordOsuColumn.DISCORD_ID])
            member = guild.get_member(discord_id)

            if not member:
                await interaction.followup.send(
                    f"⚠️ User not found in server: <@{discord_id}>"
                )
                continue

            new_league_name = player_record[DiscordOsuColumn.FUTURE_LEAGUE].capitalize()
            old_league_name = player_record[DiscordOsuColumn.LEAGUE].capitalize()

            new_role = role_cache.get(new_league_name)
            old_role = role_cache.get(old_league_name)

            if not new_role or not old_role:
                await interaction.followup.send(
                    f"⚠️ Role missing: {old_league_name} -> {new_league_name}"
                )
                continue

            if new_role in member.roles and old_role not in member.roles:
                await interaction.followup.send(
                    f"Appropriate roles has already been assigned to <@{member.id}>. Skipping..."
                )
                continue

            try:
                await member.remove_roles(old_role)
                await member.add_roles(new_role)
                await interaction.followup.send(
                    f"🔄 <@{member.id}>: {old_league_name} ➡️ {new_league_name}"
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    f"❌ Permission denied modifying role for <@{member.id}> from {old_league_name} to {new_league_name}. Please perform this action manually"
                )
                await self.log_handler.report_error(
                    "SeasonManagement._process_role_changes()",
                    discord.Forbidden,
                    f"Permission denied for role change of <@{member.id}> from {old_league_name} to {new_league_name}. Please perform this action manually",
                )
            except Exception as error:
                await interaction.followup.send(
                    f"❌ Failed to move <@{member.id}>: from {old_league_name} to {new_league_name}. Please perform this action manually"
                )
                await self.log_handler.report_error(
                    "SeasonManagement._process_role_changes()",
                    error,
                    f"Failed to move <@{member.id}>'s roles from {old_league_name} to {new_league_name}. An unexpected exception occured. Please perform this action manually",
                )

    @season_restart.error
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
    await bot.add_cog(SeasonManagement(bot))
