from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, url_for
from osu import Client, AuthHandler, Scope
import os
import discord
from discord.ext import commands
import logging


load_dotenv(dotenv_path="sec.env")
token = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix = '!',intents = intents)
s_role = 'Admin'


client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
redirect_url = "http://127.0.0.1:5000/"

auth = AuthHandler(client_id, client_secret, redirect_url, Scope.identify())

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

@bot.command()
async def link(ctx):
    state = ctx.author.name 
    auth_url = auth.get_auth_url() + f"&state={state}"
    embed = discord.Embed(
        title = "Click Here",
        url = auth_url
    )
    await ctx.send(embed = embed)

bot.run(token, log_handler = handler, log_level= logging.DEBUG)



