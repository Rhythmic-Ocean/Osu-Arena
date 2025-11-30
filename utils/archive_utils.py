"""
Utilities for the /archive command.

Note:
    This module utilizes helper functions from external files:
    - get_table() from db_getter.py: To fetch tables from the database.
    - render_table_image() from render.py: To render .png table images.
    These are excluded here as they are general-purpose functions also used
    by the /show command.
"""

import logging
from .core_v2 import create_supabase

"""
Functions in this module:
1. exist_archive(seash: int) -> str
"""

logging.basicConfig(filename="archive_utils.log", level=logging.DEBUG, filemode='w')

async def exist_archive(seash: int) -> str: 
    """
    Checks if a specific season has been archived.

    Queries the 'seasons' table in the database to check the value of the 
    'status' column for the specified season.

    Args:
        seash (int): The season number to query.

    Returns:
        str: The status of the season. 
             - Returns the status value (e.g., "Archived" or "Ongoing") if found.
             - Returns "DNE" if the season number does not exist.
             - Returns "Error" if an exception occurs during execution.
    """
    supabase = await create_supabase()
    try:
        query = await supabase.table('seasons').select('status').eq('season', seash).execute()
        if not query.data:  
            return "DNE"
        result = query.data[0].get('status')
        return result 
    except Exception as e:
        logging.error(f"Error at getting seassion archives:{e}")
        print(f"Error at getting session archives: {e}")
        return "Error"