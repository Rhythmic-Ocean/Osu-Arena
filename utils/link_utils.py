"""
Utilities for the /link command.

This module handles the verification of user existence in the database 
during the account linking process.
"""

import logging
from .core_v2 import create_supabase

"""
Functions in this module:
1. is_in(id: int) -> bool
"""

logging.basicConfig(filename="link_utils.log", filemode='w', level=logging.DEBUG)

async def is_in(id: int) -> bool:
    """
    Checks if a Discord user already exists in the database.

    Queries the 'discord_osu' table to see if the provided Discord ID 
    is associated with an existing osu! username.

    Args:
        id (int): The Discord user ID to check.

    Returns:
        bool: True if the user exists in the database, False otherwise.
    """
    supabase = await create_supabase()
    try:
        query = await supabase.table('discord_osu').select('osu_username').eq('discord_id', id).execute()
        if not query.data:
            return False
        return True
    except Exception as e:
        logging.error(f"Error at is_in: {e}")
        return False