"""
TubeStream — Telegram Bot
=====================================
Render-এ Deploy: 
1. GitHub এ upload করো bot.py + requirements.txt
2. Render.com → New Web Service → GitHub repo
3. Build Command: pip install -r requirements.txt
4. Start Command: python bot.py
5. Deploy করো → শেষ!
"""

import asyncio
import logging
import time
from typing import Optional
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ এখানে শুধু এই ৩টা জিনিস বসাও
BOT_TOKEN = "8517198376:AAEy6hjWJfuFtoi-BtAFXLV8yHFVtvm3z18"
WORKER_URL = "https://televideoimage.hasanahmed.workers.dev"  # ⚠️ তোমার Worker URL বসাও
API_SECRET = "tubestream-secret-2024"

known_groups = {}
last_heartbeat = 0.0
bot_username: Optional[str] = None

async def post_media(session, data):
    try:
        async with session.post(f"{WORKER_URL}/api/media", json=data, headers={"X-API-Secret": API_SECRET}, timeout=30) as r:
            return await r.json()
    except Exception as e:
        logger.error(f"Worker error: {e}")
        return {}

async def heartbeat(session):
    global last_heartbeat
    if time.time() - last_heartbeat < 300: return
    last_heartbeat = time.time()
    try:
        async with session.post(f"{WORKER_URL}/api/bot/heartbeat", json={"botUsername": bot_username, "groupCount": len(known_groups), "groups": [{"id": k, "name": v} for k, v in known_groups.items()]}, headers={"X-API-Secret": API_SECRET}, timeout=15) as r:
            await r.json()
        logger.info(f"Heartbeat OK | Groups: {len(known_groups)}")
    except Exception as e:
        logger.warning(f"Heartbeat failed: {e}")

def is_group(update): return update.effective_chat.type in ("group", "supergroup", "channel")
def get_msg(update): return update.message or update.channel_post

async def handle_media(update, ctx, media_type, get_data_func):
    if not is_group(update): return
    msg = get_msg(update)
    if not msg: return
    media = getattr(msg, media_type, None)
    if not media: return
    
    gid = str(update.effective_chat.id)
    gname = update.effective_chat.title or update.effective_chat.username or str(gid)
    known_groups[gid] = gname
    
    data = get_data_func(media, msg, gid, gname, msg.message_id, str(msg.from_user.id) if msg.from_user else None)
    
    async with aiohttp.ClientSession() as s:
        r = await post_media(s, data)
        await heartbeat(s)
    
    icon = "✅" if r.get("created") else "♻️" if r.get("duplicate") else "⚠️"
    logger.info(f"{icon} {media_type} | {gname}")

def video_data(v, msg, gid, gname, mid, sid):
    return dict(fileUniqueId=v.file_unique_id, fileId=v.file_id, type="reel" if v.duration and v.duration <= 90 else "video", caption=msg.caption, mimeType=v.mime_type or "video/mp4", fileSize=v.file_size, duration=v.duration, width=v.width, height=v.height, groupId=gid, groupName=gname, messageId=mid, senderId=sid, thumbnailFileId=v.thumbnail.file_id if v.thumbnail else None)

def photo_data(p, msg, gid, gname, mid, sid):
    return dict(fileUniqueId=p.file_unique_id, fileId=p.file_id, type="image", caption=msg.caption, mimeType="image/jpeg", fileSize=p.file_size, width=p.width, height=p.height, groupId=gid, groupName=gname, messageId=mid, senderId=sid, thumbnailFileId=p.file_id)

def animation_data(a, msg, gid, gname, mid, sid):
    return dict(fileUniqueId=a.file_unique_id, fileId=a.file_id, type="reel", caption=msg.caption, mimeType=a.mime_type or "video/mp4", fileSize=a.file_size, duration=a.duration, width=a.width, height=a.height, groupId=gid, groupName=gname, messageId=mid, senderId=sid, thumbnailFileId=a.thumbnail.file_id if a.thumbnail else None)

def doc_data(d, msg, gid, gname, mid, sid):
    return dict(fileUniqueId=d.file_unique_id, fileId=d.file_id, type="video", caption=msg.caption, mimeType=d.mime_type, fileSize=d.file_size, groupId=gid, groupName=gname, messageId=mid, senderId=sid, thumbnailFileId=d.thumbnail.file_id if d.thumbnail else None)

async def on_video(update, ctx): await handle_media(update, ctx, "video", video_data)
async def on_photo(update, ctx): await handle_media(update, ctx, "photo", photo_data)
async def on_animation(update, ctx): await handle_media(update, ctx, "animation", animation_data)
async def on_document(update, ctx): 
    if not is_group(update): return
    msg = get_msg(update)
    if msg and msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
        await handle_media(update, ctx, "document", doc_data)

async def on_start(app):
    global bot_username
    me = await app.bot.get_me()
    bot_username = me.username
    logger.info(f"Bot started: @{bot_username}")

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(on_start).build()
    gc = filters.ChatType.GROUPS | filters.ChatType.CHANNEL
    app.add_handler(MessageHandler(filters.VIDEO & gc, on_video))
    app.add_handler(MessageHandler(filters.PHOTO & gc, on_photo))
    app.add_handler(MessageHandler(filters.ANIMATION & gc, on_animation))
    app.add_handler(MessageHandler(filters.Document.VIDEO & gc, on_document))
    logger.info("TubeStream bot polling...")
    app.run_polling(allowed_updates=["message", "channel_post"])

if __name__ == "__main__":
    main()
