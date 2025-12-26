from utils import bot, GUILD
import discord


@bot.tree.command(name="help", description="Shows all available commands", guild=GUILD)
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📘 Bot Help Menu",
        description="Here's a list of available slash commands and what they do:",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="🔗 /link",
        value="Link your osu! account securely via OAuth2.\n"
        "All users signed up before **June 18, 2025, 22:50 CDT** were linked manually.",
        inline=False,
    )

    embed.add_field(
        name="📊 /show [league]",
        value="Shows the table for a specific league.\n"
        "**Leagues**: `Novice, Bronze, Silver, Gold, Platinum, Diamond, Elite, Master`\n"
        "**Misc Tables**: `Rivals`, `Points`, `S_points`\n"
        "*(Note: Ranker league is deprecated)*\n"
        "Example: `/show league:Bronze` or `/show league:S_points`",
        inline=False,
    )

    embed.add_field(
        name="📂 /archived [season] [league]",
        value="View tables from previous seasons/finished challenges.\n"
        "- **season**: Integer (e.g., 1, 3).\n"
        "- **league**: League name (e.g., Bronze, S_points).\n"
        "- **Special Rules**:\n"
        "  • `season:0` is only valid for `leag:Rivals`.\n"
        "  • `Ranker` only available for `season:1`.\n"
        "  • `S_points` archives start from `season:3`.\n"
        "  • Universal `Points` cannot be archived.\n"
        "Example: `/archived season:3 leag:S_points`",
        inline=False,
    )

    embed.add_field(
        name="⚔️ /challenge @user <pp>",
        value="Challenge a player in your league for a match.\n"
        "- Max **3 active** challenges.\n"
        "- PP must be **250–750**.\n"
        "- You can’t challenge the same player **more than once a day**.\n"
        "- Challenge expires in **10 mins** if not accepted.\n"
        "Example: `/challenge player:@Rhythmic_Ocean pp:700`",
        inline=False,
    )

    embed.add_field(
        name="❌ /revoke_challenge @user",
        value="Revoke a pending challenge you issued.\n"
        "- Only **unaccepted (pending)** challenges can be revoked.\n"
        "Example: `/revoke_challenge player:@Rhythmic_Ocean`",
        inline=False,
    )

    embed.add_field(
        name="⚖️ /points @user [points]",
        value="**(Restricted)** Add/remove points for any user.\n"
        "- Affects both seasonal and universal points.\n"
        "- Only usable by Admin and Speed-rank-judge.",
        inline=False,
    )

    embed.add_field(
        name="🗑️ /delete @user",
        value="**(Admin Only)** Forcefully delete a player from the database.\n"
        "- Wipes all user data (Rivals, history, etc).\n"
        "- Strips league roles and assigns **Casual** role.",
        inline=False,
    )

    embed.add_field(
        name="🛠️ /session_restart",
        value="**(Admin Only)** Reset the current session, create backups, and reassign users to leagues.",
        inline=False,
    )

    embed.set_footer(text="osu!Arena Bot • Created by Rhythmic_Ocean")
    await interaction.response.send_message(embed=embed)
