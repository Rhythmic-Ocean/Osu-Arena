from core_v2 import token, handler, bot
import logging
import commands 

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    print(f"We are ready to go in, {bot.user.name}")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)


