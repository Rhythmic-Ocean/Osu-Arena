from dotenv import load_dotenv
from osu import Scope, AsynchronousClient, AsynchronousAuthHandler
import os
import discord
from discord.ext import commands
import logging
import datetime
from datetime import datetime
from itsdangerous import URLSafeSerializer
from discord.ui import View, Button
from dateutil import parser
import pytz
import pandas as pd
import aiofiles 
import matplotlib.pyplot as plt
from io import BytesIO

from supabase._async.client import AsyncClient, create_client

load_dotenv(dotenv_path="sec.env")
token = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

RIVAL_RESULTS_ID =  1378928704121737326 # 1386091184706818220
GUILD_ID = 1366563799569666158  #1389336700630732930 
WELCOME_ID =  1366564371899224115  #1389336701310337190

logging.basicConfig(filename="core_v2.log", level=logging.DEBUG, filemode='w')

bot = commands.Bot(command_prefix = '!',intents = intents)
s_role = 'admin'

SEC_KEY = os.getenv("SEC_KEY")
client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

GUILD = discord.Object(id=GUILD_ID)



redirect_url = "https://rt4d-production.up.railway.app/"
serializer = URLSafeSerializer(SEC_KEY)

auth = AsynchronousAuthHandler(client_id, client_secret, redirect_url, Scope.identify())
client_updater = AsynchronousClient.from_credentials(client_id, client_secret, redirect_url)

async def create_supabase() -> AsyncClient:
    return await create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    )

LEAGUE_MODES = {
    1: "bronze",
    2: "silver",
    3: "gold",
    4: "platinum",
    5: "diamond",
    6: "elite",
    7: "ranker",
    8: "master",
}

ROLE_MODES = {
    1: "Bronze",
    2: "Silver",
    3: "Gold",
    4: "Platinum",
    5: "Diamond",
    6: "Elite",
    7: "Ranker",
    8: "Master",
}

TABLE_MODES = {
    1: "Bronze",
    2: "Silver",
    3: "Gold",
    4: "Platinum",
    5: "Diamond",
    6: "Elite",
    7: "Ranker",
    8: "Master",
    9: "Rivals"
}

CHALLENGE_STATUS={
    1: "Pending",
    2: "Declined",
    3: "Unfinished",
    4: "Finished",
    5: "Revoked"
}

SEASON_STATUS={
    1: "Ongoing",
    2: "Archived",
    3: "DNE",
    4: "Error"
}

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

async def backup_database():
    supabase = await create_supabase()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    for _, league in LEAGUE_MODES.items():
        try:
            response = await supabase.table(league).select("*").execute()
            data = response.data

            if not data:
                logging.error(f"No data found in {league}")
                return
            

            df = pd.DataFrame(data)
            filename = f"{league}_{timestamp}.csv"
            df.to_csv(filename, index = False)


            async with aiofiles.open(filename, "rb") as f:
                contents = await f.read()


            storage_path = f"{league}/{filename}"
            upload_response = await supabase.storage.from_("backups").upload(storage_path, contents)
            print(upload_response)
        except Exception as e:
            logging.error(f"Error backing up {league}: {e}")
    folder = f"backup_{timestamp}"
    return folder
            



async def get_pp(osu_username :str = None, discord_username :str = None) -> int|None:
    supabase = await create_supabase()
    if osu_username:
        try:
            response = await supabase.table('discord_osu').select("current_pp").eq('osu_username',osu_username ).execute()
            return response.data[0]['current_pp']
        except Exception as e:
            logging.error(f"First error at get_pp: {e}")
            return None

    if discord_username:
        try:
            response = await supabase.table('discord_osu').select("current_pp").eq("discord_username", discord_username).execute()
            return response.data[0]['current_pp']
        except Exception as e:
            logging.error(f"Second error at get_pp: {e}")
            return None


async def get_table_data(leag, stat = None):
    league = leag.lower()
    supabase = await create_supabase()
    if league == "rivals":
        try:
            await supabase.rpc("sync_rivals").execute()
        except Exception as e:
            print(f"error as sync rivals: {e}")
            return
        try:
            if stat == CHALLENGE_STATUS[4]:
                response = await supabase.table(league).select("challenger, challenged, for_pp, winner, challenge_status").eq("challenge_status", CHALLENGE_STATUS[4]).order("challenge_id", desc= False).execute()
            else:
                response = await supabase.table(league).select("challenger, challenged, challenger_stats, challenged_stats").eq("challenge_status", CHALLENGE_STATUS[3]).order("challenge_id", desc= False).execute()
        except Exception as e:
            print(f"error show rivals: {e}")
            return
    else:
        try:
            await supabase.rpc("sync_table_pp",{"tbl_name": league}).execute()
        except Exception as e:
            print(f"error sync leagus: {e}")
            return
        try:
            response = await supabase.table(league).select("osu_username, initial_pp, current_pp, pp_change, percentage_change, ii").order("pp_change", desc= True).execute()
        except Exception as e:
            print(f"error at show league tables: {e}")
            return
    if response.data:
        rows = response.data
        headers = list(rows[0].keys()) 
        row_tuples = [tuple(row[h] for h in headers) for row in rows]
        return headers, row_tuples
    else:
        print("doen_v3")
        return [], []
    

async def get_osu_uname(discord_uname: str) ->str|None:
    supabase = await create_supabase()
    try:
        response = await supabase.table('discord_osu').select('osu_username').eq("discord_username", discord_uname).execute()
        if response.data:
            return response.data[0]['osu_username']
        else:
            return None
    except Exception as e:
        logging.error(f"Error at get_osu_uname: {e}")


async def check_challenger_challenges(usernme: str) -> int:
    username = await get_osu_uname(usernme)
    supabase = await create_supabase()
    try:
        response = await (
            supabase.table('rivals')
            .select("challenger")
            .eq("challenger", username)
            .in_("challenge_status", [CHALLENGE_STATUS[1], CHALLENGE_STATUS[3]])
            .order("issued_at", desc=True)
            .execute()
        )
        response2 = await (
            supabase.table('rivals')
            .select("challenged")
            .eq("challenged", username)
            .in_("challenge_status", [CHALLENGE_STATUS[1], CHALLENGE_STATUS[3]])
            .order("issued_at", desc=True)
            .execute()
        )
        val = len(response.data) + len(response2.data)
        return val
    except Exception as e:
        logging.error(f"error at check_challenger_challenges(): {e}")
        return 0


async def challenge_allowed(challenger: str, challenged: str, league: str) -> int:
    challenger_uname = await get_osu_uname(challenger)
    challenged_uname = await get_osu_uname(challenged)


    if challenger_uname is None or challenged_uname is None:
        return 5

    supabase = await create_supabase()
    or_clause = f"and(challenger.eq.{challenger_uname},challenged.eq.{challenged_uname}),and(challenger.eq.{challenged_uname},challenged.eq.{challenger_uname})"
    try:
        query = await (
            supabase.table("rivals")
            .select("challenger, challenged, issued_at, challenge_status")
            .or_(or_clause)
            .execute()
            )

        for item in query.data:
            if item["challenge_status"] == CHALLENGE_STATUS[1]:
                return 2
            elif item["challenge_status"] == CHALLENGE_STATUS[3]:
                return 3
            issued_at_str = item["issued_at"]
            chler = item['challenger']
            chled = item['challenged']
            time_diff = datetime.now(pytz.UTC) - parser.parse(issued_at_str)
            if time_diff.total_seconds() < 24 * 60 * 60 and chler == challenger_uname and chled == challenged_uname:
                return 4

    except Exception as e:
        logging.error(f"error at challenge_allowed: {e}")
        return 6

    return 1


async def check_league(user: str, leag: str)-> bool:
    league = leag.lower()
    supabase = await create_supabase()
    try:
        response = await supabase.table('discord_osu').select('league').eq('discord_username', user).execute()
        if len(response.data) > 0 and not response.data == None:
            if response.data[0]['league'] == league:
                return True
            else:
                return False
    except Exception as e:
        logging.error(f"Error at check_league: {e}")
 

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
    supabase = await create_supabase()
    try:
        await supabase.table('rivals').update({"challenge_status": CHALLENGE_STATUS[5]}).eq("challenge_id", id).execute()
    except Exception as e:
        logging.error(f"Error at challenge_revoked: {e}")


async def store_msg_id(challenge_id, msg_id):
    supabase = await create_supabase()
    try:
        await supabase.table('mesg_id').insert({"msg_id": msg_id, "challenge_id": challenge_id}).execute()
    except Exception as e:
        logging.error(f"Error when storing mesg_id: {e}")

async def get_msg_id(challenge_id):
    supabase = await create_supabase()
    try:
        row = await supabase.table('mesg_id').select("msg_id").eq("challenge_id", challenge_id).execute()
        result = row.data[0]['msg_id']
        if result is None:
            return None
        print (result)
        return result
    except Exception as e:
        logging.error(f"Error at get msg id: {e}")
    return None

async def check_pending(challenger, challenged):
    challenger_uname = await get_osu_uname(challenger)
    challenged_uname = await get_osu_uname(challenged)
    supabase = await create_supabase()
    try:
        response = await supabase.table('rivals').select('challenge_id, challenge_status').eq("challenger",challenger_uname).eq("challenged", challenged_uname).order("issued_at", desc=True).execute()
        if len(response.data) > 0 and not response.data == None:
            result = response.data[0]['challenge_status']
            result_id = response.data[0]['challenge_id']
        if result ==  CHALLENGE_STATUS[1]:
            return result_id
        else:
            return None
    except Exception as e:
        logging.error(f"Error at check pending: {e}")


def render_table_image(headers, rows):
    df = pd.DataFrame(rows, columns=headers)
    n_rows, n_cols = df.shape

    fig, ax = plt.subplots(figsize=(n_cols * 3, n_rows * 0.6 + 1))
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')
    ax.axis('off')

    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')

    table.auto_set_font_size(False)
    table.set_fontsize(14)
    table.scale(1.3, 1.3)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=16)
            cell.set_facecolor('#FF69B4')  
        else:
            cell.set_text_props(color='white')
            cell.set_facecolor('#222222' if row % 2 == 0 else '#000000')

        cell.set_linewidth(1)
        cell.set_edgecolor('white')

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=250, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf
    
async def update_init_pp(league):
    supabase = await create_supabase()
    try:
        await supabase.rpc("update_init_pp",{"tbl_name": league}).execute()
    except Exception as e:
        print(f"error updating init pp: {e}")
        return 
    
async def update_leagues():
    supabase = await create_supabase()
    print("here")
    players = []
    try:
        query = await supabase.table('discord_osu').select('discord_username, discord_id, league, future_league').execute()
        datas = query.data
        for data in datas:
            print(data)
            league = data['league']
            future_league = data['future_league']
            u_id = data['discord_id']
            uname = data['discord_username']
            print(uname)
            if data['league'] == data['future_league']:
                continue
            osu_uname = await get_osu_uname(discord_uname=uname)
            pp = await get_pp(discord_username=uname)
            print(f"{osu_uname}, {pp}")
            await supabase.table(league).delete().eq('discord_username', uname).execute()
            await supabase.table(future_league).insert({'discord_username': uname, 'osu_username': osu_uname, 'initial_pp': pp}).execute()
            await supabase.table('discord_osu').update({'league': future_league}).eq('discord_username', uname).execute()
            players.append({
                'discord_username': uname,
                'league_transferred': future_league,
                'old_league': league,
                'discord_id': u_id
            })
        return players
    except Exception as e:
        logging.error(f"Error updating leagues: {e}")
        return []
    
async def get_discord_id(username):
    supabase = await create_supabase()
    try:
        print(username)
        query = await supabase.table('discord_osu').select('discord_id').eq('osu_username', username).execute()
        print(query)
        result = query.data[0]['discord_id']
        print(result)
        return result
    except Exception as e:
        logging.error(f"Error at get_discord_id: {e}")
        print(f"Error at get_discord_id: {e}")
        return None

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





