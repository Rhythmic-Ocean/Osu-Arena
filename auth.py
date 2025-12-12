"""
Main Entry Point for the Discord Bot.

This module handles the bot's startup process, including:
1. syncing slash commands to the specific guild.
2. initializing background monitoring tasks.
"""
import logging
import discord
import commands

from utils import token, bot, RIVAL_RESULTS_ID, GUILD_ID
from utils.monitoring import monitor_database, monitor_new_players, monitor_top_plays

# specific logger for this file
log = logging.getLogger(__name__)

@bot.event
async def on_ready():
    """
    Triggered when the bot connects. 
    Includes a guard to prevent code running twice on reconnects.
    """
    # The Safety Guard
    # We check if we have already set up the bot. If so, return early.
    if hasattr(bot, 'setup_finished') and bot.setup_finished:
        print(f"Bot reconnected as {bot.user}.")
        return

    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Sync Commands with Osu_Arena Server. The GUILD_ID is for Osu_Arena server
    try:
        print(GUILD_ID)
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} commands to guild {GUILD_ID}!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    # Background tasks initialization
    # monitor_database is for Rivals table monitoring for any wins/ losses. Then update it on the server
    # monitor_new_user is for any new user that did /link and was added to the db. Then announce which league they were put in.
    bot.loop.create_task(monitor_database(bot, RIVAL_RESULTS_ID))
    bot.loop.create_task(monitor_new_players(bot))
    bot.loop.create_task(monitor_top_plays(bot))
    
    # Mark setup as done so we don't repeat this if the bot reconnects
    bot.setup_finished = True
    print("Bot startup complete.")

if __name__ == "__main__":
    bot.run(token)

