"""
Contains functions invoked at the end of challenge processing
depending on the challenged user's response.
"""

from .points_utils import add_points
from .core_v2 import create_supabase, CHALLENGE_STATUS
import logging

"""
Functions in this module:
1. challenge_accepted(id: int) -> bool | None
2. challenge_declined(id: int) -> bool | None
3. revoke_success(id: int) -> bool | None
"""

logging.basicConfig(filename="challenge_final.log", level=logging.DEBUG, filemode="w")


async def challenge_accepted(id: int) -> bool | None:
    """
    Handles the acceptance of a challenge by the user.

    Updates the 'challenge_status' in the 'rivals' table from 'Pending'
    to 'Unfinished'.

    Args:
        id (int): The unique identifier of the challenge (challenge_id).

    Returns:
        bool | None: True if the update is successful, None if an error occurs.
    """
    supabase = await create_supabase()
    try:
        await (
            supabase.table("rivals")
            .update({"challenge_status": CHALLENGE_STATUS[3]})
            .eq("challenge_id", id)
            .execute()
        )
        return True
    except Exception as e:
        logging.error(f"Error at challenge_accepted: {e}")


async def challenge_declined(id: int) -> bool | None:
    """
    Handles the declination of a challenge or a timeout event.

    Invoked when the challenge is explicitly declined by the user OR if the
    user takes too long to respond. Updates 'challenge_status' to 'Revoked'.

    Args:
        id (int): The unique identifier of the challenge (challenge_id).

    Returns:
        bool | None: True if the update is successful, None if an error occurs.
    """
    supabase = await create_supabase()
    try:
        await (
            supabase.table("rivals")
            .update({"challenge_status": CHALLENGE_STATUS[2]})
            .eq("challenge_id", id)
            .execute()
        )
        return True
    except Exception as e:
        logging.error(f"Error at challenge_declined: {e}")


async def revoke_success(id: int) -> bool | None:
    """
    Handles the revocation of a challenge by the challenger.

    Invoked when the challenger revokes their own challenge request.
    Updates 'challenge_status' to 'Declined'.

    Args:
        id (int): The unique identifier of the challenge (challenge_id).

    Returns:
        bool | None: True if the update is successful, None if an error occurs.
    """
    print("Here at revoked")
    supabase = await create_supabase()
    try:
        await (
            supabase.table("rivals")
            .update({"challenge_status": CHALLENGE_STATUS[5]})
            .eq("challenge_id", id)
            .execute()
        )
        return True
    except Exception as e:
        logging.error(f"Error at challenge_revoked: {e}")


async def challenge_finish_point_distribution(winner, loser, for_pp):
    response1 = await add_points(winner, for_pp)
    response2 = await add_points(loser, -int(round(for_pp / 2)))
    if response1 and response2:
        return True
    return False
