import discord
from discord.ext import commands
import requests
import os
import webserver

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix='Lu!', intents=intents)

@bot.command()
async def test(ctx, *args):
    answer = ' '.join(args)
    await ctx.send(answer)

@bot.event
async def on_ready():
    print(f"Luna Assistant Inicializada: {bot.user}")

webserver.keep_alive()
bot.run(DISCORD_TOKEN)