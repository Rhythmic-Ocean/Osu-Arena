from core_v2 import get_table_data, TABLE_MODES, bot, render_table_image
from discord.ext import commands
import discord

@bot.command()
@commands.cooldown(1, 20, commands.BucketType.user)
async def show(ctx, leag: str):
    league = leag.capitalize()
    if league not in TABLE_MODES.values():
        await ctx.send("❌ Invalid league name. Use one of: " + ", ".join(TABLE_MODES.values()))
        return

    loading_message = await ctx.send(f"⏳ Loading data for **{league}** league, please wait...")

    try:
        headers, rows = await get_table_data(league.lower())
    except Exception as e:
        print(f"error: {e}")
        await loading_message.edit(content="⚠️ Failed to load data.")
        return

    if not rows:
        await loading_message.edit(content="⚠️ This table is empty.")
        return

    image_buf = render_table_image(headers, rows)
    file = discord.File(fp=image_buf, filename="table.png")
    embed = discord.Embed(title=f"{league} League")
    embed.set_image(url="attachment://table.png")

    await loading_message.delete()
    await ctx.send(embed=embed, file=file)

@show.error
async def show_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = error.retry_after
        await ctx.send(f"⏳ You are on cooldown! Try again in {retry_after:.2f} seconds.")


