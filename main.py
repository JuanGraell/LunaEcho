import discord
from discord.ext import commands
import requests
import os
import webserver
import spacy
import re


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix='Lu!', intents=intents)

nlp = spacy.load("es_core_news_sm")

# Variable global para almacenar el ID del canal
listening_channel_id = None

# Comando de set_channel
@bot.command(description="Configura el canal de escucha")
async def set_channel(ctx, channel: discord.TextChannel):
    global listening_channel_id
    listening_channel_id = channel.id
    await ctx.send(f"Canal de escucha configurado a: {channel.mention}")
    await ctx.send("Recuerda que si quieres dar ordenes, los nombres de canales, categorias y roles deben ir entre comillas.")

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
is_creating_channel, name_channel_status, name_category_status  = False, False, False

@bot.event
async def on_message(message):
    global listening_channel_id, is_creating_channel, name_category_status, name_channel_status
    if message.author == bot.user:
        return

    if message.channel.id == listening_channel_id:

        # await message.channel.send(f"Escuché: {message.content}")
        
        # Procesar mensaje con spaCy
        doc = nlp(message.content.lower())

        # Lógica para crear canales

        keywords_saludar = {"hola", "bot", "buenas", "saludos", "hey", "hello", "hi", "holi", "holis", "holu", "holus", "holaa", "holaaa", "holaaaas", "holaaaaas", "holaaaaaas", "holaaaaaa"}
        keywords_crearcanales = {"crea","crear", "abrir", "generar", "hacer", "iniciar", "nuevo", "canal"}
        types_channels = {"texto": "text",
                 "chat": "text",
                 "chatear":"text",
                 "mensaje": "text",
                 "mensajes": "text",
                 "voz": "voice",
                 "audio": "voice",
                 "llamada": "voice",
                 "hablar": "voice",
                }
        
        channel_name = None
        category_name = None
        channel_type = "text" #Predeterminado a texto
        intent = None
        # is_creating_channel = True
        # name_channel_status = True
        # name_category_status = True

        # Tokenizar el mensaje
        for token in doc:
            if token.lemma_ in keywords_saludar:
                await message.channel.send(f"Hola, {message.author.mention}! ¿En qué puedo ayudarte?")
            if token.lemma_ in keywords_crearcanales:
                intent = "crear_canal"
            if token.lemma_ in types_channels:
                channel_type = types_channels[token.lemma_]
        
        if not channel_name:
            match_name = re.search(r"(llamado|con el nombre|denominado)\s+[\"']([^\"']+)[\"']", message.content)
            if match_name:
                channel_name = match_name.group(2).replace(" ", "-")
                name_channel_status = True
                print(match_name)
                
        # Crear canal
        if intent == "crear_canal":
            if not channel_name and not name_channel_status:
                await message.channel.send("No pude identificar el nombre del canal.\n¿Cómo quieres que se llame el canal? (Escribe el nombre entre comillas)")
                
                try:
                    response = await bot.wait_for(
                        "message",
                        timeout=30.0,  # Espera 30 segundos
                        check=lambda m: m.author == message.author and m.channel == message.channel
                    )
                    channel_name = response.content.replace(" ", "-")
                except:
                    await message.channel.send("No recibí un nombre. Operación cancelada.")
                    name_channel_status = False
                    name_category_status = False
                    return

            # Extraer categoría
            if not category_name and not name_category_status:
                match_category = re.search(r"(categor[ií]a|en)\s+[\"']([^\"']+)[\"']", message.content, re.IGNORECASE)
                if match_category:
                    #category_name = match_category.group(2).replace(" ", "-")
                    category_name = match_category.group(2)
                    name_category_status = True
            
                # Obtener lista de categorías
                guild = message.guild
                categoriesName = {c.name.lower(): c for c in guild.categories}
                categories = [c for c in guild.categories]
                category = categoriesName.get(category_name.lower()) if category_name else None
                if category_name is None and not name_category_status:
                    categories_display = [f"{c.name}" for c in categories]
                    category_list = "(Sin categoría, " + ", ".join(categories_display) + ")"
                    await message.channel.send(f"No pude identificar el nombre de la categoría. \nEscribe el nombre EXACTO de la categoría donde deseas crear el canal:\n{category_list}")
                    try:
                        response = await bot.wait_for("message", timeout=30.0, check=lambda m: m.author == message.author)
                        category_response = response.content.strip().lower()
                        
                        if category_response in ("sin categoría", "sin categoria"):
                            category = None
                        else:
                            # Corrección clave aquí
                            category = categoriesName.get(category_response)
                            if category is None:
                                await message.channel.send("⚠️ Categoría no encontrada. Se creará el canal sin categoría.")
                        name_category_status = True
                        
                    except:
                        await message.channel.send("⏱️ No recibí una respuesta válida. Se creará el canal sin categoría.")
                        category = None
                        name_category_status = True

            if channel_type == "text":
                new_channel = await guild.create_text_channel(channel_name, category=category)
                tipoCanal="texto"
            else:
                new_channel = await guild.create_voice_channel(channel_name, category=category)
                tipoCanal="voz"

            await message.channel.send(f"Se creo el canal de {tipoCanal} en la categoria {category}. \n<< {new_channel.mention} >>")
            name_channel_status, name_category_status = False, False

    await bot.process_commands(message)

# Definir slash commands
@bot.tree.command(name="set_channel", description="Configura el canal de escucha")
async def set_channel_slash(interaction: discord.Interaction, channel: discord.TextChannel):
    global listening_channel_id
    listening_channel_id = channel.id
    await interaction.response.send_message(f"Canal de escucha configurado a: {channel.mention}.\nRecuerda que si quieres dar ordenes, los nombres de canales, categorias y roles deben ir entre comillas.")

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