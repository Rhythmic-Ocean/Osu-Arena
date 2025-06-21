from core import bot, ROLE_MODES, ChallengeView, check_challenger_challenges, challenge_accepted,get_pp, RIVAL_RESULTS_ID, challenge_allowed, log_rivals, challenge_declined
import discord
from discord.ext import commands

MIN_PP = 250
MAX_PP = 750

@bot.command()
async def challenge(ctx, player: discord.Member, pp: int):
    challenger = ctx.author
    if challenger.id == player.id:
        await ctx.send(f"{challenger.mention}, you cannot challenge yourself!")
        return
    if not (MIN_PP <= pp <= MAX_PP):
        await ctx.send(f"{challenger.mention}, challenge failed. Choose a PP value between 250 and 750.")
        return
    try:
        number_of_challenges = await check_challenger_challenges(challenger)
    except Exception as e:
        await ctx.send(f"Error 1: {e}")

    if number_of_challenges >= 3:
        await ctx.send(f"{challenger.mention}, you already have 3 ongoing/ pending challenges. Complete them before issuing more.")
        return

    challenger_role = None
    challenged_role = None
    for league in ROLE_MODES.values():
        if challenger_role is None and any(league == role.name for role in ctx.author.roles):
            challenger_role = league
        if challenged_role is None and any(league == role.name for role in player.roles):
            challenged_role = league
        if challenger_role and challenged_role:
            break

    if challenger_role is None:
        await ctx.send(f"{ctx.author.mention}, you do not have any league. Please ask spinneracc to assign you one.")
        return

    if challenged_role is None:
        await ctx.send(f"{player.mention} has not been assigned a league.")
        return

    if challenged_role != challenger_role:
        await ctx.send(f"{challenger.mention}, challenge failed. Please choose someone from your own league.")
        return
    league = challenger_role




    try:
        allowance = await challenge_allowed(challenger.name, player.name, league)
    except Exception as e:
        await ctx.send(f"Error 2: {e}")
    if allowance == 2:
        await ctx.send(f"{challenger.mention}, you already have a pending challenge with {player.mention}")
        return
    elif allowance == 3:
        await ctx.send(f"{challenger.mention}, you already have an ongoing challenge with {player.mention}")
        return
    elif allowance == 4:
        await ctx.send(f"{challenger.mention}, you cannot challenge the same player more than once a day.")
        return
    elif allowance == 5:
        await ctx.send(f"{challenger.mention}, you or {player.mention} don't have your account linked to the database yet. Please contact me if you think it's a mistake.")
    



    try:
        id = await log_rivals(league, challenger.name, player.name, pp)
    except Exception as e:
        await ctx.send(f"{challenger.mention}Error at log function, please report. Error: {e}")
        return



    await ctx.send(f"{challenger.mention} has challenged {player.mention}. Challenge request has been sent.")
    rival_results_channel = bot.get_channel(RIVAL_RESULTS_ID)



    try:
        view = ChallengeView(challenged=player)
        await player.send(
            f"You have been challenged by {challenger.mention} for {pp}pp in **{challenger_role}** league.\nDo you accept?",
            view=view
        )
    except discord.Forbidden:
        await ctx.send(f"Challenge unsuccessful. {player.mention} may have DMs disabled. Challenge logged as voided.")
        try:
                await challenge_declined(id)
                return  
        except Exception as e:
            await ctx.send(f"{challenger.mention}, failed to log decline: `{e}`")
            return
        

    if rival_results_channel:
        try:
            challenge_request = await rival_results_channel.send(f"{challenger.mention} has issued a challenge to {player.mention} for {pp}pp in {challenger_role} league.")
        except discord.Forbidden:
            await ctx.send(f"No permission to send message in {rival_results_channel.mention} channel. You challenge is logged as pending and the challenged can still Accept your challenge.")
            try:
                await challenge_accepted(id)  
            except Exception as e:
                await ctx.send(f"{challenger.mention}, failed to log accept: `{e}`")
                return

    await view.wait()

    if view.response is None:
        await ctx.send(f"{challenger.mention}, {player.mention} did not respond in time. The challenge is voided.")
        await challenge_request.edit(content = f"{challenger.mention}, your challenged to {player.mention} has been voided.")
        try:
            await challenge_declined(id)
            return
        except Exception as e:
            await ctx.send(f"{challenger.mention}Error at challenge_decline function, please report. Error: {e}")
            return

    elif view.response:
        try:
            await challenge_accepted(id)
            await ctx.send(f"{challenger.mention}, {player.mention} accepted your challenge! Type `!show rivals` to view ongoing challenges.")
            if rival_results_channel:
                challenger_pp = await get_pp(discord_username = challenger.name, league=league)
                challenged_pp = await get_pp(discord_username= player.name, league=league)
                await challenge_request.edit(content=f"{challenger.mention}({challenger_pp}) vs {player.mention}({challenged_pp})|{pp}PP|unfinished")
        except Exception as e:
            await ctx.send(f"An error occurred at challenge accepted: {e}")
    else:
        await ctx.send(f"{challenger.mention}, {player.mention} has declined your challenge.")
        await challenge_request.edit(content = f"{challenger.mention}, your challenged to {player.mention} has been voided.")
        try:
            await challenge_declined(id)
            return
        except Exception as e:
            await ctx.send(f"{challenger.mention}Error at challenge_decline function, please report. Error: {e}")
            return
    
@challenge.error
async def challenge_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = error.retry_after
        await ctx.send(f"You are on cooldown for !challenge. Try again in {retry_after:.2f} seconds.")
