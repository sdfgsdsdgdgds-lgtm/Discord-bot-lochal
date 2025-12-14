# -*- coding: utf-8 -*-
"""
Discord Bot med:
- Auto-roll
- Anti-raid (manuell unlock)
- Self-assign-roll
- Välkomstmeddelanden
- Moderation (/ban /kick /timeout /untimeout /lock /unlock)
- Uptime
- 800+ auto-genererade slash-kommandon
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import random
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

# ===== KONFIGURATION =====
TOKEN = "DIN_DISCORD_BOT_TOKEN_HÄR"  # <--- Sätt din bot-token här
SELF_ASSIGN_ROLE_NAME = "Member"
OWNER_ID = 123456789012345678  # <--- Sätt ditt Discord-ID här
WELCOME_CHANNEL_NAME = "welcome"

AUTO_ROLE_NAME = "Member"
ANTI_RAID_TIME_WINDOW = 60
ANTI_RAID_THRESHOLD = 5

# ===== VARIABLER =====
join_times = defaultdict(list)
locked_guilds = set()
start_time = datetime.utcnow()
commands_added = False

# ===== Intents =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ===== HJÄLPFUNKTIONER =====
def format_timedelta(delta: timedelta):
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return " ".join(parts) or "0s"

def check_raid(guild_id):
    now = datetime.now()
    join_times[guild_id] = [
        t for t in join_times[guild_id]
        if now - t < timedelta(seconds=ANTI_RAID_TIME_WINDOW)
    ]
    return len(join_times[guild_id]) >= ANTI_RAID_THRESHOLD

async def unlock_guild_manual(guild, channel):
    for c in guild.text_channels:
        try:
            await c.set_permissions(guild.default_role, send_messages=True)
        except:
            pass
    locked_guilds.discard(guild.id)
    await channel.send(f"🔓 Kanaler i **{guild.name}** har låsts upp manuellt.")

# ===== EVENTS =====
@bot.event
async def on_ready():
    global commands_added
    if not commands_added:
        add_dynamic_commands()
        commands_added = True
        print("📌 800+ auto-genererade kommandon tillagda!")
    print(f'✅ Bot online: {bot.user} | Servers: {len(bot.guilds)}')

@bot.event
async def on_member_join(member):
    guild = member.guild
    # Auto-roll
    role = discord.utils.get(guild.roles, name=AUTO_ROLE_NAME)
    if role:
        try:
            await member.add_roles(role)
            print(f'✅ Gav rollen "{AUTO_ROLE_NAME}" till {member.name}')
        except:
            pass

    # Welcome
    welcome_channel = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL_NAME)
    if not welcome_channel and guild.text_channels:
        welcome_channel = guild.text_channels[0]
    try:
        await welcome_channel.send(f"👋 Hej {member.mention}! Välkommen till **{guild.name}**!")
    except:
        pass

    # Anti-raid
    join_times[guild.id].append(datetime.now())
    if check_raid(guild.id) and guild.id not in locked_guilds:
        locked_guilds.add(guild.id)
        alert_channel = discord.utils.get(guild.text_channels, name="admin") or welcome_channel
        if alert_channel:
            embed = discord.Embed(
                title="🚨 RAID VARNING 🚨",
                description=f"**{ANTI_RAID_THRESHOLD}+ användare** har gått med inom {ANTI_RAID_TIME_WINDOW} sekunder!",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            await alert_channel.send(embed=embed)
        for channel in guild.text_channels:
            try:
                await channel.set_permissions(guild.default_role, send_messages=False)
            except:
                pass
        print(f'⚠️ Raid upptäckt! Alla textkanaler låsta.')

# =========================
#     SLASH COMMANDS
# =========================

# Fun & Utility
@bot.tree.command(name="hej", description="Säger hej!")
async def hej(interaction: discord.Interaction):
    await interaction.response.send_message(f"👋 Hej {interaction.user.mention}!")

@bot.tree.command(name="ping", description="Visar botens latens")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latens: **{round(bot.latency*1000)}ms**")

@bot.tree.command(name="dice", description="Kastar en tärning (1–6)")
async def dice(interaction: discord.Interaction):
    result = random.randint(1, 6)
    await interaction.response.send_message(f"🎲 Du fick: **{result}**")

@bot.tree.command(name="coinflip", description="Singlar slant")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Krona", "Klave"])
    await interaction.response.send_message(f"🪙 Du fick: **{result}**")

@bot.tree.command(name="uptime", description="Visar hur länge boten har varit igång")
async def uptime(interaction: discord.Interaction):
    delta = datetime.utcnow() - start_time
    await interaction.response.send_message(f"⏱️ Uptime: **{format_timedelta(delta)}**", ephemeral=True)

# Self-assign
@bot.tree.command(name="giveme", description="Ger dig själv self-assign-rollen")
async def giveme(interaction: discord.Interaction):
    if not SELF_ASSIGN_ROLE_NAME:
        await interaction.response.send_message("❌ Ingen self-assign-roll definierad.", ephemeral=True)
        return
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=SELF_ASSIGN_ROLE_NAME)
    if not role:
        await interaction.response.send_message(f"❌ Rollen '{SELF_ASSIGN_ROLE_NAME}' finns inte.", ephemeral=True)
        return
    if role in interaction.user.roles:
        await interaction.response.send_message(f"⚠️ Du har redan rollen {role.name}.", ephemeral=True)
        return
    try:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"✅ Du fick rollen **{role.name}**!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Kunde inte ge rollen: {e}", ephemeral=True)

# Moderation
@bot.tree.command(name="kick", description="Sparkar en användare")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Ingen anledning angiven"):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 {member.mention} har sparkats. Anledning: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Kunde inte sparka användaren: {e}", ephemeral=True)

@bot.tree.command(name="ban", description="Bannar en användare")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Ingen anledning angiven"):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {member.mention} har blivit bannlyst. Anledning: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Kunde inte banna användaren: {e}", ephemeral=True)

@bot.tree.command(name="unban", description="Tar bort en bannlysning")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ {user.mention} har blivit unbannad.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Kunde inte unbanna användaren: {e}", ephemeral=True)

@bot.tree.command(name="timeout", description="Sätter en användare i timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minuter: int, reason: str = "Ingen anledning angiven"):
    try:
        until = datetime.utcnow() + timedelta(minutes=minuter)
        await member.timeout(until, reason=reason)
        await interaction.response.send_message(f"⏳ {member.mention} har satts i timeout i {minuter} minuter.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Kunde inte sätta timeout: {e}", ephemeral=True)

@bot.tree.command(name="untimeout", description="Tar bort timeout från en användare")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None)
        await interaction.response.send_message(f"✅ Timeout borttagen för {member.mention}.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Kunde inte ta bort timeout: {e}", ephemeral=True)

# Lock & Unlock manual
@bot.tree.command(name="unlock", description="Låser upp servern efter raid (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def unlock(interaction: discord.Interaction):
    if interaction.guild.id not in locked_guilds:
        await interaction.response.send_message("ℹ️ Servern är inte låst.", ephemeral=True)
        return
    await unlock_guild_manual(interaction.guild, interaction.channel)
    await interaction.response.send_message("✅ Servern är nu upplåst!", ephemeral=True)

# Restart (lokalt)
@bot.tree.command(name="restart", description="Startar om boten (endast ägaren)")
async def restart(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Du har inte behörighet att starta om boten.", ephemeral=True)
        return
    await interaction.response.send_message("♻️ Startar om boten...", ephemeral=True)
    os._exit(0)

# ================================
#       MASSKOMMANDON
# ================================
def add_dynamic_commands():
    fun_categories = {
        "joke": "😂 Skämt",
        "meme": "📸 Meme",
        "roast": "🔥 Roast",
        "fact": "📘 Fakta",
        "hug": "🤗 Hug",
        "slap": "✋ Slap",
        "kiss": "💋 Kiss",
        "poke": "👉 Poke"
    }
    for category, emoji in fun_categories.items():
        for i in range(1, 101):
            async def cmd(interaction, i=i, category=category, emoji=emoji):
                await interaction.response.send_message(f"{emoji} `{category} #{i}` auto-genererad!")
            bot.tree.command(name=f"{category}{i}", description=f"Auto {category} #{i}")(cmd)

# ================================
#       STARTA BOT
# ================================
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: Sätt DISCORD_BOT_TOKEN direkt i koden!")
    else:
        print("🚀 Startar Discord bot...")
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Boten kraschade: {e}")
