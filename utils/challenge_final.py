"""
Contains functions that might be invoked at the end of challenge processing 
depending on the challenged user's response.
"""
from .core_v2 import create_supabase, CHALLENGE_STATUS
import logging

logging.basicConfig(filename= "challenge_final.py", level= logging.DEBUG, filemode= 'w')

"""
This file contains the following functions:

"""
"""
<1> challenge_accepted(id : int) -> bool

    Invoked when the challenged user accepts the challenge
    Takes in challenge_id (id : int) as argument
    Updates the cell corresponding to 'challenge_status' from Pending to Unfinished
    Returns true if success, None if error with appropriate error log
"""
"""
<2> challenge_declined(id : int) -> bool

    Invoked with the challenge is declined by the challenged user OR if the challenged user takes too long to respond
    Takes in challenge_id (id : int) as argument
    Updates the cell corresponding to 'challenge_status' from Pending to Revoked
    Returns true if success, None if error with appropriate error log

"""
"""
<3> revoke_success(id : int) -> bool

    Invoked when the challenger revokes their challenge
    Takes in challenge_id (id : int) as argument
    Updates the cell corresponding to 'challenge_status' from Pending to Declined
    Returns true if success, None if error with appropriate error log
"""

async def challenge_accepted(id : int) -> bool | None:
    supabase = await create_supabase()
    try:
        await supabase.table('rivals').update({"challenge_status": CHALLENGE_STATUS[3]}).eq("challenge_id", id).execute()
        return True
    except Exception as e:
        logging.error(f"Error at challenge_accepted: {e}")




async def challenge_declined(id : int) -> bool:
    supabase = await create_supabase()
    try:
        await supabase.table('rivals').update({"challenge_status": CHALLENGE_STATUS[2]}).eq("challenge_id", id).execute()
        return True
    except Exception as e:
        logging.error(f"Error at challenge_declined: {e}")




async def revoke_success(id : int) -> bool:
    print("Here at revoked")
    supabase = await create_supabase()
    try:
        await supabase.table('rivals').update({"challenge_status": CHALLENGE_STATUS[5]}).eq("challenge_id", id).execute()
        return True
    except Exception as e:
        logging.error(f"Error at challenge_revoked: {e}")