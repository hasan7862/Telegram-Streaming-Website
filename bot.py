import os
import sqlite3
import threading
import time
import logging
from flask import Flask, jsonify, request, Response
import requests
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8517198376:AAEy6hjWJfuFtoi-BtAFXLV8yHFVtvm3z18")
PORT = int(os.environ.get("PORT", "10000"))
DB_PATH = os.environ.get("DB_PATH", "media.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT UNIQUE,
            kind TEXT,
            duration INTEGER DEFAULT 0,
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            mime TEXT,
            caption TEXT,
            added_at INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kind_id ON media(kind, id DESC)")
    conn.commit()
    conn.close()


def add_media(file_id, kind, duration=0, width=0, height=0, mime="", caption=""):
    try:
        conn = db()
        conn.execute(
            "INSERT OR IGNORE INTO media (file_id, kind, duration, width, height, mime, caption, added_at) VALUES (?,?,?,?,?,?,?,?)",
            (file_id, kind, int(duration or 0), int(width or 0), int(height or 0), mime or "", caption or "", int(time.time())),
        )
        conn.commit()
        conn.close()
        log.info("saved %s file_id=%s dur=%s", kind, file_id[:20], duration)
    except Exception as e:
        log.exception("add_media failed: %s", e)


def list_media(kind, limit=30, offset=0):
    conn = db()
    if kind == "videos":
        rows = conn.execute(
            "SELECT * FROM media WHERE kind='video' AND duration BETWEEN 1 AND 600 ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    elif kind == "reels":
        rows = conn.execute(
            "SELECT * FROM media WHERE kind IN ('video','reel','animation') AND duration BETWEEN 1 AND 180 ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    elif kind == "images":
        rows = conn.execute(
            "SELECT * FROM media WHERE kind='image' ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM media ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ======================= Telegram handlers =======================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.effective_message.reply_text("Active.")
    except Exception:
        pass


async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    cap = (msg.caption or "")[:500]
    try:
        if msg.video:
            v = msg.video
            dur = v.duration or 0
            if 1 <= dur <= 600:
                add_media(v.file_id, "video", dur, v.width or 0, v.height or 0, v.mime_type or "video/mp4", cap)
        elif msg.animation:
            a = msg.animation
            dur = a.duration or 0
            if 1 <= dur <= 180:
                add_media(a.file_id, "animation", dur, a.width or 0, a.height or 0, a.mime_type or "video/mp4", cap)
        elif msg.photo:
            p = msg.photo[-1]
            add_media(p.file_id, "image", 0, p.width or 0, p.height or 0, "image/jpeg", cap)
        elif msg.document and msg.document.mime_type:
            mime = msg.document.mime_type
            if mime.startswith("image/"):
                add_media(msg.document.file_id, "image", 0, 0, 0, mime, cap)
            elif mime.startswith("video/"):
                add_media(msg.document.file_id, "video", 0, 0, 0, mime, cap)
        elif msg.video_note:
            vn = msg.video_note
            dur = vn.duration or 0
            if 1 <= dur <= 180:
                add_media(vn.file_id, "animation", dur, vn.length or 0, vn.length or 0, "video/mp4", cap)
    except Exception as e:
        log.exception("on_media failed: %s", e)


# ======================= Web server =======================

flask_app = Flask(__name__)

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
<meta name="theme-color" content="#0b0f17" />
<title>Stream</title>
<style>
  :root{
    --bg:#0b0f17; --bg2:#0f1422; --card:#141a2a; --border:#1f2740;
    --text:#e6ebf5; --muted:#8a93a8; --accent:#3b82f6; --accent2:#22d3ee;
    --like:#ef4444;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-tap-highlight-color:transparent}
  a{color:inherit;text-decoration:none}
  .app{max-width:980px;margin:0 auto;min-height:100vh;display:flex;flex-direction:column;padding-bottom:72px}
  header{position:sticky;top:0;z-index:30;background:rgba(11,15,23,.92);backdrop-filter:saturate(140%) blur(10px);border-bottom:1px solid var(--border)}
  .brand{display:flex;align-items:center;justify-content:space-between;padding:12px 14px}
  .logo{display:flex;align-items:center;gap:10px;font-weight:800;font-size:20px;letter-spacing:.3px}
  .dot{width:10px;height:10px;border-radius:999px;background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 0 12px rgba(59,130,246,.6)}
  .tabs{display:flex;gap:6px;padding:0 8px 10px;overflow:auto;scrollbar-width:none}
  .tabs::-webkit-scrollbar{display:none}
  .tab{flex:1;text-align:center;padding:10px 14px;border-radius:999px;background:var(--card);color:var(--muted);font-weight:600;font-size:14px;border:1px solid var(--border);white-space:nowrap;cursor:pointer;transition:.2s}
  .tab.active{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-color:transparent}
  main{flex:1;padding:12px}
  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
  @media(min-width:640px){.grid{grid-template-columns:repeat(3,1fr)}}
  @media(min-width:900px){.grid{grid-template-columns:repeat(4,1fr)}}
  .tile{position:relative;border-radius:14px;overflow:hidden;background:var(--card);border:1px solid var(--border);aspect-ratio:9/16;cursor:pointer}
  .tile.image{aspect-ratio:1/1}
  .tile video,.tile img{width:100%;height:100%;object-fit:cover;display:block;background:#000}
  .tile .badge{position:absolute;left:8px;bottom:8px;background:rgba(0,0,0,.6);color:#fff;font-size:11px;padding:3px 7px;border-radius:8px;font-weight:600}
  .tile .play{position:absolute;inset:0;display:grid;place-items:center;color:#fff;font-size:42px;text-shadow:0 4px 14px rgba(0,0,0,.6);opacity:.85;pointer-events:none}
  .empty{padding:60px 20px;text-align:center;color:var(--muted)}
  .empty .em{font-size:48px;margin-bottom:8px}
  .loader{display:flex;justify-content:center;padding:20px;color:var(--muted)}
  .spinner{width:20px;height:20px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}

  /* Reels feed */
  .reels{position:fixed;inset:0;background:#000;z-index:50;display:none}
  .reels.open{display:block}
  .reels .scroller{height:100dvh;overflow-y:scroll;scroll-snap-type:y mandatory;-webkit-overflow-scrolling:touch}
  .reel{height:100dvh;scroll-snap-align:start;position:relative;display:grid;place-items:center;background:#000}
  .reel video{width:100%;height:100%;object-fit:contain;background:#000}
  .reel .meta{position:absolute;left:0;right:60px;bottom:80px;padding:0 16px;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,.7)}
  .reel .meta .cap{font-size:14px;opacity:.92;line-height:1.4;max-height:6.4em;overflow:hidden}
  .reel .side{position:absolute;right:10px;bottom:90px;display:flex;flex-direction:column;gap:18px;align-items:center;color:#fff}
  .reel .side button{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);color:#fff;width:46px;height:46px;border-radius:999px;display:grid;place-items:center;font-size:22px;cursor:pointer}
  .reel .side button.liked{color:var(--like);border-color:rgba(239,68,68,.5)}
  .reels .close{position:absolute;top:14px;left:14px;z-index:5;background:rgba(0,0,0,.5);color:#fff;border:none;width:40px;height:40px;border-radius:999px;font-size:18px;cursor:pointer}
  .reels .progress{position:absolute;top:0;left:0;right:0;height:2px;background:rgba(255,255,255,.1)}
  .reels .progress .bar{height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .15s linear}

  /* Modal viewer (videos & images) */
  .modal{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;z-index:60;align-items:center;justify-content:center;padding:0}
  .modal.open{display:flex}
  .modal .body{width:100%;height:100%;display:grid;place-items:center;position:relative}
  .modal video,.modal img{max-width:100%;max-height:100dvh;object-fit:contain;background:#000}
  .modal .close{position:absolute;top:14px;right:14px;background:rgba(0,0,0,.5);color:#fff;border:none;width:40px;height:40px;border-radius:999px;font-size:18px;cursor:pointer;z-index:2}
  .modal .cap{position:absolute;left:0;right:0;bottom:0;padding:14px 18px;color:#fff;background:linear-gradient(transparent,rgba(0,0,0,.7));font-size:14px}

  /* Bottom nav */
  nav.bottom{position:fixed;bottom:0;left:0;right:0;z-index:40;background:rgba(11,15,23,.95);backdrop-filter:blur(10px);border-top:1px solid var(--border);display:flex;justify-content:space-around;padding:8px 6px env(safe-area-inset-bottom)}
  nav.bottom .nb{flex:1;text-align:center;padding:8px;color:var(--muted);font-size:11px;font-weight:600;cursor:pointer;border-radius:10px}
  nav.bottom .nb.active{color:var(--text)}
  nav.bottom .nb .ic{font-size:20px;display:block;margin-bottom:2px}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand">
      <div class="logo"><span class="dot"></span> Stream</div>
      <div style="font-size:12px;color:var(--muted)" id="count">—</div>
    </div>
    <div class="tabs">
      <div class="tab active" data-tab="reels">Reels</div>
      <div class="tab" data-tab="videos">Videos</div>
      <div class="tab" data-tab="images">Images</div>
    </div>
  </header>
  <main id="main">
    <div class="grid" id="grid"></div>
    <div class="loader" id="loader" style="display:none"><div class="spinner"></div></div>
    <div class="empty" id="empty" style="display:none"><div class="em">📭</div><div>No content yet. The bot will collect new media as it arrives.</div></div>
  </main>
</div>

<div class="reels" id="reels">
  <div class="progress"><div class="bar" id="rbar"></div></div>
  <button class="close" id="reelsClose">✕</button>
  <div class="scroller" id="rscroll"></div>
</div>

<div class="modal" id="modal">
  <button class="close" id="mClose">✕</button>
  <div class="body" id="mBody"></div>
</div>

<nav class="bottom">
  <div class="nb active" data-tab="reels"><span class="ic">▶</span>Reels</div>
  <div class="nb" data-tab="videos"><span class="ic">🎬</span>Videos</div>
  <div class="nb" data-tab="images"><span class="ic">🖼</span>Images</div>
</nav>

<script>
const grid = document.getElementById('grid');
const loader = document.getElementById('loader');
const empty = document.getElementById('empty');
const countEl = document.getElementById('count');
let currentTab = 'reels';
let offset = 0;
const PAGE = 30;
let loading = false;
let done = false;
let items = [];

function fmtDur(s){
  s = +s||0; if(!s) return '';
  const m = Math.floor(s/60), r = s%60;
  return (m? m+':' : '0:') + String(r).padStart(2,'0');
}

function tile(it){
  const t = document.createElement('div');
  t.className = 'tile' + (it.kind==='image' ? ' image' : '');
  if(it.kind === 'image'){
    t.innerHTML = `<img loading="lazy" src="/file/${it.file_id}" alt="">`;
  } else {
    t.innerHTML = `
      <video preload="metadata" muted playsinline src="/file/${it.file_id}#t=0.1"></video>
      <div class="play">▶</div>
      ${it.duration ? `<div class="badge">${fmtDur(it.duration)}</div>` : ''}
    `;
  }
  t.addEventListener('click', () => openItem(it));
  return t;
}

async function load(reset=false){
  if(loading) return;
  if(reset){ offset=0; done=false; items=[]; grid.innerHTML=''; empty.style.display='none'; }
  if(done) return;
  loading = true; loader.style.display='flex';
  try{
    const res = await fetch(`/api/media?type=${currentTab}&limit=${PAGE}&offset=${offset}`);
    const data = await res.json();
    if(data.length === 0){
      done = true;
      if(items.length===0) empty.style.display='block';
    } else {
      items = items.concat(data);
      data.forEach(it => grid.appendChild(tile(it)));
      offset += data.length;
      if(data.length < PAGE) done = true;
    }
    countEl.textContent = items.length + (done?' total':'+');
  }catch(e){ console.error(e); }
  finally{ loading=false; loader.style.display='none'; }
}

function setTab(name){
  currentTab = name;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.nb').forEach(t => t.classList.toggle('active', t.dataset.tab===name));
  load(true);
}

document.querySelectorAll('.tab,.nb').forEach(el => {
  el.addEventListener('click', () => setTab(el.dataset.tab));
});

window.addEventListener('scroll', () => {
  if(window.innerHeight + window.scrollY >= document.body.offsetHeight - 600){
    load();
  }
});

// ===== Reels feed (vertical) =====
const reels = document.getElementById('reels');
const rscroll = document.getElementById('rscroll');
const rbar = document.getElementById('rbar');
document.getElementById('reelsClose').addEventListener('click', closeReels);

function openReelsAt(startIdx){
  const reelItems = items.filter(i => i.kind !== 'image');
  if(reelItems.length === 0) return;
  rscroll.innerHTML = '';
  reelItems.forEach((it,idx) => {
    const r = document.createElement('div');
    r.className = 'reel';
    r.innerHTML = `
      <video src="/file/${it.file_id}" loop playsinline preload="${idx<2?'auto':'metadata'}" ${idx===0?'autoplay':''}></video>
      <div class="meta"><div class="cap">${(it.caption||'').replace(/[<>&]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))}</div></div>
      <div class="side">
        <button data-act="like">♥</button>
        <button data-act="mute">🔊</button>
      </div>
    `;
    rscroll.appendChild(r);
  });
  reels.classList.add('open');
  document.body.style.overflow='hidden';
  setTimeout(() => {
    const target = rscroll.children[Math.max(0,startIdx)];
    if(target) target.scrollIntoView({behavior:'instant', block:'start'});
    bindReelObserver();
  }, 30);
}

function closeReels(){
  reels.classList.remove('open');
  document.body.style.overflow='';
  rscroll.querySelectorAll('video').forEach(v => { try{v.pause()}catch(_){} v.removeAttribute('src'); v.load(); });
  rscroll.innerHTML='';
}

let muted = true;
function bindReelObserver(){
  rscroll.querySelectorAll('.side button').forEach(b => {
    b.onclick = (e) => {
      e.stopPropagation();
      if(b.dataset.act === 'like'){ b.classList.toggle('liked'); }
      if(b.dataset.act === 'mute'){
        muted = !muted;
        b.textContent = muted ? '🔊' : '🔇';
        rscroll.querySelectorAll('video').forEach(v => v.muted = muted);
      }
    };
  });
  rscroll.querySelectorAll('video').forEach(v => v.muted = muted);

  const io = new IntersectionObserver((entries) => {
    entries.forEach(en => {
      const v = en.target.querySelector('video');
      if(!v) return;
      if(en.isIntersecting && en.intersectionRatio > 0.7){
        v.play().catch(()=>{});
        v.ontimeupdate = () => {
          if(v.duration) rbar.style.width = ((v.currentTime/v.duration)*100).toFixed(2)+'%';
        };
      } else {
        v.pause();
      }
    });
  }, { threshold: [0, 0.7, 1] });
  rscroll.querySelectorAll('.reel').forEach(r => io.observe(r));
}

// ===== Modal (videos / images) =====
const modal = document.getElementById('modal');
const mBody = document.getElementById('mBody');
document.getElementById('mClose').addEventListener('click', closeModal);
modal.addEventListener('click', (e) => { if(e.target === modal) closeModal(); });

function openItem(it){
  if(currentTab === 'reels'){
    const idx = items.filter(i => i.kind !== 'image').findIndex(i => i.file_id === it.file_id);
    openReelsAt(idx >= 0 ? idx : 0);
    return;
  }
  if(it.kind === 'image'){
    mBody.innerHTML = `<img src="/file/${it.file_id}">${it.caption?`<div class="cap">${(it.caption||'').replace(/[<>&]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))}</div>`:''}`;
  } else {
    mBody.innerHTML = `<video src="/file/${it.file_id}" controls autoplay playsinline></video>${it.caption?`<div class="cap">${(it.caption||'').replace(/[<>&]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))}</div>`:''}`;
  }
  modal.classList.add('open');
  document.body.style.overflow='hidden';
}

function closeModal(){
  modal.classList.remove('open');
  document.body.style.overflow='';
  const v = mBody.querySelector('video');
  if(v){ try{v.pause()}catch(_){ } }
  mBody.innerHTML='';
}

// auto refresh every 30s on top
setInterval(() => { if(window.scrollY < 80 && !reels.classList.contains('open') && !modal.classList.contains('open')) load(true); }, 30000);

load(true);
</script>
</body>
</html>
"""


@flask_app.route("/")
def home():
    return Response(INDEX_HTML, mimetype="text/html; charset=utf-8")


@flask_app.route("/healthz")
def health():
    return "ok"


@flask_app.route("/api/media")
def api_media():
    kind = request.args.get("type", "reels")
    try:
        limit = max(1, min(int(request.args.get("limit", "30")), 100))
        offset = max(0, int(request.args.get("offset", "0")))
    except ValueError:
        limit, offset = 30, 0
    items = list_media(kind, limit, offset)
    return jsonify(items)


@flask_app.route("/file/<path:file_id>")
def file_proxy(file_id):
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=20,
        )
        if r.status_code != 200:
            return Response("not found", status=404)
        data = r.json()
        if not data.get("ok"):
            return Response("not found", status=404)
        path = data["result"]["file_path"]
        upstream = requests.get(
            f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}",
            stream=True,
            timeout=60,
        )
        if upstream.status_code != 200:
            return Response("upstream error", status=502)

        ctype = upstream.headers.get("Content-Type", "application/octet-stream")
        if ctype == "application/octet-stream":
            ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
            ctype = {
                "mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm",
                "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "gif": "image/gif", "webp": "image/webp",
            }.get(ext, ctype)

        headers = {
            "Content-Type": ctype,
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes",
        }
        cl = upstream.headers.get("Content-Length")
        if cl:
            headers["Content-Length"] = cl

        def stream():
            try:
                for chunk in upstream.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        return Response(stream(), headers=headers)
    except Exception as e:
        log.exception("file proxy: %s", e)
        return Response("error", status=500)


def run_web():
    from waitress import serve
    log.info("web listening on 0.0.0.0:%d", PORT)
    serve(flask_app, host="0.0.0.0", port=PORT, threads=8)


def run_bot():
    log.info("starting telegram bot")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    media_filter = (
        filters.PHOTO
        | filters.VIDEO
        | filters.ANIMATION
        | filters.VIDEO_NOTE
        | filters.Document.IMAGE
        | filters.Document.VIDEO
    )
    application.add_handler(MessageHandler(media_filter, on_media))
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
        close_loop=False,
    )


def main():
    init_db()
    t = threading.Thread(target=run_web, daemon=True)
    t.start()
    run_bot()


if __name__ == "__main__":
    main()
