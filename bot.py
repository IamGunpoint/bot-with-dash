import discord
from discord.ext import commands
import json
import os

TOKEN = "YOUR_BOT_TOKEN"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

USERS_FILE = "users.json"

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

@bot.command()
async def register(ctx, username: str, password: str):
    users = load_users()
    uid = str(ctx.author.id)

    if uid in users:
        await ctx.send("❌ You're already registered.")
        return

    users[uid] = {
        "username": username,
        "password": password,
        "guild_id": ctx.guild.id
    }
    save_users(users)
    await ctx.send(f"✅ Registered. You can now login on the dashboard using **{username}**.")
    
bot.run(TOKEN)
