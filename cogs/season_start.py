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


class SeasonStarter(commands.Cog):
    GUILD = discord.Object(ENV.OSU_ARENA)

    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler

    @app_commands.command(
        name="season_start",
        description="Start a new season and update player's leagues (Admin Only)",
    )
    @app_commands.guilds(GUILD)
    @app_commands.checks.has_any_role(ENV.REQ_ROLE)
    async def season_start(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        if not await self._get_confirmation(interaction):
            return

        if await self.db_handler.get_current_season():
            await interaction.followup.send(
                "❌**Ongoing Season**: An ongoing season alreadly exist. Cannot start another one at the moment."
            )
            return

        try:
            current_season = await self._step_add_new_season(interaction)
            if current_season == FuncStatus.ERROR:
                return

            if await self._step_reset_points(interaction) == FuncStatus.ERROR:
                return

            if await self._step_reset_leagues(interaction) == FuncStatus.ERROR:
                return

            if await self._step_migrate_roles(interaction) == FuncStatus.ERROR:
                return
            await interaction.followup.send(
                "🎉 **Success!** All players reassigned.\n"
                f"🏆 Good luck to all players for Season : {current_season}!"
            )

            guild = self.bot.guild
            channel = guild.get_channel(ENV.BOT_UPDATES)
            try:
                await channel.send(
                    f"🎉 **New Season Started** : Welcome to Osu!Arena Season {current_season} .\n"
                )
            except Exception as e:
                await self.log_handler.report_error(
                    "Failed announcement for new season start!", e
                )

        except Exception as e:
            await self.log_handler.report_error("Season start Critical Failure", e)
            await interaction.edit_original_response(
                content="❌ **CRITICAL ERROR** during start sequence. Check logs."
            )

    async def _get_confirmation(self, interaction: discord.Interaction) -> bool:

        view = ResetConfirmView(interaction)
        await interaction.edit_original_response(
            content=(
                "⚠️ **WARNING** ⚠️\n"
                "You are about to **START A NEW SEASON**.\n"
                "This will reset points, and move players.\n\n"
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

    async def _step_add_new_season(
        self, interaction: discord.Interaction
    ) -> int | FuncStatus:
        """Phase 1: Add a new entry to season column"""
        current_season = await self.db_handler.add_new_season()
        if current_season == FuncStatus.ERROR:
            await interaction.followup.send(
                "❌**ERROR AT PHASE 1**: Error adding new season, error logged."
            )
        return current_season

    async def _step_reset_points(self, interaction: discord.Interaction) -> FuncStatus:
        """Phase 2: Reset points for the new season."""
        await interaction.followup.send("⏳ Resetting seasonal points...")
        try:
            response = await self.db_handler.reset_seasonal_points()
            if response is FuncStatus.GOOD:
                await interaction.followup.send("✅ Seasonal points reset.")
                return FuncStatus.GOOD
            raise Exception(
                "Error at phase 2. Got error response from reset_seasonal_points()"
            )
        except Exception as e:
            await self.log_handler.report_error(
                "SeasonManagement._step_reset_points", e
            )
            await interaction.followup.send(
                "❌**ERROR AT PHASE 2** : Error resetting points"
            )
            return FuncStatus.ERROR

    async def _step_reset_leagues(self, interaction: discord.Interaction) -> FuncStatus:
        """Phase 3: Duplicate league tables and re-initiate."""
        for league in [leag for leag in TablesLeagues]:
            msg = await interaction.followup.send(
                f"⏳ Processing **{league} League**..."
            )
            response = await self.db_handler.update_init_pp(league)
            if response == FuncStatus.ERROR:
                await msg.edit(
                    content=f"❌**ERROR AT PHASE 4** Error initializing pp for {league}"
                )
                return FuncStatus.ERROR
            await msg.edit(
                content=f"✅ **{league.capitalize()} League**: Season Reinitiated."
            )

        return FuncStatus.GOOD

    async def _step_migrate_roles(self, interaction: discord.Interaction) -> FuncStatus:
        """Phase 3: Move players to their new leagues based on DB stats."""
        await interaction.followup.send("⏳ Starting Player Role Migration...")

        try:
            players_data = await self.db_handler.update_leagues()

            await self._process_role_changes(interaction, players_data)

            return FuncStatus.GOOD
        except Exception as e:
            await self.log_handler.report_error(
                "SeasonManagement._step_migrate_roles()", e
            )
            await interaction.followup.send(
                "❌**ERROR AT PHASE 3** : Critical Error updating player's leagues. Please refer to log."
            )
            return FuncStatus.ERROR

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

    @season_start.error
    async def session_restart_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(
                "❌ **Access Denied.** Admin role required.", ephemeral=True
            )
            await self.log_handler.report_info(
                f"<@{interaction.user.id}> tried accessing the command season_start"
            )
        else:
            await self.log_handler.report_error("session_start_error()", error)
            await interaction.followup.send(
                "❌ An unexpected error occurred. Consult the logs", ephemeral=True
            )


async def setup(bot: OsuArena):
    await bot.add_cog(SeasonStarter(bot))
