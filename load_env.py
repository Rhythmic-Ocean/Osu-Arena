from dotenv import load_dotenv
import os


load_dotenv(dotenv_path="sec.env")


class ENV:
    AUTH_ID = os.getenv("AUTH_ID")
    AUTH_TOKEN = os.getenv("AUTH_TOKEN")
    DISCORD_TOKEN_AUX = os.getenv("DISCORD_TOKEN_aux")
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    FLASK_SECKEY = os.getenv("FLASK_SECKEY")
    OSU_CLIENT_ID = os.getenv("osu_client_id")
    OSU_CLIENT_SECRET = os.getenv("osu_client_secret")
    OSU_CLIENT2_ID = os.getenv("OSU_CLIENT2_ID")
    OSU_CLIENT2_SECRET = os.getenv("OSU_CLIENT2_SECRET")
    SEC_KEY = os.getenv("SEC_KEY")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    OSU_ARENA = os.getenv("OSU_ARENA")
    MY_SERVER = os.getenv("MY_SERVER")
    RIVAL_RESULTS_ID = os.getenv("RIVAL_RESULTS_ID")
    WELCOME_ID = os.getenv("WELCOME_ID")
    BOT_LOGS = os.getenv("BOT_LOGS")
