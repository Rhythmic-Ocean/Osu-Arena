from core_v2 import bot, ROLE_MODES, ChallengeView, check_challenger_challenges, challenge_accepted,get_pp, RIVAL_RESULTS_ID, challenge_allowed, log_rivals, challenge_declined, store_msg_id, check_league, revoke_success
import discord
from discord.ext import commands

MIN_PP = 250
MAX_PP = 750

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def challenge(ctx, player: discord.Member, pp: int):
    challenge_request = None
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
        await ctx.send(f"Error 1 at challenge command: {e}")

    if number_of_challenges >= 3:
        await ctx.send(f"{challenger.mention}, you already have 3 ongoing/ pending challenges. Complete or revoke any pending challenges before issuing more.")
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
    bool1 = await check_league(challenger.name, league)
    bool2 = await check_league(player.name, league)

    if not bool1:
        await ctx.send(f"{challenger.mention}, your role and database league are mismatched, please ask the admins to fix it. You won't be able to challenge or receive challenge until then.")
        if not bool2:
            await ctx.send(f"{player.mention}, your role and database league are mismatched, please ask admins to fix it. You won't be able to challenge or receive challenge until then.")
        return

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
        return
    elif allowance == 6:
        await ctx.send(f"{challenger.mention}, ERROR: Failed to execute function 'challenged_allowed'. Challenge failed.")
    try:
        challenge_id = await log_rivals(league, challenger.name, player.name, pp)
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
        await ctx.send(f"Challenge unsuccessful. {player.mention} may have DMs disabled. Challenge has been revoked.")
        try:
                await revoke_success(challenge_id)
                return  
        except Exception as e:
            await ctx.send(f"ERROR: failed to log revokes: `{e}`")
            return
        
    if rival_results_channel:
        try:

            challenge_request = await rival_results_channel.send(f"{challenger.mention} has issued a challenge to {player.mention} for {pp}pp in {challenger_role} league.")
            msg_id = challenge_request.id
            await store_msg_id(challenge_id, msg_id)
        except discord.Forbidden:
            await ctx.send(f"No permission to send message in {rival_results_channel.mention} channel. You challenge is logged as pending and the challenged can still Accept your challenge.")
    try:
        await view.wait()
    except Exception as e:
        await ctx.send(f"Waiting error:{e}")
        return 
    try:
        challenger_pp = await get_pp(discord_username = challenger.name,)
        challenged_pp = await get_pp(discord_username= player.name)
    except Exception as e:
        print(f"Error getting pp: {e}")
    if view.response is None:
        await ctx.send(f"{challenger.mention}, {player.mention} did not respond in time. The challenge is voided.")
        try:
            stats = await challenge_declined(challenge_id)
            if stats is None:
                await player.send("The challenge above is no longer available. Any interaction with it might fail.")
                return
            await challenge_request.edit(content = f"{challenger.mention}({challenger_pp}) vs {player.mention}({challenged_pp}) |{pp}PP| Declined")
        except Exception as e:
            await ctx.send(f"{challenger.mention}Error at challenge_decline function, please report. Error: {e}")
            return
        

    elif view.response is True:
        try:
            status = await challenge_accepted(challenge_id)
            if status is None:
                await player.send("The challenge above is no longer available. Any interaction with it might fail.")
                return
            await ctx.send(f"{challenger.mention}, {player.mention} accepted your challenge! Type `!show rivals` to view ongoing challenges.")
            if rival_results_channel:
                await challenge_request.edit(content=f"{challenger.mention}({challenger_pp}) vs {player.mention}({challenged_pp}) |{pp}PP| Unfinished")
        except Exception as e:
            await ctx.send(f"An error occurred at challenge accepted: {e}")



    else:
        await ctx.send(f"{challenger.mention}, {player.mention} has declined your challenge.")
        await challenge_request.edit(content = f"{challenger.mention}({challenger_pp}) vs {player.mention}({challenged_pp})|{pp}PP|Declined")
        try:
            stats = await challenge_declined(challenge_id)
            if stats is None:
                await player.send("The challenge above is no longer available. Any interaction with it might fail.")
                return
            await challenge_request.edit(content = f"{challenger.mention}({challenger_pp}) vs {player.mention}({challenged_pp})|{pp}PP|Declined")
        except Exception as e:
            await ctx.send(f"{challenger.mention}Error at challenge_decline function, please report. Error: {e}")
            return
        
@challenge.error
async def challenge_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = error.retry_after
        await ctx.send(f"You are on cooldown for !challenge. Try again in {retry_after:.2f} seconds.")
