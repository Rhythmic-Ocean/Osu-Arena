from dotenv import load_dotenv
from osu import Scope, GameModeStr, AsynchronousClient, AsynchronousAuthHandler
import os
import discord
from discord.ext import commands
import logging
import aiosqlite
import shutil
import datetime
from datetime import datetime, timedelta, timezone
from itsdangerous import URLSafeSerializer
from discord.ui import View, Button
import sqlite3

load_dotenv(dotenv_path="sec.env")
token = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

DB_PATH = "instance/rt4d.db"
BACKUP_DIR = "instance/backups"
RIVAL_RESULTS_ID = 1386091184706818220
#1378928704121737326

os.makedirs(BACKUP_DIR, exist_ok=True)


bot = commands.Bot(command_prefix = '!',intents = intents)
s_role = 'admin'

SEC_KEY = os.getenv("SEC_KEY")
client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
redirect_url = "https://rhythmicocean.pythonanywhere.com/"
serializer = URLSafeSerializer(SEC_KEY)

auth = AsynchronousAuthHandler(client_id, client_secret, redirect_url, Scope.identify())
client_updater = AsynchronousClient.from_credentials(client_id, client_secret, redirect_url)


LEAGUE_MODES = {
    1: "Bronze",
    2: "Silver",
    3: "Gold",
    4: "Platinum",
    5: "Diamond",
    6: "Elite",
    7: "Ranker",
    8: "Master",
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
    4: "Finished"
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

def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(b):
    return datetime.fromisoformat(b.decode())

########## just so u see this one
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("DATETIME", convert_datetime)
#######


def backup_database():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    shutil.copyfile(DB_PATH,backup_path)
    return backup_path

async def get_table_data(league):
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.cursor()
        await cursor.execute(f"SELECT osu_username, initial_pp, current_pp, pp_change FROM {league} ORDER BY pp_change DESC")
        rows = await cursor.fetchall()
        headers = [description[0] for description in cursor.description]
    return headers, rows

async def get_osu_uname(discord_uname, league):
    query = f"SELECT osu_username FROM {league} WHERE discord_username = ?"
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.cursor()
        await cursor.execute(query,(discord_uname,))
        data = await cursor.fetchone()
        return data[0]

async def get_pp(osu_username = None, discord_username = None, league = None):
    if osu_username:
        user = await client_updater.get_user(osu_username, GameModeStr.STANDARD)
        pp = round(user.statistics.pp)
        return pp
    elif discord_username and league:
            data = await get_osu_uname(discord_username, league)
            if data is None:
                return None
            pp = await get_pp(osu_username=data)
            return pp
    else:
        return None



async def update_current_pp(league):
    async with aiosqlite.connect(DB_PATH) as conn:
        query = f"SELECT osu_username, initial_pp FROM {league}"
        cursor = await conn.cursor()
        await cursor.execute(query)
        rows = await cursor.fetchall()
        updates = []
        for name, initial_pp in rows:
            pp = await get_pp(name)
            pp_change = int(pp) - int(initial_pp)
            updates.append((pp, pp_change, name))
        await cursor.executemany(
            f"UPDATE {league} SET current_pp = ?, pp_change = ? WHERE osu_username = ?",
            updates
        )
        await conn.commit()

async def update_init_pp(league):
    async with aiosqlite.connect(DB_PATH) as conn:
        query = f"SELECT osu_username FROM {league}"
        cursor = await conn.cursor()
        await cursor.execute(query)
        rows = await cursor.fetchall()
        updates = []
        for name_tuple in rows: 
            name = name_tuple[0] 
            user = await client_updater.get_user(name, GameModeStr.STANDARD) 
            pp = round(user.statistics.pp) 
            pp_change = 0 
            updates.append((pp, pp, pp_change, name)) 
        await cursor.executemany(
            f"UPDATE {league} SET initial_pp = ?, current_pp = ?, pp_change = ? WHERE osu_username = ?",
            updates
        )
        await conn.commit()

async def check_challenger_challenges(challenger):
    async with aiosqlite.connect (DB_PATH) as conn:
        query = f"SELECT challenger, challenge_status FROM Rivals"
        cursor = await conn.cursor()
        await cursor.execute(query)
        rows = await cursor.fetchall()
        challenges = 0
        for name, status in rows:
            if name[0] == challenger:
                if status in (CHALLENGE_STATUS[1], CHALLENGE_STATUS[3]):
                    challenges = challenges + 1
        return challenges

async def challenge_accepted(id):
    async with aiosqlite.connect(DB_PATH) as conn:
        query_v1 = "SELECT challenger, challenged FROM Rivals WHERE id = ?"
        query_v2 = """
            UPDATE Rivals
            SET challenger_initial_pp = ?, challenger_final_pp = ?,
                challenged_initial_pp = ?, challenged_final_pp = ?,
                challenger_stats = ?, challenged_stats = ?, challenge_status = ?
            WHERE id = ?
        """
        cursor = await conn.cursor()
        await cursor.execute(query_v1, (id,))
        result_v1 = await cursor.fetchone()

        if not result_v1:
            return 

        challenger_uname, challenged_uname = result_v1
        challenger_pp = await get_pp(osu_username=challenger_uname)
        challenged_pp = await get_pp(osu_username=challenged_uname)

        await cursor.execute(
            query_v2,
            (
                challenger_pp, challenger_pp,
                challenged_pp, challenged_pp,
                "0", "0", "Unfinished", id
            )
        )
        await conn.commit()


async def challenge_allowed(challenger, challenged, league):
    challenger_uname = await get_osu_uname(challenger, league)
    challenged_uname = await get_osu_uname(challenged, league)

    if challenger_uname is None or challenged_uname is None:
        return 5

    query = "SELECT issued_at, challenge_status FROM Rivals WHERE challenger = ? AND challenged = ? ORDER BY issued_at DESC LIMIT 1"
    results = []

    async with aiosqlite.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        cursor = await conn.cursor()

        for a, b in [(challenger_uname, challenged_uname), (challenged_uname, challenger_uname)]:
            await cursor.execute(query, (a, b))
            row = await cursor.fetchone()
            if row:
                results.append(row)

    for issued_at_str, status in results:
        if status == "Pending":
            return 2
        elif status == "Unfinished":
            return 3
        issued_at = datetime.strptime(issued_at_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now(timezone.utc) - issued_at < timedelta(hours=24):
            return 4

    return 1  


async def update_rival_table():
    query_v1 = """
    SELECT id, challenger, challenged, challenger_initial_pp, challenged_initial_pp, challenge_status
    FROM Rivals
    """

    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.cursor()
        await cursor.execute(query_v1)
        results = await cursor.fetchall()

        updates = []

        for row in results:
            id, challenger, challenged, challenger_initial_pp, challenged_initial_pp, challenge_status = row

            if challenge_status != "Unfinished":
                continue

            challenger_pp = await get_pp(challenger)
            challenged_pp = await get_pp(challenged)

            challenger_diff = challenger_pp - challenger_initial_pp
            challenged_diff = challenged_pp - challenged_initial_pp

            challenger_stats = f"{'+' if challenger_diff >= 0 else ''}{challenger_diff}"
            challenged_stats = f"{'+' if challenged_diff >= 0 else ''}{challenged_diff}"

            updates.append((
                challenger_pp,
                challenged_pp,
                challenger_stats,
                challenged_stats,
                id
            ))

        update_query = """
        UPDATE Rivals
        SET challenger_final_pp = ?, challenged_final_pp = ?, challenger_stats = ?, challenged_stats = ?
        WHERE id = ?
        """

        for update in updates:
            await cursor.execute(update_query, update)

        await conn.commit()

async def show_rival_table():
    query = """
    SELECT league, challenger, challenged, challenger_stats, challenged_stats,for_pp
    FROM Rivals
    WHERE challenge_status = ?
    """
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.cursor()
        await cursor.execute(query, ("Unfinished",))
        rows = await cursor.fetchall()
        headers = [description[0] for description in cursor.description]
        return rows, headers

from datetime import datetime, timezone

from datetime import datetime, timezone

async def log_rivals(league, challenger, challenged, pp):
    query = """
        INSERT INTO Rivals (league, challenger, challenged, issued_at, challenge_status, for_pp)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    challenger_uname = await get_osu_uname(challenger, league)
    challenged_uname = await get_osu_uname(challenged, league)
    status = CHALLENGE_STATUS[1]
    now_time = datetime.now(timezone.utc)

    async with aiosqlite.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        cursor = await conn.cursor()
        await cursor.execute(query, (league, challenger_uname, challenged_uname, now_time, status, pp))
        await conn.commit()
        return cursor.lastrowid
    
async def challenge_declined(id):
    query = "UPDATE Rivals SET challenge_status = ? WHERE id = ?"
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.cursor()
        await cursor.execute(query,(CHALLENGE_STATUS[2], id))
        await conn.commit()

        


        


 




    
            


