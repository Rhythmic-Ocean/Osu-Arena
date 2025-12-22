"""
Background monitoring tasks.

This module contains the asynchronous loops that run indefinitely alongside
the bot. They are responsible for:
1. Monitoring active challenges to detect winners (Rivals).
2. Monitoring the database for new user registrations to assign roles (Welcome).
"""

import datetime
import supabase
from werkzeug.wrappers import response
import supaabse
from zoneinfo import ZoneInfo
from .core_v2 import (
    create_supabase,
    CHALLENGE_STATUS,
    GUILD_ID,
    WELCOME_ID,
    TOP_PLAY_ID,
    LEAGUE_MODES,
)
from osu import Client
import os
from .db_getter import get_discord_id, get_msg_id, get_pp
import logging
import asyncio
import discord
from discord.ext import commands
from typing import Any, Dict, List
from osu import SoloScore, LegacyScore
from dotenv import load_dotenv
from .challenge_final import challenge_finish_point_distribution

load_dotenv(dotenv_path="sec.env")
redirect_url = "http://127.0.0.1:8080"  # not used directly, fine to keep


last_checked_date = None
cached_status = False

OSU_CLIENT_ID = os.getenv("OSU_CLIENT2_ID")
OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT2_SECRET")

client_updater = Client.from_credentials(OSU_CLIENT_ID, OSU_CLIENT_SECRET, redirect_url)

"""
Functions in this module:
1. monitor_database(bot: commands.Bot, channel_id: int) -> None
2. win(winner: int, id: int) -> Dict[str, Any] | None
3. send_winner_announcement(bot: commands.Bot, channel_id: int, result: Dict, id: int, pp: int) -> None
4. monitor_new_user(bot: commands.Bot) -> None
5. give_role_nickname(discord_id: int, league: str, guild: discord.Guild, osu_username: str) -> None
"""

# Global state to track existing users to prevent re-welcoming them on bot restart.
init = asyncio.Event()

logging.basicConfig(filename="monitoring.log", level=logging.DEBUG, filemode="w")


async def monitor_database(bot: commands.Bot, channel_id: int) -> None:
    """
    Background task: Monitors active challenges.

    Updates weekly points every Sunday, once
    Continuously polls the 'rivals' table for challenges with 'Unfinished' status.
    It compares the current stats (pp_change since challenge's start) of the players against the 'for_pp' target.
    If current_stats is greater than for_pp for any of the two players, it updates the database and triggers an announcement.

    Args:
        bot (commands.Bot): The active bot instance.
        channel_id (int): The ID of the channel to send results to.
    """
    while True:
        try:
            if await to_trigger():
                await weekly_point_update(bot)
        except Exception as e:
            print(f"Error in weekly trigger check: {e}")
        try:
            supabase = await create_supabase()
            try:
                query = (
                    await supabase.table("rivals")
                    .select(
                        "challenger, challenged, challenge_id, for_pp, challenger_stats, challenged_stats"
                    )
                    .eq("challenge_status", CHALLENGE_STATUS[3])
                    .execute()
                )
                datas = query.data
            except Exception as e:
                print(f"Exception fetching rivals: {e}")
                datas = []

            for data in datas:
                for_pp = data["for_pp"]
                # Check if Challenger won
                if for_pp <= data["challenger_stats"]:
                    winner = data["challenger"]
                    loser = data["challenged"]
                    result = await win(winner, data["challenge_id"])
                    await send_winner_announcement(
                        bot, channel_id, result, data["challenge_id"], data["for_pp"]
                    )
                    challenge_finish_point_distribution(winner, loser, for_pp)

                # Check if Challenged won
                elif for_pp <= data["challenged_stats"]:
                    winner = data["challenged"]
                    loser = data["challenger"]
                    result = await win(winner, data["challenge_id"])
                    await send_winner_announcement(
                        bot, channel_id, result, data["challenge_id"], data["for_pp"]
                    )
                    challenge_finish_point_distribution(winner, loser, for_pp)

        except Exception as e:
            logging.error(f"Error at monitor_database: {e}")

        await asyncio.sleep(10)


async def win(winner: int, id: int) -> Dict[str, Any] | None:
    """
    Updates the database when a challenge is won.

    Sets the challenge status to 'Finished' and records the winner.

    Args:
        winner (int): The osu! username/identifier of the winner.
        id (int): The challenge ID.

    Returns:
        Dict | None: The updated row data if successful, None otherwise.
    """
    supabase = await create_supabase()
    try:
        await (
            supabase.table("rivals")
            .update({"challenge_status": CHALLENGE_STATUS[4], "winner": winner})
            .eq("challenge_id", id)
            .execute()
        )

        result = (
            await supabase.table("rivals")
            .select("challenger, challenged, winner")
            .eq("challenge_id", id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        logging.error(f"Error at win: {e}")
        return None


async def send_winner_announcement(
    bot: commands.Bot, channel_id: int, result: Dict, id: int, pp: int
) -> None:
    """
    Announces the winner of a challenge in the corresponding discord channe(Rival results here).

    If the original challenge message exists, it edits it.
    Otherwise, it sends a new message.

    Args:
        bot (commands.Bot): The bot instance.
        channel_id (int): The channel to post/edit the message.
        result (Dict): The challenge data containing winner/loser details.
        id (int): The challenge ID.
        pp (int): The PP threshold of the challenge.
    """
    if not result:
        return

    challenger = await get_discord_id(result["challenger"])
    challenged = await get_discord_id(result["challenged"])
    winner = await get_discord_id(result["winner"])

    msg_id = await get_msg_id(id)
    channel = bot.get_channel(channel_id)

    if channel:
        if msg_id is None:
            await channel.send(
                f"<@{challenger}> vs <@{challenged}> | {pp}PP | Finished. WINNER: <@{winner}>"
            )
        else:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(
                    content=f"<@{challenger}> vs <@{challenged}> | {pp}PP | Finished. WINNER: <@{winner}>"
                )
            except discord.NotFound:
                # Message was deleted, send a new one
                await channel.send(
                    f"<@{challenger}> vs <@{challenged}> | {pp}PP | Finished. WINNER: <@{winner}>"
                )


async def monitor_new_players(bot: commands.Bot) -> None:
    """
    Background task: Checks for 'new_player_announce' = True
    """
    await bot.wait_until_ready()

    guild = bot.get_guild(GUILD_ID)
    print(guild)
    if not guild:
        print("monitor_new_players: Guild not found.")
        return

    channel = guild.get_channel(WELCOME_ID)
    supabase = await create_supabase()
    print("Started New Player Monitor.")

    while True:
        try:
            # Query only users marked for new player announcement
            response = (
                await supabase.table("discord_osu")
                .select("discord_id, league, osu_id, osu_username")
                .eq("new_player_announce", True)
                .execute()
            )

            for data in response.data:
                discord_id = data["discord_id"]
                osu_username = data.get("osu_username", "Unknown")

                # 1. Turn off the flag in DB immediately
                try:
                    await (
                        supabase.table("discord_osu")
                        .update({"new_player_announce": False})
                        .eq("osu_id", data["osu_id"])
                        .execute()
                    )
                except Exception as e:
                    logging.error(
                        f"Failed to update DB for new player {osu_username}: {e}"
                    )
                    continue

                # 2. Assign Role & Welcome
                try:
                    await give_role_nickname(
                        discord_id, data["league"], guild, osu_username
                    )
                    if channel:
                        await channel.send(
                            f"<@{discord_id}>, you have been assigned to {data['league'].capitalize()} league."
                        )

                    logging.info(f"Processed new player: {osu_username}")
                except Exception as e:
                    logging.error(
                        f"Error executing logic for new player {osu_username}: {e}"
                    )

        except Exception as e:
            print(f"Error in monitor_new_players loop: {e}")

        await asyncio.sleep(5)


async def give_role_nickname(
    discord_id: int, league: str, guild: discord.Guild, osu_username: str
) -> None:
    """
    Assigns league roles and updates the nickname for a user.

    Args:
        discord_id (int): The user's Discord ID.
        league (str): The league name (e.g., 'gold').
        guild (discord.Guild): The guild object.
        osu_username (str): The new nickname to set.
    """
    member = await guild.fetch_member(discord_id)
    role = discord.utils.get(guild.roles, name=league.capitalize())
    role_part = discord.utils.get(guild.roles, name="Participant")

    try:
        # Remove 'Inactive' role if present
        for role_m in member.roles:
            if role_m.name == "Inactive":
                await member.remove_roles(role_m)

        if role:
            await member.add_roles(role)
        if role_part:
            await member.add_roles(role_part)

    except Exception as e:
        logging.error(f"Error adding/removing roles: {e}")
        print(f"Error adding/removing roles: {e}")

    try:
        await member.edit(nick=osu_username)
    except Exception as e:
        logging.error(f"Error changing nickname: {e}")
        print(f"Error changing nickname: {e}")


async def monitor_top_plays(bot: commands.Bot) -> None:
    """
    Background task: Checks for 'top_player_announce' = True
    """
    await bot.wait_until_ready()

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("monitor_top_players: Guild not found.")
        return

    # You might want a different channel for achievements?
    # If using the same welcome channel:
    channel = guild.get_channel(TOP_PLAY_ID)

    supabase = await create_supabase()
    print("Started Top Player Monitor.")

    while True:
        try:
            # Query only users marked for top player announcement
            response = (
                await supabase.table("discord_osu")
                .select("discord_id, osu_username, osu_id, top_play_id")
                .eq("top_play_announce", True)
                .execute()
            )

            for data in response.data:
                discord_id = data.get("discord_id", 0)
                osu_username = data.get("osu_username", "Unknown")
                top_play_id = data["top_play_id"]
                print(top_play_id)
                top_play = client_updater.get_score_by_id_only(top_play_id)
                title = top_play.beatmapset.title
                # 1. Turn off the flag in DB
                try:
                    await (
                        supabase.table("discord_osu")
                        .update({"top_play_announce": False})
                        .eq("osu_id", data["osu_id"])
                        .execute()
                    )
                except Exception as e:
                    print(f"Failed to update DB for top player {osu_username}: {e}")
                    continue

                # 2. Announce Achievement
                embed = await create_score_embed(top_play)
                content_str = (
                    f"New Top Play from <@{discord_id}>!"
                    if discord_id
                    else "New Top Play!"
                )
                try:
                    if channel:
                        await channel.send(content=content_str, embed=embed)
                    logging.info(f"Announced top player: {osu_username}")
                except Exception as e:
                    logging.error(f"Error announcing top player {osu_username}: {e}")

        except Exception as e:
            print(f"Error in monitor_top_players loop: {e}")

        await asyncio.sleep(5)


async def create_score_embed(play: SoloScore | LegacyScore):
    user = play.user
    beatmap = play.beatmap
    beatmapset = play.beatmapset
    base = 127397

    # cuz it's compact type, so sometime stats and country code might not get thru
    if user.statistics is None or user.country_code is None:
        try:
            user = client_updater.get_user(user.id, mode="osu")
        except Exception as e:
            print(f"Could not fetch full user: {e}")

    if isinstance(play, SoloScore):
        # Lazer / SoloScore
        played_date = play.ended_at
        score_val = play.total_score
        accuracy = play.accuracy * 100
        mod_acronyms = [m.mod.value for m in play.mods]
        combo = play.max_combo
        pp = play.pp if play.pp else 0
        misses = getattr(play.statistics, "miss", 0)
        rank_str = play.rank.name
    else:
        played_date = play.created_at
        score_val = play.score
        accuracy = play.accuracy * 100
        mod_acronyms = [m.value for m in play.mods]
        combo = play.max_combo
        pp = play.pp if play.pp else 0
        misses = play.statistics.count_miss
        rank_str = play.rank.name
    mods = "+" + "".join(mod_acronyms) if mod_acronyms else "+NM"

    ts = int(played_date.timestamp())
    time_ago = f"<t:{ts}:R>"  # "2 hours ago"

    map_link = f"https://osu.ppy.sh/b/{beatmap.id}"
    user_link = f"https://osu.ppy.sh/u/{user.id}"
    cover_url = beatmapset.covers.list_2x

    try:
        total_pp = user.statistics.pp
        global_rank = (
            f"#{user.statistics.global_rank}" if user.statistics.global_rank else "-"
        )
        country_code = user.country_code
        country_rank = user.statistics.country_rank
        flag = "".join(chr(base + ord(c)) for c in country_code.upper())
    except AttributeError:
        total_pp = 0
        global_rank = "-"
        country_code = "??"
        country_rank = 0
        flag = "🏳️"

    m, s = divmod(beatmap.total_length, 60)
    length_str = f"{m:02d}:{s:02d}"

    embed = discord.Embed(color=0x2ECC71)

    author_text = f"{flag} {user.username}: {total_pp:,.0f}pp ({global_rank} {country_code}{country_rank})"
    embed.set_author(name=author_text, url=user_link, icon_url=user.avatar_url)

    embed.title = f"{beatmapset.artist} - {beatmapset.title} [{beatmap.version}] [{beatmap.difficulty_rating:.2f}★]"
    embed.url = map_link

    grade_map = {
        "XH": "<:XH:1449232200368259265>",
        "X": "<:X_:1449232164771332096>",
        "SH": "<:SH:1449232118751297670>",
        "S": "<:S_:1449232073779974194>",
        "A": "<:A_:1449231818392998030>",
        "B": "<:B_:1449231894368485528>",
        "C": "<:C_:1449231970126135438>",
        "D": "<:D_:1449232012341674085>",
        "F": "💔",
    }
    grade_emoji = grade_map.get(rank_str, "❓")

    description = (
        f"__**New Top Play**__\n"
        f"{grade_emoji} **{mods}** • {score_val:,} • **{accuracy:.2f}%** • {time_ago}\n"
        f"**{pp:.2f}**pp • **{combo}x**/{beatmap.max_combo}x • {misses} ❌\n"
        f"`{length_str}` • BPM: `{beatmap.bpm}` • CS: `{beatmap.cs}` AR: `{beatmap.ar}` OD: `{beatmap.accuracy}` HP: `{beatmap.drain}`"
    )
    embed.description = description

    if cover_url:
        embed.set_thumbnail(url=cover_url)

    embed.set_footer(
        text=f"Mapset by {beatmapset.creator} • Status: {beatmapset.status.name.capitalize()}"
    )

    return embed


async def weekly_point_update(bot):
    await bot.wait_until_ready()

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("monitor_top_players: Guild not found.")
        return

    channel = guild.get_channel(1398919513877250129)
    weekly_point_update_supabase = await create_supabase()

    try:
        for a_league in LEAGUE_MODES.values():
            try:
                # Sync the league table first
                await weekly_point_update_supabase.rpc(
                    "sync_table_pp", {"tbl_name": a_league}
                ).execute()
            except Exception as e:
                print(f"Error sync leagues: {e}")
                continue

            # Call the award function
            response = await weekly_point_update_supabase.rpc(
                "award_weekly_winner", {"league_table_name": a_league}
            ).execute()

            datas = response.data

            if datas and channel:
                for row in datas:
                    # 1. Parse the dictionary keys returned by Postgres
                    u_name = row["osu_username"]
                    total_points = row["new_points"]
                    seasonal_points = row["new_seasonal_points"]

                    # 2. Get Discord ID for the ping
                    discord_id = await get_discord_id(u_name)

                    # 3. Create a nice formatted message
                    message = (
                        f"🏆 **Weekly Winner: {a_league}**\n"
                        f"Congratulations <@{discord_id}>! You've been awarded **+100 points**.\n"
                        f"> **Total Points:** {total_points}\n"
                        f"> **Seasonal Points:** {seasonal_points}"
                    )

                    await channel.send(content=message)

            print(f"Updated this weeks winner points for {a_league}.")

    except Exception as e:
        print(f"Error at function weekly_point_update() : {e}")


async def to_trigger():
    global last_checked_date, cached_status
    cdt_time = datetime.datetime.now(ZoneInfo("America/Chicago"))
    trigger_check_supabase = await create_supabase()
    today = cdt_time.weekday()
    if last_checked_date != today:
        try:
            response = (
                await trigger_check_supabase.table("miscellaneous")
                .select("status")
                .eq("variable", "done_updating_weekly_point")
                .execute()
            )
            if response.data:
                cached_status = response.data[0]["status"]
                last_checked_date = today  # Mark this day as synced
                print(f"Daily Sync: Database says status is {cached_status}")
        except Exception as e:
            print(f"Error syncing with DB: {e}")
            return False  # Fail safe
    if today == 0:
        if not cached_status:
            try:
                await (
                    trigger_check_supabase.table("miscellaneous")
                    .update({"status": True})
                    .eq("variable", "done_updating_weekly_point")
                    .execute()
                )
                cached_status = True
                return True
            except Exception as e:
                print(f"Error putting done_updating_weekly_points to True {e}")
                return False
    else:
        if cached_status:
            await (
                trigger_check_supabase.table("miscellaneous")
                .update({"status": False})
                .eq("variable", "done_updating_weekly_point")
                .execute()
            )
            cached_status = False
            print("Reset weekly status to False for the new week.")
    return False
