import logging
from .core_v2 import create_supabase, TABLE_MODES
from .db_getter import get_pp, get_osu_uname

logging.basicConfig(filename= "reset_utils.py", level= logging.DEBUG, filemode= 'w')

async def update_init_pp(league):
    supabase = await create_supabase()
    try:
        await supabase.rpc("update_init_pp",{"tbl_name": league}).execute()
    except Exception as e:
        print(f"error updating init pp: {e}")
        return 
    
async def update_leagues():
    supabase = await create_supabase()
    print("here")
    players = []
    try:
        query = await supabase.table('discord_osu').select('discord_username, discord_id, league, future_league').execute()
        datas = query.data
        for data in datas:
            league = data['league']
            future_league = data['future_league']
            u_id = data['discord_id']
            uname = data['discord_username']
            print(f"Current league: {league}, Future league: {future_league}")
            if data['league'] == data['future_league']:
                continue
            if data['future_league'] == None or data['league'] == None:
                continue
            print(f"HERE MFER          Current league: {league}, Future league: {future_league}")
            print(f"Current league: {league}, Future league: {future_league}")
            osu_uname = await get_osu_uname(discord_uname=uname)
            pp = await get_pp(discord_username=uname)
            print(f"{osu_uname}, {pp}")
            if league != TABLE_MODES[7]:
                await supabase.table(league).delete().eq('discord_username', uname).execute()
            await supabase.table(future_league).insert([{
                'discord_username': uname,
                'osu_username': osu_uname,
                'initial_pp': pp
            }]).execute()
            await supabase.table('discord_osu').update({'league': future_league}).eq('discord_username', uname).execute()
            players.append({
                'discord_username': uname,
                'league_transferred': future_league,
                'old_league': league,
                'discord_id': u_id
            })
        return players
    except Exception as e:
        logging.error(f"Error updating leagues: {e}")
        return []