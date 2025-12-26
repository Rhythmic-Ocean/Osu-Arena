import discord
from .core_v2 import create_supabase, bot, GUILD_ID


async def remove_player(discord_id: int) -> bool:
    """
    1. Removes player from 'discord_osu' table.
    2. If successful, strips ALL roles and assigns 'Casual'.
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
                        print(f"User {discord_id} left server, skipping role strip.")
                        member = None

                if member:
                    casual_role = discord.utils.get(guild.roles, name="Casual")

                    if casual_role:
                        await member.edit(roles=[casual_role])
                        print(f"✅ Stripped roles for {member.name}, gave 'Casual'.")
                    else:
                        print("⚠️ Warning: 'Casual' role not found in server.")

        except discord.Forbidden:
            print(
                f"❌ Bot lacks permissions to strip roles from {discord_id} (Target might be Admin)."
            )
        except Exception as e:
            print(f"⚠️ Discord error during delete: {e}")

        return True

    except Exception as e:
        print(f"Error manually deleting player {discord_id}: {e}")
        return False
