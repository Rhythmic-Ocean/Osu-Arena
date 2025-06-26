from core_v2 import bot, check_pending, revoke_success, get_msg_id, RIVAL_RESULTS_ID
import discord

@bot.command()
async def revoke_challenge(ctx,player:discord.Member):
    challenger = ctx.author
    challenged = player
    checking = await check_pending(challenger.name, challenged.name)
    if checking is None:
        await ctx.send(f"{challenger.mention}. You have no pending challenges with {challenged.mention}")
        return
    try:
        try:
            msg_id = await get_msg_id(checking)
            channel = bot.get_channel(RIVAL_RESULTS_ID)
            if channel is None:
                await ctx.send("Could not find the #rival-result channel.")
                return
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=f"{challenger.mention} vs {player.mention}|Challenge Revoked")
        except Exception as e:
            await ctx.send(f"Failed to delete content in '#rival-result'. Error: {e}")
        await revoke_success(checking)
        await ctx.send(f"{challenger.mention}, your challenge to {challenged.mention} has been revoked successfully.")
        await challenged.send(f"{challenger.mention} has revoked the previous challenge. Any interaction with the above interface WILL be invalid.")
    except Exception as e:
        await ctx.send(f"Error in challenge deletion: {e}")
    