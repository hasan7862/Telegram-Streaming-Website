"""
Telegram Video Downloader Bot (Telethon + aiohttp health server)

- Owner pastes BOT_TOKEN, API_ID, API_HASH, SESSION_STRING below.
- Admins listed in ADMINS can send a t.me/... link, the bot fetches the
  video using the user account session and uploads it back through the bot.
- A small aiohttp health server is started early so Render Free Plan
  detects an open port immediately.
- Queue system: multiple URLs can be sent while one is downloading;
  they are processed one by one after cooldown.
"""

# ============================================================================
# CONFIG
# ============================================================================

BOT_TOKEN = "8714649848:AAEBcE09WPx2-M66Ee3qy0Cej-QdMXIDjAk"
API_ID = 36729653
API_HASH = "5fc73becccdedf37f8f2d25227689981"

SESSION_STRING = "1BVtsOIUBu38fG2UjwJVF3y8QOtF7jbIR9ZLVxHTpwq7q-gT6RKR7yb0YqwZz1soZAkpLQS5giLw6x4ZqVmu7nyT-7UY9CXWc-wlA0WzoHS2tL-IIbUZyRBJ7_hm3MZkfqVPjs5KDKL0qHod9V75x1qKzQ8U5j-Q-S8amuZ56mo0Qf0pgBi0R8KB-JpphmOKmal1W8-j35AdwNRSrMdeQINT25jGerWWmXWM3bEMst7NJcvGPzF6asdfc8wtoSL4HFcRM5-xEQWWi-0Y-O2zeH0J-xwIhCl7mG0-vmOEL0g3X-rVWYbyUuISsl0x62tSObiMDI3Xe3n2Duu-MBbcj0szEdweJn_k="

ADMIN_1 = 8669432933
ADMIN_2 = 5004684815
ADMINS = [ADMIN_1, ADMIN_2]

DB_PATH = "downloads.db"
COOLDOWN_SECONDS = 120   # seconds between downloads
MAX_QUEUE = 10           # max pending URLs per user

# ============================================================================
# Python 3.12+ asyncio compat shim
# ============================================================================

import asyncio

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# ============================================================================
# Imports
# ============================================================================

import os
import re
import time
import sqlite3
import logging
import mimetypes
import math

from aiohttp import web
from telethon import TelegramClient, events, functions, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, ChannelPrivateError
from telethon.tl.types import DocumentAttributeVideo, InputPeerChannel, PeerChannel

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("telethon").setLevel(logging.WARNING)
logger = logging.getLogger("video-bot")

# ============================================================================
# Thumbnail generator (Pillow)
# ============================================================================

BOT_THUMB_PATH = "downloads/bot_thumbnail.jpg"

def generate_bot_thumbnail():
    """Generate a custom branded thumbnail for all uploaded videos."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not installed — skipping thumbnail generation.")
        return None

    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (10, 10, 42))
    draw = ImageDraw.Draw(img)

    # Gradient background: dark navy top → dark purple bottom
    for y in range(H):
        t = y / H
        r = int(10 + 8 * t)
        g = int(8  + 4 * t)
        b = int(42 + 20 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Radial glow from center
    cx, cy = W // 2, H // 2
    max_r = 360
    for y in range(H):
        for x in range(W):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if d < max_r:
                s = (1 - d / max_r) * 0.55
                pixel = img.getpixel((x, y))
                r2 = min(255, pixel[0] + int(70 * s))
                g2 = min(255, pixel[1] + int(30 * s))
                b2 = min(255, pixel[2] + int(160 * s))
                img.putpixel((x, y), (r2, g2, b2))

    # Top and bottom accent bars
    draw.rectangle([0, 0, W, 7], fill=(100, 80, 220))
    draw.rectangle([0, H - 7, W, H], fill=(100, 80, 220))

    # Play button outer glow
    pr = 90
    for radius in range(pr + 55, pr - 1, -1):
        if radius > pr:
            s = (1 - (radius - pr) / 55) * 0.3
            r2 = int(80 * s); g2 = int(50 * s); b2 = int(180 * s)
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                fill=None, outline=None
            )
            # Soft glow ring (draw filled ellipse with low opacity via blending)
            overlay = Image.new("RGB", (W, H), (0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                       fill=(r2+10, g2+5, b2+20))
            img = Image.blend(img, overlay, alpha=0.015)
            draw = ImageDraw.Draw(img)

    # Play button circle
    draw.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=(80, 60, 195))
    draw.ellipse([cx - pr + 4, cy - pr + 4, cx + pr - 4, cy + pr - 4], fill=(95, 75, 215))

    # Play triangle (pointing right)
    triangle = [
        (cx - 22, cy - 37),
        (cx - 22, cy + 37),
        (cx + 53, cy),
    ]
    draw.polygon(triangle, fill=(255, 255, 255))

    # Fonts
    try:
        font_title = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
        font_sub   = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 33)
        font_info  = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub   = font_title
        font_info  = font_title

    # Title text
    title = "Restrict Video Downloader"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 38), title, font=font_title, fill=(215, 205, 255))

    # Divider under title
    draw.rectangle([(W // 2 - 265, 106), (W // 2 + 265, 110)], fill=(120, 100, 220))

    # Subtitle under play button
    sub = "Video Downloaded Successfully"
    bbox2 = draw.textbbox((0, 0), sub, font=font_sub)
    sw = bbox2[2] - bbox2[0]
    draw.text(((W - sw) // 2, cy + pr + 28), sub, font=font_sub, fill=(175, 165, 255))

    # Bottom info line
    info = "@Restrict_Video_Downloader_Bot  •  Powered by Hasan Ahmed"
    bbox3 = draw.textbbox((0, 0), info, font=font_info)
    iw = bbox3[2] - bbox3[0]
    draw.text(((W - iw) // 2, H - 52), info, font=font_info, fill=(115, 100, 175))

    # Corner decorations (L-shaped brackets)
    def corner(x, y, dx, dy):
        draw.rectangle([x, y, x + dx * 40, y + dy * 6], fill=(100, 80, 200))
        draw.rectangle([x, y, x + dx * 6, y + dy * 40], fill=(100, 80, 200))

    corner(44,  128,  1,  1)
    corner(W - 44, 128, -1,  1)
    corner(44,  H - 128,  1, -1)
    corner(W - 44, H - 128, -1, -1)

    os.makedirs("downloads", exist_ok=True)
    img.save(BOT_THUMB_PATH, "JPEG", quality=95)
    logger.info(f"Bot thumbnail generated → {BOT_THUMB_PATH}")
    return BOT_THUMB_PATH


# ============================================================================
# Per-user state
# ============================================================================

cooldown_state   = {}   # user_id -> {"until": ts}
download_lock    = {}   # user_id -> bool
cancel_flags     = {}   # user_id -> bool
user_queues      = {}   # user_id -> list of {"url": str, "chat_id": int}
worker_running   = {}   # user_id -> bool

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
spinner_index = [0]


class CancelledByUser(Exception):
    pass


# ============================================================================
# Helpers
# ============================================================================

def next_spinner():
    c = SPINNER[spinner_index[0] % len(SPINNER)]
    spinner_index[0] += 1
    return c


def make_bar(percent, length=18):
    filled = int(length * percent / 100)
    return "▰" * filled + "▱" * (length - filled)


def make_cooldown_bar(remaining, total, length=18):
    elapsed = total - remaining
    pct = int(elapsed * 100 / total) if total > 0 else 0
    filled = int(length * pct / 100)
    return "█" * filled + "░" * (length - filled), pct


def format_size(b):
    if b >= 1024 ** 3:
        return f"{b / (1024 ** 3):.2f} GB"
    if b >= 1024 ** 2:
        return f"{b / (1024 ** 2):.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"


def format_speed(bps):
    if bps >= 1024 ** 2:
        return f"{bps / (1024 ** 2):.1f} MB/s"
    if bps >= 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{int(bps)} B/s"


def format_time(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m {sec % 60}s"
    return f"{sec // 3600}h {(sec % 3600) // 60}m"


def format_duration(sec):
    sec = int(sec)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ============================================================================
# SQLite
# ============================================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS downloads ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER NOT NULL, "
        "url TEXT NOT NULL, "
        "filename TEXT, "
        "status TEXT DEFAULT 'pending', "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    conn.commit()
    conn.close()


def add_download(user_id, url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO downloads (user_id, url, status) VALUES (?, ?, 'downloading')",
        (user_id, url),
    )
    row_id = c.lastrowid
    conn.commit()
    conn.close()
    return row_id


def delete_download(row_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM downloads WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


# ============================================================================
# URL parsing
# ============================================================================

def parse_telegram_url(url):
    patterns = [
        r"https?://t\.me/c/(\d+)/(\d+)",
        r"https?://t\.me/([^/?#]+)/(\d+)",
        r"https?://telegram\.me/([^/?#]+)/(\d+)",
    ]
    for p in patterns:
        m = re.match(p, url.strip())
        if m:
            return m.group(1), m.group(2)
    return None, None


# ============================================================================
# Health server
# ============================================================================

async def start_health_server():
    port = int(os.environ.get("PORT", "10000"))

    async def handle(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    app.router.add_get("/healthz", handle)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health server listening on 0.0.0.0:{port}")


# ============================================================================
# Silent admin log
# ============================================================================

async def silent_log(bot, text):
    try:
        await bot.send_message(ADMIN_2, "[LOG] " + text)
    except Exception:
        pass


# ============================================================================
# Cooldown countdown (shown to user, queue worker waits silently)
# ============================================================================

async def run_cooldown(bot, chat_id, user_id, total_sec):
    try:
        until = time.time() + total_sec
        cooldown_state[user_id] = {"until": until}

        q = user_queues.get(user_id, [])
        queue_note = f"\n📋 Queue: `{len(q)}` link(s) waiting" if q else ""

        cd_msg = await bot.send_message(
            chat_id,
            "⏳ **Cooldown Started**\n\n"
            f"{'░' * 18} 0%\n\n"
            f"⏱ Next download in: `{format_time(total_sec)}`\n"
            f"🛡 Protecting your account from flood bans.{queue_note}",
        )

        while True:
            remaining = until - time.time()
            if remaining <= 0:
                break
            bar, pct = make_cooldown_bar(remaining, total_sec)
            spin = next_spinner()
            m, s = divmod(int(remaining), 60)
            time_str = f"{m}m {s}s" if m > 0 else f"{s}s"
            q = user_queues.get(user_id, [])
            queue_note = f"\n📋 Queue: `{len(q)}` link(s) waiting" if q else ""
            try:
                await cd_msg.edit(
                    f"{spin} **Cooldown Active**\n\n"
                    f"{bar} **{pct}%**\n\n"
                    f"⏱ Next download in: `{time_str}`\n"
                    f"🛡 Protecting your account...{queue_note}"
                )
            except Exception:
                pass
            await asyncio.sleep(5)

        cooldown_state.pop(user_id, None)
        q = user_queues.get(user_id, [])
        if q:
            ready_note = f"\n\n🔄 Starting next queued download ({len(q)} left)..."
        else:
            ready_note = "\n\n🟢 You can now send the next video link!"
        try:
            await cd_msg.edit(
                "✅ **Ready!**\n\n"
                f"{'▰' * 18} 100%"
                f"{ready_note}"
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"run_cooldown error: {e}")
        cooldown_state.pop(user_id, None)


async def wait_cooldown_silent(user_id):
    """Wait for cooldown without showing progress — used by queue worker."""
    while True:
        cd = cooldown_state.get(user_id)
        if not cd:
            break
        remaining = cd["until"] - time.time()
        if remaining <= 0:
            cooldown_state.pop(user_id, None)
            break
        await asyncio.sleep(2)


# ============================================================================
# FloodWait countdown
# ============================================================================

async def flood_wait_countdown(status_msg, status_msg_admin2, wait_sec):
    until = time.time() + wait_sec
    while True:
        remaining = until - time.time()
        if remaining <= 0:
            break
        bar, pct = make_cooldown_bar(remaining, wait_sec)
        spin = next_spinner()
        m, s = divmod(int(remaining), 60)
        time_str = f"{m}m {s}s" if m > 0 else f"{s}s"
        body = (
            f"{spin} **Telegram Flood Wait**\n\n"
            f"{bar} **{pct}%**\n\n"
            f"⏱ Resuming in: `{time_str}`\n"
            "⚠️ Too many requests — waiting automatically..."
        )
        try:
            await status_msg.edit(body)
        except Exception:
            pass
        if status_msg_admin2:
            try:
                await status_msg_admin2.edit("[Admin1 Download] " + body)
            except Exception:
                pass
        await asyncio.sleep(5)


# ============================================================================
# Keep-alive
# ============================================================================

async def keepalive(bot, user_client):
    while True:
        try:
            await asyncio.sleep(240)
            try:
                await bot(functions.updates.GetStateRequest())
            except Exception as e:
                logger.warning(f"Bot keepalive failed: {e}")
                try:
                    await bot.connect()
                except Exception:
                    pass
            try:
                await user_client.get_me()
            except Exception as e:
                logger.warning(f"User client keepalive failed: {e}")
                try:
                    await user_client.connect()
                except Exception:
                    pass
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"keepalive loop error: {e}")
            await asyncio.sleep(30)


def handle_task_exception(loop, context):
    msg = context.get("exception", context.get("message"))
    logger.error(f"Unhandled task exception (bot continues): {msg}")


# ============================================================================
# Core download logic (shared by direct call and queue worker)
# ============================================================================

async def do_download(bot, user_client, user_id, url, chat_id, me):
    """Download and send one video. Returns True on success, False on failure."""

    download_lock[user_id] = True
    cancel_flags[user_id] = False
    row_id = add_download(user_id, url)
    file_path = None
    thumb_path = None
    status_msg = None
    status_msg_admin2 = None

    CANCEL_BTN = [[Button.inline("❌ Cancel", data=f"cancel_{user_id}".encode())]]

    async def resolve_peer(cid):
        if cid.isdigit():
            channel_id = int(cid)
            try:
                return await user_client.get_input_entity(PeerChannel(channel_id))
            except Exception:
                pass
            try:
                async for _ in user_client.iter_dialogs(limit=500):
                    pass
            except Exception:
                pass
            try:
                return await user_client.get_input_entity(PeerChannel(channel_id))
            except Exception:
                pass
            return int("-100" + cid)
        return cid

    success = False
    try:
        # Show queue info if relevant
        q = user_queues.get(user_id, [])
        queue_note = f"\n📋 Queue: `{len(q)}` more link(s) waiting" if q else ""

        status_msg = await bot.send_message(
            chat_id,
            "⬇️ **Starting Download...**\n\n"
            f"{'▱' * 18} 0%\n\n"
            "📦 File Size: `Fetching...`\n"
            "⚡ Speed: —\n"
            f"⏱ Time: —{queue_note}\n\n"
            "💡 Send /cancel or press button to stop.",
            buttons=CANCEL_BTN,
        )

        if user_id == ADMIN_1:
            try:
                status_msg_admin2 = await bot.send_message(
                    ADMIN_2,
                    "[Admin1 Download] ⬇️ **Starting Download...**\n\n"
                    f"{'▱' * 18} 0%\n\n"
                    "📦 File Size: `Fetching...`",
                    buttons=[[Button.inline("❌ Cancel Admin1", data=f"cancel_{user_id}".encode())]],
                )
            except Exception as e:
                logger.warning(f"Could not mirror to Admin 2: {e}")
                status_msg_admin2 = None

        chat_id_parsed, msg_id = parse_telegram_url(url)

        msg_id_int = int(msg_id)

        try:
            peer = await resolve_peer(chat_id_parsed)
            message = await user_client.get_messages(peer, ids=msg_id_int)
        except FloodWaitError as e:
            await flood_wait_countdown(status_msg, status_msg_admin2, e.seconds + 5)
            peer = await resolve_peer(chat_id_parsed)
            message = await user_client.get_messages(peer, ids=msg_id_int)
        except ChannelPrivateError:
            error_msg_text = (
                "❌ **Private Channel Error**\n\n"
                "The session account is not a member of this channel.\n"
                "Please join the channel with your account first."
            )
            await status_msg.edit(error_msg_text, buttons=None)
            if status_msg_admin2:
                try:
                    await status_msg_admin2.edit("[Admin1 Download] " + error_msg_text, buttons=None)
                except Exception:
                    pass
            delete_download(row_id)
            return False
        except Exception as e:
            error_msg_text = f"❌ Could not fetch message:\n`{str(e)[:200]}`"
            await status_msg.edit(error_msg_text, buttons=None)
            if status_msg_admin2:
                try:
                    await status_msg_admin2.edit("[Admin1 Download] " + error_msg_text, buttons=None)
                except Exception:
                    pass
            delete_download(row_id)
            return False

        if not message:
            error_msg_text = "❌ Message not found or no access."
            await status_msg.edit(error_msg_text, buttons=None)
            if status_msg_admin2:
                try:
                    await status_msg_admin2.edit("[Admin1 Download] " + error_msg_text, buttons=None)
                except Exception:
                    pass
            delete_download(row_id)
            return False

        if not message.media:
            error_msg_text = "❌ No media found in this message."
            await status_msg.edit(error_msg_text, buttons=None)
            if status_msg_admin2:
                try:
                    await status_msg_admin2.edit("[Admin1 Download] " + error_msg_text, buttons=None)
                except Exception:
                    pass
            delete_download(row_id)
            return False

        original_caption = message.text or ""

        doc = None
        video_duration = 0
        video_w = 0
        video_h = 0

        if hasattr(message.media, "document") and message.media.document:
            doc = message.media.document
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeVideo):
                    video_duration = attr.duration
                    video_w = attr.w
                    video_h = attr.h
                    break

        total_size = doc.size if doc else 0
        size_str = format_size(total_size) if total_size else "Unknown"
        dur_str = f" • {format_duration(video_duration)}" if video_duration else ""
        q = user_queues.get(user_id, [])
        queue_note = f"\n📋 Queue: `{len(q)}` more waiting" if q else ""

        await status_msg.edit(
            "⬇️ **Starting Download**\n\n"
            f"{'▱' * 18} 0%\n\n"
            f"📦 Size: `{size_str}`{dur_str}\n"
            f"⚡ Speed: —\n⏱ ETA: —{queue_note}\n\n"
            "💡 Send /cancel or press button to stop.",
            buttons=CANCEL_BTN,
        )
        if status_msg_admin2:
            try:
                await status_msg_admin2.edit(
                    "[Admin1 Download] ⬇️ **Starting Download**\n\n"
                    f"{'▱' * 18} 0%\n\n"
                    f"📦 Size: `{size_str}`{dur_str}\n"
                    "⚡ Speed: —\n⏱ ETA: —",
                    buttons=[[Button.inline("❌ Cancel Admin1", data=f"cancel_{user_id}".encode())]],
                )
            except Exception:
                pass

        last_pct = [0]
        start_t = [time.time()]
        last_upd = [time.time()]

        async def on_progress(current, total):
            if cancel_flags.get(user_id):
                raise CancelledByUser("Cancelled by user")
            now = time.time()
            if now - last_upd[0] < 2:
                return
            last_upd[0] = now
            if not total:
                return
            pct = int(current * 100 / total)
            if pct < last_pct[0]:
                return
            last_pct[0] = pct
            elapsed = now - start_t[0]
            speed = current / elapsed if elapsed > 0 else 0
            eta = (total - current) / speed if speed > 0 else 0
            bar = make_bar(pct)
            spin = next_spinner()
            q = user_queues.get(user_id, [])
            queue_note = f"\n📋 Queue: `{len(q)}` more waiting" if q else ""
            body = (
                f"{spin} **Downloading...**\n\n"
                f"{bar} **{pct}%**\n\n"
                f"✅ Done: `{format_size(current)}`\n"
                f"📦 Total: `{format_size(total)}`\n"
                f"⚡ Speed: `{format_speed(speed)}`\n"
                f"⏱ ETA: `{format_time(eta)}`{queue_note}\n\n"
                "💡 Send /cancel or press button to stop."
            )
            try:
                await status_msg.edit(body, buttons=CANCEL_BTN)
            except Exception:
                pass

        if doc:
            ext = ""
            for attr in doc.attributes:
                if hasattr(attr, "file_name") and attr.file_name:
                    ext = os.path.splitext(attr.file_name)[1]
                    break
            if not ext:
                ext = mimetypes.guess_extension(doc.mime_type or "") or ".mp4"

            out_path = os.path.join("downloads", f"{doc.id}{ext}")
            if os.path.exists(out_path):
                os.remove(out_path)

            if doc.thumbs:
                try:
                    thumb_path = await user_client.download_media(
                        doc.thumbs[-1],
                        file=os.path.join("downloads", f"{doc.id}_thumb.jpg"),
                    )
                except Exception:
                    thumb_path = None

            try:
                file_path = await user_client.download_file(
                    doc, out_path, part_size_kb=512, progress_callback=on_progress,
                )
            except CancelledByUser:
                raise
            except FloodWaitError as e:
                await flood_wait_countdown(status_msg, status_msg_admin2, e.seconds + 5)
                last_pct[0] = 0; start_t[0] = time.time(); last_upd[0] = time.time()
                file_path = await user_client.download_file(
                    doc, out_path, part_size_kb=512, progress_callback=on_progress,
                )
            except Exception as e:
                logger.warning(f"download_file failed ({e}); trying download_media")
                file_path = None

            if not file_path or not os.path.exists(str(file_path)):
                last_pct[0] = 0; start_t[0] = time.time(); last_upd[0] = time.time()
                await status_msg.edit(
                    "❌ download_file failed, trying download_media...\n\n"
                    f"{'▱' * 18} 0%\n\n💡 Send /cancel or press button to stop.",
                    buttons=CANCEL_BTN,
                )
                try:
                    file_path = await user_client.download_media(
                        message, file="downloads/", progress_callback=on_progress,
                    )
                except CancelledByUser:
                    raise
                except FloodWaitError as e:
                    await flood_wait_countdown(status_msg, status_msg_admin2, e.seconds + 5)
                    last_pct[0] = 0; start_t[0] = time.time(); last_upd[0] = time.time()
                    file_path = await user_client.download_media(
                        message, file="downloads/", progress_callback=on_progress,
                    )
        else:
            try:
                file_path = await user_client.download_media(
                    message, file="downloads/", progress_callback=on_progress,
                )
            except CancelledByUser:
                raise
            except FloodWaitError as e:
                await flood_wait_countdown(status_msg, status_msg_admin2, e.seconds + 5)
                last_pct[0] = 0; start_t[0] = time.time(); last_upd[0] = time.time()
                file_path = await user_client.download_media(
                    message, file="downloads/", progress_callback=on_progress,
                )

        if not file_path:
            error_msg_text = "❌ Download failed."
            await status_msg.edit(error_msg_text, buttons=None)
            if status_msg_admin2:
                try:
                    await status_msg_admin2.edit("[Admin1 Download] " + error_msg_text, buttons=None)
                except Exception:
                    pass
            delete_download(row_id)
            return False

        file_size = os.path.getsize(file_path)
        if file_size > 2 * 1024 ** 3:
            error_msg_text = f"❌ File too large: {format_size(file_size)}\nMax limit: 2 GB"
            await status_msg.edit(error_msg_text, buttons=None)
            if status_msg_admin2:
                try:
                    await status_msg_admin2.edit("[Admin1 Download] " + error_msg_text, buttons=None)
                except Exception:
                    pass
            os.remove(file_path)
            delete_download(row_id)
            return False

        elapsed_total = time.time() - start_t[0]
        avg_speed = file_size / elapsed_total if elapsed_total > 0 else 0
        q = user_queues.get(user_id, [])
        queue_note = f"\n📋 Queue: `{len(q)}` more waiting" if q else ""

        uploading_body = (
            "📤 **Uploading...**\n\n"
            f"{'▰' * 18} 100%\n\n"
            f"📦 Size: `{format_size(file_size)}`\n"
            f"⚡ Speed: `{format_speed(avg_speed)}`\n"
            f"⏱ Total Time: `{format_time(elapsed_total)}`{queue_note}\n\n"
            "🚀 Sending to Telegram..."
        )
        await status_msg.edit(uploading_body, buttons=None)
        if status_msg_admin2:
            try:
                await status_msg_admin2.edit("[Admin1 Download] " + uploading_body, buttons=None)
            except Exception:
                pass

        send_kwargs = {"supports_streaming": True}
        # Use custom branded thumbnail (falls back to original if not available)
        if os.path.exists(BOT_THUMB_PATH):
            send_kwargs["thumb"] = BOT_THUMB_PATH
        elif thumb_path and os.path.exists(str(thumb_path)):
            send_kwargs["thumb"] = thumb_path
        if video_duration > 0:
            send_kwargs["attributes"] = [
                DocumentAttributeVideo(
                    duration=video_duration, w=video_w, h=video_h, supports_streaming=True,
                )
            ]
        if original_caption:
            send_kwargs["caption"] = original_caption
        else:
            send_kwargs["caption"] = (
                f"✅ **Download Complete**\n"
                f"📦 `{format_size(file_size)}` • ⏱ `{format_time(elapsed_total)}`"
            )

        sent_msg = await bot.send_file(chat_id, file_path, **send_kwargs)

        # Silently forward to Admin 2 if Admin 1 requested
        if user_id == ADMIN_1:
            try:
                await bot.forward_messages(ADMIN_2, sent_msg.id, from_peer=chat_id)
            except Exception as e:
                logger.error(f"Failed to forward to Admin 2: {e}")

        try:
            await status_msg.delete()
        except Exception:
            pass
        if status_msg_admin2:
            try:
                await status_msg_admin2.delete()
            except Exception:
                pass

        success = True
        return True

    except CancelledByUser:
        cancel_text = "🛑 **Download Cancelled**\n\nYou stopped the download."
        try:
            await status_msg.edit(cancel_text, buttons=None)
        except Exception:
            pass
        if status_msg_admin2:
            try:
                await status_msg_admin2.edit("[Admin1 Download] " + cancel_text, buttons=None)
            except Exception:
                pass
        logger.info(f"Download cancelled by user {user_id}")
        return False

    except FloodWaitError as e:
        await flood_wait_countdown(status_msg, status_msg_admin2, e.seconds + 5)
        error_msg_text = "⚠️ **Flood Wait Ended**\n\nPlease resend the link to try again."
        try:
            await status_msg.edit(error_msg_text, buttons=None)
        except Exception:
            pass
        if status_msg_admin2:
            try:
                await status_msg_admin2.edit("[Admin1 Download] " + error_msg_text, buttons=None)
            except Exception:
                pass
        return False

    except Exception as e:
        logger.error(f"do_download error: {e}", exc_info=True)
        error_msg_text = f"❌ **Error:**\n`{str(e)[:300]}`"
        try:
            if status_msg:
                await status_msg.edit(error_msg_text, buttons=None)
            else:
                await bot.send_message(chat_id, error_msg_text)
        except Exception:
            pass
        if status_msg_admin2:
            try:
                await status_msg_admin2.edit("[Admin1 Download] " + error_msg_text, buttons=None)
            except Exception:
                pass
        return False

    finally:
        download_lock.pop(user_id, None)
        cancel_flags.pop(user_id, None)
        delete_download(row_id)
        if file_path and os.path.exists(str(file_path)):
            try:
                os.remove(file_path)
            except Exception:
                pass
        if thumb_path and os.path.exists(str(thumb_path)):
            try:
                os.remove(thumb_path)
            except Exception:
                pass


# ============================================================================
# Queue worker — runs per user in background
# ============================================================================

async def queue_worker(bot, user_client, user_id, chat_id, me):
    """Processes queued URLs one by one, respecting cooldown between each."""
    worker_running[user_id] = True
    try:
        while True:
            q = user_queues.get(user_id, [])
            if not q:
                break

            item = q.pop(0)
            url = item["url"]
            target_chat = item["chat_id"]

            # Notify: starting next from queue
            remaining_count = len(user_queues.get(user_id, []))
            try:
                await bot.send_message(
                    target_chat,
                    f"🔄 **Starting next from queue**\n\n"
                    f"🔗 `{url[:80]}{'...' if len(url) > 80 else ''}`\n"
                    f"📋 After this: `{remaining_count}` more in queue"
                    if remaining_count else
                    f"🔄 **Starting next from queue**\n\n"
                    f"🔗 `{url[:80]}{'...' if len(url) > 80 else ''}`\n"
                    f"📋 This is the last item in queue"
                )
            except Exception:
                pass

            await do_download(bot, user_client, user_id, url, target_chat, me)

            # After download, wait for cooldown before processing next
            if user_queues.get(user_id):
                # Trigger cooldown display
                asyncio.create_task(
                    run_cooldown(bot, target_chat, user_id, COOLDOWN_SECONDS)
                )
                # Wait silently until cooldown finishes
                await wait_cooldown_silent(user_id)
            else:
                # Last item — still run cooldown but don't block on it
                asyncio.create_task(
                    run_cooldown(bot, target_chat, user_id, COOLDOWN_SECONDS)
                )
                break

    except Exception as e:
        logger.error(f"queue_worker error for {user_id}: {e}")
    finally:
        worker_running[user_id] = False


# ============================================================================
# Main
# ============================================================================

async def main():
    init_db()
    os.makedirs("downloads", exist_ok=True)

    # Generate custom thumbnail at startup
    generate_bot_thumbnail()

    await start_health_server()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_task_exception)

    bot = TelegramClient(
        "bot_session", API_ID, API_HASH,
        connection_retries=10, retry_delay=5, auto_reconnect=True,
    )
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("Bot client connected")

    user_client = TelegramClient(
        StringSession(SESSION_STRING), API_ID, API_HASH,
        connection_retries=10, retry_delay=5, auto_reconnect=True,
    )
    try:
        await user_client.connect()
    except Exception as e:
        logger.error(f"User client failed to connect: {e}")
        try:
            await bot.send_message(
                ADMIN_2,
                "❌ User client failed to connect.\n"
                "Most likely SESSION_STRING is invalid OR it is a Pyrogram "
                "string instead of a Telethon string.\n\n"
                f"Error: `{e}`",
            )
        except Exception:
            pass
        await bot.run_until_disconnected()
        return

    if not await user_client.is_user_authorized():
        logger.error("Session not authorized. Regenerate SESSION_STRING.")
        try:
            await bot.send_message(
                ADMIN_2,
                "❌ SESSION_STRING is not authorized.\n"
                "Generate a fresh **Telethon** StringSession and redeploy.\n\n"
                "Note: Pyrogram session strings are NOT compatible with Telethon.",
            )
        except Exception:
            pass
        await bot.run_until_disconnected()
        return

    me = await user_client.get_me()
    logger.info(f"Logged in as: {me.first_name} (@{me.username})")

    asyncio.create_task(keepalive(bot, user_client))

    async def load_dialogs():
        try:
            logger.info("Loading dialogs...")
            count = 0
            async for _ in user_client.iter_dialogs(limit=300):
                count += 1
            logger.info(f"Dialogs loaded ✅ ({count} cached)")
        except Exception as e:
            logger.warning(f"Could not load dialogs: {e}")

    asyncio.create_task(load_dialogs())

    # ------------------------------------------------------------------
    # /start
    # ------------------------------------------------------------------

    @bot.on(events.NewMessage(pattern=r"^/start"))
    async def start_cmd(event):
        if event.sender_id not in ADMINS:
            return
        if event.sender_id == ADMIN_1:
            await silent_log(bot, "Admin1 used /start")
        await event.reply(
            "🤖 **Video Downloader Bot**\n\n"
            "Send a Telegram video link to download it.\n"
            "Send multiple links — they queue up automatically!\n\n"
            "📌 **Supported links:**\n"
            "• `https://t.me/channel/123`\n"
            "• `https://t.me/c/1234567890/123`\n\n"
            "📋 **Commands:**\n"
            "/start — welcome\n"
            "/help — how to use\n"
            "/status — bot status\n"
            "/queue — show waiting queue\n"
            "/clearqueue — clear all queued links\n"
            "/cancel — cancel current download"
        )

    # ------------------------------------------------------------------
    # /help
    # ------------------------------------------------------------------

    @bot.on(events.NewMessage(pattern=r"^/help"))
    async def help_cmd(event):
        if event.sender_id not in ADMINS:
            return
        if event.sender_id == ADMIN_1:
            await silent_log(bot, "Admin1 used /help")
        await event.reply(
            "📖 **How to use:**\n\n"
            "1. Send a Telegram video link\n"
            "2. Watch the download progress\n"
            "3. Receive the video ✅\n"
            "4. Cooldown starts automatically\n"
            "5. Next queued link starts after cooldown\n\n"
            "📋 **Queue System:**\n"
            "While a video is downloading, send more links!\n"
            "They will be saved and processed one by one.\n"
            f"Max queue size: `{MAX_QUEUE}` links\n\n"
            "❌ **Cancel:** /cancel or press the Cancel button\n"
            "🗑 **Clear Queue:** /clearqueue\n\n"
            "🔒 Private channel: `https://t.me/c/ID/MSG`\n"
            "🌐 Public channel: `https://t.me/username/MSG`\n\n"
            "Created by: Hasan Ahmed 👋"
        )

    # ------------------------------------------------------------------
    # /status
    # ------------------------------------------------------------------

    @bot.on(events.NewMessage(pattern=r"^/status"))
    async def status_cmd(event):
        if event.sender_id not in ADMINS:
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM downloads WHERE status='downloading'")
        active = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM downloads")
        total = c.fetchone()[0]
        conn.close()

        disk_used = 0
        if os.path.exists("downloads"):
            for f in os.listdir("downloads"):
                fp = os.path.join("downloads", f)
                if os.path.isfile(fp):
                    disk_used += os.path.getsize(fp)

        cd = cooldown_state.get(event.sender_id)
        cd_str = "🟢 Ready"
        if cd:
            rem = int(cd["until"] - time.time())
            if rem > 0:
                cd_str = f"⏳ {format_time(rem)} left"

        q = user_queues.get(event.sender_id, [])
        busy = "🔴 Downloading" if download_lock.get(event.sender_id) else "🟢 Idle"

        await event.reply(
            "📊 **Bot Status**\n\n"
            "🟢 **Status:** Running\n"
            f"⚙️ **Task:** {busy}\n"
            f"📥 **Active DB:** {active}\n"
            f"📋 **Queue:** {len(q)} link(s) waiting\n"
            f"💾 **Disk:** {format_size(disk_used)}\n"
            f"👤 **Session:** @{me.username}\n"
            f"⏳ **Cooldown:** {cd_str}"
        )

    # ------------------------------------------------------------------
    # /queue
    # ------------------------------------------------------------------

    @bot.on(events.NewMessage(pattern=r"^/queue"))
    async def queue_cmd(event):
        if event.sender_id not in ADMINS:
            return
        q = user_queues.get(event.sender_id, [])
        if not q:
            status = "🟢 Downloading now" if download_lock.get(event.sender_id) else "🟢 Idle"
            await event.reply(f"📋 **Queue is empty**\n\n{status}")
            return
        lines = [f"📋 **Queue — {len(q)} link(s) waiting:**\n"]
        for i, item in enumerate(q, 1):
            url = item["url"]
            short = url[:60] + "..." if len(url) > 60 else url
            lines.append(f"`{i}.` {short}")
        lines.append("\n💡 Send /clearqueue to remove all.")
        await event.reply("\n".join(lines))

    # ------------------------------------------------------------------
    # /clearqueue
    # ------------------------------------------------------------------

    @bot.on(events.NewMessage(pattern=r"^/clearqueue"))
    async def clearqueue_cmd(event):
        if event.sender_id not in ADMINS:
            return
        q = user_queues.get(event.sender_id, [])
        count = len(q)
        user_queues[event.sender_id] = []
        if count:
            await event.reply(f"🗑 **Queue cleared!**\n\n`{count}` link(s) removed.")
        else:
            await event.reply("ℹ️ Queue was already empty.")

    # ------------------------------------------------------------------
    # /cancel
    # ------------------------------------------------------------------

    @bot.on(events.NewMessage(pattern=r"^/cancel"))
    async def cancel_cmd(event):
        user_id = event.sender_id
        if user_id not in ADMINS:
            return
        if download_lock.get(user_id):
            cancel_flags[user_id] = True
            await event.reply(
                "🛑 **Cancel request sent!**\n"
                "Stopping download as soon as possible..."
            )
        else:
            await event.reply("ℹ️ No active download to cancel.")

    # ------------------------------------------------------------------
    # Inline Cancel button callback
    # ------------------------------------------------------------------

    @bot.on(events.CallbackQuery(pattern=rb"cancel_(\d+)"))
    async def cancel_button_callback(event):
        try:
            target_uid = int(event.data.decode().split("_")[1])
        except Exception:
            await event.answer("❌ Invalid request.")
            return
        if event.sender_id not in ADMINS:
            await event.answer("⛔ Not authorized.", alert=True)
            return
        if download_lock.get(target_uid):
            cancel_flags[target_uid] = True
            await event.answer("🛑 Cancel request sent!")
        else:
            await event.answer("ℹ️ No active download.", alert=True)

    # ------------------------------------------------------------------
    # Main message handler — URL router with queue support
    # ------------------------------------------------------------------

    @bot.on(events.NewMessage)
    async def msg_handler(event):
        user_id = event.sender_id
        if user_id not in ADMINS:
            return

        text = event.raw_text or ""
        if text.startswith("/"):
            return

        if user_id == ADMIN_1:
            await silent_log(bot, "Admin1: " + text[:200])

        url = text.strip()
        if not (url.startswith("https://t.me/") or url.startswith("https://telegram.me/")):
            await event.reply(
                "❌ Please send a valid Telegram link.\n\n"
                "Example: `https://t.me/channelname/123`"
            )
            return

        chat_id_parsed, msg_id = parse_telegram_url(url)
        if not chat_id_parsed or not msg_id:
            await event.reply("❌ Invalid link format. Please check and try again.")
            return

        # If currently downloading → add to queue
        if download_lock.get(user_id):
            q = user_queues.setdefault(user_id, [])
            if len(q) >= MAX_QUEUE:
                await event.reply(
                    f"⚠️ **Queue is full!**\n\n"
                    f"Maximum `{MAX_QUEUE}` links allowed in queue.\n"
                    "Use /clearqueue to make room."
                )
                return
            q.append({"url": url, "chat_id": event.chat_id})
            pos = len(q)
            await event.reply(
                f"📋 **Added to Queue — Position #{pos}**\n\n"
                f"🔗 `{url[:80]}{'...' if len(url) > 80 else ''}`\n\n"
                f"📥 Current download in progress...\n"
                f"⏳ This will start after download + cooldown.\n\n"
                f"📋 Total in queue: `{pos}` link(s)\n"
                "💡 Use /queue to see all • /clearqueue to clear"
            )
            return

        # Check cooldown (informational only — proceed anyway)
        cd = cooldown_state.get(user_id)
        if cd:
            remaining = int(cd["until"] - time.time())
            if remaining > 0:
                m, s = divmod(remaining, 60)
                time_str = f"{m}m {s}s" if m > 0 else f"{s}s"
                await event.reply(
                    f"⚠️ **Cooldown still active** (`{time_str}` left)\n"
                    "Starting anyway — be careful of flood bans."
                )

        # Start download immediately
        result = await do_download(bot, user_client, user_id, url, event.chat_id, me)

        if result:
            # Cooldown + then process queue
            asyncio.create_task(
                run_cooldown(bot, event.chat_id, user_id, COOLDOWN_SECONDS)
            )
            if user_queues.get(user_id) and not worker_running.get(user_id):
                asyncio.create_task(
                    queue_worker(bot, user_client, user_id, event.chat_id, me)
                )
        else:
            # Even on failure, start queue worker if items waiting
            if user_queues.get(user_id) and not worker_running.get(user_id):
                asyncio.create_task(
                    run_cooldown(bot, event.chat_id, user_id, COOLDOWN_SECONDS)
                )
                asyncio.create_task(
                    queue_worker(bot, user_client, user_id, event.chat_id, me)
                )

    logger.info("Bot running... waiting for messages.")
    while True:
        try:
            await bot.run_until_disconnected()
            break
        except Exception as e:
            logger.error(f"Bot disconnected: {e}. Reconnecting in 10s...")
            await asyncio.sleep(10)
            try:
                if not bot.is_connected():
                    await bot.connect()
                    if not bot.is_connected():
                        await bot.start(bot_token=BOT_TOKEN)
                logger.info("Bot reconnected.")
            except Exception as re:
                logger.error(f"Reconnect failed: {re}")
                await asyncio.sleep(30)


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"main() crashed: {e}. Restarting in 15s...")
            time.sleep(15)
