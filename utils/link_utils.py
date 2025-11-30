"""
Utils for /link command
"""
import logging
from .core_v2 import create_supabase
logging.basicConfig(filename= "link_utils.log", filemode= 'w', level= logging.DEBUG)

"""
Checks if there exist a discord user with corresponding discord id in the database
"""
async def is_in(id: int) -> bool:
    supabase = await create_supabase()
    try:
        query = await supabase.table('discord_osu').select('osu_username'). eq('discord_id', id).execute()
        if not query.data:
            return False
        return True
    except Exception as e:
        logging.error(f"Error at is_in {e}")