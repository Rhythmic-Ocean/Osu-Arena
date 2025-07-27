from core_v2 import create_supabase, CHALLENGE_STATUS, get_discord_id, get_msg_id, GUILD_ID, WELCOME_ID
import logging
import asyncio
import discord


existing_id = set()

init = asyncio.Event()


logging.basicConfig(filename="monitoring.log", level=logging.DEBUG, filemode='w')

async def monitor_database(bot, channel_id):
    while True:
        try:
            supabase = await create_supabase()
            try:
                query = await supabase.table('rivals').select(
                'challenger, challenged,challenge_id, for_pp, challenger_stats, challenged_stats'
                ).eq('challenge_status', CHALLENGE_STATUS[3]).execute()
                datas = query.data
            except Exception as e:
                print("Exception as {}",e)


            for data in datas:
                if data['for_pp'] <= data['challenger_stats']:
                    winner = data['challenger']
                    result = await win(winner, data['challenge_id'])
                    await send_winner_announcement(bot, channel_id, result, data['challenge_id'], data['for_pp'])
                elif data['for_pp'] <= data['challenged_stats']:
                    winner = data['challenged']
                    result = await win(winner, data['challenge_id'])
                    await send_winner_announcement(bot, channel_id, result, data['challenge_id'], data['for_pp'])
        except Exception as e:
            logging.error(f"Error at monitor_database: {e}")

        await asyncio.sleep(10) 

async def win(winner, id):
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
    


async def send_winner_announcement(bot, channel_id, result, id, pp):
    if not result:
        return
    challenger = await get_discord_id(result['challenger'])
    challenged = await get_discord_id(result['challenged'])
    winner = await get_discord_id(result['winner'])
    msg_id = await get_msg_id(id)
    channel =  bot.get_channel(channel_id)
    if channel:
        if msg_id is None:
            await channel.send(
               f"<@{challenger}> vs <@{challenged}>|{pp}PP|Finished. WINNER: <@{winner}>"
            )
        else:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=f"<@{challenger}> vs <@{challenged}> |{pp}PP| Finished. WINNER: <@{winner}>")  

    if not channel:
        return      

async def monitor_new_user(bot):
    guild = bot.get_guild(GUILD_ID)
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
                print(f"something wrong at query in monitor_new_user at monitoring.py: {e}")
                logging.error(f"something wrong at query in monitor_new_user at monitoring.py: {e}")
            if not init.is_set():
                for data in query.data:
                    existing_id.add(data['discord_id'])
                init.set()
            else:
                for data in query.data:
                    if data['discord_id'] in existing_id:
                        continue
                    else:
                        try:
                            query = await supabase.table('discord_osu').select('osu_username').eq('discord_id', data['discord_id']).execute()
                            osu_username = query.data[0]['osu_username']
                        except Exception as e:
                            print(f"Failed to query new discord_id: {e}")
                        try:
                            await give_role_nickname (data['discord_id'], data['league'], guild, osu_username)
                            await channel.send(f"<@{data['discord_id']}>, you have been assigned to {data['league'].capitalize()} league.")
                            existing_id.add(data['discord_id'])
                        except Exception as e:
                            logging.error(f"Error inside monitor_new_user: {e}")
                            print(f"Error inside add in user: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Error at the end of monitor_new_user(): {e}")
            print(f"Error at the end of monitor_new_user(): {e}")




async def give_role_nickname (discord_id, league, guild, osu_username):
    member = await guild.fetch_member(discord_id)
    role = discord.utils.get(guild.roles, name = league.capitalize())
    role_part = discord.utils.get(guild.roles, name = 'Participant')
    try:
        await member.add_roles(role)
        await member.add_roles(role_part)
    except Exception as e:
        logging.error(f"Error adding role: {e}")
        print(f"Error adding role: {e}")

    try:
        await member.edit(nick = osu_username)
    except Exception as e:
        logging.error(f"Error changing nickname {e}")
        print (f"Error changing nickname {e}")

                        



    





    

        