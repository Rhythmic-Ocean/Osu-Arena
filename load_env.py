from dotenv import load_dotenv
import os


load_dotenv(dotenv_path="local.env")


class ENV:
    # Discord Token for your bot
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    # Client ID and Client secret from osu. You can get this from your profile settings
    # Used for Oauth so Redirect URL is required as well
    AUTH_ID = int(os.getenv("AUTH_ID"))
    AUTH_TOKEN = os.getenv("AUTH_TOKEN")
    REDIRECT_URL = os.getenv("REDIRECT_URL")
    # Secerate key for session data encryption. It's arbitary, but recommended you use a long random string.
    # Just type : '$ openssl rand -hex 32' into your console to get one fast
    QUART_SECKEY = os.getenv("QUART_SECKEY")
    # Seconday Osu Client ID and Client Secret.
    # Primarily used to fetch data of users with known osu id, so no redirect url required.
    # You can arbitarily put anything in osu's 'Application Callback URLs' section. I would just write 'http://localhost'
    OSU_CLIENT_ID = int(os.getenv("OSU_CLIENT_ID"))
    OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET")
    # Does the same job as above.
    OSU_CLIENT2_ID = int(os.getenv("OSU_CLIENT2_ID"))
    OSU_CLIENT2_SECRET = os.getenv("OSU_CLIENT2_SECRET")
    # To serialize and deserialize the url during Oauth
    SEC_KEY = os.getenv("SEC_KEY")
    # Database key and url. You can get one from free tier.
    # Latest database schema can be provided when asked although I will try my best to maintain it in supabase_schema.sql
    # I'm trying to actively move all db modificiation type queries to postgres function, so it might be outdated
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    # All the guild related constants.
    # The primary guild's id. i.e the guild you want your got to run on
    OSU_ARENA = int(os.getenv("OSU_ARENA"))
    # Various channel id in the guild that bot will message in (moving all of them to be webhooks soon)
    RIVAL_RESULTS_ID = int(os.getenv("RIVAL_RES_ID"))
    WELCOME_ID = int(os.getenv("WELCOME_ID"))
    BOT_UPDATES = int(os.getenv("BOT_UPDATES"))
    TOP_PLAY_ID = int(os.getenv("TOP_PLAY_ID"))
    # Roles for special commands
    # This one's for /season_reset, /delete and /points
    REQ_ROLE = os.getenv("REQ_ROLE")
    # This one's for /points only
    REQ_ROLE_POINTS = os.getenv("REQ_ROLE_POINTS")
    # Webhook of the channel you want the bot to log errors and occasionally infos
    LOGS_WEBHOOK = os.getenv("LOGS_WEBHOOK")
