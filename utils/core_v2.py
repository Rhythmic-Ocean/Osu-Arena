"""
This is the "core" util which defines all the misellanious parameters and objects required for the entire project.

"""
from dotenv import load_dotenv
from osu import Scope, AsynchronousClient, AsynchronousAuthHandler
import os
import discord
from discord.ext import commands
import logging
from itsdangerous import URLSafeSerializer

from supabase._async.client import AsyncClient, create_client

#Defining the bot's intent, has been enabled on discord's developer dashboard
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

#Creating the bot objects with the intents defined above and the default command prefix
#Note, we use / commands, so except for !session_restart command, the default prefix is irrelevent
bot = commands.Bot(command_prefix = '!',intents = intents)

#Locally my env file's name is sec.env so that's the name here too
load_dotenv(dotenv_path="sec.env")

#Hold's discord authentication token
token = os.getenv('DISCORD_TOKEN')

#Our Osu!Arena server, Rival_Results and Welcome channel's id
GUILD_ID   =  1366563799569666158
RIVAL_RESULTS_ID = 1378928704121737326
WELCOME_ID = 1366564371899224115

logging.basicConfig(filename="core_v2.log", level=logging.DEBUG, filemode='w')

#just defining string here, will be used in session_restart.py
s_role = 'admin'

#osu! API's client id and secret
client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")

#supabase API's URL and KEY
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

#Serializer for our URL during oauth
SEC_KEY = os.getenv("SEC_KEY")

#a generic discord object for guild
GUILD = discord.Object(id=GUILD_ID)


#website's url
redirect_url = "https://rt4d-production.up.railway.app/"
serializer = URLSafeSerializer(SEC_KEY)

#auth handler for osu oauth
auth = AsynchronousAuthHandler(client_id, client_secret, redirect_url, Scope.identify())

#client to access osu!API
client_updater = AsynchronousClient.from_credentials(client_id, client_secret, redirect_url)

#to create an async client to access our database at supabase
async def create_supabase() -> AsyncClient:
    return await create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    )

"""
Different dictionaries for keywords used throughout our project
"""
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


