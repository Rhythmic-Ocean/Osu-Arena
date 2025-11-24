from dotenv import load_dotenv
from osu import Scope, AsynchronousClient, AsynchronousAuthHandler
import os
import discord
from discord.ext import commands
import logging
from itsdangerous import URLSafeSerializer

from supabase._async.client import AsyncClient, create_client

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix = '!',intents = intents)

load_dotenv(dotenv_path="sec.env")
token = os.getenv('DISCORD_TOKEN')

RIVAL_RESULTS_ID = 1378928704121737326
GUILD_ID   =  1366563799569666158
WELCOME_ID = 1366564371899224115

logging.basicConfig(filename="core_v2.log", level=logging.DEBUG, filemode='w')

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
    9: "novice"
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
    9: "Novice",
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
    9: "Rivals",
    10: "Novice",
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


