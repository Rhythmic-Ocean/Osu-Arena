"""
Background monitoring tasks.

This module contains the asynchronous loops that run indefinitely alongside 
the bot. They are responsible for:
1. Monitoring active challenges to detect winners (Rivals).
2. Monitoring the database for new user registrations to assign roles (Welcome).
"""

from .core_v2 import create_supabase, CHALLENGE_STATUS, GUILD_ID, WELCOME_ID, TOP_PLAY_ID
from osu import Client, GameModeStr
import os
from .db_getter import get_discord_id, get_msg_id
import logging
import asyncio
import discord
from discord.ext import commands
from typing import Any, Dict, List
from osu import SoloScore, LegacyScore
from dotenv import load_dotenv

load_dotenv(dotenv_path="sec.env")
redirect_url = "http://127.0.0.1:8080"  # not used directly, fine to keep

OSU_CLIENT_ID = os.getenv("OSU_CLIENT2_ID")
OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT2_SECRET")

client_updater = Client.from_credentials(OSU_CLIENT_ID,
                                             OSU_CLIENT_SECRET,
                                             redirect_url)

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

logging.basicConfig(filename="monitoring.log", level=logging.DEBUG, filemode='w')

async def monitor_database(bot: commands.Bot, channel_id: int) -> None:
    """
    Background task: Monitors active challenges.

    Continuously polls the 'rivals' table for challenges with 'Unfinished' status.
    It compares the current stats (pp_change since challenge's start) of the players against the 'for_pp' target.
    If current_stats is greater than for_pp for any of the two players, it updates the database and triggers an announcement.

    Args:
        bot (commands.Bot): The active bot instance.
        channel_id (int): The ID of the channel to send results to.
    """
    while True:
        try:
            supabase = await create_supabase()
            try:
                query = await supabase.table('rivals').select(
                    'challenger, challenged, challenge_id, for_pp, challenger_stats, challenged_stats'
                ).eq('challenge_status', CHALLENGE_STATUS[3]).execute()
                datas = query.data
            except Exception as e:
                print(f"Exception fetching rivals: {e}")
                datas = []

            for data in datas:
                # Check if Challenger won
                if data['for_pp'] <= data['challenger_stats']:
                    winner = data['challenger']
                    result = await win(winner, data['challenge_id'])
                    await send_winner_announcement(bot, channel_id, result, data['challenge_id'], data['for_pp'])
                
                # Check if Challenged won
                elif data['for_pp'] <= data['challenged_stats']:
                    winner = data['challenged']
                    result = await win(winner, data['challenge_id'])
                    await send_winner_announcement(bot, channel_id, result, data['challenge_id'], data['for_pp'])

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
        await supabase.table('rivals').update({
            'challenge_status': CHALLENGE_STATUS[4],
            'winner': winner
        }).eq('challenge_id', id).execute()
        
        result = await supabase.table('rivals').select('challenger, challenged, winner').eq('challenge_id', id).single().execute()
        return result.data
    except Exception as e:
        logging.error(f"Error at win: {e}")
        return None

async def send_winner_announcement(bot: commands.Bot, channel_id: int, result: Dict, id: int, pp: int) -> None:
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
        
    challenger = await get_discord_id(result['challenger'])
    challenged = await get_discord_id(result['challenged'])
    winner = await get_discord_id(result['winner'])
    
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
                await msg.edit(content=f"<@{challenger}> vs <@{challenged}> | {pp}PP | Finished. WINNER: <@{winner}>")  
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
            response = await supabase.table('discord_osu')\
                .select("discord_id, league, osu_id, osu_username")\
                .eq("new_player_announce", True)\
                .execute()

            for data in response.data:
                discord_id = data['discord_id']
                osu_username = data.get('osu_username', 'Unknown')

                # 1. Turn off the flag in DB immediately
                try:
                    await supabase.table("discord_osu").update({
                        "new_player_announce": False
                    }).eq("osu_id", data['osu_id']).execute()
                except Exception as e:
                    logging.error(f"Failed to update DB for new player {osu_username}: {e}")
                    continue 

                # 2. Assign Role & Welcome
                try:
                    await give_role_nickname(discord_id, data['league'], guild, osu_username)
                    if channel:
                        await channel.send(f"<@{discord_id}>, you have been assigned to {data['league'].capitalize()} league.")
                    
                    logging.info(f"Processed new player: {osu_username}")
                except Exception as e:
                    logging.error(f"Error executing logic for new player {osu_username}: {e}")

        except Exception as e:
            print(f"Error in monitor_new_players loop: {e}")
        
        await asyncio.sleep(5)



async def give_role_nickname(discord_id: int, league: str, guild: discord.Guild, osu_username: str) -> None:
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
    role_part = discord.utils.get(guild.roles, name='Participant')
    
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
            response = await supabase.table('discord_osu')\
                .select("discord_id, osu_username, osu_id, top_play_id")\
                .eq("top_play_announce", True)\
                .execute()

            for data in response.data:
                osu_username = data.get('osu_username', 'Unknown')
                top_play_id = data['top_play_id']
                print(top_play_id)
                top_play  = client_updater.get_score_by_id_only(top_play_id)
                title = top_play.beatmapset.title
                # 1. Turn off the flag in DB
                try:
                    await supabase.table("discord_osu").update({
                        "top_play_announce": False
                    }).eq("osu_id", data['osu_id']).execute()
                except Exception as e:
                    print(f"Failed to update DB for top player {osu_username}: {e}")
                    continue

                # 2. Announce Achievement
                try:
                    if channel:
                        await channel.send(f"<@{data['discord_id']}> has a new Top play on {title}! : {int(top_play.pp) if top_play else 0}pp")
                    logging.info(f"Announced top player: {osu_username}")
                except Exception as e:
                    logging.error(f"Error announcing top player {osu_username}: {e}")

        except Exception as e:
            print(f"Error in monitor_top_players loop: {e}")

        await asyncio.sleep(5)


                        



    



        