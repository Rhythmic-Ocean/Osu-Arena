from core import bot, check_pending, revoke_challenge
import discord

#revoke a pending challenge

@bot.command()
async def revoke_challenge(ctx,player:discord):
    challenger = ctx.author
    challenged = player
    checking = await check_pending(challenger.name, challenged.name)
    if checking is None:
        await ctx.send(f"{challenger.mention}. You have no pending challenges with {challenged.mention}")
        return
    try:
        await revoke_challenge(id)
        ctx.send(f"{challenger.mention}, your challenge to {challenged.mention} has been revoked successfully.")
    except Exception as e:
        ctx.send(f"Error in challenge deletion: {e}")
    