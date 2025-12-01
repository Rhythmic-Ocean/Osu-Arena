"""
Rivalry Authentication & Validation Utilities.

This module handles the validation logic for the Rivals system, including:
1. Checking if players are eligible to challenge each other.
2. Enforcing cooldowns and league restrictions.
3. verifying pending challenge statuses.
"""

from .db_getter import get_osu_uname
from .core_v2 import CHALLENGE_STATUS, create_supabase
import logging
import pytz
from dateutil import parser
from datetime import datetime
from typing import Optional

"""
Functions in this module:
1. check_challenger_challenges(username: str) -> int
2. challenge_allowed(challenger: str, challenged: str, league: str) -> int
3. check_league(user: str, leag: str) -> bool
4. check_pending(challenger: str, challenged: str) -> int | None
"""

logging.basicConfig(filename="rivalry_auth.log", level=logging.DEBUG, filemode='w')

async def check_challenger_challenges(username: str) -> int:
    """
    Counts the number of active challenges for a specific user.

    Checks both 'challenger' and 'challenged' columns for challenges 
    that are either 'Pending' or 'Unfinished'.

    Args:
        username (str): The Discord username to check.

    Returns:
        int: The total count of active challenges. Returns 0 on error.
    """
    osu_user = await get_osu_uname(username)
    supabase = await create_supabase()
    try:
        # Check count where user is the challenger
        response = await (
            supabase.table('rivals')
            .select("challenger")
            .eq("challenger", osu_user)
            .in_("challenge_status", [CHALLENGE_STATUS[1], CHALLENGE_STATUS[3]])
            .order("issued_at", desc=True)
            .execute()
        )
        # Check count where user is the challenged
        response2 = await (
            supabase.table('rivals')
            .select("challenged")
            .eq("challenged", osu_user)
            .in_("challenge_status", [CHALLENGE_STATUS[1], CHALLENGE_STATUS[3]])
            .order("issued_at", desc=True)
            .execute()
        )
        val = len(response.data) + len(response2.data)
        return val
    except Exception as e:
        logging.error(f"Error at check_challenger_challenges(): {e}")
        return 0

async def challenge_allowed(challenger: str, challenged: str, league: str) -> int:
    """
    Determines if a challenge is allowed between two users.

    Args:
        challenger (str): Discord username of the challenger.
        challenged (str): Discord username of the challenged.
        league (str): The league context (unused in logic currently, but kept for signature).

    Returns:
        int: Status code indicating the result:
             1: Allowed (Success).
             2: Pending challenge already exists.
             3: Unfinished challenge already exists.
             4: Cooldown active (<24h since last challenge between this pair).
             5: One or both users are not linked to an osu! account.
             6: Internal Error.
    """
    challenger_uname = await get_osu_uname(challenger)
    challenged_uname = await get_osu_uname(challenged)

    if challenger_uname is None or challenged_uname is None:
        return 5

    supabase = await create_supabase()
    
    # Construct a complex OR filter for Supabase to check bidirectional history
    # Matches: (A vs B) OR (B vs A)
    or_clause = f"and(challenger.eq.{challenger_uname},challenged.eq.{challenged_uname}),and(challenger.eq.{challenged_uname},challenged.eq.{challenger_uname})"
    
    try:
        query = await (
            supabase.table("rivals")
            .select("challenger, challenged, issued_at, challenge_status")
            .or_(or_clause)
            .execute()
        )

        for item in query.data:
            # Check for existing active states
            if item["challenge_status"] == CHALLENGE_STATUS[1]:
                return 2
            elif item["challenge_status"] == CHALLENGE_STATUS[3]:
                return 3
            
            # Check for Cooldowns on historical matches
            issued_at_str = item["issued_at"]
            chler = item['challenger']
            chled = item['challenged']
            
            # Parse DB timestamp
            time_diff = datetime.now(pytz.UTC) - parser.parse(issued_at_str)
            
            # If the Challenger challenges the SAME person again within 24 hours
            if time_diff.total_seconds() < 24 * 60 * 60 and chler == challenger_uname and chled == challenged_uname:
                return 4

    except Exception as e:
        logging.error(f"Error at challenge_allowed: {e}")
        return 6

    return 1

async def check_league(user: str, leag: str) -> bool:
    """
    Verifies if a Discord user belongs to a specific league.

    Args:
        user (str): Discord username.
        leag (str): League name to verify against.

    Returns:
        bool: True if user is in the league, False otherwise.
    """
    league = leag.lower()
    supabase = await create_supabase()
    try:
        response = await supabase.table('discord_osu').select('league').eq('discord_username', user).execute()
        
        if response.data and len(response.data) > 0:
            if response.data[0]['league'] == league:
                return True
            else:
                return False
        return False
    except Exception as e:
        logging.error(f"Error at check_league: {e}")
        return False

async def check_pending(challenger: str, challenged: str) -> Optional[int]:
    """
    Checks for a specific pending challenge between two users.

    Args:
        challenger (str): Discord username of the challenger.
        challenged (str): Discord username of the challenged.

    Returns:
        int | None: The 'challenge_id' if a pending match exists, otherwise None.
    """
    challenger_uname = await get_osu_uname(challenger)
    challenged_uname = await get_osu_uname(challenged)
    supabase = await create_supabase()
    
    try:
        response = await (
            supabase.table('rivals')
            .select('challenge_id, challenge_status')
            .eq("challenger", challenger_uname)
            .eq("challenged", challenged_uname)
            .order("issued_at", desc=True)
            .execute()
        )

        if response.data and len(response.data) > 0:
            result = response.data[0]['challenge_status']
            result_id = response.data[0]['challenge_id']
            
            if result == CHALLENGE_STATUS[1]: # Pending
                return result_id
                
        return None
        
    except Exception as e:
        logging.error(f"Error at check pending: {e}")
        return None