import discord
from discord.ext import commands
import os
import webserver
import spacy
import re
from spacy.matcher import Matcher
from rapidfuzz import process, fuzz
from typing import Optional, Dict, Set, Any
import spacy
import aiohttp

# Token de Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Cargar el modelo de spaCy (se intenta primero el modelo mediano)
try:
    nlp = spacy.load("es_core_news_md")
except Exception:
    nlp = spacy.load("es_core_news_sm")

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix='Lu!', intents=intents)

nlp = spacy.load("es_core_news_sm")

# Configuración global centralizada
config: Dict[str, Any] = {
    "listening_channel_id": None,   # ID del canal en el que el bot escucha
    "listening_message": None,        # Mensaje de escucha (si se configura)
    "allowed_users": {}               # {guild_id: set(user_id, ...)}
}

# Roles por default para staff (ejemplo para comando "staff")
default_staff_roles = {
    "Owner": {"administrator": True},
    "Co-Owner": {"manage_guild": True, "manage_roles": True, "manage_channels": True, "ban_members": True, "kick_members": True},
    "Admin": {"manage_channels": True, "ban_members": True, "kick_members": True, "manage_messages": True},
    "Mod": {"manage_messages": True, "kick_members": True}
}

# Diccionarios de permisos y descripciones
permissions_mapping: Dict[str, str] = {
    "administrador": "administrator",
    "administrator": "administrator",
    "banear": "ban_members",
    "banear miembros": "ban_members",
    "ban": "ban_members",
    "ban_members": "ban_members",
    "expulsar": "kick_members",
    "kick": "kick_members",
    "kickear": "kick_members",
    "kick_members": "kick_members",
    "gestionar servidor": "manage_guild",
    "manage guild": "manage_guild",
    "manage_guild": "manage_guild",
    "gestionar roles": "manage_roles",
    "manage roles": "manage_roles",
    "manage_roles": "manage_roles",
    "gestionar canales": "manage_channels",
    "manage channels": "manage_channels",
    "manage_channels": "manage_channels",
    "crear invitaciones": "create_instant_invite",
    "create invitation": "create_instant_invite",
    "create invites": "create_instant_invite",
    "create_instant_invite": "create_instant_invite",
    "cambiar apodo": "change_nickname",
    "change nickname": "change_nickname",
    "change_nickname": "change_nickname",
    "gestionar apodos": "manage_nicknames",
    "manage nicknames": "manage_nicknames",
    "manage_nicknames": "manage_nicknames",
    "gestionar emojis": "manage_emojis",
    "manage emojis": "manage_emojis",
    "manage_emojis": "manage_emojis",
    "gestionar webhooks": "manage_webhooks",
    "manage webhooks": "manage_webhooks",
    "manage_webhooks": "manage_webhooks",
    "moderar mensajes": "manage_messages",
    "manage messages": "manage_messages",
    "manage_messages": "manage_messages",
    "enviar mensajes": "send_messages",
    "send messages": "send_messages",
    "send_messages": "send_messages",
    "enviar mensajes tts": "send_tts_messages",
    "send tts messages": "send_tts_messages",
    "send_tts_messages": "send_tts_messages",
    "insertar links": "embed_links",
    "embed links": "embed_links",
    "embed_links": "embed_links",
    "adjuntar archivos": "attach_files",
    "attach files": "attach_files",
    "attach_files": "attach_files",
    "leer historial": "read_message_history",
    "read history": "read_message_history",
    "read_message_history": "read_message_history",
    "mencionar a todos": "mention_everyone",
    "mention everyone": "mention_everyone",
    "mention_everyone": "mention_everyone",
    "usar emojis externos": "external_emojis",
    "external emojis": "external_emojis",
    "external_emojis": "external_emojis",
    "agregar reacciones": "add_reactions",
    "add reactions": "add_reactions",
    "add_reactions": "add_reactions",
    "conectar": "connect",
    "connect": "connect",
    "hablar": "speak",
    "speak": "speak",
    "silenciar miembros": "mute_members",
    "mute members": "mute_members",
    "mute_members": "mute_members",
    "ensordecer miembros": "deafen_members",
    "deafen members": "deafen_members",
    "deafen_members": "deafen_members",
    "mover miembros": "move_members",
    "move members": "move_members",
    "move_members": "move_members",
    "usar vad": "use_vad",
    "use vad": "use_vad",
    "use_vad": "use_vad",
    "revisar audit log": "view_audit_log",
    "ver audit log": "view_audit_log",
    "audit log": "view_audit_log",
    "desconectar miembros": "move_members"
}

permissions_descriptions: Dict[str, str] = {
    "administrator": "Permite la administración completa del servidor.",
    "ban_members": "Permite banear a miembros.",
    "kick_members": "Permite expulsar a miembros.",
    "manage_guild": "Permite gestionar el servidor.",
    "manage_roles": "Permite gestionar roles.",
    "manage_channels": "Permite gestionar canales.",
    "create_instant_invite": "Permite crear invitaciones instantáneas.",
    "change_nickname": "Permite cambiar apodos.",
    "manage_nicknames": "Permite gestionar apodos.",
    "manage_emojis": "Permite gestionar emojis.",
    "manage_webhooks": "Permite gestionar webhooks.",
    "manage_messages": "Permite gestionar mensajes (editar, borrar, etc.).",
    "send_messages": "Permite enviar mensajes.",
    "send_tts_messages": "Permite enviar mensajes TTS.",
    "embed_links": "Permite insertar links en mensajes.",
    "attach_files": "Permite adjuntar archivos.",
    "read_message_history": "Permite leer el historial de mensajes.",
    "mention_everyone": "Permite mencionar a todos.",
    "external_emojis": "Permite usar emojis externos.",
    "add_reactions": "Permite agregar reacciones.",
    "connect": "Permite conectarse a canales de voz.",
    "speak": "Permite hablar en canales de voz.",
    "mute_members": "Permite silenciar a miembros.",
    "deafen_members": "Permite ensordecer a miembros.",
    "move_members": "Permite mover miembros entre canales de voz.",
    "use_vad": "Permite usar la detección de actividad de voz.",
    "view_audit_log": "Permite revisar el registro de auditoría."
}

# Configuración global del Matcher de spaCy para comandos de creación de rol
matcher = Matcher(nlp.vocab)
role_pattern = [
    {"LOWER": {"IN": ["crear", "haz", "genera", "generar", "armar", "construir"]}},
    {"LOWER": {"IN": ["un", "el", "la"]}, "OP": "?"},
    {"LOWER": "rol"},
    {"LOWER": {"IN": ["llamado", "nombrado", "denominado"]}},
    {"IS_PUNCT": False, "OP": "+"}
]
matcher.add("ROLE_CREATE", [role_pattern])

def get_permission(perm_item: str) -> Optional[str]:
    perm_item = perm_item.strip().lower()
    perm_item = re.sub(r'^(de\s+|del\s+|la\s+|los\s+)', '', perm_item)
    if perm_item in permissions_mapping:
        return permissions_mapping[perm_item]
    best_match = process.extractOne(perm_item, permissions_mapping.keys(), scorer=fuzz.partial_ratio)
    if best_match and best_match[1] >= 80:
        return permissions_mapping[best_match[0]]
    return None

def process_color(color_input: str) -> Optional[discord.Color]:
    color_input = color_input.strip()
    if color_input.startswith("#"):
        try:
            hex_value = int(color_input[1:], 16)
            return discord.Color(hex_value)
        except Exception:
            return None
    color_names = {
        "rojo": 0xFF0000,
        "verde": 0x00FF00,
        "azul": 0x0000FF,
        "amarillo": 0xFFFF00,
        "naranja": 0xFFA500,
        "morado": 0x800080,
        "rosa": 0xFFC0CB,
        "negro": 0x000000,
        "blanco": 0xFFFFFF,
        "gris": 0x808080,
    }
    return discord.Color(color_names[color_input.lower()]) if color_input.lower() in color_names else None

def parse_role_command(text: str) -> Dict[str, Any]:
    result = {"role_name": "", "permissions_text": "", "color": "", "mentionable": False, "hoisted": False}
    name_match = re.search(r'(?i)rol\s+(?:llamado|nombrado|denominado)\s+["\']?(?P<rolename>[^"\'\n]+)["\']?', text)
    if name_match:
        result["role_name"] = name_match.group("rolename").strip()
    colors = re.findall(r'(?i)(?:de|con|tenga(?:\s+el)?)\s+color\s+([a-zA-Z0-9#]+)\b', text)
    if colors:
        result["color"] = colors[-1].strip()
    perms_match = re.search(
        r'(?i)(?:tenga\s+los\s+permisos\s+de|con\s+permisos\s+de)\s+(?P<perms>.+?)(?=\s*(?:,?\s*(?:de\s+color|$)))', text
    )
    if perms_match:
        result["permissions_text"] = perms_match.group("perms").strip()
    result["mentionable"] = bool(re.search(r'(?i)mencionable', text))
    result["hoisted"] = bool(re.search(r'(?i)(destacado|hoisted|arriba)', text))
    return result

def segment_message(text: str) -> list:
    segments = re.split(r'\s*(?:\n| y )\s*', text)
    return [seg for seg in segments if seg.strip()]

def detect_intent(text: str) -> str:
    text_lower = text.lower()
    if any(x in text_lower for x in ["crear rol", "rol llamado", "rol nombrado", "rol denominado"]):
        return "crear_rol"
    if any(x in text_lower for x in ["mover rol", "por encima", "arriba", "encima", "debajo"]):
        return "mover_rol"
    if any(x in text_lower for x in ["asignar rol", "asigna el rol", "añadir rol", "agregar rol", "dale el rol"]):
        return "asignar_rol"
    if any(x in text_lower for x in ["borrar rol", "borra el rol"]):
        return "borrar_rol"
    if any(x in text_lower for x in ["modificar rol", "cambiar rol", "tenga permiso", "modifica", "modifica el rol"]):
        return "modificar_rol"
    return "desconocido"

async def prompt_user(message: discord.Message, prompt: str, timeout: int = 30) -> Optional[discord.Message]:
    await message.channel.send(prompt)
    try:
        response = await bot.wait_for(
            "message",
            check=lambda m: m.author == message.author and m.channel == message.channel,
            timeout=timeout
        )
        return response
    except Exception:
        return None

async def process_command(segment: str, message: discord.Message):
    if len(segment.split()) < 3:
        return
    intent = detect_intent(segment)
    
    if intent == "crear_rol":
        role_data = parse_role_command(segment)
        if not role_data or not role_data["role_name"]:
            await message.channel.send("No se pudo extraer el nombre del rol.")
            return
        role_name = role_data["role_name"]
        perms_text = role_data["permissions_text"]
        role_color = process_color(role_data["color"]) if role_data["color"] else None
        perms_dict = {}
        if perms_text:
            perms_items = re.split(r'\s*(?:,| y | and )\s*', perms_text.lower())
            for perm_item in perms_items:
                perm = get_permission(perm_item)
                if perm:
                    perms_dict[perm] = True
        if not perms_dict:
            response = await prompt_user(message, f"No se detectaron permisos válidos para el rol **{role_name}**. ¿Desea configurarlos de manera interactiva? (sí/no)")
            if response and response.content.lower() in ["sí", "si"]:
                for perm, description in permissions_descriptions.items():
                    r = await prompt_user(message, f"El permiso **{perm}**: {description}\n¿Desea agregarlo? (sí/no)")
                    if r and r.content.lower() in ["sí", "si"]:
                        perms_dict[perm] = True
                extra = await prompt_user(message, "¿Desea agregar algún permiso adicional no listado? (sí/no)")
                if extra and extra.content.lower() in ["sí", "si"]:
                    await message.channel.send("Ingrese el permiso adicional (escriba 'fin' para terminar):")
                    while True:
                        extra_perm = await bot.wait_for(
                            "message",
                            check=lambda m: m.author == message.author and m.channel == message.channel,
                            timeout=30
                        )
                        if extra_perm.content.lower() == "fin":
                            break
                        p = get_permission(extra_perm.content)
                        if p:
                            perms_dict[p] = True
                            await message.channel.send(f"Permiso **{p}** agregado.")
                        else:
                            await message.channel.send("Permiso no reconocido.")
            else:
                perms_dict = {}
        if not role_color:
            response = await prompt_user(message, f"No se detectó un color válido para el rol **{role_name}**. ¿Desea configurarlo? (sí/no)\nPuedes consultar https://www.color-hex.com/ para buscar códigos hexadecimales.")
            if response and response.content.lower() in ["sí", "si"]:
                default_colors = "rojo, verde, azul, amarillo, naranja, morado, rosa, negro, blanco, gris"
                attempts = 0
                valid = False
                while not valid and attempts < 3:
                    col_resp = await prompt_user(
                        message,
                        f"Ingrese el color (nombre o código hexadecimal). Colores válidos: {default_colors}.\n"
                        "Si no te gustan esos, consulta https://www.color-hex.com/ para más opciones.\n"
                        "(Escribe 'cancelar' para usar el color por defecto.)"
                    )
                    if col_resp and col_resp.content.lower() == "cancelar":
                        break
                    role_color = process_color(col_resp.content) if col_resp else None
                    if role_color:
                        valid = True
                    else:
                        await message.channel.send("Color no reconocido.")
                    attempts += 1
            else:
                role_color = None
        mentionable = role_data["mentionable"]
        hoisted = role_data["hoisted"]
        role_kwargs = {
            "name": role_name,
            "permissions": discord.Permissions(**perms_dict),
            "mentionable": mentionable,
            "hoist": hoisted
        }
        if role_color is not None:
            role_kwargs["color"] = role_color
        try:
            new_role = await message.guild.create_role(**role_kwargs)
            await message.channel.send(f"Se creó el rol **{new_role.name}** en la posición {new_role.position}.")
        except Exception as e:
            await message.channel.send(f"Error al crear el rol: {e}")
    
    elif intent == "modificar_rol":
        # Si se menciona "permiso" se modifica la configuración de permisos
        if "permiso" in segment.lower():
            mod_pattern = re.compile(
                r'^(?:quiero\s+que\s+|modifica(?:r)?\s+(?:el\s+rol\s+)?)[\'"]?(?P<role_name>[^"\']+)[\'"]?.*tenga\s+permiso[s]?\s+(?:de\s+)?(?P<perm_text>.+)$',
                re.IGNORECASE
            )
            mod_match = mod_pattern.search(segment)
            if mod_match:
                role_name_mod = mod_match.group("role_name").strip().strip('"').strip("'")
                perm_text = mod_match.group("perm_text").strip()
                role_to_modify = discord.utils.get(message.guild.roles, name=role_name_mod)
                if not role_to_modify:
                    for r in message.guild.roles:
                        if r.name.lower() == role_name_mod.lower():
                            role_to_modify = r
                            break
                if role_to_modify:
                    perms_items = re.split(r'\s*(?:,| y | and )\s*', perm_text.lower())
                    new_perms = role_to_modify.permissions
                    for perm_item in perms_items:
                        perm = get_permission(perm_item)
                        if perm:
                            setattr(new_perms, perm, True)
                    try:
                        await role_to_modify.edit(permissions=new_perms)
                        await message.channel.send(f"El rol **{role_to_modify.name}** fue modificado.")
                    except Exception as e:
                        await message.channel.send(f"Error al modificar el rol: {e}")
                else:
                    await message.channel.send("No se encontró el rol para modificar.")
            else:
                await message.channel.send("No se pudo interpretar la modificación de rol.")
        else:
            # Modificar opciones: marcaje (hoist) y mencionable
            mod_options_pattern = re.compile(
                r'(?:modifica(?:r)?(?:\s+el\s+rol\s+)?|modificar rol)\s+["\']?(?P<role_name>[^"\']+)["\']?(?:\s+para\s+que\s+(?P<options>.+))?',
                re.IGNORECASE
            )
            mod_options_match = mod_options_pattern.search(segment)
            if mod_options_match:
                role_name_mod = mod_options_match.group("role_name").strip().strip('"').strip("'")
                options_text = mod_options_match.group("options") or ""
                role_to_modify = discord.utils.get(message.guild.roles, name=role_name_mod)
                if not role_to_modify:
                    for r in message.guild.roles:
                        if r.name.lower() == role_name_mod.lower():
                            role_to_modify = r
                            break
                if role_to_modify:
                    new_mentionable = role_to_modify.mentionable or ("mencionable" in options_text.lower())
                    new_hoist = role_to_modify.hoist or (
                        "destacado" in options_text.lower() or 
                        "destacable" in options_text.lower() or 
                        "hoisted" in options_text.lower() or 
                        "arriba" in options_text.lower()
                    )
                    try:
                        await role_to_modify.edit(mentionable=new_mentionable, hoist=new_hoist)
                        await message.channel.send(f"El rol **{role_to_modify.name}** se modificó: mencionable={new_mentionable}, destacado={new_hoist}.")
                    except Exception as e:
                        await message.channel.send(f"Error al modificar el rol: {e}")
                else:
                    await message.channel.send("No se encontró el rol para modificar.")
            else:
                await message.channel.send("No se pudo interpretar la modificación de rol.")
    
    elif intent == "mover_rol":
        move_pattern = re.compile(
            r'(?i)(?:mover(?:\s+el)?\s+rol\s+)?["\']?(?P<role1>[^"\']+)["\']?\s+(?:por\s+encima\s+de|arriba\s+de|encima\s+de|debajo\s+de)\s+["\']?(?P<role2>[^"\']+)["\']?'
        )
        move_match = move_pattern.search(segment)
        if move_match:
            role1 = move_match.group("role1").strip()
            role2 = move_match.group("role2").strip()
            role_to_move = discord.utils.get(message.guild.roles, name=role1)
            role_ref = discord.utils.get(message.guild.roles, name=role2)
            if not role_to_move:
                for r in message.guild.roles:
                    if r.name.lower() == role1.lower():
                        role_to_move = r
                        break
            if not role_ref:
                for r in message.guild.roles:
                    if r.name.lower() == role2.lower():
                        role_ref = r
                        break
            if role_to_move and role_ref:
                new_position = role_ref.position + 1 if re.search(r'(?i)(encima|arriba)', segment) else max(role_ref.position - 1, 0)
                try:
                    await role_to_move.edit(position=new_position)
                    await message.channel.send(f"El rol **{role_to_move.name}** se movió respecto a **{role_ref.name}**.")
                except discord.HTTPException as e:
                    if e.code == 50013:
                        await message.channel.send("No tengo los suficientes permisos para mover el rol.")
                    else:
                        await message.channel.send("Error al mover el rol.")
            else:
                await message.channel.send("No se encontraron los roles especificados para mover.")
        else:
            await message.channel.send("No se pudo interpretar el comando de mover rol.")
    
    elif intent == "borrar_rol":
        del_pattern = re.compile(r'(?i)(?:borrar|borra)\s+el\s+rol\s+["\']?(?P<role_name>[^"\']+)["\']?')
        del_match = del_pattern.search(segment)
        if del_match:
            role_name_del = del_match.group("role_name").strip().strip('"').strip("'")
            role_to_delete = discord.utils.get(message.guild.roles, name=role_name_del)
            if not role_to_delete:
                for r in message.guild.roles:
                    if r.name.lower() == role_name_del.lower():
                        role_to_delete = r
                        break
            if role_to_delete:
                confirmation = await prompt_user(message, f"¿Está seguro que desea borrar el rol **{role_to_delete.name}**? (sí/no)")
                if confirmation and confirmation.content.lower() in ["sí", "si"]:
                    try:
                        await role_to_delete.delete()
                        await message.channel.send(f"El rol **{role_to_delete.name}** fue borrado.")
                    except discord.HTTPException as e:
                        if e.code == 50013:
                            await message.channel.send("No tengo los suficientes permisos para borrar el rol.")
                        else:
                            await message.channel.send("Error al borrar el rol.")
                else:
                    await message.channel.send("Operación cancelada.")
            else:
                await message.channel.send("No se encontró el rol para borrar.")
        else:
            await message.channel.send("No se pudo interpretar el comando de borrar rol.")
    
    elif intent == "asignar_rol":
        assign_pattern = re.compile(
            r'(?i)(?:asignar|asigna|añadir|agregar)\s+(?:el\s+)?rol\s+["\']?(?P<role_name>[^"\']+)["\']?\s+(?:a|al)\s+(?P<member>.+)'
        )
        assign_match = assign_pattern.search(segment)
        if assign_match:
            role_name_assign = assign_match.group("role_name").strip().strip('"').strip("'")
            member_str = assign_match.group("member").strip()
            member = None
            member_id_match = re.search(r'<@!?(\d+)>', member_str)
            if member_id_match:
                member_id = int(member_id_match.group(1))
                member = message.guild.get_member(member_id)
            if not member:
                member = discord.utils.get(message.guild.members, name=member_str.lstrip("@"))
            role_to_assign = discord.utils.get(message.guild.roles, name=role_name_assign)
            if role_to_assign and member:
                try:
                    await member.add_roles(role_to_assign)
                    await message.channel.send(f"El rol **{role_to_assign.name}** fue asignado a {member.mention}.")
                except Exception as e:
                    await message.channel.send(f"Error al asignar el rol: {e}")
            else:
                await message.channel.send("No se encontró el rol o el usuario para asignar.")
        else:
            await message.channel.send("No se pudo interpretar el comando de asignar rol.")

@bot.event
async def on_message(message: discord.Message):
    # Ignorar mensajes del bot o mensajes privados
    if message.author == bot.user or not message.guild:
        return

    guild_id = message.guild.id
    # Si no existe aún, se configura allowed_users con el dueño del servidor
    if guild_id not in config["allowed_users"]:
        config["allowed_users"][guild_id] = {message.guild.owner_id}
    # Solo procesar si el autor está en la lista de permitidos
    if message.author.id not in config["allowed_users"][guild_id]:
        return

    # ---------------------------
    # PARTE DE ROLES:
    # Procesa cada segmento del mensaje (por ejemplo: "crea un rol llamado 'Prueba'" o "modifica el rol 'Sol'")
    segments = segment_message(message.content)
    for segment in segments:
        await process_command(segment, message)

    # ---------------------------
    # PARTE DE CANALES Y CATEGORÍAS:
    # Se procesa siempre, sin depender de que el mensaje esté en un canal específico.
    guild = message.guild
    doc = nlp(message.content.lower())

    # Definir palabras clave para detectar intenciones
    keywords_saludar = {"hola", "bot", "buenas", "saludos", "hey", "hello", "hi", "holi", "holis", "holu", "holus"}
    keywords_crear = {"crea", "crear", "abrir", "generar", "hacer", "iniciar", "nuevo"}
    keywords_canal = {"canal", "chat", "texto", "voz", "audio", "llamada", "hablar"}
    keywords_categoria = {"categoría", "categoria"}
    keywords_eliminar = {"eliminar", "borrar", "quitar", "remover", "suprimir"}
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
    channel_type = "text"  # Valor predeterminado
    intent = None

    # Analizar tokens para determinar intención
    for token in doc:
        if token.lemma_ in keywords_saludar:
            await message.channel.send(f"Hola, {message.author.mention}! ¿En qué puedo ayudarte?")
        if token.lemma_ in keywords_eliminar:
            intent = "eliminar"  # Se da prioridad a la intención de eliminar
        if token.lemma_ in keywords_crear and intent != "eliminar":
            intent = "crear"
        if token.lemma_ in keywords_canal and intent == "crear":
            intent = "crear_canal"
        if token.lemma_ in keywords_categoria and intent == "crear":
            intent = "crear_categoria"
        if token.lemma_ in types_channels:
            channel_type = types_channels[token.lemma_]

    # Extraer nombre de canal (si lo hay) mediante expresión regular
    match_name = re.search(r"(llamado|con el nombre|denominado)\s+[\"']([^\"']+)[\"']", message.content)
    if match_name:
        channel_name = match_name.group(2).replace(" ", "-")

    # Extraer nombre de categoría (si lo hay)
    match_category = re.search(r"(categor[ií]a|en|dentro)\s+[\"']([^\"']+)[\"']", message.content, re.IGNORECASE)
    if match_category:
        category_name = match_category.group(2)

    # Si se escribió solo "crear" sin especificar qué, se pregunta
    if intent == "crear" and not any(token.lemma_ in keywords_canal or token.lemma_ in keywords_categoria for token in doc):
        await message.channel.send("¿Qué deseas crear? Escribe `crear canal` o `crear categoría`.")
        return

    # Lógica para crear un canal
    if intent == "crear_canal":
        if not channel_name:
            await message.channel.send("No pude identificar el nombre del canal.\n¿Cómo quieres que se llame? (Escribe el nombre entre comillas)")
            try:
                response = await bot.wait_for(
                    "message",
                    timeout=30.0,
                    check=lambda m: m.author == message.author and m.channel == message.channel
                )
                channel_name = response.content.replace(" ", "-")
            except:
                await message.channel.send("No recibí un nombre. Operación cancelada.")
                return

        # Intentar determinar la categoría, si se especifica
        categoriesName = {c.name.lower(): c for c in guild.categories}
        category = None
        if category_name:
            category = categoriesName.get(category_name.lower())
            if category is None:
                await message.channel.send(f"⚠️ Categoría '{category_name}' no encontrada. Se creará el canal sin categoría.")
        else:
            # Si no se identificó la categoría, se pregunta al usuario
            categories_display = [c.name for c in guild.categories]
            category_list = "(Sin categoría, " + ", ".join(categories_display) + ")"
            await message.channel.send(f"No pude identificar la categoría.\nEscribe el nombre EXACTO de la categoría donde deseas crear el canal:\n{category_list}")
            try:
                response = await bot.wait_for(
                    "message",
                    timeout=30.0,
                    check=lambda m: m.author == message.author
                )
                category_response = response.content.strip().lower()
                if category_response in ("sin categoría", "sin categoria"):
                    category = None
                else:
                    category = categoriesName.get(category_response)
                    if category is None:
                        await message.channel.send("⚠️ Categoría no encontrada. Se creará el canal sin categoría.")
                # Una vez obtenida la respuesta, no se vuelve a preguntar
            except:
                await message.channel.send("⏱️ No recibí respuesta válida. Se creará el canal sin categoría.")
                category = None

        # Crear el canal según el tipo
        if channel_type == "text":
            new_channel = await guild.create_text_channel(channel_name, category=category)
            tipoCanal = "texto"
        else:
            new_channel = await guild.create_voice_channel(channel_name, category=category)
            tipoCanal = "voz"

        category_display = category.name if category else "Sin categoría"
        await message.channel.send(f"Se creó el canal de {tipoCanal} en la categoría {category_display}.\n<< {new_channel.mention} >>")
        return

    # Lógica para crear una categoría
    elif intent == "crear_categoria":
        if not category_name:
            await message.channel.send("No pude identificar el nombre de la categoría.\n¿Cómo deseas llamarla? (Escribe el nombre entre comillas)")
            try:
                response = await bot.wait_for(
                    "message",
                    timeout=30.0,
                    check=lambda m: m.author == message.author and m.channel == message.channel
                )
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

    # Lógica para eliminar canal o categoría
    elif intent == "eliminar":
        match_delete = re.search(r"(canal|categor[ií]a)\s+[\"']([^\"']+)[\"']", message.content, re.IGNORECASE)
        if match_delete:
            target_type = match_delete.group(1).lower()  # "canal" o "categoría"
            target_name = match_delete.group(2).strip()
            if target_type == "canal":
                channel = discord.utils.get(guild.channels, name=target_name)
                if channel:
                    await channel.delete()
                    await message.channel.send(f"El canal {channel.mention} ha sido eliminado.")
                else:
                    await message.channel.send(f"No se encontró el canal '{target_name}'.")
            elif target_type in {"categoría", "categoria"}:
                category = discord.utils.get(guild.categories, name=target_name)
                if category:
                    await category.delete()
                    await message.channel.send(f"La categoría {category.name} ha sido eliminada.")
                else:
                    await message.channel.send(f"No se encontró la categoría '{target_name}'.")
        else:
            await message.channel.send("No pude identificar qué deseas eliminar. Por favor, usa: `borrar canal \"Nombre\"` o `borrar categoría \"Nombre\"`.")

    # Procesa otros comandos registrados (como comandos de barra)
    await bot.process_commands(message)

# ---------------------------
# Comandos de configuración y de canales/categorías (se mantienen tal cual)
@bot.command(description="Configura el canal de escucha")
async def set_channel(ctx: commands.Context, channel: discord.TextChannel):
    config["listening_channel_id"] = channel.id
    await ctx.send(f"Canal de escucha configurado a: {channel.mention}")

@bot.command(description="Deja de escuchar en el canal configurado")
async def unset_channel(ctx: commands.Context):
    config["listening_channel_id"] = None
    await ctx.send("El bot ha dejado de escuchar en el canal configurado.")

@bot.command(name="set_message", description="Configura el mensaje de escucha")
async def set_message(ctx: commands.Context, *, message_content: str):
    config["listening_message"] = message_content
    await ctx.send(f"Mensaje de escucha configurado: {message_content}")

@bot.command(name="unset_message", description="Elimina el mensaje de escucha configurado")
async def unset_message(ctx: commands.Context):
    config["listening_message"] = None
    await ctx.send("El mensaje de escucha ha sido eliminado.")

@bot.command(name="bot_help", description="Lista todos los comandos disponibles")
async def bot_help(ctx: commands.Context):
    commands_list = "\n".join([f"/{command.name} - {command.description}" for command in bot.commands])
    await ctx.send(f"Comandos disponibles:\n{commands_list}")

@bot.command(description="Elimina un canal especificado")
async def delete_channel(ctx, channel: discord.TextChannel):
    try:
        await channel.delete()
        await ctx.send(f"El canal {channel.mention} ha sido eliminado.")
    except Exception as e:
        await ctx.send(f"Error al eliminar el canal: {e}")

@bot.command(description="Elimina una categoría especificada")
async def delete_category(ctx, category: discord.CategoryChannel):
    try:
        await category.delete()
        await ctx.send(f"La categoría {category.name} ha sido eliminada.")
    except Exception as e:
        await ctx.send(f"Error al eliminar la categoría: {e}")

# Comandos slash (incluyendo add_allowed y remove_allowed)
@bot.tree.command(name="set_channel", description="Configura el canal de escucha")
async def set_channel_slash(interaction: discord.Interaction, channel: discord.TextChannel):
    config["listening_channel_id"] = channel.id
    await interaction.response.send_message(f"Canal de escucha configurado a: {channel.mention}")

@bot.tree.command(name="unset_channel", description="Deja de escuchar en el canal de escucha")
async def unset_channel_slash(interaction: discord.Interaction):
    config["listening_channel_id"] = None
    await interaction.response.send_message("El bot ha dejado de escuchar en el canal configurado.")

@bot.tree.command(name="bot_help", description="Lista todos los comandos disponibles")
async def bot_help_slash(interaction: discord.Interaction):
    commands_list = "\n".join([f"/{command.name} - {command.description}" for command in bot.commands])
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

@bot.tree.command(name="add_allowed", description="Agrega un miembro a la lista de usuarios permitidos")
async def add_allowed_slash(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("Solo el dueño del servidor puede ejecutar este comando.", ephemeral=True)
        return
    guild_id = interaction.guild.id
    allowed: Set[int] = config["allowed_users"].get(guild_id, set())
    allowed.add(member.id)
    config["allowed_users"][guild_id] = allowed
    await interaction.response.send_message(f"{member.mention} ha sido agregado a la lista de usuarios permitidos.")

@bot.tree.command(name="remove_allowed", description="Elimina un miembro de la lista de usuarios permitidos")
async def remove_allowed_slash(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("Solo el dueño del servidor puede ejecutar este comando.", ephemeral=True)
        return
    guild_id = interaction.guild.id
    allowed: Set[int] = config["allowed_users"].get(guild_id, set())
    if member.id in allowed:
        allowed.remove(member.id)
        config["allowed_users"][guild_id] = allowed
        await interaction.response.send_message(f"{member.mention} ha sido eliminado de la lista de usuarios permitidos.")
    else:
        await interaction.response.send_message(f"{member.mention} no estaba en la lista de usuarios permitidos.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Luna Assistant Inicializada: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos de barra.")
    except Exception as e:
        print(f"Error al sincronizar comandos de barra: {e}")

webserver.keep_alive()
bot.run(DISCORD_TOKEN)


















