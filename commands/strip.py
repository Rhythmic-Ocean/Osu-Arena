from core_v2 import get_table_data, TABLE_MODES, bot, render_table_image, GUILD, is_in, s_role
from discord.ext import commands
import discord
from discord.ext.commands import has_role, MissingRole

@bot.command(name="strip")
@has_role(s_role)
async def strip(ctx):
    guild = ctx.guild
    members = guild.members
    count = 0
    inactive_role = discord.utils.get(guild.roles, name="Inactive")

    if inactive_role is None:
        await ctx.send("❌ 'Inactive' role not found.")
        return

    for member in members:
        if member.name == "Osu!Arena":
            continue
        check = await is_in(member.id)
        print(member.name)
        if not check:
            if member.bot:
                continue
            print(f"fucke: {member.name}")
            for role in member.roles:
                if role.name != "@everyone":
                    await member.remove_roles(role)
            await member.add_roles(inactive_role)
            count += 1
            await ctx.send(f"<@{member.id}> marked inactive.")
    
    await ctx.send(f"✅ Done. {count} members marked as inactive.")

@strip.error 
async def session_restart_error(ctx, error):
    if isinstance(error, MissingRole):
        await ctx.send(f"Sorry {ctx.author.mention}, you don't have the required role (`{s_role}`) to use this command.")
    else:
        print(f"An unhandled error occurred in session_restart: {error}")
        await ctx.send(f"An unexpected error occurred while running this command: `{error}`")