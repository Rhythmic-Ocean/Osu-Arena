"""
Core utility module.

This module defines the essential parameters, objects, and configuration constants 
required for the project's operation, including database clients, API authentication, 
and static lookup dictionaries.
"""

from dotenv import load_dotenv
from osu import Scope, AsynchronousClient, AsynchronousAuthHandler
import os
import discord
from discord.ext import commands
import logging
from itsdangerous import URLSafeSerializer
from supabase._async.client import AsyncClient, create_client

"""
Functions in this module:
1. create_supabase() -> AsyncClient
"""

# -----------------------------------------------------------------------------
# Bot Configuration & Intents
# -----------------------------------------------------------------------------

# Configure Discord intents to allow access to message content and member information.
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize the Bot object.
# Note: The prefix is primarily used for the '!session_restart' command; 
# most user interactions occur via slash commands.
bot = commands.Bot(command_prefix='!', intents=intents)

# Load environment variables from the configuration file.
load_dotenv(dotenv_path="sec.env")

# Discord Authentication Token.
token = os.getenv('DISCORD_TOKEN')

# -----------------------------------------------------------------------------
# Constants & IDs
# -----------------------------------------------------------------------------

# Discord IDs for the Server (Guild), specific channels, and roles.
GUILD_ID = 1366563799569666158
RIVAL_RESULTS_ID = 1378928704121737326
WELCOME_ID = 1366564371899224115

# Admin role identifier used in session management.
s_role = 'admin'

# Generic Discord Object representing the target Guild.
GUILD = discord.Object(id=GUILD_ID)

# -----------------------------------------------------------------------------
# Logging & Authentication
# -----------------------------------------------------------------------------

logging.basicConfig(filename="core_v2.log", level=logging.DEBUG, filemode='w')

# osu! API Credentials.
client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")

# Supabase Database Credentials.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# URL Safe Serializer using the security key for OAuth state handling.
SEC_KEY = os.getenv("SEC_KEY")
serializer = URLSafeSerializer(SEC_KEY)

# Web redirection URL for OAuth flows.
redirect_url = "https://rt4d-production.up.railway.app/"

# -----------------------------------------------------------------------------
# API Clients
# -----------------------------------------------------------------------------

# Asynchronous Authentication Handler for osu! OAuth.
auth = AsynchronousAuthHandler(client_id, client_secret, redirect_url, Scope.identify())

# Asynchronous Client for interacting with the osu! API.
client_updater = AsynchronousClient.from_credentials(client_id, client_secret, redirect_url)

async def create_supabase() -> AsyncClient:
    """
    Creates and returns an asynchronous Supabase client.

    Uses the environment variables SUPABASE_URL and SUPABASE_KEY to establish
    the connection.

    Returns:
        AsyncClient: The initialized Supabase client instance.
    """
    return await create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )

# -----------------------------------------------------------------------------
# Lookup Dictionaries
# -----------------------------------------------------------------------------
"""
The following dictionaries map internal integer IDs to their corresponding 
string representations for Leagues, Roles, Tables, and Statuses.
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

CHALLENGE_STATUS = {
    1: "Pending",
    2: "Declined",
    3: "Unfinished",
    4: "Finished",
    5: "Revoked"
}

SEASON_STATUS = {
    1: "Ongoing",
    2: "Archived",
    3: "DNE",
    4: "Error"
}

