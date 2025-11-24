from utils import bot, GUILD
import discord

bot.remove_command('help')

@bot.tree.command(name="help", description="Shows all available commands", guild=GUILD)
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📘 Bot Help Menu",
        description="Here's a list of available commands and what they do:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🔗 /link",
        value="Link your osu! account.\n"
              "All users signed up before **June 18, 2025, 22:50 CDT** were linked manually.",
        inline=False
    )

    embed.add_field(
        name="📊 /show [league]",
        value="Shows the table for a specific league.\n"
              "Example: `/show league:Bronze`, `/show league:Silver`, or `/show league:Rivals`\n"
              "Available leagues: `Bronze, Silver, Gold, Platinum, Diamond, Elite, Ranker, Master, Rivals`",
        inline=False
    )

    embed.add_field(
        name="📂 /archived [season] [league]",
        value="View archived tables from previous seasons/ finished challenges.\n"
              "- **season**: Season number (integer).\n"
              "- **league**: League name (e.g., Bronze, Silver, Gold, Rivals).\n"
              "- **Note**: season:0 is the only valid value for leag:Rivals\n"
              "Examples: `/archived season:1 lea:Bronze, /archived season:0 leag:Rivals`\n"
              "Only works for **finished** seasons and challenges.",
        inline=False
    )

    embed.add_field(
        name="⚔️ /challenge @user <pp>",
        value="Challenge a player in your league for a match.\n"
              "- Max **3 active** challenges.\n"
              "- PP must be **250–750**.\n"
              "- You can’t challenge the same player **more than once a day**.\n"
              "- The challenged player gets a DM to accept/decline.\n"
              "Example: `/challenge player:@Rhythmic_Ocean pp:700`",
        inline=False
    )

    embed.add_field(
        name="❌ /revoke_challenge @user",
        value="Revoke a pending challenge you issued to a player.\n"
              "- Only **unaccepted (pending)** challenges can be revoked.\n"
              "- If the challenge has already been accepted, it **cannot** be revoked.\n"
              "Example: `/revoke_challenge player:@Rhythmic_Ocean`",
        inline=False
    )

    embed.add_field(
        name="🛠️ !session_restart",
        value="Admin-only command to reset the current session.",
        inline=False
    )

    embed.set_footer(text="osu!Arena Bot • Created by Rhythmic_Ocean")
    await interaction.response.send_message(embed=embed)

