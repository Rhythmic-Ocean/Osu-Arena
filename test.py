from osu import Client, UserScoreType
import os
from dotenv import load_dotenv


load_dotenv(dotenv_path="sec.env")

client_id = int(os.getenv('AUTH_ID'))
client_secret = os.getenv('AUTH_TOKEN')
redirect_url = "https://rt4d-production.up.railway.app/"


client = Client.from_credentials(client_id, client_secret, redirect_url)

user_id = 12997448

top_scores = client.get_user_scores(user_id, UserScoreType.BEST, limit=1)

if not top_scores:
    print("Hi")
for i, score in enumerate(top_scores):
    print(f"{i+1}. {score.id} {score.beatmapset.artist} - {score.beatmapset.title}: {score.pp} {score.ended_at}")
