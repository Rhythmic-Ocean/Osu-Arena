from core import bot,get_table_data,update_current_pp, TABLE_MODES, update_rival_table, show_rival_table
from discord.ext import commands

@bot.command()
@commands.cooldown(1, 20, commands.BucketType.user)
async def show(ctx, leag: str):
    league = leag.capitalize()
    if league not in TABLE_MODES.values():
        await ctx.send("❌ Invalid league name. Use one of: " + ", ".join(TABLE_MODES.values()))
        return


    loading_message = await ctx.send(f"⏳ Loading data for **{league}** league, please wait...")


    if league == "Rivals":
         await update_rival_table()
         rows, headers = await show_rival_table()

    else:
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
        await loading_message.edit(content = f"{league} League")
        await ctx.send(f"```txt\n{formatted}```")
        

@show.error
async def show_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = error.retry_after
        await ctx.send(f"You are on cooldown! Try again in {retry_after:.2f} seconds.")
