from .core_v2 import create_supabase, CHALLENGE_STATUS
import logging

logging.basicConfig(filename= "challenge_final.py", level= logging.DEBUG, filemode= 'w')

async def challenge_accepted(id):
    supabase = await create_supabase()
    try:
        response = await supabase.table('rivals').update({"challenge_status": CHALLENGE_STATUS[3]}).eq("challenge_id", id).execute()
        return True
    except Exception as e:
        logging.error(f"Error at challenge_accepted: {e}")

async def challenge_declined(id):
    supabase = await create_supabase()
    try:
        await supabase.table('rivals').update({"challenge_status": CHALLENGE_STATUS[2]}).eq("challenge_id", id).execute()
        return True
    except Exception as e:
        logging.error(f"Error at challenge_declined: {e}")

async def revoke_success(id):
    print("Here at revoked")
    supabase = await create_supabase()
    try:
        await supabase.table('rivals').update({"challenge_status": CHALLENGE_STATUS[5]}).eq("challenge_id", id).execute()
        print("revoked_suc?")
    except Exception as e:
        logging.error(f"Error at challenge_revoked: {e}")
        print(f"Error at challenge_revoked: {e}")