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
BOT_VERSION = "1.1.0"

MAAFIA_VC_ID = 1273030319477362823   # your Maafia voice channel ID
LOG_CHANNEL_ID = None
BOT_PFP = "https://github.com/Teal-Wolf-25-v2/Teal-Bot/blob/main/icon.png?raw=true"


# ─────────────────────────────────────────────
# Build Info Embed
# ─────────────────────────────────────────────
def build_info_embed(latency_ms: int = 0):
    commit = requests.get("https://api.github.com/repos/Teal-Wolf-25-v2/Teal-Bot/commits/main")
    if commit.status_code == 200:
        data = commit.json()
        bot_hash = data["sha"]
        bot_hash_short = f"[`{bot_hash[-7:]}`](https://repo.tw25.net/Teal-Bot/commit/{bot_hash})"
        bot_updated = data["commit"]["author"]["date"]
        updated_unix = int(datetime.fromisoformat(bot_updated.replace("Z", "+00:00")).timestamp())
    else:
        bot_hash_short = "null"
        updated_unix = int(datetime.now().timestamp())

    uptime = int(datetime.now().timestamp())

    embed = discord.Embed(
        color=0x00FFFF,
        title="Cyan",
        url="https://repo.tw25.net/Teal-Bot",
        description="Discord bot to handle various Teal Wolf 25's Nexus functions.",
    )
    embed.set_thumbnail(url=BOT_PFP)
    embed.add_field(name="Version", value=f"{BOT_VERSION} {bot_hash_short}", inline=False)
    handles_value = (
    "- Bot Info\n"
    "  - `/info` — Displays version, uptime, last update, and ping.\n"
    "  - Automatically updates commit info from GitHub.\n\n"
    "- Maafia Voting System\n"
    "  - `/maafia` — Creates the voting embed and reactions.\n"
    "  - `/maafia_results` — Counts votes and shows top-voted player.\n"
    "  - Auto-updates the voting embed when users join/leave the Maafia VC.\n"
    "  - Stores the latest voting message for automated refreshes.\n\n"
    "- Voice Channel Tools\n"
    "  - `/vc_record` — Logs all current VC members with timestamps.\n"
    "- Moderator System\n"
    "  - `/mod_msg` — Lets members send private reports or notes to moderators.\n"
    "  - Supports optional message link previews for rule-breaking reports.\n"
    "  - Pings the moderator role `<@&1388997170656575569>` in the mod channel."
)
    embed.add_field(name="Handles", value=handles_value, inline=False)
    embed.add_field(name="Last Updated", value=f"<t:{updated_unix}:F> (<t:{updated_unix}:R>)", inline=False)
    embed.add_field(name="Uptime", value=f"Since <t:{uptime}:R>", inline=False)
    embed.add_field(name="Ping", value=f"{latency_ms} ms", inline=False)
    return embed


# ─────────────────────────────────────────────
# Maafia Voting Embed Builder
# ─────────────────────────────────────────────
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

    if maafia_invalids:
        maafia_invalids += " Please send Teal a valid emoji to use"
    maafia_voting.add_field(name="Skip", value="<:not_mafia:1281781263937573038>", inline=False)
    return maafia_voting, maafia_invalids


# ─────────────────────────────────────────────
# Slash Commands
# ─────────────────────────────────────────────
@tree.command(name="info", description="Get the bot info for Cyan (includes ping).")
async def info(interaction: discord.Interaction):
    latency_ms = round(client.latency * 1000)
    embed = build_info_embed(latency_ms)
    await interaction.response.send_message(embed=embed)


@tree.command(name="maafia", description="Prompts the Maafia Voting embed message")
async def maafia(interaction: discord.Interaction):
    maafia_channel = interaction.guild.get_channel(MAAFIA_VC_ID)
    if not maafia_channel or not isinstance(maafia_channel, discord.VoiceChannel):
        await interaction.response.send_message("❌ Voice channel not found or invalid.")
        return

    member_ids = [str(m.id) for m in maafia_channel.members]
    if not member_ids:
        await interaction.response.send_message("No members are currently in the voice channel.")
        return

    with open("emojis.json", "r") as file:
        emoji_objects = json.load(file)

    maafia_voting, maafia_invalids = maafia_voting_embed(member_ids)
    await interaction.response.send_message(
        content=maafia_invalids,
        embed=maafia_voting,
        allowed_mentions=discord.AllowedMentions(users=True),
    )
    sent_msg = await interaction.original_response()

    # Save this message ID for auto-updates
    with open("maafia_message.json", "w") as f:
        json.dump({"channel_id": sent_msg.channel.id, "message_id": sent_msg.id}, f)

    for emoji_obj in emoji_objects:
        if emoji_obj["user_id"] in member_ids and not emoji_obj.get("invalid", False):
            emoji_id = emoji_obj["emoji_id"]
            emoji_name = emoji_obj["emoji_name"]
            try:
                await sent_msg.add_reaction(f"<{emoji_name}{emoji_id}>")
            except Exception as e:
                print(f"⚠️ Could not react with {emoji_name}: {e}")
    try:
        await sent_msg.add_reaction("<:not_mafia:1281781263937573038>")
    except Exception as e:
        print(f"⚠️ Could not add skip reaction: {e}")


@tree.command(name="maafia_results", description="Display current vote results from a Maafia message.")
@app_commands.describe(message_link="Link to the Maafia voting message.")
async def maafia_results(interaction: discord.Interaction, message_link: str):
    await interaction.response.defer(thinking=True)
    try:
        parts = message_link.strip().split("/")
        channel_id = int(parts[-2])
        message_id = int(parts[-1])
    except Exception:
        await interaction.followup.send("❌ Invalid message link.")
        return

    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        await interaction.followup.send("❌ Channel not found.")
        return

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.followup.send("❌ Message not found.")
        return

    results = {}
    for reaction in message.reactions:
        async for user in reaction.users():
            if user.bot:
                continue
            emoji_str = str(reaction.emoji)
            results.setdefault(emoji_str, []).append(user.display_name)

    if not results:
        await interaction.followup.send("⚠️ No votes recorded yet.")
        return

    embed = discord.Embed(title="🗳️ Maafia Vote Results", color=0x8800FF)
    top_emoji, top_count = None, 0
    for emoji, voters in results.items():
        embed.add_field(name=emoji, value=", ".join(voters), inline=False)
        if len(voters) > top_count:
            top_emoji, top_count = emoji, len(voters)
    if top_emoji:
        embed.add_field(name="<:mafia:1281781262671020104> Voted Out", value=f"{top_emoji} — {top_count} vote(s)", inline=False)
    await interaction.followup.send(embed=embed)


@tree.command(name="status_set", description="Change the bot's presence (owner only).")
@app_commands.describe(activity_type="playing, watching, listening, competing", message="The status message")
async def status_set(interaction: discord.Interaction, activity_type: str, message: str):
    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    activity_type = activity_type.lower()
    if activity_type == "playing":
        activity = discord.Game(name=message)
    elif activity_type == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=message)
    elif activity_type == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=message)
    elif activity_type == "competing":
        activity = discord.Activity(type=discord.ActivityType.competing, name=message)
    else:
        await interaction.response.send_message("❌ Invalid activity type.", ephemeral=True)
        return

    await client.change_presence(activity=activity)
    await interaction.response.send_message(f"✅ Status set to {activity_type.title()} **{message}**")


@tree.command(name="vc_record", description="Save a timestamped record of all users in the Maafia voice channel.")
async def vc_record(interaction: discord.Interaction):
    vc = interaction.guild.get_channel(MAAFIA_VC_ID)
    if not vc or not isinstance(vc, discord.VoiceChannel):
        await interaction.response.send_message("❌ Voice channel not found.")
        return

    members = [f"{m.display_name} ({m.id})" for m in vc.members]
    record = {"timestamp": datetime.now().isoformat(), "members": members}
    os.makedirs("records", exist_ok=True)
    with open("records/vc_records.json", "a") as f:
        f.write(json.dumps(record) + "\n")
    await interaction.response.send_message(f"✅ Recorded {len(members)} member(s) in VC.")

@tree.command(
    name="mod_msg",
    description="Send a private message to the moderators (optionally include a message link).",
)
@app_commands.describe(
    note="Your message or report for the moderators.",
    message_link="Optional link to the message you're reporting (if applicable).",
)
async def mod_msg(interaction: discord.Interaction, note: str, message_link: str = None):
    mod_channel_id = 1253166365100085342
    mod_role_ping = "<@&1388997170656575569>"  # Moderator role ping
    mod_channel = interaction.guild.get_channel(mod_channel_id)

    if not mod_channel:
        await interaction.response.send_message(
            "❌ Could not find the moderator channel.", ephemeral=True
        )
        return

    # Build the base embed
    embed = discord.Embed(
        title="Concern for Moderators",
        color=0xFF8800,
        timestamp=datetime.now(),
        description=note,
    )
    embed.set_author(
        name=f"{interaction.user.display_name} ({interaction.user.id})",
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
    )
    embed.add_field(
        name="Reporter",
        value=f"{interaction.user.mention} (`{interaction.user.id}`)",
        inline=False,
    )

    # Try to attach reported message details (if provided)
    if message_link:
        try:
            parts = message_link.strip().split("/")
            guild_id = int(parts[-3])
            channel_id = int(parts[-2])
            msg_id = int(parts[-1])
            if guild_id != interaction.guild.id:
                raise ValueError("Message not in this server.")
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                msg = await channel.fetch_message(msg_id)
                link_field = (
                    f"[Jump to Message]({message_link})\n"
                    f"**Author:** {msg.author.mention}\n"
                    f"**Content:** {msg.content[:300]}{'...' if len(msg.content) > 300 else ''}"
                )
                embed.add_field(name="Reported Message", value=link_field, inline=False)
            else:
                embed.add_field(name="Reported Message", value=f"[Jump to Message]({message_link})", inline=False)
        except Exception as e:
            embed.add_field(
                name="Message Link Error",
                value=f"⚠️ Could not process message link.\n`{e}`",
                inline=False,
            )

    # Send message with role ping outside the embed
    try:
        await mod_channel.send(
            content=f"{mod_role_ping} — new report received.",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        await interaction.response.send_message(
            "✅ Your message has been sent to the moderators.", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"⚠️ Failed to send to moderators:\n`{e}`", ephemeral=True
        )


# ─────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────
@client.event
async def on_voice_state_update(member, before, after):
    joined = after.channel and after.channel.id == MAAFIA_VC_ID
    left = before.channel and before.channel.id == MAAFIA_VC_ID and after.channel != before.channel
    if not (joined or left):
        return

    msg = f"🔊 **{member.display_name}** joined the Maafia VC." if joined else f"🔇 **{member.display_name}** left the Maafia VC."
    print(msg)
    log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(msg)

    # Auto-update Maafia embed
    try:
        with open("maafia_message.json", "r") as f:
            data = json.load(f)
        ch = member.guild.get_channel(data["channel_id"])
        msg_obj = await ch.fetch_message(data["message_id"])
    except Exception:
        print("⚠️ No Maafia message recorded for auto-update.")
        return

    vc = member.guild.get_channel(MAAFIA_VC_ID)
    if not vc:
        return
    member_ids = [str(m.id) for m in vc.members]
    maafia_voting, maafia_invalids = maafia_voting_embed(member_ids)
    await msg_obj.edit(content=maafia_invalids, embed=maafia_voting)
    try:
        await msg_obj.clear_reactions()
    except discord.Forbidden:
        print("⚠️ Missing permission to clear reactions.")

    with open("emojis.json", "r") as file:
        emoji_objects = json.load(file)
    for emoji_obj in emoji_objects:
        if emoji_obj["user_id"] in member_ids and not emoji_obj.get("invalid", False):
            emoji = f"<{emoji_obj['emoji_name']}{emoji_obj['emoji_id']}>"
            try:
                await msg_obj.add_reaction(emoji)
            except Exception as e:
                print(f"⚠️ Could not react with {emoji_obj['emoji_name']}: {e}")
    try:
        await msg_obj.add_reaction("<:not_mafia:1281781263937573038>")
    except Exception as e:
        print(f"⚠️ Could not add skip reaction: {e}")


# ─────────────────────────────────────────────
# Ready
# ─────────────────────────────────────────────
@client.event
async def on_ready():
    owner = client.get_user(BOT_OWNER_ID)
    owner_pfp = (
        owner.avatar.url if owner and owner.avatar else "https://avatars.githubusercontent.com/u/155310651?v=4"
    )
    embed = build_info_embed()
    embed.set_author(name="Teal Wolf 25", url="https://repo.tw25.net", icon_url=owner_pfp)
    commands = [com for com in tree.walk_commands() if isinstance(com, app_commands.Command)]
    embed.add_field(name="Existing Commands", value=len(commands), inline=False)
    await tree.sync()
    print(f"{client.user} has connected to Discord!")


client.run(TOKEN)
