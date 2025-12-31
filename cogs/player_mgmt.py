from __future__ import annotations
import discord
from discord.ext import commands
from typing import TYPE_CHECKING, Any
from discord import app_commands
import secrets
import time

from itsdangerous import URLSafeSerializer

from load_env import ENV
from utils_v2.enums.status import FuncStatus
from utils_v2.enums.tables_internals import RivalsColumn

if TYPE_CHECKING:
    from bot import OsuArena


class PlayerManagement(commands.Cog):
    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler
        self.osu_auth = self.bot.osu_auth
        self.serializer = URLSafeSerializer(ENV.SEC_KEY)

    @app_commands.command(name="help", description="Shows all available commands")
    async def help(self, interaction: discord.Interaction):
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
            name="🛠️ /session_restart",
            value="**(Admin Only)** Reset the current session, create backups, and reassign users to leagues.",
            inline=False,
        )

        embed.set_footer(text="osu!Arena Bot • Created by Rhythmic_Ocean")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="link", description="Link your osu! account securely")
    async def link(self, interaction: discord.Interaction):
        nonce = secrets.token_urlsafe(8)

        secret = {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "nonce": nonce,
            "created_at": int(time.time()),
        }

        state = self.serializer.dumps(secret)
        auth_url = self.osu_auth.get_auth_url() + f"&state={state}"

        embed = discord.Embed(
            title="Link Your osu! Account",
            description=(
                "Click the link above to log in with osu!.\n"
                "⚠️ **This link expires in 5 minutes.**\n"
                "🔒 **Do not share this link with anyone.**"
            ),
            color=discord.Color.blue(),
            url=auth_url,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="delete", description="Delete player from DB and reset roles to 'casual'."
    )
    @app_commands.describe(player="Intended player to be removed")
    @app_commands.checks.has_any_role(ENV.REQ_ROLE)
    async def delete(self, interaction: discord.Interaction, player: discord.Member):
        await interaction.response.defer()

        # to use  later to revoke rivals, fails silently if no such user exists
        osu_username = await self.db_handler.get_username(discord_id=player.id)

        success = await self.db_handler.remove_player(player.id)

        if not success:
            await interaction.followup.send(
                f"⚠️ **Not Found**: <@{player.id}> was not in the database.",
                ephemeral=True,
            )
            await self.log_handler.report_info(
                f"Attempted to delete non-existent user <@{player.id}>"
            )
            return
        # NOTE: This is only possible because Rivals tables is independent
        # of other tables. If it ever gets foreign keyed, then this will need
        # to be changed

        await interaction.followup.send(
            f"✅ **Deleted**: <@{player.id}> has been wiped from the database."
        )

        role_success = await self._role_nick_deletion(interaction, player)

        if not role_success:
            await interaction.followup.send(
                "⚠️ Database erasure successful, but failed to reset roles/nickname."
            )

        challenges = await self.db_handler.get_active_challenges(
            player.id, osu_username
        )
        if challenges == FuncStatus.ERROR:
            await interaction.followup.send(
                f"⚠️ Failed retriving any existing challenges for <@{player.id}>. Please delete any of their existing challenges manually."
            )
            return

        if not len(challenges):
            await interaction.followup.send(
                f"⚠️ No existing challenges for <@{player.id}>."
            )
            return

        total_revoked_challenges = 0
        for challenge in challenges:
            if await self.revoke_challenge(interaction, challenge):
                total_revoked_challenges += 1
        await interaction.followup.send(
            f"⚠️{total_revoked_challenges}/{len(challenges)} challenges revoked."
        )

    async def revoke_challenge(
        self, interaction: discord.Interaction, challenge: dict[str, Any]
    ):
        challenger = challenge[RivalsColumn.CHALLENGER]
        challenged = challenge[RivalsColumn.CHALLENGED]
        challenge_id = challenge[RivalsColumn.CHALLENGE_ID]

        revoke_success = await self.db_handler.revoke_challenge(challenge_id)
        if not revoke_success:
            error = Exception(
                f"Failed to revoke challenge, challenge_id : {challenge_id}. {challenger} vs {challenged}"
            )
            await self.log_handler.report_error(
                "PlayerManagement.revoke_challenge()",
                error,
            )
            return False

        msg_id = await self.db_handler.get_msg_id(challenge_id)
        guild = interaction.guild
        channel = guild.get_channel(ENV.RIVAL_RESULTS_ID)

        if not channel:
            return True
        new_content = f"{challenger} vs {challenged} | Revoked"
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                if msg:
                    await msg.edit(content=new_content)
            except discord.NotFound:
                await channel.send(content=new_content)
        return True

    async def _role_nick_deletion(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        guild = interaction.guild
        if not guild or not member:
            return False

        casual_role = discord.utils.get(guild.roles, name="casual")
        if not casual_role:
            await self.log_handler.report_error(
                "PlayerManagement",
                Exception("Role 'casual' not found"),
                "Config Error",
            )
            return False

        try:
            await member.edit(nick=None, roles=[casual_role])
            self.log_handler.report_info(f"Reset nickname and roles for <@{member.id}>")
            return True

        except discord.Forbidden:
            await interaction.followup.send(
                f"⚠️ Bot lacks permission to manage <@{member.id}> (User might be Admin or above Bot)."
            )
            return False

        except Exception as error:
            await self.log_handler.report_error(
                "PlayerManagement._role_nick_deletion()",
                error,
                f"Failed resetting roles/nick for <@{member.id}>",
            )
            return False

    @delete.error
    async def delete_error(self, interaction: discord.Interaction, error):
        sender = (
            interaction.followup.send
            if interaction.response.is_done()
            else interaction.response.send_message
        )

        if isinstance(error, app_commands.MissingAnyRole):
            await sender("❌ **Access Denied.** Admin role required.", ephemeral=True)
            await self.log_handler.report_info(
                f"<@{interaction.user.id}> unauthorized access to /delete"
            )
        else:
            await self.log_handler.report_error(
                "PlayerManagement.delete_error()", error
            )
            await sender("❌ An unexpected error occurred.", ephemeral=True)


async def setup(bot: OsuArena):
    bot.remove_command("help")
    await bot.add_cog(PlayerManagement(bot))
