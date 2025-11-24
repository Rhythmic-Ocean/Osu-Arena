"""
All of our data fetching from our database happens here
"""

from .core_v2 import create_supabase, CHALLENGE_STATUS
import logging

logging.basicConfig(filename="db_getter.log", level=logging.DEBUG, filemode='w')


"""
Fetching an entire table from our database
"""
async def get_table_data(leag : str, stat = None):
    league = leag.lower()
    supabase = await create_supabase()
    if league == "rivals":
        try:
            await supabase.rpc("sync_rivals").execute()
        except Exception as e:
            print(f"Error syncing Rivals: {e}")
            return
        try:
            if stat == CHALLENGE_STATUS[4]:
                response = await supabase.table(league).select("challenger, challenged, for_pp, winner, challenge_status").eq("challenge_status", CHALLENGE_STATUS[4]).order("challenge_id", desc= False).execute()
            else:
                response = await supabase.table(league).select("challenger, challenged, challenger_stats, challenged_stats, for_pp").eq("challenge_status", CHALLENGE_STATUS[3]).order("challenge_id", desc= False).execute()
        except Exception as e:
            print(f"error show rivals: {e}")
            return
    else:
        try:
            await supabase.rpc("sync_table_pp",{"tbl_name": league}).execute()
        except Exception as e:
            print(f"error sync leagus: {e}")
            return
        try:
            response = await supabase.table(league).select("osu_username, initial_pp, current_pp, pp_change, percentage_change, ii").order("pp_change", desc= True).execute()
        except Exception as e:
            print(f"error at show league tables: {e}")
            return
    if response.data:
        rows = response.data
        headers = list(rows[0].keys()) 
        row_tuples = [tuple(row[h] for h in headers) for row in rows]
        return headers, row_tuples
    else:
        return [], []
    


"""
Given either osu_username or discord_username, this function returns current_pp of the said user from our supabase database.
Returns None with appropriate log warnings/ errors if fails
NOTE*: Only our supabase database does direct interaction with osu!API to fetch latest user's pp. If we need the data for any
       other purpose, we fetch it from whatever's in our database.
"""
async def get_pp(osu_username: str = None, discord_username: str = None) -> int | None:
    supabase = await create_supabase()

    if osu_username:
        try:
            response = await supabase.table('discord_osu').select("current_pp").eq('osu_username', osu_username).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]['current_pp']
            else:
                logging.warning(f"[get_pp] No data found for osu_username: {osu_username}")
                return None
        except Exception as e:
            logging.error(f"[get_pp] Error while fetching by osu_username ({osu_username}): {e}")
            return None

    if discord_username:
        try:
            response = await supabase.table('discord_osu').select("current_pp").eq("discord_username", discord_username).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]['current_pp']
            else:
                logging.warning(f"[get_pp] No data found for discord_username: {discord_username}")
                return None
        except Exception as e:
            logging.error(f"[get_pp] Error while fetching by discord_username ({discord_username}): {e}")
            return None

    logging.warning("[get_pp] No username provided.")
    return None

async def get_osu_uname(discord_uname: str) ->str|None:
    supabase = await create_supabase()
    try:
        response = await supabase.table('discord_osu').select('osu_username').eq("discord_username", discord_uname).execute()
        if response.data:
            return response.data[0]['osu_username']
        else:
            return None
    except Exception as e:
        logging.error(f"Error at get_osu_uname: {e}")

async def get_discord_id(username):
    supabase = await create_supabase()
    try:
        print(username)
        query = await supabase.table('discord_osu').select('discord_id').eq('osu_username', username).execute()
        print(query)
        result = query.data[0]['discord_id']
        print(result)
        return result
    except Exception as e:
        logging.error(f"Error at get_discord_id: {e}")
        print(f"Error at get_discord_id: {e}")
        return None

async def get_msg_id(challenge_id):
    supabase = await create_supabase()
    try:
        row = await supabase.table('mesg_id').select("msg_id").eq("challenge_id", challenge_id).execute()
        result = row.data[0]['msg_id']
        if result is None:
            return None
        print (result)
        return result
    except Exception as e:
        logging.error(f"Error at get msg id: {e}")
    return None