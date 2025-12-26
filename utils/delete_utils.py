import discord
from .core_v2 import create_supabase, bot, GUILD_ID


async def remove_player(discord_id: int) -> bool:
    """
    1. Deletes user from Supabase.
    2. If successful, strips ALL roles (except managed ones) and assigns 'Casual'.
    3. Resets their server nickname.
    """
    supabase = await create_supabase()
    try:
        response = await (
            supabase.table("discord_osu")
            .delete()
            .eq("discord_id", discord_id)
            .execute()
        )

        if not response.data:
            return False

        try:
            guild = bot.get_guild(GUILD_ID)
            if guild:
                member = guild.get_member(discord_id)
                if not member:
                    try:
                        member = await guild.fetch_member(discord_id)
                    except discord.NotFound:
                        print(
                            f"User {discord_id} left server, skipping Discord cleanup."
                        )
                        member = None

                if member:
                    casual_role = discord.utils.get(guild.roles, name="casual")

                    if casual_role:
                        await member.edit(nick=None, roles=[casual_role])
                        print(
                            f"✅ Wiped roles & nick for {member.name}, set to 'Casual'."
                        )
                    else:
                        print("⚠️ Warning: 'Casual' role not found in server.")

        except discord.Forbidden:
            print(
                f"❌ Bot lacks permission to manage {discord_id} (User might be Admin or higher than Bot)."
            )
        except Exception as e:
            print(f"⚠️ Discord error during cleanup: {e}")

        return True

    except Exception as e:
        print(f"Error manually deleting player {discord_id}: {e}")
        return False
