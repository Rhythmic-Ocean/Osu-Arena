from utils import bot, check_pending, revoke_success, get_msg_id, RIVAL_RESULTS_ID, GUILD
import discord
from discord import app_commands

@bot.tree.command(name="revoke_challenge", description="Revoke a pending challenge with another player.", guild=GUILD)
@app_commands.describe(player="The player you want to revoke your challenge with.")
async def revoke_challenge(interaction: discord.Interaction, player: discord.Member):
    challenger = interaction.user
    challenged = player
    await interaction.response.defer()

    checking = await check_pending(challenger.name, challenged.name)
    if checking is None:
        await interaction.followup.send(
            f"{challenger.mention}, you have no pending challenges with {challenged.mention}."
        )
        return

    try:
        try:
            msg_id = await get_msg_id(checking)
            channel = bot.get_channel(RIVAL_RESULTS_ID)
            if channel is None:
                await interaction.followup.send("Could not find the #rival-result channel.")
                return
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=f"{challenger.mention} vs {player.mention} | Challenge Revoked")
        except Exception as e:
            await interaction.followup.send(f"Failed to update message in #rival-result. Error: {e}")
            return

        await revoke_success(checking)
        await interaction.followup.send(
            f"{challenger.mention}, your challenge to {challenged.mention} has been revoked successfully."
        )

        try:
            await challenged.send(
                f"{challenger.mention} has revoked the previous challenge. Any interaction with the above interface WILL be invalid."
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"{challenged.mention} has DMs disabled. Could not notify them."
            )

    except Exception as e:
        await interaction.followup.send(f"Error in challenge deletion: {e}")
