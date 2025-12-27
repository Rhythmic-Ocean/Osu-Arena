from utils import bot, GUILD, s_role, add_point_role, add_points, get_osu_uname
import discord
from discord import app_commands

from utils.db_getter import get_osu_uname_by_d_id


@bot.tree.command(name="points", description="Modify a player's point", guild=GUILD)
@app_commands.describe(
    user="The player you want to modify",
    points="Amount to add (use negative numbers to remove)",
)
@app_commands.checks.has_any_role(add_point_role, s_role)
async def points(interaction: discord.Interaction, user: discord.Member, points: int):
    await interaction.response.defer()

    user_id = user.id
    print(user.name)
    osu_username = await get_osu_uname_by_d_id(user_id)
    print(osu_username)
    response = await add_points(osu_username, points)

    if response:
        new_seasonal_points = response.get("new_seasonal_points")
        new_points = response.get("new_points")

        # 1. Public confirmation
        await interaction.followup.send(
            f"✅ {points} points modification done for <@{user.id}>\n"
            f"Total points : **{new_points}**, Total Seasonal Points : **{new_seasonal_points}**"
        )

        MY_ID = 367680834322563074
        try:
            admin_user = await bot.fetch_user(MY_ID)

            await admin_user.send(
                f"📝 **Audit Log**\n"
                f"**Admin:** {interaction.user.name} (ID: {interaction.user.id})\n"
                f"**Action:** Modified points for {user.name}\n"
                f"**Amount:** {points}\n"
                f"**New Total:** {new_points}"
            )
        except Exception as e:
            print(f"Failed to DM admin log: {e}")

    else:
        await interaction.followup.send(f"❌ The update failed for <@{user.id}>")
