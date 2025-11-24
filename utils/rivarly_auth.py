from .db_getter import get_osu_uname
from .core_v2 import CHALLENGE_STATUS, create_supabase
import logging
import pytz
from dateutil import parser
from datetime import datetime

logging.basicConfig(filename="rivarly_auth.log", level=logging.DEBUG, filemode='w')

async def check_challenger_challenges(usernme: str) -> int:
    username = await get_osu_uname(usernme)
    supabase = await create_supabase()
    try:
        response = await (
            supabase.table('rivals')
            .select("challenger")
            .eq("challenger", username)
            .in_("challenge_status", [CHALLENGE_STATUS[1], CHALLENGE_STATUS[3]])
            .order("issued_at", desc=True)
            .execute()
        )
        response2 = await (
            supabase.table('rivals')
            .select("challenged")
            .eq("challenged", username)
            .in_("challenge_status", [CHALLENGE_STATUS[1], CHALLENGE_STATUS[3]])
            .order("issued_at", desc=True)
            .execute()
        )
        val = len(response.data) + len(response2.data)
        return val
    except Exception as e:
        logging.error(f"error at check_challenger_challenges(): {e}")
        return 0
    
async def challenge_allowed(challenger: str, challenged: str, league: str) -> int:
    challenger_uname = await get_osu_uname(challenger)
    challenged_uname = await get_osu_uname(challenged)


    if challenger_uname is None or challenged_uname is None:
        return 5

    supabase = await create_supabase()
    or_clause = f"and(challenger.eq.{challenger_uname},challenged.eq.{challenged_uname}),and(challenger.eq.{challenged_uname},challenged.eq.{challenger_uname})"
    try:
        query = await (
            supabase.table("rivals")
            .select("challenger, challenged, issued_at, challenge_status")
            .or_(or_clause)
            .execute()
            )

        for item in query.data:
            if item["challenge_status"] == CHALLENGE_STATUS[1]:
                return 2
            elif item["challenge_status"] == CHALLENGE_STATUS[3]:
                return 3
            issued_at_str = item["issued_at"]
            chler = item['challenger']
            chled = item['challenged']
            time_diff = datetime.now(pytz.UTC) - parser.parse(issued_at_str)
            if time_diff.total_seconds() < 24 * 60 * 60 and chler == challenger_uname and chled == challenged_uname:
                return 4

    except Exception as e:
        logging.error(f"error at challenge_allowed: {e}")
        return 6

    return 1

async def check_league(user: str, leag: str)-> bool:
    league = leag.lower()
    supabase = await create_supabase()
    try:
        response = await supabase.table('discord_osu').select('league').eq('discord_username', user).execute()
        if len(response.data) > 0 and not response.data == None:
            if response.data[0]['league'] == league:
                return True
            else:
                return False
    except Exception as e:
        logging.error(f"Error at check_league: {e}")


async def check_pending(challenger, challenged):
    challenger_uname = await get_osu_uname(challenger)
    challenged_uname = await get_osu_uname(challenged)
    supabase = await create_supabase()
    try:
        response = await supabase.table('rivals').select('challenge_id, challenge_status').eq("challenger",challenger_uname).eq("challenged", challenged_uname).order("issued_at", desc=True).execute()
        if len(response.data) > 0 and not response.data == None:
            result = response.data[0]['challenge_status']
            result_id = response.data[0]['challenge_id']
        if result ==  CHALLENGE_STATUS[1]:
            return result_id
        else:
            return None
    except Exception as e:
        logging.error(f"Error at check pending: {e}")