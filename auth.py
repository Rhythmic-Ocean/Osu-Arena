from core_v2 import token, handler, bot, RIVAL_RESULTS_ID, GUILD_ID
import logging
import commands 
from monitoring import monitor_database, monitor_new_user
import discord
@bot.event
async def on_ready():
    await bot.wait_until_ready()
    try:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print("Slash commands synced to guild!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    channel_id = RIVAL_RESULTS_ID
    bot.loop.create_task(monitor_database(bot, channel_id))
    bot.loop.create_task(monitor_new_user(bot))
    print(f"We are ready to go in, {bot.user.name}")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)


