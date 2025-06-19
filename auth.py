from dotenv import load_dotenv
from osu import Client, AuthHandler, Scope, GameModeStr, AsynchronousClient, AsynchronousAuthHandler
import os
import discord
# from discord import Member # Corrected potential import, but unused
from discord.ext import commands
from discord.ext.commands import has_role, MissingRole # Corrected has_permissions to has_role, and added MissingRole
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

DB_PATH = "instance/rt4d.db"
BACKUP_DIR = "instance/backups"

os.makedirs(BACKUP_DIR, exist_ok=True)


bot = commands.Bot(command_prefix = '!',intents = intents)
s_role = 'admin' # Make sure 'admin' is the exact name of the role

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

def backup_database():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    shutil.copyfile(DB_PATH,backup_path)
    return backup_path

async def get_table_data(league):
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.cursor()
        await cursor.execute(f"SELECT osu_username, initial_pp, current_pp, pp_change FROM {league} ORDER BY pp_change DESC")
        rows = await cursor.fetchall()
        headers = [description[0] for description in cursor.description]
    return headers, rows

async def update_current_pp(league):
    async with aiosqlite.connect(DB_PATH) as conn:
        query = f"SELECT osu_username, initial_pp FROM {league}"
        cursor = await conn.cursor()
        await cursor.execute(query)
        rows = await cursor.fetchall()
        updates = []
        for name, initial_pp in rows:
            # Assuming get_user takes just the username string, not a tuple
            user = await client_updater.get_user(name, GameModeStr.STANDARD) # Removed "@" prefix, assuming osu api handles it
            pp = round(user.statistics.pp)
            pp_change = int(pp) - int(initial_pp)
            updates.append((pp, pp_change, name)) # Append as a tuple
        await cursor.executemany(
            f"UPDATE {league} SET current_pp = ?, pp_change = ? WHERE osu_username = ?",
            updates
        )
        await conn.commit()

async def update_init_pp(league):
    async with aiosqlite.connect(DB_PATH) as conn: # Changed path to DB_PATH constant
        query = f"SELECT osu_username FROM {league}"
        cursor = await conn.cursor()
        await cursor.execute(query)
        rows = await cursor.fetchall()
        updates = []
        for name_tuple in rows: # Renamed to name_tuple to clarify it's a tuple
            name = name_tuple[0] # Extract the string username from the tuple
            user = await client_updater.get_user(name, GameModeStr.STANDARD) # Removed "!" prefix
            pp = round(user.statistics.pp) # Round PP to integer
            pp_change = 0 # As it's initial update, pp_change should be 0
            updates.append((pp, pp, pp_change, name)) # Append as a tuple
        await cursor.executemany(
            f"UPDATE {league} SET initial_pp = ?, current_pp = ?, pp_change = ? WHERE osu_username = ?",
            updates
        )
        await conn.commit()


@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

@bot.command()
@commands.cooldown(1, 20, commands.BucketType.user)
async def show(ctx, leag: str):
    league = leag.capitalize()
    if league not in LEAGUE_MODES.values():
        await ctx.send("❌ Invalid league name. Use one of: " + ", ".join(LEAGUE_MODES.values()))
        return

    loading_message = await ctx.send(f"⏳ Loading data for **{league}** league, please wait...")

    await update_current_pp(league)

    headers, rows = await get_table_data(league)

    if not rows:
        await loading_message.edit(content="⚠️ This table is empty.")
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
        await loading_message.edit(content="⚠️ Too much data to display in one message.")
    else:
        await loading_message.edit(content=f"```txt\n{formatted}```")



@bot.command()
@has_role(s_role)
async def session_restart(ctx):
    # Step 1: Backup the previous session
    loader = await ctx.send("⏳ Backing up previous session...")
    filename = backup_database()
    await loader.edit(content=f"✅ Previous session database backed up as **{filename}**")

    # Step 2: Reinitialize all leagues
    leagues = [
        "Bronze", "Silver", "Gold", "Platinum",
        "Diamond", "Elite", "Ranker", "Master"
    ]

    for league in leagues:
        msg = await ctx.send(f"⏳ Starting new session for **{league} League**. Please wait...")
        await update_init_pp(league)
        await msg.edit(content=f"✅ Session successfully reinitiated for **{league} League**")

    # Final confirmation
    await ctx.send("🎉 All leagues have been successfully reinitiated!")
    await ctx.send("🏆 Good luck to all players!")


# --- ERROR HANDLER FOR session_restart ---
@session_restart.error # THIS MUST BE AFTER THE COMMAND DEFINITION
async def session_restart_error(ctx, error):
    if isinstance(error, MissingRole): # Use MissingRole instead of commands.MissingRole
        # Ensure 's_role' is a string of the role name, or the role ID
        await ctx.send(f"Sorry {ctx.author.mention}, you don't have the required role (`{s_role}`) to use this command.")
    else:
        # Log other errors for debugging
        print(f"An unhandled error occurred in session_restart: {error}")
        await ctx.send(f"An unexpected error occurred while running this command: `{error}`")


@bot.command()
async def link(ctx):
    state = ctx.author.name
    auth_url = auth.get_auth_url() + f"&state={state}"
    embed = discord.Embed(
        title = "Click Here",
        url = auth_url
    )
    await ctx.send(embed = embed)

bot.remove_command('help')

@bot.command()
async def help(ctx):
    await ctx.send("!link-->To link you osu! Account, (inactive rn). I've manually linked all the members that were signed up before June 18th 2025, 22:50 CDT time.")
    await ctx.send("!show Bronze --> To show Bronze League Table. Similary replace 'Bronze' with 'Silver' or any other league to get that league's table. Just type !show to see all the valid leagues.")
    await ctx.send("!session_restart --> Admin only command to reset the session.")
    


@show.error
async def show_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = error.retry_after
        await ctx.send(f"You are on cooldown! Try again in {retry_after:.2f} seconds.")


@bot.remove_command('help') 

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📘 Bot Help Menu",
        description="Here's a list of available commands and what they do:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🔗 !link",
        value="Link your osu! account *(currently inactive)*.\n"
              "All users signed up before **June 18, 2025, 22:50 CDT** were linked manually.",
        inline=False
    )

    embed.add_field(
        name="📊 !show [league]",
        value="Shows the table for a specific league.\n"
              "Example: `!show Bronze` or `!show Silver`\n"
              "Type `!show` alone to see all valid leagues.",
        inline=False
    )

    embed.add_field(
        name="🛠️ !session_restart",
        value="Admin-only command to reset the current session.",
        inline=False
    )

    embed.set_footer(text="osu! League Bot • Created by Rhythmic_Ocean")
    await ctx.send(embed=embed)



bot.run(token, log_handler = handler, log_level= logging.DEBUG)


