from core import serializer, auth, bot
import discord

@bot.command()
async def link(ctx):
    state = serializer.dumps({"discord_username": ctx.author.name})
    auth_url = auth.get_auth_url() + f"&state={state}"
    embed = discord.Embed(
    title="Link Your osu! Account",
    description="Click the title to begin linking your account. Please DO NOT share this link.",
    color=discord.Color.blue(),
    url=auth_url
    )
    try:
        await ctx.author.send(embed=embed)
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention}, I couldn't DM you. Please enable DMs from server members.")
