from core_v2 import backup_database ,bot, s_role, LEAGUE_MODES, update_init_pp, update_leagues
from discord.ext import commands
from discord.ext.commands import has_role, MissingRole
import discord

@bot.command()
@has_role(s_role)
async def session_restart(ctx):
    person = None

    #for league in LEAGUE_MODES.values():
     #   msg = await ctx.send(f"⏳ Starting new session for **{league} League**. Please wait...")
      #  await update_init_pp(league)
       # await msg.edit(content=f"✅ Session successfully reinitiated for **{league} League**")

    try:
        players = await update_leagues()
        for player in players:
            person = ctx.guild.get_member(int(player['discord_id']))
            if not person:
                await ctx.send(f"⚠️ Could not find user: <@{player['discord_id']}>")
                continue
            league = player['league_transferred'].capitalize()
            old_league = player['old_league'].capitalize()
            old_role = discord.utils.get(ctx.guild.roles, name = old_league)
            new_role = discord.utils.get(ctx.guild.roles, name = league)
            if not old_role or not new_role:
                await ctx.send(f"⚠️ One or both roles not found: {old_league}, {league}")
                continue
            if new_role in person.roles and old_role not in person.roles:
                await ctx.send(f"ℹ️ <@{person.id}> is already correctly assigned to {league} role. Skipping.")
                continue
            await ctx.send(f"<@{person.id}> transferred to {league} from {old_league}")
            try:
                await person.remove_roles(old_role)
                await person.add_roles(new_role)
            except Exception as e:
                await ctx.send (f"Failed reassigning role for user: <@{player['discord_id']}>")
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