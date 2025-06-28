from core_v2 import create_supabase, CHALLENGE_STATUS, get_discord_id, get_msg_id
import logging
import asyncio


logging.basicConfig(filename="monitoring.log", level=logging.DEBUG, filemode='w')

async def monitor_database(bot, channel_id):
    while True:
        try:
            supabase = await create_supabase()
            query = await supabase.table('rivals').select(
            'challenger, challenged,challenge_id, for_pp, challenger_status, challenged_status'
            ).eq('challenge_status', CHALLENGE_STATUS[3]).execute()
            datas = query.data

            for data in datas:
                if data['for_pp'] <= data['challenger_status']:
                    winner = data['challenger']
                    result = await win(winner, data['challenge_id'])
                    await send_winner_announcement(bot, channel_id, result, data['challenge_id'], data['for_pp'])
                elif data['for_pp'] <= data['challenged_status']:
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
    




    

        