from utils import (
    bot,
    s_role,
    LEAGUE_MODES,
    update_init_pp,
    update_leagues,
    seasonal_point_update,
    reset_seasonal_points,
    get_current_season,
    backup_seasonal_points,
    mark_season_archived,
    duplicate_table,
    GUILD,
    ResetConfirmView,
)
from discord.ext.commands import MissingRole
import discord
from discord import app_commands


@bot.tree.command(
    name="session_restart", description="End current season with backups", guild=GUILD
)
@app_commands.checks.has_any_role(s_role)
async def session_restart(interaction: discord.Interaction):
    await interaction.response.defer()
    view = ResetConfirmView(interaction)
    await interaction.followup.send(
        "⚠️ **WARNING** ⚠️\n"
        "You are about to **END THE CURRENT SEASON**.\n"
        "This will archive data, reset points, and move players.\n\n"
        "Are you sure you want to proceed?",
        view=view,
    )

    await view.wait()

    if view.value is None:
        await interaction.followup.send("❌ **Timed out.** Operation cancelled.")
        return
    elif not view.value:
        await interaction.followup.send("❌ **Operation cancelled** by user.")
        return

    await interaction.followup.send(
        "✅ Confirmation received. Starting restart sequence..."
    )

    person = None
    current = await get_current_season()
    if not current:
        await interaction.followup.send("No ongoing season.")
        return

    marking = await mark_season_archived(current)
    if not marking:
        await interaction.followup.send(
            f"Failed to mark {current} as archived, please fix this first."
        )
        return

    await interaction.followup.send(f"Ending current season : Season {current}.")

    await interaction.followup.send("⏳Updating end of season points.")
    try:
        await seasonal_point_update()
    except Exception as e:
        await interaction.followup.send(f"Error updating sesonal points {e}")
        return
    await interaction.followup.send("✅End of season points have been distributed!")

    await interaction.followup.send("⏳Backing up seasonal points.")
    try:
        await backup_seasonal_points(current)
    except Exception as e:
        await interaction.followup.send(f"Error backing up sesonal points {e}")
        return
    await interaction.followup.send("✅Seasonal points backed up!")

    await interaction.followup.send("⏳Resetting seasonal points.")
    try:
        await reset_seasonal_points()
    except Exception as e:
        await interaction.followup.send(f"Error resetting up sesonal points {e}")
        return
    await interaction.followup.send("✅Seasonal Points have been reset.")

    for league in LEAGUE_MODES.values():
        if league == LEAGUE_MODES[7]:
            continue
        msg = await interaction.followup.send(
            f"⏳ Starting backup for **{league} League**. Please wait..."
        )
        duplicating_response = await duplicate_table(league, current)
        if not duplicating_response:
            await msg.edit(
                content=f"Error duplicating {league}. Error at creating table {league}_{current}"
            )
            return
        await msg.edit(content=f"✅ Successfully backed up for **{league} League**")
        msg = await interaction.followup.send(
            f"⏳ Starting new session for **{league} League**. Please wait..."
        )
        await update_init_pp(league)
        await msg.edit(
            content=f"✅ Session successfully reinitiated for **{league} League**"
        )

    try:
        players = await update_leagues()
        for player in players:
            person = interaction.guild.get_member(int(player["discord_id"]))
            if not person:
                await interaction.followup.send(
                    f"⚠️ Could not find user: <@{player['discord_id']}>"
                )
                continue
            league = player["league_transferred"].capitalize()
            old_league = player["old_league"].capitalize()
            old_role = discord.utils.get(interaction.guild.roles, name=old_league)
            new_role = discord.utils.get(interaction.guild.roles, name=league)
            if not old_role or not new_role:
                await interaction.followup.send(
                    f"⚠️ One or both roles not found: {old_league}, {league}"
                )
                continue
            if new_role in person.roles and old_role not in person.roles:
                await interaction.followup.send(
                    f"ℹ️ <@{person.id}> is already correctly assigned to {league} role. Skipping."
                )
                continue
            await interaction.followup.send(
                f"<@{person.id}> transferred to {league} from {old_league}"
            )
            try:
                await person.remove_roles(old_role)
                await person.add_roles(new_role)
            except Exception as e:
                await interaction.followup.send(
                    f"Failed reassigning role for user: <@{player['discord_id']}>"
                )
        await interaction.followup.send(
            "All players have been reassigned to leagues based on their current rankings. If you find any mistakes in your positioning, please inform."
        )

    except Exception as e:
        await interaction.followup.send(f"CRITICAL ERROR updating leagues: {e}")
        print(f"error:{e}")
        return

    await interaction.followup.send(
        "🎉 All leagues have been successfully reinitiated!"
    )

    await interaction.followup.send("🏆 Good luck to all players!")


@session_restart.error
async def session_restart_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingAnyRole):
        await interaction.response.send_message(
            "❌ Access Denied. You need one of the allowed roles (admin or speed rank judge).",
            ephemeral=True,
        )
    else:
        print(f"An error occurred: {error}")
