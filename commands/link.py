from utils import serializer, auth, bot, GUILD
import discord
from discord import app_commands


@bot.tree.command(name="link", description="Link your osu! account", guild=GUILD)
async def link(interaction: discord.Interaction):
    user_id = interaction.user.id
    user_name = interaction.user.name
    secret = {"user_id": user_id, "user_name": user_name}
    state = serializer.dumps(secret)
    auth_url = auth.get_auth_url() + f"&state={state}"
    embed = discord.Embed(
        title="Link Your osu! Account",
        description="Click the title to begin linking your account. Please DO NOT share this link.",
        color=discord.Color.blue(),
        url=auth_url,
    )

    try:
        await interaction.user.send(embed=embed)
        await interaction.response.send_message(
            "📬 I’ve sent you a DM with the link!", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ I couldn’t DM you. Please enable DMs from server members.",
            ephemeral=True,
        )
