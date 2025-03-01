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

# Variable global para almacenar el ID del canal
listening_channel_id = None

# Comando de set_channel
@bot.command(description="Configura el canal de escucha")
async def set_channel(ctx, channel: discord.TextChannel):
    global listening_channel_id
    listening_channel_id = channel.id
    await ctx.send(f"Canal de escucha configurado a: {channel.mention}")

# Comando de unset_channel
@bot.command(description="Deja de escuchar en el canal configurado")
async def unset_channel(ctx):
    global listening_channel_id
    listening_channel_id = None
    await ctx.send("El bot ha dejado de escuchar en el canal configurado.")

# Comando de bot_help
@bot.command(name="bot_help", description="Lista todos los comandos disponibles")
async def bot_help(ctx):
    commands_list = ""
    for command in bot.commands:
        commands_list += f"/{command.name} - {command.description}\n"
    await ctx.send(f"Comandos disponibles:\n{commands_list}")

# Confirmar inicialización del bot
@bot.event
async def on_ready():
    print(f"Luna Assistant Inicializada: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos de barra.")
    except Exception as e:
        print(f"Error al sincronizar comandos de barra: {e}")

# Escuchar mensajes
@bot.event
async def on_message(message):
    global listening_channel_id
    if message.author == bot.user:
        return

    if message.channel.id == listening_channel_id:
        await message.channel.send(f"Escuché: {message.content}")

    await bot.process_commands(message)

# Definir slash commands
@bot.tree.command(name="set_channel", description="Configura el canal de escucha")
async def set_channel_slash(interaction: discord.Interaction, channel: discord.TextChannel):
    global listening_channel_id
    listening_channel_id = channel.id
    await interaction.response.send_message(f"Canal de escucha configurado a: {channel.mention}")

@bot.tree.command(name="unset_channel", description="Deja de escuchar en el canal configurado")
async def unset_channel_slash(interaction: discord.Interaction):
    global listening_channel_id
    listening_channel_id = None
    await interaction.response.send_message("El bot ha dejado de escuchar en el canal configurado.")

@bot.tree.command(name="bot_help", description="Lista todos los comandos disponibles")
async def bot_help_slash(interaction: discord.Interaction):
    commands_list = ""
    for command in bot.commands:
        commands_list += f"/{command.name} - {command.description}\n"
    await interaction.response.send_message(f"Comandos disponibles:\n{commands_list}")

webserver.keep_alive()
bot.run(DISCORD_TOKEN)