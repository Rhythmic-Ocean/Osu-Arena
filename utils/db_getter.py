"""
All of our functions that do data fetching from our database are here
See the schema of all supabase database at supabase_schema.txt in root
"""

from .core_v2 import create_supabase, CHALLENGE_STATUS
import logging
from typing import List, Tuple, Any

logging.basicConfig(filename="db_getter.log", level=logging.DEBUG, filemode='w')


"""
This file contains the following functions:
<1>get_table_data(leag : str, stat : str = None) -> Tuple[List[str], List[Tuple[str,...]]]
<2>get_pp(osu_username: str = None, discord_username: str = None) -> int | None
<3>get_osu_uname(discord_uname: str) ->str|None
<4>get_discord_id(osu_username : str) -> Any
<5>get_msg_id(challenge_id : Any) -> Any
"""
"""
<1>get_table_data(leag : str, stat : str = None) -> Tuple[List[str], List[Tuple[str,...]]]:

    This function is used to get every type of table. the state is for CHALLENGE_STATE, Unfinished and Finished ones

    On success returns two lists (or a tuple consisting of 2 lists). The first list consists of all the headers
    of table. The second list is a list of tuples, each tuple consisting Any type of data, usually str or int. 
    They are the table's data. 
    An example of return might be: ([Rank, Player_name, current_pp], [(1, Rhythmic_Ocean, 4545), (2, spinneracc, 5454)
    ,(3, Arriet, 9856)])
    On falilure the functions returns a tuple of two empty list, i.e. ([],[])
    The table is from our supabase database. Any table current or archived can be gotten from this function.

    NOTE: There is only ONE table in the supabase database that's always kept up to date, it's named discord_osu, it's
        updated every few seconds to match the latest pp of the players. However the individual tables is synced with the 
        discord_osu table only at the time of it being called. For eg: whenever we pass on rivals as leag argument in
        this function, the function runs ("sync_rivals") function internally in supabase which updates the rivals table. This
        table is then returned by this function.
    
    NOTE: For Rivals tables, all the pending, unfinished, finished and revoked challenges are kept in the same table. 

    NOTE: For other leagues, the table is stored as it's league names, like silver etc. For historical tables, it's followed with _
        and the season number. Eg: silver_1 means silver league's table by the end of season 1. See more at supabase_schema.txt in root
"""
"""
<2>get_pp(osu_username: str = None, discord_username: str = None) -> int | None:

    Given either osu_username or discord_username, this function returns current_pp of the said user from our supabase database.
    Returns None with appropriate log warnings/ errors if fails
    NOTE: Only our supabase database does direct interaction with osu!API to fetch latest user's pp. If we need the data for any
        other purpose, we fetch it from whatever's in our database.

"""
"""
<3>get_osu_uname(discord_uname: str) ->str|None

    Given a discord_username, this function returns the corresponding osu_username. 
    It gets the username from discord_osu table at our supabase database

"""
"""
<4>get_discord_id(osu_username : str) -> Any

    Given a valid osu_username, it returns the corresponding user's discord id from the database. 
    It again gets the discord id from the table at our supabase database
"""
"""
<5>get_msg_id(challenge_id : Any) -> Any

    Not sure about the type of data supabase sends so using Any
    Used to get msg id for corresponding challenges
    Usually when someone challengs someone else, after the bot makes the announcement, the id of that announcement 
    is stored in msg_id table. That id is later modified to update the status of challenge when that status changes

"""

#1
async def get_table_data(leag : str, stat : str = None) -> Tuple[List[str], List[Tuple[str,...]]]:
    league = leag.lower()
    supabase = await create_supabase()
    if league == "rivals":
        try:
            await supabase.rpc("sync_rivals").execute()
        except Exception as e:
            print(f"Error syncing Rivals: {e}")
            return [], []
        try:
            if stat == CHALLENGE_STATUS[4]:
                response = await supabase.table(league).select("challenger, challenged, for_pp, winner, challenge_status").eq("challenge_status", CHALLENGE_STATUS[4]).order("challenge_id", desc= False).execute()
            else:
                response = await supabase.table(league).select("challenger, challenged, challenger_stats, challenged_stats, for_pp").eq("challenge_status", CHALLENGE_STATUS[3]).order("challenge_id", desc= False).execute()
        except Exception as e:
            print(f"error show rivals: {e}")
            return [], []
    else:
        try:
            await supabase.rpc("sync_table_pp",{"tbl_name": league}).execute()
        except Exception as e:
            print(f"error sync leagus: {e}")
            return [], []
        try:
            response = await supabase.table(league).select("osu_username, initial_pp, current_pp, pp_change, percentage_change, ii").order("pp_change", desc= True).execute()
        except Exception as e:
            print(f"error at show league tables: {e}")
            return [], []
    if response.data:
        rows = response.data
        headers = list(rows[0].keys()) 
        row_tuples = [tuple(row[h] for h in headers) for row in rows]
        return headers, row_tuples
    else:
        return [], []
    

#2
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


#3
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


#4
# I did Any here cuz I'm not sure if supabase returns int or str for ids... It should be stored as int8 in the databse tho
async def get_discord_id(osu_username : str) -> Any:
    supabase = await create_supabase()
    try:
        query = await supabase.table('discord_osu').select('discord_id').eq('osu_username', osu_username).execute()
        result = query.data[0]['discord_id']
        return result
    except Exception as e:
        logging.error(f"Error at get_discord_id: {e}")
        print(f"Error at get_discord_id: {e}")
        return None


#5
async def get_msg_id(challenge_id : Any) -> Any:
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