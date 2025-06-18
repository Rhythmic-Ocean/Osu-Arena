from dotenv import load_dotenv
from osu import Client, AuthHandler, Scope
import sqlite3
import os
import discord
from discord.ext import commands
import logging


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
auth = AuthHandler(client_id, client_secret, redirect_url, Scope.identify())

def get_table_data(league):
    conn = sqlite3.connect("instance/rt4d.db")  # change path to your DB
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {league}")  # change table name
    rows = cursor.fetchall()
    headers = [description[0] for description in cursor.description]
    conn.close()
    return headers, rows

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

@bot.command()
async def show(ctx, league: str):
    lea = league
    if lea not in LEAGUE_MODES.values():
        await ctx.send("Invalid league name. Use one of: " + ", ".join(LEAGUE_MODES.values()))
        return

    headers, rows = get_table_data(f"{lea}")
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

    if len(formatted) > 1990:
        await ctx.send("Too much data to display.")
    else:
        await ctx.send(f"```\n{formatted}\n```")


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



