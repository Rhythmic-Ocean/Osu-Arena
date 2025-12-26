from utils import bot, GUILD, s_role, remove_player
import discord
from discord import app_commands


@bot.tree.command(
    name="delete",
    description="Forcefully delete a player from the database",
    guild=GUILD,
)
@app_commands.describe(user="The player you want to delete")
@app_commands.checks.has_role(s_role)
async def delete(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer()

    success = await remove_player(user.id)

    if success:
        await interaction.followup.send(
            f"✅ **Deleted**: <@{user.id}> has been wiped from the database."
        )
    else:
        await interaction.followup.send(
            f"⚠️ **Not Found**: <@{user.id}> was not in the database to begin with.",
            ephemeral=True,
        )


@delete.error
async def delete_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message(
            "❌ Access Denied. Only Admins can delete users.",
            ephemeral=True,
        )
    else:
        print(f"Delete command error: {error}")
