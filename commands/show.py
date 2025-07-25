from core_v2 import get_table_data, TABLE_MODES, bot, render_table_image, GUILD
from discord.ext import commands
import discord
from discord import app_commands

@bot.tree.command(name="show", description="Show the league table", guild=GUILD)
@app_commands.describe(leag="League name")
async def show(interaction: discord.Interaction, leag: str):
    league = leag.capitalize()
    if league not in TABLE_MODES.values():
        await interaction.response.send_message(
                "❌ Invalid league name. Use one of: " + ", ".join(TABLE_MODES.values()), ephemeral=True
            )
        return
    await interaction.response.defer()
    try:
        headers, rows = await get_table_data(league.lower())
    except Exception as e:
        print(f"error: {e}")
        await interaction.response.send_message(content="⚠️ Failed to load data.")
        return

    if not rows:
        await interaction.response.send_message(content="⚠️ This table is empty.")
        return

    image_buf = render_table_image(headers, rows)
    file = discord.File(fp=image_buf, filename="table.png")
    embed = discord.Embed(title=f"{league} League")
    embed.set_image(url="attachment://table.png")
    try:
        await interaction.followup.send(embed=embed, file=file)
    except Exception as e:
        await interaction.followup.send_message("⚠️ An unknown error occurred.")
        print(f"Unexpected error in /show: {e}")
    




