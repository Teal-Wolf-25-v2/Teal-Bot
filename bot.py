import os
import discord
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from discord import app_commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents=discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

bot_owner = 1129784219418234950
owner_raw = client.get_user(bot_owner)
if owner_raw != None:
    owner_pfp_raw = owner_raw.avatar()
    owner_pfp = owner_pfp_raw.url()
else:
    owner_pfp = f"https://avatars.githubusercontent.com/u/155310651?v=4"

bot_pfp = "https://github.com/Teal-Wolf-25-v2/Teal-Bot/blob/main/icon.png?raw=true"
bot_commit = requests.get("https://api.github.com/repos/Teal-Wolf-25-v2/Teal-Bot/commits/main")
if bot_commit.status_code == 200:
    bot_hash = bot_commit.json()["sha"]
    bot_hash_short = bot_hash[-7:]
    bot_updated = bot_commit.json()["commit"]["author"]["date"]
    updated_unix = int(datetime.fromisoformat(bot_updated.replace("Z","+00:00")).timestamp())
else:
    bot_hash = "Error: Not Found"
    bot_hash_short = "null"
bot_version = "0.1.0"
bot_uptime = int(datetime.now().timestamp())

bot_info=discord.Embed(color=0x00ffff,title="Cyan",url="https://repo.tw25.net/Teal-Bot",description="Discord bot to handle various Teal Wolf 25's Nexus functions.")
bot_info.set_author(name="Teal Wolf 25",url="https://repo.tw25.net",icon_url=owner_pfp)
bot_info.set_thumbnail(url=bot_pfp)
bot_info.add_field(name="Version",value=f"{bot_version} `{bot_hash_short}`",inline=False)
bot_info.add_field(name="Handles",value="- Bot Info",inline=False)
bot_info.add_field(name="Last Updated",value=f"<t:{updated_unix}:F> (<t:{updated_unix}:R>)")
bot_info.add_field(name="Uptime",value=f"Since <t:{bot_uptime}:R>")


@tree.command(
    name="info",
    description="Get the bot info for Cyan"
)
async def info(interaction):
    await interaction.response.send_message(embed=bot_info)

commands = [com for com in tree.walk_commands() if isinstance(com, app_commands.Command)]
bot_info.add_field(name="Existing Commands",value=len(commands),inline=False)

@client.event
async def on_ready():
    await tree.sync()
    print(f'{client.user} has connected to Discord!')

client.run(TOKEN)
