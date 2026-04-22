"""
TubeStream — Telegram Bot
=========================
Render FREE Web Service-এ deploy করার ধাপ:

1. GitHub-এ নতুন repo তৈরি করো
2. এই bot.py আর requirements.txt আপলোড করো
3. Render.com → New → Web Service → GitHub repo select করো
4. Build Command:  pip install -r requirements.txt
5. Start Command:  python bot.py
6. Deploy করো — শেষ!

সব কিছু এই ফাইলেই আছে, আলাদা কিছু লাগবে না।
"""

import asyncio
import logging
import time
from typing import Optional
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════
#  এখানে তোমার সব তথ্য দেওয়া আছে
# ════════════════════════════════════════════
BOT_TOKEN   = "8517198376:AAEy6hjWJfuFtoi-BtAFXLV8yHFVtvm3z18"
WORKER_URL  = "https://Televideoimage.hasanahmed.workers.dev"
API_SECRET  = "tubestream-secret-2024"
# ════════════════════════════════════════════

known_groups = {}
last_heartbeat = 0.0
bot_username: Optional[str] = None


async def post_media(session: aiohttp.ClientSession, data: dict) -> dict:
    try:
        async with session.post(
            f"{WORKER_URL}/api/media",
            json=data,
            headers={"X-API-Secret": API_SECRET},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            return await r.json()
    except Exception as e:
        logger.error(f"Worker error: {e}")
        return {}


async def heartbeat(session: aiohttp.ClientSession):
    global last_heartbeat
    if time.time() - last_heartbeat < 300:
        return
    last_heartbeat = time.time()
    try:
        async with session.post(
            f"{WORKER_URL}/api/bot/heartbeat",
            json={
                "botUsername": bot_username,
                "groupCount": len(known_groups),
                "groups": [{"id": k, "name": v} for k, v in known_groups.items()],
            },
            headers={"X-API-Secret": API_SECRET},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            await r.json()
        logger.info(f"Heartbeat OK | গ্রুপ: {len(known_groups)}")
    except Exception as e:
        logger.warning(f"Heartbeat failed: {e}")


def chat_info(update: Update):
    c = update.effective_chat
    return str(c.id), (c.title or c.username or str(c.id))


def is_group(update: Update) -> bool:
    t = update.effective_chat.type if update.effective_chat else None
    return t in ("group", "supergroup", "channel")


def get_msg(update: Update):
    return update.message or update.channel_post


# ─── ভিডিও ───────────────────────────────────────────────────
async def on_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        return
    msg = get_msg(update)
    if not msg or not msg.video:
        return

    gid, gname = chat_info(update)
    known_groups[gid] = gname
    v = msg.video
    dur = v.duration or 0
    mtype = "reel" if dur <= 90 else "video"

    data = dict(
        fileUniqueId=v.file_unique_id, fileId=v.file_id, type=mtype,
        caption=msg.caption, mimeType=v.mime_type or "video/mp4",
        fileSize=v.file_size, duration=dur or None,
        width=v.width, height=v.height,
        groupId=gid, groupName=gname,
        messageId=msg.message_id,
        senderId=str(msg.from_user.id) if msg.from_user else None,
        thumbnailFileId=v.thumbnail.file_id if v.thumbnail else None,
    )
    async with aiohttp.ClientSession() as s:
        r = await post_media(s, data)
        await heartbeat(s)
    icon = "✅" if r.get("created") else "♻️" if r.get("duplicate") else "⚠️"
    logger.info(f"{icon} {mtype} | {gname} | {v.file_unique_id[:10]}")


# ─── ছবি ─────────────────────────────────────────────────────
async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        return
    msg = get_msg(update)
    if not msg or not msg.photo:
        return

    gid, gname = chat_info(update)
    known_groups[gid] = gname
    ph = msg.photo[-1]

    data = dict(
        fileUniqueId=ph.file_unique_id, fileId=ph.file_id, type="image",
        caption=msg.caption, mimeType="image/jpeg",
        fileSize=ph.file_size, width=ph.width, height=ph.height,
        groupId=gid, groupName=gname,
        messageId=msg.message_id,
        senderId=str(msg.from_user.id) if msg.from_user else None,
        thumbnailFileId=ph.file_id,
    )
    async with aiohttp.ClientSession() as s:
        r = await post_media(s, data)
        await heartbeat(s)
    icon = "✅" if r.get("created") else "♻️" if r.get("duplicate") else "⚠️"
    logger.info(f"{icon} image | {gname} | {ph.file_unique_id[:10]}")


# ─── অ্যানিমেশন / GIF রিলস ───────────────────────────────────
async def on_animation(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        return
    msg = get_msg(update)
    if not msg or not msg.animation:
        return

    gid, gname = chat_info(update)
    known_groups[gid] = gname
    a = msg.animation

    data = dict(
        fileUniqueId=a.file_unique_id, fileId=a.file_id, type="reel",
        caption=msg.caption, mimeType=a.mime_type or "video/mp4",
        fileSize=a.file_size, duration=a.duration,
        width=a.width, height=a.height,
        groupId=gid, groupName=gname,
        messageId=msg.message_id,
        senderId=str(msg.from_user.id) if msg.from_user else None,
        thumbnailFileId=a.thumbnail.file_id if a.thumbnail else None,
    )
    async with aiohttp.ClientSession() as s:
        r = await post_media(s, data)
        await heartbeat(s)
    icon = "✅" if r.get("created") else "♻️" if r.get("duplicate") else "⚠️"
    logger.info(f"{icon} reel | {gname} | {a.file_unique_id[:10]}")


# ─── ভিডিও ডকুমেন্ট ──────────────────────────────────────────
async def on_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_group(update):
        return
    msg = get_msg(update)
    if not msg or not msg.document:
        return
    doc = msg.document
    if not doc.mime_type or not doc.mime_type.startswith("video/"):
        return

    gid, gname = chat_info(update)
    known_groups[gid] = gname

    data = dict(
        fileUniqueId=doc.file_unique_id, fileId=doc.file_id, type="video",
        caption=msg.caption, mimeType=doc.mime_type,
        fileSize=doc.file_size,
        groupId=gid, groupName=gname,
        messageId=msg.message_id,
        senderId=str(msg.from_user.id) if msg.from_user else None,
        thumbnailFileId=doc.thumbnail.file_id if doc.thumbnail else None,
    )
    async with aiohttp.ClientSession() as s:
        r = await post_media(s, data)
        await heartbeat(s)
    icon = "✅" if r.get("created") else "♻️" if r.get("duplicate") else "⚠️"
    logger.info(f"{icon} doc-video | {gname} | {doc.file_unique_id[:10]}")


# ─── শুরু ─────────────────────────────────────────────────────
async def on_start(app: Application):
    global bot_username
    me = await app.bot.get_me()
    bot_username = me.username
    logger.info(f"Bot started: @{bot_username}")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_start)
        .build()
    )

    gc = filters.ChatType.GROUPS | filters.ChatType.CHANNEL

    app.add_handler(MessageHandler(filters.VIDEO & gc, on_video))
    app.add_handler(MessageHandler(filters.PHOTO & gc, on_photo))
    app.add_handler(MessageHandler(filters.ANIMATION & gc, on_animation))
    app.add_handler(MessageHandler(filters.Document.VIDEO & gc, on_document))

    logger.info("TubeStream bot polling...")
    app.run_polling(allowed_updates=["message", "channel_post"])


if __name__ == "__main__":
    main()
