"""
Main Entry Point for the Discord Bot.

This module handles the bot's startup process, including:
1. syncing slash commands to the specific guild.
2. initializing background monitoring tasks.
"""

import logging
import discord
import commands

from utils import (
    token,
    bot,
    RIVAL_RESULTS_ID,
    GUILD_ID,
    handle_member_leave,
    sync_ghost_users,
)
from utils.monitoring import monitor_database, monitor_new_players, monitor_top_plays

log = logging.getLogger(__name__)


@bot.event
async def on_ready():
    """
    Triggered when the bot connects.
    Includes a guard to prevent code running twice on reconnects.
    """
    if hasattr(bot, "setup_finished") and bot.setup_finished:
        print(f"Bot reconnected as {bot.user}.")
        return

    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    try:
        print(GUILD_ID)
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} commands to guild {GUILD_ID}!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    bot.loop.create_task(monitor_database(bot, RIVAL_RESULTS_ID))
    bot.loop.create_task(monitor_new_players(bot))
    bot.loop.create_task(monitor_top_plays(bot))

    bot.loop.create_task(sync_ghost_users(bot))
    bot.setup_finished = True
    print("Bot startup complete.")


@bot.event
async def on_member_remove(member):
    await handle_member_leave(member)


if __name__ == "__main__":
    bot.run(token)
