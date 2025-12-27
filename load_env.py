from dotenv import load_dotenv
import os


load_dotenv(dotenv_path="sec.env")


class ENV:
    AUTH_ID = int(os.getenv("AUTH_ID"))
    AUTH_TOKEN = os.getenv("AUTH_TOKEN")
    DISCORD_TOKEN_AUX = os.getenv("DISCORD_TOKEN")
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN_aux")
    FLASK_SECKEY = int(os.getenv("FLASK_SECKEY"))
    OSU_CLIENT_ID = int(os.getenv("osu_client_id"))
    OSU_CLIENT_SECRET = os.getenv("osu_client_secret")
    OSU_CLIENT2_ID = int(os.getenv("OSU_CLIENT2_ID"))
    OSU_CLIENT2_SECRET = os.getenv("OSU_CLIENT2_SECRET")
    SEC_KEY = os.getenv("SEC_KEY")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    OSU_ARENA = int(os.getenv("MY_SERVER"))
    MY_SERVER = int(os.getenv("OSU_ARENA"))
    RIVAL_RESULTS_ID = int(os.getenv("RIVAL_RES_ID"))
    WELCOME_ID = int(os.getenv("WELCOME_ID"))
    BOT_LOGS = int(os.getenv("BOT_LOGS"))
    BOT_UPDATES = int(os.getenv("BOT_UPDATES"))
    REDIRECT_URL = os.getenv("REDIRECT_URL")
