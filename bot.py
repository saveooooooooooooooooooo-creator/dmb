import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
import os
from flask import Flask
from threading import Thread
from unidecode import unidecode

# ================= KEEP ALIVE SERVER =================

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

keep_alive()

# ================= DISCORD BOT SETUP =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")

# ================= CONFIG =================

MAX_WARNINGS = 5
MUTE_DURATION = 300  # seconds

user_warnings = {}

SLUR_PATTERNS = [
    r"n+\W*[i1!]+\W*[gq9]+\W*[e3a]+\W*[r]+",
    r"f+\W*[a@4]+\W*[gq9]+\W*[o0]+\W*[t]+",
]

def normalize(text):
    text = unidecode(text.lower())
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def contains_slur(message):
    raw = message.content.lower()
    normalized = normalize(raw)

    for pattern in SLUR_PATTERNS:
        if re.search(pattern, raw) or re.search(pattern, normalized):
            return True
    return False

# ================= EVENTS =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if contains_slur(message):
        await message.delete()

        user_id = message.author.id
        user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
        warnings = user_warnings[user_id]

        warn_msg = await message.channel.send(
            f"⚠️ {message.author.mention} Inappropriate language detected.\n"
            f"Warning {warnings}/{MAX_WARNINGS}"
        )
        await asyncio.sleep(5)
        await warn_msg.delete()

        if warnings >= MAX_WARNINGS:
            user_warnings[user_id] = 0

            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if not muted_role:
                muted_role = await message.guild.create_role(name="Muted")
                for channel in message.guild.channels:
                    await channel.set_permissions(muted_role, send_messages=False, speak=False)

            await message.author.add_roles(muted_role)

            mute_notice = await message.channel.send(
                f"🔇 {message.author.mention} has been muted for repeated violations."
            )
            await asyncio.sleep(5)
            await mute_notice.delete()

            await asyncio.sleep(MUTE_DURATION)
            await message.author.remove_roles(muted_role)

    await bot.process_commands(message)

# ================= SLASH COMMANDS =================

@bot.tree.command(name="warnings", description="Check a user's warnings")
@app_commands.describe(user="The user to check")
async def warnings(interaction: discord.Interaction, user: discord.Member):
    count = user_warnings.get(user.id, 0)
    await interaction.response.send_message(
        f"⚠️ {user.mention} has {count}/{MAX_WARNINGS} warnings.",
        delete_after=5
    )

@bot.tree.command(name="clearwarnings", description="Clear a user's warnings")
@app_commands.describe(user="The user to reset")
async def clearwarnings(interaction: discord.Interaction, user: discord.Member):
    user_warnings[user.id] = 0
    await interaction.response.send_message(
        f"✅ Warnings reset for {user.mention}.",
        delete_after=5
    )

@bot.tree.command(name="mute", description="Manually mute a user")
@app_commands.describe(user="User to mute")
async def mute(interaction: discord.Interaction, user: discord.Member):
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await interaction.guild.create_role(name="Muted")
        for channel in interaction.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)

    await user.add_roles(muted_role)
    await interaction.response.send_message(
        f"🔇 {user.mention} has been muted by moderator.",
        delete_after=5
    )

@bot.tree.command(name="unmute", description="Unmute a user")
@app_commands.describe(user="User to unmute")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if muted_role:
        await user.remove_roles(muted_role)

    await interaction.response.send_message(
        f"🔊 {user.mention} has been unmuted.",
        delete_after=5
    )

# ================= RUN =================

bot.run(TOKEN)
