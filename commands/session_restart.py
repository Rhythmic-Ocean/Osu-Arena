from core_v2 import backup_database ,bot, s_role
from discord.ext import commands
from discord.ext.commands import has_role, MissingRole

@bot.command()
@has_role(s_role)
async def session_restart(ctx):
    loader = await ctx.send("⏳ Backing up previous session...")
    filename = backup_database()
    await loader.edit(content=f"✅ Previous session database backed up as **{filename}**")

    leagues = [
        "Bronze", "Silver", "Gold", "Platinum",
        "Diamond", "Elite", "Ranker", "Master"
    ]

    for league in leagues:
        msg = await ctx.send(f"⏳ Starting new session for **{league} League**. Please wait...")
        await update_init_pp(league)
        await msg.edit(content=f"✅ Session successfully reinitiated for **{league} League**")

    await ctx.send("🎉 All leagues have been successfully reinitiated!")
    await ctx.send("🏆 Good luck to all players!")


@session_restart.error 
async def session_restart_error(ctx, error):
    if isinstance(error, MissingRole):
        await ctx.send(f"Sorry {ctx.author.mention}, you don't have the required role (`{s_role}`) to use this command.")
    else:
        print(f"An unhandled error occurred in session_restart: {error}")
        await ctx.send(f"An unexpected error occurred while running this command: `{error}`")