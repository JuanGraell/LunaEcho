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
@bot.event
async def on_message(message):
    global listening_channel_id
    if message.author == bot.user:
        return

    if message.channel.id == listening_channel_id:

        # await message.channel.send(f"Escuché: {message.content}")
        
        # Procesar mensaje con spaCy
        doc = nlp(message.content.lower())

        # Lógica para crear canales

        keywords_saludar = {"hola", "bot", "buenas", "saludos", "hey", "hello", "hi", "holi", "holis", "holu", "holus", "holaa", "holaaa", "holaaaas", "holaaaaas", "holaaaaaas", "holaaaaaa"}
        keywords_crearcanales = {"crear", "abrir", "generar", "hacer", "iniciar", "nuevo", "canal"}
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

        # Tokenizar el mensaje
        for token in doc:
            if token.lemma_ in keywords_saludar:
                await message.channel.send(f"Hola, {message.author.mention}! ¿En qué puedo ayudarte?")
            if token.lemma_ in keywords_crearcanales:
                intent = "crear_canal"
            if token.lemma_ in types_channels:
                channel_type = types_channels[token.lemma_]

        # Extraer el posible nombre del canal
        # for ent in doc.ents:
        #     if ent.label_ in ["MISC", "ORG", "PRODUCT"]:
        #         channel_name = ent.text.replace(" ", "-")
        #         print(doc.ents)
        
        
        if not channel_name:
            match_name = re.search(r"(llamado|con el nombre|denominado)\s+[\"']([^\"']+)[\"']", message.content)
            if match_name:
                channel_name = match_name.group(2).replace(" ", "-")
                print(match_name)
                

        # Crear canal
        if intent == "crear_canal":
            if not channel_name:
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
                    return

            # Extraer categoría
            if not category_name:
                match_category = re.search(r"(categoria)\s+[\"']([^\"']+)[\"']", message.content)
                if match_category:
                    #category_name = match_category.group(2).replace(" ", "-")
                    category_name = match_category.group(2)
                    print(category_name)
            
            # Obtener lista de categorías
            guild = message.guild
            categoriesName = {c.name.lower(): c for c in guild.categories}  # Mapeo de nombre a categoría
            categories = [c for c in message.guild.categories]
            category = categoriesName.get(category_name.lower()) if category_name else None
            print("categorias: ",categories)
            if category_name is None:
                category_list = "\n".join(f"**{i+1}.** {c.name}" for i, c in enumerate(categories))
                category_list = f"**0.** Sin categoría\n{category_list}"
                await message.channel.send(f"Selecciona la categoría donde deseas crear el canal:\n{category_list}")

                try:
                    response = await bot.wait_for(
                        "message",
                        timeout=30.0,
                        check=lambda m: m.author == message.author and m.channel == message.channel
                    )
                    selected_index = int(response.content) - 1
                    if selected_index == -1:
                        category = None
                    elif 0 <= selected_index < len(categories):
                        category = categories[selected_index]
                    else:
                        await message.channel.send("Selección inválida. Se creará el canal sin categoría.")
                except:
                    await message.channel.send("No recibí una respuesta válida. Se creará el canal sin categoría.")

            elif category_name.lower() not in categoriesName:
                await message.channel.send("No existe la categoría especificada. Selecciona una categoría válida:")
                category_list = "\n".join(f"**{i+1}.** {c.name}" for i, c in enumerate(categories))
                category_list = f"**0.** Sin categoría\n{category_list}"
                await message.channel.send(f"Selecciona la categoría donde deseas crear el canal:\n{category_list}")
    
                try:
                    response = await bot.wait_for(
                        "message",
                        timeout=30.0,
                        check=lambda m: m.author == message.author and m.channel == message.channel
                    )
                    selected_index = int(response.content) - 1
                    if selected_index == -1:
                        category = None
                    elif 0 <= selected_index < len(categories):
                        category = categories[selected_index]
                    else:
                        await message.channel.send("Selección inválida. Se creará el canal sin categoría.")
                except:
                    await message.channel.send("No recibí una respuesta válida. Se creará el canal sin categoría.")
            elif category_name in categoriesName:
                pass

            if channel_type == "text":
                new_channel = await guild.create_text_channel(channel_name, category=category)
                tipoCanal="texto"
            else:
                new_channel = await guild.create_voice_channel(channel_name, category=category)
                tipoCanal="voz"

            await message.channel.send(f"Se creo el canal de {tipoCanal} en la categoria {category}. \n<< {new_channel.mention} >>")

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