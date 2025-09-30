import discord
from core_v2 import bot, SEASON_STATUS, GUILD, exist_archive, TABLE_MODES, get_table_data,render_table_image, CHALLENGE_STATUS
from discord import app_commands

@bot.tree.command(name="archived", description="Shows archived tables", guild=GUILD)
@app_commands.describe(season="any finished season", league="league name")
async def archived(interaction: discord.Interaction, season: int, league: str):
    leag = league.capitalize()
    if leag not in TABLE_MODES.values():
        await interaction.response.send_message(
            "❌ Invalid league name. Use one of: " + ", ".join(TABLE_MODES.values()), ephemeral=True
        )
        return

    await interaction.response.defer()
    if leag == TABLE_MODES[9]:
        if season != 0:
            await interaction.followup.send(
                "❌ Season 0 is the only valid season for Rivals League."
            )
            return
    
    elif leag == TABLE_MODES[10]:
        if season == 1:
            await interaction.followup.send(
                "⚠ Novice League does not exist for Season 1"
            )
            return
    elif leag == TABLE_MODES[7]:
        if season != 1:
            await interaction.followup.send(
                "⚠ Ranker League does not exist for Season {season}. It was deprecated after Season 1."
            )
            return
    else: 
        status = await exist_archive(seash=season)
        print(status)
        if status == SEASON_STATUS[3]:
            await interaction.followup.send("❌ Invalid season.")
            return
        elif status == SEASON_STATUS[4]:
            await interaction.followup.send("❌ Error occurred processing request, please contact the admins")
            return
        elif status == SEASON_STATUS[1]:
            await interaction.followup.send("❌ This session is ongoing, please use !show command.")
            return

    le = leag.lower()
    st = le + "_" + str(season)
    print(st)
    try:
        if leag == TABLE_MODES[9]:
            headers, rows = await get_table_data(le, stat= CHALLENGE_STATUS[4])
        else:
            headers, rows = await get_table_data(st)
    except Exception as e:
        print(f"error: {e}")
        await interaction.followup.send(content="⚠️ Failed to load data.", ephemeral=True)
        return

    if not rows:
        await interaction.followup.send(content="⚠ This table is empty.", ephemeral=True)
        return

    image_buf = render_table_image(headers, rows)
    file = discord.File(fp=image_buf, filename="table.png")
    if season == 0:
        embed = discord.Embed(title="Rivals - Archived")
    else: 
        embed = discord.Embed(title=f"{leag} League - Season {season}")
    embed.set_image(url="attachment://table.png")
    try:
        await interaction.followup.send(embed=embed, file=file)
    except Exception as e:
        await interaction.followup.send(content="⚠️ An unknown error occurred.")
        print(f"Unexpected error in /archived: {e}")
    
    
    

    
