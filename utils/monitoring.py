"""
Background monitoring tasks.

This module contains the asynchronous loops that run indefinitely alongside 
the bot. They are responsible for:
1. Monitoring active challenges to detect winners (Rivals).
2. Monitoring the database for new user registrations to assign roles (Welcome).
"""

from .core_v2 import create_supabase, CHALLENGE_STATUS, GUILD_ID, WELCOME_ID
from .db_getter import get_discord_id, get_msg_id
import logging
import asyncio
import discord
from discord.ext import commands
from typing import Any, Dict, List

"""
Functions in this module:
1. monitor_database(bot: commands.Bot, channel_id: int) -> None
2. win(winner: int, id: int) -> Dict[str, Any] | None
3. send_winner_announcement(bot: commands.Bot, channel_id: int, result: Dict, id: int, pp: int) -> None
4. monitor_new_user(bot: commands.Bot) -> None
5. give_role_nickname(discord_id: int, league: str, guild: discord.Guild, osu_username: str) -> None
"""

# Global state to track existing users to prevent re-welcoming them on bot restart.
existing_id = set()
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

async def monitor_new_user(bot: commands.Bot) -> None:
    """
    Background task: Monitors for new users.

    Checks the 'discord_osu' table for new entries. 
    - On startup, it populates a cache of existing users.
    - On subsequent checks, if a new user is found, it assigns them roles 
      and welcomes them in the welcome channel.
    """
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f"Found guild: {guild.name}")
    else:
        print("Guild not found in cache.")
        return # Cannot proceed without guild

    channel = guild.get_channel(WELCOME_ID)
    if channel is None:
        logging.error(f"Could not find channel with ID {WELCOME_ID}")
        print(f"Could not find channel with ID {WELCOME_ID}")

    while True:
        try:
            supabase = await create_supabase()
            try:
                query = await supabase.table('discord_osu').select('discord_id, league').execute()
            except Exception as e:
                print(f"Something wrong at query in monitor_new_user: {e}")
                logging.error(f"Something wrong at query in monitor_new_user: {e}")
                await asyncio.sleep(5)
                continue

            # First run: Populate cache only
            if not init.is_set():
                for data in query.data:
                    existing_id.add(data['discord_id'])
                init.set()
            
            # Subsequent runs: Check for new users
            else:
                for data in query.data:
                    if data['discord_id'] in existing_id:
                        continue
                    else:
                        # New user found
                        try:
                            query_uname = await supabase.table('discord_osu').select('osu_username').eq('discord_id', data['discord_id']).execute()
                            osu_username = query_uname.data[0]['osu_username']
                        except Exception as e:
                            print(f"Failed to query new discord_id: {e}")
                            continue

                        try:
                            await give_role_nickname(data['discord_id'], data['league'], guild, osu_username)
                            if channel:
                                await channel.send(f"<@{data['discord_id']}>, you have been assigned to {data['league'].capitalize()} league.")
                            existing_id.add(data['discord_id'])
                        except Exception as e:
                            logging.error(f"Error inside monitor_new_user logic: {e}")
                            print(f"Error inside add in user: {e}")

            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Error at the end of monitor_new_user(): {e}")
            print(f"Error at the end of monitor_new_user(): {e}")

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
                        



    





    

        