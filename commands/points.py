from utils import bot, GUILD, s_role, add_point_role, add_points, get_osu_uname
import discord
from discord import app_commands


@bot.tree.command(name="points", description="Modify a player's point", guild=GUILD)
@app_commands.describe(
    user="The player you want to modify",
    points="Amount to add (use negative numbers to remove)",
)
@app_commands.checks.has_any_role(add_point_role, s_role)
async def points(interaction: discord.Interaction, user: discord.Member, points: int):
    await interaction.response.defer()
    user_name = user.name
    osu_username = await get_osu_uname(user_name)
    response = await add_points(osu_username, points)
    if response:
        new_seasonal_points = response.get("new_seasonal_points")
        new_points = response.get("new_points")
        await interaction.followup.send(
            f"✅{points} points modification done for <@{user.id}>\n"
            f"Total points : **{new_points}**, Total Seasonal Points : **{new_seasonal_points}**"
        )
    else:
        await interaction.response.send_message(f"❌The update for <@{user.id}>")


@points.error
async def points_error(interaction: discord.Interaction, error):
    # NOTE: The error type changes to 'MissingAnyRole' (singular 'Any')
    if isinstance(error, app_commands.MissingAnyRole):
        await interaction.response.send_message(
            "❌ Access Denied. You need one of the allowed roles (admin or speed rank judge).",
            ephemeral=True,
        )
    else:
        print(f"An error occurred: {error}")
