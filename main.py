import discord
from discord.ext import commands
import os
import webserver
import spacy
import re
import aiohttp

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
    await ctx.send("Recuerda que si quieres dar órdenes, los nombres de canales, categorías y roles deben ir entre comillas.")

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

# Comando para eliminar un canal
@bot.command(description="Elimina un canal especificado")
async def delete_channel(ctx, channel: discord.TextChannel):
    try:
        await channel.delete()
        await ctx.send(f"El canal {channel.mention} ha sido eliminado.")
    except Exception as e:
        await ctx.send(f"Error al eliminar el canal: {e}")

# Comando para eliminar una categoría
@bot.command(description="Elimina una categoría especificada")
async def delete_category(ctx, category: discord.CategoryChannel):
    try:
        await category.delete()
        await ctx.send(f"La categoría {category.name} ha sido eliminada.")
    except Exception as e:
        await ctx.send(f"Error al eliminar la categoría: {e}")

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
is_creating_channel, name_channel_status, name_category_status = False, False, False

@bot.event
async def on_message(message):
    global listening_channel_id, is_creating_channel, name_category_status, name_channel_status
    if message.author == bot.user or message.guild is None:
        return

    if message.channel.id == listening_channel_id:
        guild = message.guild  # Definir guild aquí para que esté disponible en todo el bloque

        # Procesar mensaje con spaCy
        doc = nlp(message.content.lower())

        # Lógica para crear canales y categorías, y eliminar canales y categorías

        keywords_saludar = {"hola", "bot", "buenas", "saludos", "hey", "hello", "hi", "holi", "holis", "holu", "holus", "holaa", "holaaa", "holaaaas", "holaaaaas", "holaaaaaas", "holaaaaaa"}
        keywords_crear = {"crea", "crear", "abrir", "generar", "hacer", "iniciar", "nuevo"}
        keywords_canal = {"canal", "chat", "texto", "voz", "audio", "llamada", "hablar"}
        keywords_categoria = {"categoría", "categoria"}
        keywords_eliminar = {"eliminar", "borrar", "quitar", "remover", "suprimir"}
        keywords_en = {"en", "dentro", "categoría", "categoria"}  # Palabras clave para identificar categorías
        types_channels = {
            "texto": "text",
            "chat": "text",
            "chatear": "text",
            "mensaje": "text",
            "mensajes": "text",
            "voz": "voice",
            "audio": "voice",
            "llamada": "voice",
            "hablar": "voice",
        }

        channel_name = None
        category_name = None
        channel_type = "text"  # Predeterminado a texto
        intent = None

        # Tokenizar el mensaje
        for token in doc:
            if token.lemma_ in keywords_saludar:
                await message.channel.send(f"Hola, {message.author.mention}! ¿En qué puedo ayudarte?")
            if token.lemma_ in keywords_eliminar:
                intent = "eliminar"  # Priorizar la intención de eliminar
            if token.lemma_ in keywords_crear and intent != "eliminar":
                intent = "crear"
            if token.lemma_ in keywords_canal and intent == "crear":
                intent = "crear_canal"
            if token.lemma_ in keywords_categoria and intent == "crear":
                intent = "crear_categoria"
            if token.lemma_ in types_channels:
                channel_type = types_channels[token.lemma_]

        # Extraer nombres de canal o categoría usando expresiones regulares
        match_name = re.search(r"(llamado|llamada|con el nombre|denominado)\s+[\"']([^\"']+)[\"']", message.content)
        if match_name:
            channel_name = match_name.group(2).replace(" ", "-")
            name_channel_status = True

        match_category = re.search(r"(categor[ií]a|en|dentro)\s+[\"']([^\"']+)[\"']", message.content, re.IGNORECASE)
        if match_category:
            category_name = match_category.group(2)
            name_category_status = True

        # Si solo se escribe "crear", preguntar qué se desea crear
        if intent == "crear" and not any(token.lemma_ in keywords_canal or token.lemma_ in keywords_categoria for token in doc):
            await message.channel.send("¿Qué deseas crear? Escribe `crear canal` o `crear categoría`.")
            return

        # Crear canal en una categoría en un solo mensaje
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
                    name_channel_status = False
                    name_category_status = False
                    return

            if not category_name:
                categoriesName = {c.name.lower(): c for c in guild.categories}
                categories_display = [f"{c.name}" for c in guild.categories]
                category_list = "(Sin categoría, " + ", ".join(categories_display) + ")"
                await message.channel.send(f"No pude identificar el nombre de la categoría. \nEscribe el nombre EXACTO de la categoría donde deseas crear el canal:\n{category_list}")
                try:
                    response = await bot.wait_for("message", timeout=30.0, check=lambda m: m.author == message.author)
                    category_response = response.content.strip().lower()

                    if category_response in ("sin categoría", "sin categoria"):
                        category = None
                    else:
                        category = categoriesName.get(category_response)
                        if category is None:
                            await message.channel.send("⚠️ Categoría no encontrada. Se creará el canal sin categoría.")
                    name_category_status = True

                except:
                    await message.channel.send("⏱️ No recibí una respuesta válida. Se creará el canal sin categoría.")
                    category = None
                    name_category_status = True
            else:
                categoriesName = {c.name.lower(): c for c in guild.categories}
                category = categoriesName.get(category_name.lower())
                if category is None:
                    await message.channel.send(f"⚠️ Categoría '{category_name}' no encontrada. Se creará el canal sin categoría.")
                    category = None

            if channel_type == "text":
                new_channel = await guild.create_text_channel(channel_name, category=category)
                tipoCanal = "texto"
            else:
                new_channel = await guild.create_voice_channel(channel_name, category=category)
                tipoCanal = "voz"

            category_name = category.name if category else "Sin categoría"
            try:
                await message.channel.send(f"Se creó el canal de {tipoCanal} en la categoría {category_name}. \n<< {new_channel.mention} >>")
            except aiohttp.ClientOSError as e:
                print(f"Error de conexión SSL: {e}")
            name_channel_status, name_category_status = False, False
            return

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
            category = None  # Inicializar category como None por defecto
            if not category_name and not name_category_status:
                # Obtener lista de categorías
                categoriesName = {c.name.lower(): c for c in guild.categories}
                categories = [c for c in guild.categories]
                if category_name:
                    category = categoriesName.get(category_name.lower())
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
                tipoCanal = "texto"
            else:
                new_channel = await guild.create_voice_channel(channel_name, category=category)
                tipoCanal = "voz"

            category_name = category.name if category else "Sin categoría"
            try:
                await message.channel.send(f"Se creó el canal de {tipoCanal} en la categoría {category_name}. \n<< {new_channel.mention} >>")
            except aiohttp.ClientOSError as e:
                print(f"Error de conexión SSL: {e}")
            name_channel_status, name_category_status = False, False

        # Crear categoría
        elif intent == "crear_categoria":
            if not category_name:
                await message.channel.send("No pude identificar el nombre de la categoría.\n¿Cómo quieres que se llame la categoría? (Escribe el nombre entre comillas)")
                try:
                    response = await bot.wait_for("message", timeout=30.0, check=lambda m: m.author == message.author and m.channel == message.channel)
                    category_name = response.content.strip().strip("\"'")
                except:
                    await message.channel.send("No recibí un nombre. Operación cancelada.")
                    return

            existing_categories = {c.name.lower(): c for c in guild.categories}
            if category_name.lower() in existing_categories:
                await message.channel.send("Ya existe una categoría con ese nombre.")
            else:
                new_category = await guild.create_category(category_name)
                await message.channel.send(f"Se creó la categoría: {new_category.name}")

        # Eliminar canal o categoría
        elif intent == "eliminar":
            # Extraer el nombre del canal o categoría a eliminar
            match_delete = re.search(r"(canal|categor[ií]a)\s+[\"']([^\"']+)[\"']", message.content, re.IGNORECASE)
            if match_delete:
                target_type = match_delete.group(1).lower()  # "canal" o "categoría"
                target_name = match_delete.group(2).strip()  # Nombre del canal o categoría

                if target_type == "canal":
                    channel = discord.utils.get(guild.channels, name=target_name)
                    if channel:
                        await channel.delete()
                        await message.channel.send(f"El canal {channel.mention} ha sido eliminado.")
                    else:
                        await message.channel.send(f"No se encontró el canal '{target_name}'.")
                elif target_type == "categoría" or target_type == "categoria":
                    category = discord.utils.get(guild.categories, name=target_name)
                    if category:
                        await category.delete()
                        await message.channel.send(f"La categoría {category.name} ha sido eliminada.")
                    else:
                        await message.channel.send(f"No se encontró la categoría '{target_name}'.")
            else:
                await message.channel.send("No pude identificar qué deseas eliminar. Por favor, escribe algo como: `borrar canal \"Nombre del canal\"` o `borrar categoría \"Nombre de la categoría\"`.")

    await bot.process_commands(message)

# Definir slash commands
@bot.tree.command(name="set_channel", description="Configura el canal de escucha")
async def set_channel_slash(interaction: discord.Interaction, channel: discord.TextChannel):
    global listening_channel_id
    listening_channel_id = channel.id
    await interaction.response.send_message(f"Canal de escucha configurado a: {channel.mention}.\nRecuerda que si quieres dar órdenes, los nombres de canales, categorías y roles deben ir entre comillas.")

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

@bot.tree.command(name="delete_channel", description="Elimina un canal especificado")
async def delete_channel_slash(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        await channel.delete()
        await interaction.response.send_message(f"El canal {channel.mention} ha sido eliminado.")
    except Exception as e:
        await interaction.response.send_message(f"Error al eliminar el canal: {e}")

@bot.tree.command(name="delete_category", description="Elimina una categoría especificada")
async def delete_category_slash(interaction: discord.Interaction, category: discord.CategoryChannel):
    try:
        await category.delete()
        await interaction.response.send_message(f"La categoría {category.name} ha sido eliminada.")
    except Exception as e:
        await interaction.response.send_message(f"Error al eliminar la categoría: {e}")

webserver.keep_alive()
bot.run(DISCORD_TOKEN)