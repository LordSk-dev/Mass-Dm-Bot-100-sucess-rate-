"""
Mass DM Bot — Fully Automated Edition
─────────────────────────────────────────
• Requires only Bot Token in .env (no manual delay config)
• Intelligent pacing & anti-spam variation built-in
• Tracks 403/429 limits to prevent Cloudflare IP bans (10k/10m limit)
• Maximizes speed safely by instantly skipping closed DMs
• Built-in Web Server for 24/7 Bot Hosting (Replit, Render, etc.)
"""

import os
import re
import json
import random
import asyncio
import logging
import time
from pathlib import Path
from datetime import datetime
from threading import Thread
from flask import Flask

import discord
from discord.ext import commands
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PREFIX    = os.getenv("PREFIX", "!")
ADMIN_IDS = [x.strip().strip('"').strip("'") for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

MAX_RETRIES = 3

# ═══════════════════════════════════════════════════════════════════════
#  LOGGING & ERROR TRACKING
# ═══════════════════════════════════════════════════════════════════════

Path("data").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("massdm")

# Disable Flask default logging to keep console clean
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# ═══════════════════════════════════════════════════════════════════════
#  KEEP ALIVE WEB SERVER (Bot Hosting)
# ═══════════════════════════════════════════════════════════════════════

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive and running!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Starts the web server in a separate thread so it doesn't block the bot."""
    t = Thread(target=run_server)
    t.daemon = True
    t.start()
    log.info("Keep-Alive Web Server started on port %s", os.environ.get("PORT", 8080))

# ═══════════════════════════════════════════════════════════════════════
#  DATA PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════

SENT_FILE   = Path("data/sent.json")
FAILED_FILE = Path("data/failed.json")

def load_set(path: Path) -> set:
    if path.exists():
        try:
            return set(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()

def save_set(path: Path, data: set):
    path.write_text(json.dumps(list(data)), encoding="utf-8")

# ═══════════════════════════════════════════════════════════════════════
#  MESSAGE PARSING & ANTI-SPAM ENGINE
# ═══════════════════════════════════════════════════════════════════════

_ZW = ["\u200b", "\u200c", "\u200d", "\ufeff"]

def vary_message(template: str, member: discord.Member, guild: discord.Guild) -> str:
    """
    Replaces placeholders and injects invisible zero-width characters 
    to bypass exact-message hashing filters.
    """
    msg = template
    msg = msg.replace("{user}", member.display_name)
    msg = msg.replace("{username}", member.name)
    msg = msg.replace("{mention}", member.mention)
    msg = msg.replace("{server}", guild.name)
    msg = msg.replace("{members}", str(guild.member_count))
    msg = msg.replace("{nl}", "\n")

    # Process any {rand:a|b} blocks if the user manually included them
    msg = re.sub(
        r"\{rand:([^}]+)\}",
        lambda m: random.choice(m.group(1).split("|")),
        msg,
    )

    # Invisible anti-spam variation (Injects zero-width characters at random boundaries)
    words = msg.split(" ")
    if len(words) > 2:
        positions = random.sample(
            range(1, len(words)),
            k=min(random.randint(1, 3), len(words) - 1),
        )
        for pos in sorted(positions, reverse=True):
            words[pos] = random.choice(_ZW) + words[pos]
    msg = " ".join(words)

    return msg

# ═══════════════════════════════════════════════════════════════════════
#  FULLY AUTOMATED SMART PACER & RATELIMIT HANDLER
# ═══════════════════════════════════════════════════════════════════════

class AutoPacer:
    """
    Automatically calculates safe limits using Discord's ratelimit rules:
    - IP addresses are banned at 10,000 invalid requests (401, 403, 429) per 10 mins.
    - Uses sliding window to enforce a strict cap of 8,000 invalid requests per 10m.
    - Moves extremely fast through closed-DM (403) users safely.
    - Applies human-like jitter to successful DMs to evade heuristics.
    """
    def __init__(self):
        self.invalid_requests = []  # Timestamps of 403s/429s/errors
        self.sent_count = 0
        self.base_delay = 0.2
        
    def add_invalid(self):
        self.invalid_requests.append(time.time())

    async def wait(self, ctx, result: str):
        now = time.time()
        
        # Sliding window: keep only invalid requests from the last 10 minutes (600s)
        self.invalid_requests = [t for t in self.invalid_requests if now - t < 600]
        
        # HARD LIMIT AVOIDANCE (Protecting against Cloudflare ban)
        if len(self.invalid_requests) >= 8000:
            oldest = self.invalid_requests[0]
            pause_time = 600 - (now - oldest) + 5
            if pause_time > 0:
                log.critical("⚠ CRITICAL: Approaching Cloudflare limit (8k invalid/10m). Pausing for %.1fs", pause_time)
                if ctx:
                    await ctx.send(f"🚨 **CRITICAL ANTI-BAN ENGAGED** 🚨\nApproaching Discord API hard limit for invalid requests (users with closed DMs). Pausing for **{pause_time/60:.1f} minutes** to protect your bot IP from a Cloudflare ban.")
                await asyncio.sleep(pause_time)
                self.invalid_requests = []
                now = time.time()

        if result == "forbidden":
            # Very fast skip for users with DMs closed.
            # Safe because the sliding window above protects us from the 10k/10m limit.
            await asyncio.sleep(random.uniform(0.01, 0.1))
            return
            
        if result == "sent":
            self.sent_count += 1
            
            # Automated human-like batching
            if self.sent_count % random.randint(35, 55) == 0:
                cd = random.uniform(5, 15)
                log.info("Auto-batch pause: %.1fs", cd)
                await asyncio.sleep(cd)
                
            # Automated mega-pause to reset global heuristics
            if self.sent_count % random.randint(180, 220) == 0:
                cd = random.uniform(30, 60)
                log.info("Auto-mega pause: %.1fs", cd)
                await asyncio.sleep(cd)
                
            # Normal delay + jitter
            delay = self.base_delay + random.uniform(0.1, 0.5)
            await asyncio.sleep(delay)
            
        elif result == "429":
            # Hard rate limit hit, backoff substantially
            log.warning("Rate Limited (429)! Backing off...")
            await asyncio.sleep(random.uniform(10.0, 15.0))
        else:
            # General Errors
            await asyncio.sleep(random.uniform(3.0, 6.0))


# ═══════════════════════════════════════════════════════════════════════
#  CAMPAIGN STATE
# ═══════════════════════════════════════════════════════════════════════

class Campaign:
    def __init__(self):
        self.active     = False
        self.stop_flag  = False
        self.paused     = False
        self.guild_id   = None
        self.template   = ""
        self.total      = 0
        self.sent       = 0
        self.failed     = 0
        self.skipped    = 0
        self.start_time = None
        self.sent_ids   = load_set(SENT_FILE)
        self.failed_ids = load_set(FAILED_FILE)

    def save(self):
        save_set(SENT_FILE, self.sent_ids)
        save_set(FAILED_FILE, self.failed_ids)

    def reset(self):
        self.active    = False
        self.stop_flag = False
        self.paused    = False
        self.total     = 0
        self.sent      = 0
        self.failed    = 0
        self.skipped   = 0
        self.start_time = None

campaign = Campaign()
pacer    = AutoPacer()

# ═══════════════════════════════════════════════════════════════════════
#  DM ENGINE & ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════════

async def send_dm(member: discord.Member, guild: discord.Guild) -> str:
    """Returns: 'sent' | 'forbidden' | '429' | 'error'"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            content = vary_message(campaign.template, member, guild)
            await member.send(content)
            return "sent"

        except discord.Forbidden as exc:
            # DMs disabled or blocked
            if exc.code == 50007:
                return "forbidden"
            # 40003 corresponds to bot being globally rate limited on DM creations
            if exc.code == 40003:
                return "429"
            return "forbidden"

        except discord.HTTPException as exc:
            if exc.status == 429:
                return "429"
            if exc.status == 403:
                return "forbidden"
            if exc.status == 401:
                log.error("Token is invalid or got unauthorized during campaign!")
                return "error"
            
            log.error("HTTP %s on attempt %d for %s: %s", exc.status, attempt, member, exc)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(5 * attempt)
                continue
            return "error"

        except Exception as exc:
            log.error("Unexpected error on attempt %d for %s: %s", attempt, member, exc)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(5 * attempt)
                continue
            return "error"

    return "error"


# ═══════════════════════════════════════════════════════════════════════
#  BOT SETUP
# ═══════════════════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.members         = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

def is_admin():
    async def predicate(ctx):
        return str(ctx.author.id) in ADMIN_IDS
    return commands.check(predicate)

# ═══════════════════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    log.info("Bot online: %s (%s)", bot.user, bot.user.id)
    log.info("Servers: %d  |  Admin IDs: %s", len(bot.guilds), ADMIN_IDS)
    print("\n✅ Fully Automated Pacer Engine initialized.")
    print("✅ Web Server Host protection active.\n")

@bot.command(name="massdm")
@is_admin()
async def massdm_cmd(ctx, *, message: str = None):
    if campaign.active:
        return await ctx.send("❌ A campaign is already running. Use `!stop` first.")

    guild = ctx.guild
    if guild is None:
        return await ctx.send("❌ This command must be used inside a server, not in DMs.")

    # Check if the user replied to a message to use its content
    if ctx.message.reference and ctx.message.reference.message_id:
        try:
            replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_msg.content.strip():
                message = replied_msg.content
        except Exception:
            pass

    if message is None or not str(message).strip():
        return await ctx.send(f"**Usage:** `{PREFIX}massdm <message>`\n*(Or reply to a message with `{PREFIX}massdm`)*")

    # ── Init Campaign
    campaign.active     = True
    campaign.stop_flag  = False
    campaign.paused     = False
    campaign.guild_id   = guild.id
    campaign.template   = message.replace("\\n", "\n")
    campaign.start_time = datetime.now()
    campaign.sent = campaign.failed = campaign.skipped = 0

    status_msg = await ctx.send("🔄 Fetching members...")

    try:
        if not guild.chunked: await guild.chunk()
    except discord.Forbidden:
        campaign.reset()
        return await status_msg.edit(content="❌ Missing Permissions! The bot cannot see the member list.")
    except Exception as exc:
        log.error("Chunking failed: %s", exc)
        campaign.reset()
        return await status_msg.edit(content="❌ Failed to fetch members. Make sure **Server Members Intent** is enabled in the Discord Developer Portal.")

    members = [m for m in guild.members if not m.bot and str(m.id) not in campaign.sent_ids]
    random.shuffle(members)
    campaign.total = len(members)

    if campaign.total == 0:
        campaign.reset()
        return await status_msg.edit(content="⚠ No new members to DM (all completed or bots).")

    await status_msg.edit(content=f"🚀 Starting automated campaign for **{campaign.total}** members in **{guild.name}**.\n*Smart pacer running in background.*")
    log.info("Started campaign: %d members in %s", campaign.total, guild.name)

    # ── Main DM Loop
    for i, member in enumerate(members):
        if campaign.stop_flag: break
        while campaign.paused:
            await asyncio.sleep(1)
            if campaign.stop_flag: break
        if campaign.stop_flag: break

        result = await send_dm(member, guild)

        if result in ("forbidden", "error", "429"):
            pacer.add_invalid()

        if result == "sent":
            campaign.sent += 1
            campaign.sent_ids.add(str(member.id))
            log.info("✅ [%d/%d] Sent → %s", campaign.sent, campaign.total, member.name)
        elif result == "forbidden":
            campaign.skipped += 1
            log.info("⛔ [%d/%d] Closed → %s", campaign.sent, campaign.total, member.name)
        elif result == "429":
            campaign.failed += 1
            log.warning("⏳ [%d/%d] Ratelimited → %s", campaign.sent, campaign.total, member.name)
        else:
            campaign.failed += 1
            campaign.failed_ids.add(str(member.id))
            log.warning("❌ [%d/%d] Failed → %s", campaign.sent, campaign.total, member.name)

        if i > 0 and i % 50 == 0:
            campaign.save()

        await pacer.wait(ctx, result)

    # ── Campaign End
    campaign.save()
    elapsed = (datetime.now() - campaign.start_time).total_seconds()
    
    embed = discord.Embed(title="📬 Campaign Finished" if not campaign.stop_flag else "🛑 Campaign Stopped", color=0x5865F2)
    embed.add_field(name="✅ Sent", value=str(campaign.sent), inline=True)
    embed.add_field(name="⛔ Skipped (Closed DMs)", value=str(campaign.skipped), inline=True)
    embed.add_field(name="❌ Failed", value=str(campaign.failed), inline=True)
    embed.add_field(name="⏱ Duration", value=f"{elapsed/60:.1f} minutes", inline=False)
    await ctx.send(embed=embed)

    campaign.reset()

@bot.command(name="servers")
@is_admin()
async def servers_cmd(ctx):
    if not bot.guilds: return await ctx.send("❌ Bot is not in any servers.")
    lines = [f"• **{g.name}** — `{g.id}` ({g.member_count} members)" for g in bot.guilds]
    await ctx.send(embed=discord.Embed(title="🌐 Servers", description="\n".join(lines), color=0x5865F2))

@bot.command(name="ping")
@is_admin()
async def ping_cmd(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: `{latency}ms`")

@bot.command(name="stop")
@is_admin()
async def stop_cmd(ctx):
    if not campaign.active: return await ctx.send("⚠ No active campaign.")
    campaign.stop_flag = True
    await ctx.send("🛑 Stopping...")

@bot.command(name="pause")
@is_admin()
async def pause_cmd(ctx):
    if not campaign.active: return await ctx.send("⚠ No active campaign.")
    campaign.paused = True
    await ctx.send("⏸ Paused. Use `!resume`.")

@bot.command(name="resume")
@is_admin()
async def resume_cmd(ctx):
    if not campaign.active: return await ctx.send("⚠ No active campaign.")
    campaign.paused = False
    await ctx.send("▶ Resumed.")

@bot.command(name="status")
@is_admin()
async def status_cmd(ctx):
    if not campaign.active:
        return await ctx.send(f"No active campaign. Total sent all-time: **{len(campaign.sent_ids)}**")
    
    processed = campaign.sent + campaign.failed + campaign.skipped
    pct = (processed / campaign.total * 100) if campaign.total else 0
    await ctx.send(f"📊 **{pct:.1f}%** — Sent: **{campaign.sent}** | Closed DMs: **{campaign.skipped}** | Invalid Tracking: **{len(pacer.invalid_requests)}/8000**")

@bot.command(name="reset")
@is_admin()
async def reset_cmd(ctx):
    if campaign.active: return await ctx.send("❌ Stop campaign first.")
    count = len(campaign.sent_ids)
    campaign.sent_ids.clear()
    campaign.failed_ids.clear()
    campaign.save()
    await ctx.send(f"🗑 Cleared **{count}** records. You can re-DM everyone.")

# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL ERROR HANDLER
# ═══════════════════════════════════════════════════════════════════════

@bot.event
async def on_command_error(ctx, error):
    """Catches all errors across all commands so the bot never crashes."""
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🔒 Unauthorized. You are not listed in ADMIN_IDS in `.env`.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠ Missing argument: `{error.param.name}`. Run `{PREFIX}massdm` for usage.")
    elif isinstance(error, commands.CommandNotFound):
        pass # Ignore unknown commands
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ The bot is missing permissions to do this.")
    else:
        log.error("Unhandled Command Error: %s", error)

# ═══════════════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.error("Set your BOT_TOKEN in the .env file!")
        exit(1)
        
    try:
        keep_alive()
    except Exception as e:
        log.error("Failed to start keep_alive web server: %s", e)

    bot.run(BOT_TOKEN, log_handler=None)
