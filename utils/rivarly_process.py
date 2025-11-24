from .db_getter import get_osu_uname, get_pp
from  .core_v2 import create_supabase, CHALLENGE_STATUS
import logging
import discord
from discord.ui import View, Button

logging.basicConfig(filename="rivarly_process.log", level=logging.DEBUG, filemode='w')

class ChallengeView(View):
    def __init__(self, challenged:discord.Member,timeout = 86400):
        super().__init__(timeout=timeout)
        self.challenged = challenged
        self.response = None
    @discord.ui.button(label = "Accept", style= discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.challenged:
            await interaction.response.send_message("This challenge is not for you")
            return
        self.response = True
        await interaction.response.send_message("You have accepted the challenge")
        self.stop()
    
    @discord.ui.button(label = "Decline", style = discord.ButtonStyle.danger)
    async def decline(self, interaction:discord.Interaction, button: Button):
        if interaction.user != self.challenged:
            await interaction.response.send_message("This challenge is not for you.")
            return
        self.response = False
        await interaction.response.send_message("You have declined the challenge.")
        self.stop()



async def log_rivals(leag: str, challenger: str, challenged: str, pp: float):
    supabase = await create_supabase()
    league = leag.lower()
    try:
        challenger_uname = await get_osu_uname(challenger)
        challenged_uname = await get_osu_uname(challenged)

        if not challenger_uname or not challenged_uname:
            logging.warning(f"Missing osu username for challenger or challenged.")
            return None

        challenger_pp = await get_pp(discord_username=challenger)
        challenged_pp = await get_pp(discord_username=challenged)

        if challenger_pp is None or challenged_pp is None:
            logging.warning(f"Missing PP data for challenger or challenged.")
            return None

        response = await supabase.table('rivals').insert({
            "league": league,
            "challenger": challenger_uname,
            "challenged": challenged_uname,
            "for_pp": pp,
            "challenger_initial_pp": challenger_pp,
            "challenged_initial_pp": challenged_pp,
            "challenge_status": CHALLENGE_STATUS[1],
        }).execute()

        if not response.data or 'challenge_id' not in response.data[0]:
            logging.error("Failed to insert into 'rivals' or missing 'challenge_id'")
            return None

        challenge_id = response.data[0]['challenge_id']
        print(challenge_id)
        try:

            await supabase.table('challenged').insert({
                "challenge_id": challenge_id,
                "discord_username": challenged,
                "osu_username": challenged_uname,
                "initial_pp": challenged_pp
            }).execute()

            await supabase.table('challenger').insert({
                "challenge_id": challenge_id,  
                "discord_username": challenger,
                "osu_username": challenger_uname,
                "initial_pp": challenger_pp
            }).execute()
        except Exception as e:
            logging.error(f"Error here: {e}")
            print((f"Error here: {e}"))

        print(challenge_id)
        return challenge_id
    except Exception as e:
        logging.error(f"Error in log_rivals(): {e}")
        return None
    
async def store_msg_id(challenge_id, msg_id):
    supabase = await create_supabase()
    try:
        await supabase.table('mesg_id').insert({"msg_id": msg_id, "challenge_id": challenge_id}).execute()
    except Exception as e:
        logging.error(f"Error when storing mesg_id: {e}")