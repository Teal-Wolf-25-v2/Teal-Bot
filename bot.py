import os
import discord
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from discord import app_commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

BOT_OWNER_ID = 1129784219418234950
BOT_VERSION = "0.3.1"

bot_pfp = "https://github.com/Teal-Wolf-25-v2/Teal-Bot/blob/main/icon.png?raw=true"

# Get last commit info
bot_commit = requests.get("https://api.github.com/repos/Teal-Wolf-25-v2/Teal-Bot/commits/main")
if bot_commit.status_code == 200:
    data = bot_commit.json()
    bot_hash = data["sha"]
    bot_hash_short = f"[`{bot_hash[-7:]}`](https://repo.tw25.net/Teal-Bot/commit/{bot_hash})"
    bot_updated = data["commit"]["author"]["date"]
    updated_unix = int(datetime.fromisoformat(bot_updated.replace("Z", "+00:00")).timestamp())
else:
    bot_hash_short = "null"
    updated_unix = int(datetime.now().timestamp())

bot_uptime = int(datetime.now().timestamp())

# Create the info embed
bot_info = discord.Embed(
    color=0x00FFFF,
    title="Cyan",
    url="https://repo.tw25.net/Teal-Bot",
    description="Discord bot to handle various Teal Wolf 25's Nexus functions.",
)
bot_info.set_thumbnail(url=bot_pfp)
bot_info.add_field(name="Version", value=f"{BOT_VERSION} {bot_hash_short}", inline=False)
bot_info.add_field(name="Handles", value="- Bot Info\n- Maafia Voting\n  - Embed Message\n  - Reactions", inline=False)
bot_info.add_field(name="Last Updated", value=f"<t:{updated_unix}:F> (<t:{updated_unix}:R>)", inline=False)
bot_info.add_field(name="Uptime", value=f"Since <t:{bot_uptime}:R>", inline=False)


def maafia_voting_embed(vc_list):
    maafia_voting = discord.Embed(
        color=0xBB00FF,
        title="Maafia Voting",
        description="React with the emoji that matches the person you want to vote for.",
    )

    with open("emojis.json", "r") as file:
        emoji_objects = json.load(file)

    maafia_invalids = ""

    for emoji_obj in emoji_objects:
        if emoji_obj["user_id"] in vc_list:
            emoji_holder = emoji_obj["name"]
            if emoji_obj.get("invalid"):
                emoji = "Invalid Emoji!"
                maafia_invalids += f"<@{emoji_obj['user_id']}>"
            else:
                emoji = f"<{emoji_obj['emoji_name']}{emoji_obj['emoji_id']}>"

            maafia_voting.add_field(name=emoji_holder, value=emoji, inline=False)

    if maafia_invalids != "":
        maafia_invalids += " Please send Teal a valid emoji to use"
    maafia_voting.add_field(name="Skip", value="<:not_mafia:1281781263937573038>", inline=False)

    return maafia_voting, maafia_invalids


@tree.command(name="info", description="Get the bot info for Cyan")
async def info(interaction: discord.Interaction):
    await interaction.response.send_message(embed=bot_info)


@tree.command(name="maafia", description="Prompts the Maafia Voting embed message")
async def maafia(interaction: discord.Interaction):
    maafia_channel_id = 1273030319477362823  # The Maafia Voice Channel
    maafia_channel = interaction.guild.get_channel(maafia_channel_id)

    if not maafia_channel or not isinstance(maafia_channel, discord.VoiceChannel):
        await interaction.response.send_message("Voice channel not found or invalid.")
        return

    member_ids = [str(member.id) for member in maafia_channel.members]
    if not member_ids:
        await interaction.response.send_message("No members are currently in the voice channel.")
        return

    # Load emoji data dynamically
    with open("emojis.json", "r") as file:
        emoji_objects = json.load(file)

    # Build the voting embed
    maafia_voting, maafia_invalids = maafia_voting_embed(member_ids)

    # Send the embed first
    await interaction.response.send_message(
        content=maafia_invalids,
        embed=maafia_voting,
        allowed_mentions=discord.AllowedMentions(users=True),
    )

    # Fetch the message we just sent (for adding reactions)
    sent_msg = await interaction.original_response()

    # Loop through each emoji in the JSON and add as reaction if it matches a user in VC
    for emoji_obj in emoji_objects:
        if emoji_obj["user_id"] in member_ids and not emoji_obj.get("invalid", False):
            emoji_id = emoji_obj["emoji_id"]
            emoji_name = emoji_obj["emoji_name"]
            try:
                # Custom emoji format: <:name:id>
                emoji = f"<{emoji_name}{emoji_id}>"
                await sent_msg.add_reaction(emoji)
            except Exception as e:
                print(f"⚠️ Could not react with {emoji_name}: {e}")

    # Finally add the "Skip" reaction
    try:
        await sent_msg.add_reaction("<:not_mafia:1281781263937573038>")
    except Exception as e:
        print(f"⚠️ Could not add skip reaction: {e}")

@tree.command(name="maafia_edit", description="Edit an existing Maafia Voting embed by message link")
@app_commands.describe(message_link="Link to the message to update (must be in this guild).")
async def maafia_edit(interaction: discord.Interaction, message_link: str):
    await interaction.response.defer(thinking=True)  # allows async work safely

    # Parse message link: format https://discord.com/channels/<guild>/<channel>/<message>
    try:
        parts = message_link.strip().split("/")
        guild_id = int(parts[-3])
        channel_id = int(parts[-2])
        message_id = int(parts[-1])
    except (IndexError, ValueError):
        await interaction.followup.send("❌ Invalid message link format.")
        return

    # Ensure message is from this guild
    if interaction.guild.id != guild_id:
        await interaction.followup.send("❌ That message isn’t in this server.")
        return

    # Fetch target message
    channel = interaction.guild.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        await interaction.followup.send("❌ Invalid text channel.")
        return

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.followup.send("❌ Message not found.")
        return

    # Identify voice channel
    maafia_channel_id = 1273030319477362823
    maafia_channel = interaction.guild.get_channel(maafia_channel_id)
    if not maafia_channel or not isinstance(maafia_channel, discord.VoiceChannel):
        await interaction.followup.send("❌ Voice channel not found.")
        return

    member_ids = [str(member.id) for member in maafia_channel.members]
    if not member_ids:
        await interaction.followup.send("⚠️ No members currently in the voice channel.")
        return

    # Load emojis dynamically
    with open("emojis.json", "r") as file:
        emoji_objects = json.load(file)

    # Build updated embed and invalid text
    maafia_voting, maafia_invalids = maafia_voting_embed(member_ids)

    # Edit the existing message
    await message.edit(content=maafia_invalids, embed=maafia_voting)

    # Clear all existing reactions
    try:
        await message.clear_reactions()
    except discord.Forbidden:
        await interaction.followup.send("⚠️ I lack permission to clear reactions.")
        return

    # Reapply new reactions for members in VC
    added = 0
    for emoji_obj in emoji_objects:
        if emoji_obj["user_id"] in member_ids and not emoji_obj.get("invalid", False):
            emoji_id = emoji_obj["emoji_id"]
            emoji_name = emoji_obj["emoji_name"].strip(":")
            emoji = f"<:{emoji_name}:{emoji_id}>"
            try:
                await message.add_reaction(emoji)
                added += 1
            except Exception as e:
                print(f"⚠️ Could not react with {emoji_name}: {e}")

    # Add skip reaction
    try:
        await message.add_reaction("<:not_mafia:1281781263937573038>")
    except Exception as e:
        print(f"⚠️ Could not add skip reaction: {e}")

    await interaction.followup.send(
        f"✅ Updated embed and reapplied {added} emoji reactions on [this message]({message_link})."
    )


@client.event
async def on_ready():
    # Now you can safely access cached users
    owner = client.get_user(BOT_OWNER_ID)
    owner_pfp = (
        owner.avatar.url if owner and owner.avatar else "https://avatars.githubusercontent.com/u/155310651?v=4"
    )
    bot_info.set_author(name="Teal Wolf 25", url="https://repo.tw25.net", icon_url=owner_pfp)

    # Register command count dynamically
    commands = [com for com in tree.walk_commands() if isinstance(com, app_commands.Command)]
    bot_info.add_field(name="Existing Commands", value=len(commands), inline=False)

    await tree.sync()
    print(f"{client.user} has connected to Discord!")


client.run(TOKEN)
