from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, url_for
from osu import Client, AuthHandler, Scope
import os


load_dotenv(dotenv_path="sec.env")
client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
redirect_url = "http://127.0.0.1:5000/"
state = "Rhythmic_Ocean"

auth = AuthHandler(client_id, client_secret, redirect_url, Scope.identify())
print(auth.get_auth_url() + f"&state={state}")
auth.get_auth_token(input("Code: "))
client = Client(auth)

mode = 'osu'
user = client.get_own_data(mode)
print(user.username)


