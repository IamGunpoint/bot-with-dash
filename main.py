import os
import sys
import json
import subprocess
import threading

# 📦 Auto-install packages
required = ["discord", "flask"]
for pkg in required:
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import discord
from discord.ext import commands
from flask import Flask, request, render_template_string, redirect, session
from http.server import BaseHTTPRequestHandler, HTTPServer

# ===== Config =====
BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
DASHBOARD_PORT = 8000     # Flask internal dashboard
FAKE_RENDER_PORT = int(os.environ.get("PORT", 10000))  # What Render expects
SECRET_KEY = "supersecret"
# ===================

# 📁 Ensure files exist
for file in ["users.json", "config.json"]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# ===== Discord Bot =====
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def register(ctx, username: str, password: str):
    with open("users.json", "r") as f:
        users = json.load(f)
    uid = str(ctx.author.id)
    if uid in users:
        await ctx.send("❌ You're already registered.")
        return
    users[uid] = {"username": username, "password": password, "guild_id": ctx.guild.id}
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)
    await ctx.send(f"✅ Registered as `{username}`.")

# ===== Flask Dashboard =====
app = Flask(__name__)
app.secret_key = SECRET_KEY

def load_users():
    with open("users.json", "r") as f:
        return json.load(f)

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=2)

html_template = """
<!DOCTYPE html>
<html><head><title>Dashboard</title></head><body>
{% if not session.get("user_id") %}
  <form method="post"><h2>Login</h2>
    <input name="username" placeholder="Username"><br>
    <input type="password" name="password" placeholder="Password"><br>
    <button type="submit">Login</button>
  </form>
{% else %}
  <h2>Welcome - {{ session.username }}</h2>
  <form action="/update" method="post">
    <h3>Ticket Panel</h3>
    <input name="title" placeholder="Title" value="{{ data.ticket_config.title }}"><br>
    <input name="desc" placeholder="Description" value="{{ data.ticket_config.desc }}"><br>
    <input name="button_text" placeholder="Button Text" value="{{ data.ticket_config.button_text }}"><br>
    <input name="color" placeholder="Color" value="{{ data.ticket_config.color }}"><br>
    <input name="panel_channel" placeholder="Panel Channel ID" value="{{ data.ticket_config.panel_channel }}"><br>
    <input name="staff_role" placeholder="Staff Role ID" value="{{ data.ticket_config.staff_role }}"><br>
    <input name="transcript_channel" placeholder="Transcript Channel ID" value="{{ data.ticket_config.transcript_channel }}"><br>
    <input name="category_id" placeholder="Category ID" value="{{ data.ticket_config.category_id }}"><br>
    <h3>AutoRole</h3>
    <input type="checkbox" name="autorole_enabled" {% if data.autorole.enabled %}checked{% endif %}> Enable AutoRole<br>
    <input name="autorole_role" placeholder="Role ID" value="{{ data.autorole.role_id }}"><br><br>
    <button type="submit">Save</button>
  </form><a href="/logout">Logout</a>
{% endif %}
</body></html>
"""

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        for uid, user in users.items():
            if user["username"] == username and user["password"] == password:
                session["user_id"] = uid
                session["username"] = username
                session["guild_id"] = str(user["guild_id"])
                return redirect("/")
        return "❌ Invalid credentials"

    config = load_config().get(session.get("guild_id", ""), {
        "ticket_config": {
            "title": "", "desc": "", "button_text": "", "color": "",
            "panel_channel": 0, "staff_role": 0,
            "transcript_channel": 0, "category_id": 0
        },
        "autorole": {"enabled": False, "role_id": 0}
    })
    return render_template_string(html_template, data=config)

@app.route("/update", methods=["POST"])
def update():
    if "user_id" not in session:
        return redirect("/")
    config = load_config()
    gid = session["guild_id"]
    ticket_config = {
        "title": request.form["title"],
        "desc": request.form["desc"],
        "button_text": request.form["button_text"],
        "color": request.form["color"],
        "panel_channel": int(request.form["panel_channel"]),
        "staff_role": int(request.form["staff_role"]),
        "transcript_channel": int(request.form["transcript_channel"] or 0),
        "category_id": int(request.form["category_id"] or 0)
    }
    autorole_config = {
        "enabled": request.form.get("autorole_enabled") == "on",
        "role_id": int(request.form["autorole_role"] or 0)
    }
    config[gid] = {
        "ticket_config": ticket_config,
        "autorole": autorole_config
    }
    save_config(config)
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ===== Fake HTTP Server to Keep Render Happy =====
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_fake_server():
    with HTTPServer(("", FAKE_RENDER_PORT), PingHandler) as httpd:
        print(f"🌐 Fake server running on port {FAKE_RENDER_PORT} (for Render)")
        httpd.serve_forever()

def run_flask():
    print(f"🔧 Flask Dashboard: http://localhost:{DASHBOARD_PORT}")
    app.run(host="0.0.0.0", port=DASHBOARD_PORT)

def run_bot():
    print("🤖 Starting Discord bot...")
    bot.run(BOT_TOKEN)

# ===== Start Everything =====
if __name__ == "__main__":
    threading.Thread(target=run_fake_server).start()
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_bot).start()
