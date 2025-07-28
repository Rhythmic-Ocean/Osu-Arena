from core_v2 import (
    bot, ROLE_MODES, ChallengeView, check_challenger_challenges, challenge_accepted, get_pp,
    RIVAL_RESULTS_ID, challenge_allowed, log_rivals, challenge_declined, store_msg_id,
    check_league, revoke_success, GUILD
)
import discord
from discord import app_commands

MIN_PP = 250
MAX_PP = 750

@bot.tree.command(name="challenge", description="Challenge a user in your league", guild=GUILD)
@app_commands.describe(player="Player to challenge", pp="Performance points (250–750)")
async def challenge(interaction: discord.Interaction, player: discord.Member, pp: int):
    challenger = interaction.user

    if challenger.id == player.id:
        await interaction.response.send_message("❌ You cannot challenge yourself!")
        return

    if not (MIN_PP <= pp <= MAX_PP):
        await interaction.response.send_message("❌ PP must be between 250 and 750.")
        return
    
    await interaction.response.defer()

    try:
        number_of_challenges = await check_challenger_challenges(challenger.name)
    except Exception as e:
        await interaction.followup.send(f"❌ Error while checking challenges: {e}")
        return

    if number_of_challenges >= 3:
        await interaction.followup.send("❌ You already have 3 active or pending challenges.")
        return
    try:
        number_of_challenges = await check_challenger_challenges(player.name)
    except Exception as e:
        await interaction.followup.send(f"❌ Error while checking challenges: {e}")
        return
    n = player.mention

    if number_of_challenges >= 3:
        await interaction.followup.send(f"❌ {n} already have 3 active or pending challenges. Please challenge someone else")
        return

    challenger_role = None
    challenged_role = None
    for league in ROLE_MODES.values():
        if not challenger_role and any(league == r.name for r in challenger.roles):
            challenger_role = league
        if not challenged_role and any(league == r.name for r in player.roles):
            challenged_role = league
        if challenger_role and challenged_role:
            break

    if not challenger_role:
        await interaction.followup.send("❌ You have not been assigned a league role.")
        return
    if not challenged_role:
        await interaction.followup.send(f"❌ {player.display_name} has not been assigned a league.")
        return
    if challenged_role != challenger_role:
        await interaction.followup.send("❌ You can only challenge players in your own league.")
        return

    # League verification
    bool1 = await check_league(challenger.name, challenger_role)
    bool2 = await check_league(player.name, challenger_role)
    if not bool1:
        await interaction.followup.send("❌ Your league in the DB doesn't match your role. Ask admin.")
        return
    if not bool2:
        await interaction.followup.send(f"⚠️ {player.mention}'s role and DB league don't match. Ask admin.")

    # Check allowance
    try:
        allowance = await challenge_allowed(challenger.name, player.name, challenger_role)
    except Exception as e:
        await interaction.followup.send(f"❌ Error while checking allowance: {e}", ephemeral=True)
        return

    allowance_messages = {
        2: f"❌ You already have a pending challenge with {player.mention}.",
        3: f"❌ You already have an ongoing challenge with {player.mention}.",
        4: f"❌ You can only challenge the same player once per day.",
        5: f"❌ One of you isn't linked to the database. Please contact an admin.",
        6: f"❌ Internal error occurred. Please contact the dev."
    }
    if allowance in allowance_messages:
        await interaction.followup.send(allowance_messages[allowance])
        return

    # Log challenge
    try:
        challenge_id = await log_rivals(challenger_role, challenger.name, player.name, pp)
    except Exception as e:
        await interaction.followup.send(f"❌ Error logging challenge: {e}")
        return

    await interaction.followup.send(f"{challenger.mention} has challenged {player.mention} for {pp}pp.")

    # Send DM to challenged player
    try:
        view = ChallengeView(challenged=player)
        await player.send(
            f"You have been challenged by {challenger.display_name} for {pp}pp in the **{challenger_role}** league.\nDo you accept?",
            view=view
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ Challenge failed. Player has DMs disabled.")
        await revoke_success(challenge_id)
        return

    # Log in results channel
    challenge_request = None
    rival_results_channel = bot.get_channel(RIVAL_RESULTS_ID)
    if rival_results_channel:
        try:
            challenge_request = await rival_results_channel.send(
                f"{challenger.mention} has issued a challenge to {player.mention} for {pp}pp in {challenger_role} league."
            )
            await store_msg_id(challenge_id, challenge_request.id)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ Could not post to {rival_results_channel.mention}. Check bot permissions.")

    try:
        await view.wait()
    except Exception as e:
        await interaction.followup.send(f"❌ Error while waiting for challenge decision: {e}")
        return

    # Get PP for final message
    try:
        challenger_pp = await get_pp(challenger.name)
        challenged_pp = await get_pp(player.name)
    except Exception as e:
        print(f"PP fetch error: {e}")
        challenger_pp = "?"
        challenged_pp = "?"

    if view.response is None:
        await interaction.followup.send(f"❌ {player.display_name} didn’t respond in time. Challenge expired.")
        if challenge_request:
            await challenge_request.edit(content=f"{challenger.mention}({challenger_pp}) vs {player.mention}({challenged_pp}) | {pp}PP | ❌ No Response")
        await challenge_declined(challenge_id)
    elif view.response:
        await interaction.followup.send(f"✅ {player.mention} accepted your challenge! Type `/show rivals` to view it.")
        await challenge_accepted(challenge_id)
        if challenge_request:
            await challenge_request.edit(content=f"{challenger.mention}({challenger_pp}) vs {player.mention}({challenged_pp}) | {pp}PP | ⏳ Unfinished")
    else:
        await interaction.followup.send(f"❌ {player.display_name} declined your challenge.")
        if challenge_request:
            await challenge_request.edit(content=f"{challenger.mention}({challenger_pp}) vs {player.mention}({challenged_pp}) | {pp}PP | ❌ Declined")
        await challenge_declined(challenge_id)

