from core_v2 import backup_database ,bot, s_role, LEAGUE_MODES, update_init_pp, update_leagues
from discord.ext import commands
from discord.ext.commands import has_role, MissingRole

@bot.command()
@has_role(s_role)
async def session_restart(ctx):
    loader = await ctx.send("⏳ Backing up previous session...")
    foldername = await backup_database()
    await loader.edit(content=f"✅ Previous session database backed up in {foldername}")

    for league in LEAGUE_MODES.values():
        msg = await ctx.send(f"⏳ Starting new session for **{league} League**. Please wait...")
        await update_init_pp(league)
        await msg.edit(content=f"✅ Session successfully reinitiated for **{league} League**")
    try:
        players = await update_leagues()
        for player in players:
            print(player)
            user = player['discord_username']
            for users in ctx.guild.members:
                if str(users) == user:
                    person = users
            league = player['league_transferred']
            old_league = player['old_league']
            mention = f""
            await ctx.send(f"<@{person.id}> transferred to {league.capitalize()} from {old_league}")
        await ctx.send("All players have been reassigned to leagues based on their current rankings. If you find any mistakes in your positioning, please inform.")
    except Exception as e:
        await ctx.send(f"CRITICAL ERROR updating leagues: {e}")
        print(f"error:{e}")
        return
    await ctx.send("🎉 All leagues have been successfully reinitiated!")
    await ctx.send("🏆 Good luck to all players!")


@session_restart.error 
async def session_restart_error(ctx, error):
    if isinstance(error, MissingRole):
        await ctx.send(f"Sorry {ctx.author.mention}, you don't have the required role (`{s_role}`) to use this command.")
    else:
        print(f"An unhandled error occurred in session_restart: {error}")
        await ctx.send(f"An unexpected error occurred while running this command: `{error}`")