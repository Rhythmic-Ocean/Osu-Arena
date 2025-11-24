import logging
from .core_v2 import create_supabase

logging.basicConfig(filename="archive_utils.log", level= logging.DEBUG, filemode= 'w')

async def exist_archive(seash: int):
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