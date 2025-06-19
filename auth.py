from dotenv import load_dotenv
from osu import Client, AuthHandler, Scope, GameModeStr, AsynchronousClient, AsynchronousAuthHandler
import os
import discord
from discord.ext import commands
import logging
import aiosqlite
import shutil
import datetime


load_dotenv(dotenv_path="sec.env")
token = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix = '!',intents = intents)
s_role = 'Admin'


client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
redirect_url = "http://127.0.0.1:5000/"

LEAGUE_MODES = {
    1: "Bronze",
    2: "Silver",
    3: "Gold",
    4: "Platinum",
    5: "Diamond",
    6: "Elite",
    7: "Ranker",
    8: "Master"
}
auth = AsynchronousAuthHandler(client_id, client_secret, redirect_url, Scope.identify())
client_updater = AsynchronousClient.from_credentials(client_id, client_secret, redirect_url)


async def get_table_data(league):
    async with aiosqlite.connect("instance/rt4d.db") as conn:  
        cursor = await conn.cursor()
        await cursor.execute(f"SELECT osu_username, initial_pp, current_pp, pp_change FROM {league} ORDER BY pp_change DESC")  
        rows = await cursor.fetchall()
        headers = [description[0] for description in cursor.description]
    return headers, rows

async def update_current_pp(league):
    async with aiosqlite.connect("instance/rt4d.db") as conn:
        query = f"SELECT osu_username, initial_pp FROM {league}"
        cursor = await conn.cursor()
        await cursor.execute(query)
        rows = await cursor.fetchall()
        updates = []
        for name, initial_pp in rows:
            user = await client_updater.get_user(f"@{name}", GameModeStr.STANDARD)
            pp = round(user.statistics.pp)
            pp_change = int(pp) - int(initial_pp)
            updates.append((pp,pp_change,name))
        await cursor.executemany(
            f"UPDATE {league} SET current_pp = ?, pp_change = ? WHERE osu_username = ?",
            updates
        )
        await conn.commit()
    
async def update_init_pp(league):
    async with aiosqlite.connect("instance/rt4d.db") as conn:
        query = f"SELECT osu_username FROM {league}"
        cursor = await conn.cursor()
        await cursor.execute(query)
        rows = await cursor.fetchall()
        updates = []
        for name in rows:
            user = await client_updater.get_user(f"!{name}", GameModeStr.STANDARD)
            pp = user.statistics.pp
            pp_change = 0
            updates.append(pp,pp,pp_change,name)
        await cursor.executemany(
            f"UPDATE {league} SET initial_pp = ?, current_pp = ?, pp_change = ? WHERE osu_username = ?", 
            updates
        )
        await conn.commit()


@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

@bot.command()
@commands.cooldown(1,20, commands.BucketType.user)
async def show(ctx, league: str):
    lea = league
    if lea not in LEAGUE_MODES.values():
        await ctx.send("Invalid league name. Use one of: " + ", ".join(LEAGUE_MODES.values()))
        return
    loading_message = await ctx.send(f"⏳ Loading data of {lea} league, please wait...")
    await update_current_pp(lea)
    headers, rows = await get_table_data(f"{lea}")
    if not rows:
        await ctx.send("This table is empty")
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, item in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(item)))

    def format_row(row):
        return " | ".join(str(item).ljust(col_widths[i]) for i, item in enumerate(row))

    formatted = format_row(headers) + "\n"
    formatted += "-+-".join("-" * w for w in col_widths) + "\n"
    for row in rows:
        formatted += format_row(row) + "\n"
        await loading_message.edit(content = f"```\n{formatted}\n```")

@show.error
async def show_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = error.retry_after
        await ctx.send(f"You are on cooldown! Try again in {retry_after:.2f} seconds.")
    else:
        raise error

@bot.command()
async def link(ctx):
    state = ctx.author.name 
    auth_url = auth.get_auth_url() + f"&state={state}"
    embed = discord.Embed(
        title = "Click Here",
        url = auth_url
    )
    await ctx.send(embed = embed)

bot.run(token, log_handler = handler, log_level= logging.DEBUG)



