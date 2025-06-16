from osu import Client, GameModeStr
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="sec.env")
client = Client.from_credentials(os.getenv("AUTH_ID"), os.getenv("AUTH_TOKEN"), None)
user = client.get_user(14895608, GameModeStr.STANDARD)
print(user)