"""
Utils for command /archive
NOTE: This command uses other helper functions too. That includes get_table() from db_getter.py to fetch the table from our database
      and render_table_image() from render.py to render our .png table image. However since they are more general functions also useful
      for /show command, it's not kept here.
"""

import logging
from .core_v2 import create_supabase

"""
This file includes the functions:
<1> exist_archive(seash : int) -> str
"""
"""
<1> exist_archive(seash : int) -> str
    
    To check if a certain season (seash : int) has been archived. 
    Checks the 'seasons' table from database, and checks the value on status column from seasons row.
    If the season's number does not exist, returns "DNE"
    If the number does exist, return it's status value, it's either "Archived" or "Ongoing"
    If error occurs logs and prints it on the terminal and returns the string "Error"
"""

logging.basicConfig(filename="archive_utils.log", level= logging.DEBUG, filemode= 'w')

#<1>
async def exist_archive(seash: int) -> str: 
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