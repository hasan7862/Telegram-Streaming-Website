// ============================================================
// TubeStream — Cloudflare Worker
// Deploy করো: https://dash.cloudflare.com/
// Workers & Pages → Create → Worker → Paste করো → Deploy
// তারপর Settings → Variables → BOT_TOKEN, API_SECRET যোগ করো
// D1 Database তৈরি করো "tubestream" নামে, Worker-এর সাথে bind করো DB নামে
// ============================================================

const BOT_API = "https://api.telegram.org";

// ─── HTML FRONTEND ────────────────────────────────────────────
const HTML = `<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TubeStream</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d0d0d;--card:#1a1a1a;--accent:#7c3aed;--accent2:#3b82f6;--text:#f1f1f1;--muted:#888;--border:#2a2a2a}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}

/* NAV */
nav{background:#111;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100;padding:0 16px}
.nav-inner{max-width:1400px;margin:0 auto;display:flex;align-items:center;gap:12px;height:56px}
.logo{font-size:20px;font-weight:800;color:var(--accent);text-decoration:none;white-space:nowrap}
.logo span{color:var(--accent2)}
.search-box{flex:1;position:relative}
.search-box input{width:100%;background:#222;border:1px solid var(--border);border-radius:8px;padding:8px 14px 8px 36px;color:var(--text);font-size:14px;outline:none}
.search-box input:focus{border-color:var(--accent)}
.search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:15px}
.nav-stats{font-size:12px;color:var(--muted);white-space:nowrap;display:none}
@media(min-width:600px){.nav-stats{display:block}}

/* TABS */
.tabs{display:flex;gap:4px;padding:12px 16px 0;max-width:1400px;margin:0 auto;overflow-x:auto;scrollbar-width:none}
.tab{padding:8px 20px;border-radius:8px 8px 0 0;cursor:pointer;font-size:14px;font-weight:600;border:none;background:transparent;color:var(--muted);transition:.2s;white-space:nowrap}
.tab.active{background:var(--card);color:var(--text);border-bottom:2px solid var(--accent)}
.tab:hover:not(.active){color:var(--text)}

/* MAIN */
main{max-width:1400px;margin:0 auto;padding:16px}

/* GRID */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.grid.reel-grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}
@media(max-width:480px){.grid{grid-template-columns:repeat(2,1fr)}.grid.reel-grid{grid-template-columns:repeat(2,1fr)}}

/* CARD */
.card{background:var(--card);border-radius:12px;overflow:hidden;cursor:pointer;border:1px solid var(--border);transition:.2s;position:relative}
.card:hover{border-color:var(--accent);transform:translateY(-2px)}
.thumb{position:relative;background:#111;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;overflow:hidden}
.reel-grid .thumb{aspect-ratio:9/16}
.thumb img{width:100%;height:100%;object-fit:cover}
.thumb .no-thumb{font-size:32px;opacity:.3}
.play-icon{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:.2s;background:rgba(0,0,0,.4)}
.card:hover .play-icon{opacity:1}
.play-icon svg{width:44px;height:44px;fill:rgba(255,255,255,.9)}
.type-badge{position:absolute;top:6px;left:6px;background:rgba(0,0,0,.7);border-radius:5px;padding:2px 7px;font-size:11px;font-weight:700;letter-spacing:.5px}
.type-badge.video{color:#60a5fa}
.type-badge.image{color:#34d399}
.type-badge.reel{color:#f472b6}
.dur{position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,.75);border-radius:4px;padding:2px 6px;font-size:11px}
.card-body{padding:8px 10px 10px}
.card-caption{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card-meta{font-size:11px;color:#555;margin-top:4px;display:flex;justify-content:space-between}
.card-meta .group-name{max-width:60%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--accent);font-size:10px}

/* MODAL */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:200;align-items:center;justify-content:center;padding:16px}
.modal-overlay.open{display:flex}
.modal{background:var(--card);border-radius:14px;max-width:900px;width:100%;max-height:90vh;overflow:hidden;position:relative;display:flex;flex-direction:column}
.modal-close{position:absolute;top:10px;right:12px;background:rgba(255,255,255,.1);border:none;color:var(--text);width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:18px;z-index:10;display:flex;align-items:center;justify-content:center}
.modal-close:hover{background:rgba(255,255,255,.2)}
.modal-media{flex:1;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden;min-height:200px;max-height:65vh}
.modal-media video{max-width:100%;max-height:65vh;width:100%}
.modal-media img{max-width:100%;max-height:65vh;object-fit:contain}
.modal-info{padding:14px 16px}
.modal-caption{font-size:14px;color:var(--text);margin-bottom:8px;word-break:break-word}
.modal-meta{display:flex;flex-wrap:wrap;gap:10px;font-size:12px;color:var(--muted)}
.modal-meta span{display:flex;align-items:center;gap:4px}
.modal-actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.btn{padding:7px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:5px}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:#6d28d9}
.btn-danger{background:#7f1d1d;color:#fca5a5}
.btn-danger:hover{background:#991b1b}
.btn-secondary{background:#222;color:var(--muted);border:1px solid var(--border)}

/* LOAD MORE */
.load-more-wrap{text-align:center;padding:24px 0}
.btn-load{padding:10px 30px;background:var(--accent);color:#fff;border:none;border-radius:10px;cursor:pointer;font-size:14px;font-weight:700}
.btn-load:hover{background:#6d28d9}
.btn-load:disabled{background:#333;color:var(--muted);cursor:not-allowed}

/* ADMIN */
.admin-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:20px}
.stat-card{background:var(--card);border-radius:12px;padding:18px;border:1px solid var(--border)}
.stat-num{font-size:32px;font-weight:800;color:var(--accent)}
.stat-label{font-size:13px;color:var(--muted);margin-top:4px}
.bot-status{background:var(--card);border-radius:12px;padding:16px;border:1px solid var(--border);margin-bottom:20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.dot{width:12px;height:12px;border-radius:50%;background:#22c55e;box-shadow:0 0 8px #22c55e;flex-shrink:0}
.dot.off{background:#ef4444;box-shadow:0 0 8px #ef4444}
.admin-table{width:100%;border-collapse:collapse;font-size:13px}
.admin-table th{text-align:left;padding:8px 10px;border-bottom:1px solid var(--border);color:var(--muted);font-weight:600}
.admin-table td{padding:8px 10px;border-bottom:1px solid #1e1e1e;vertical-align:middle}
.admin-table tr:hover td{background:#1e1e1e}

/* EMPTY */
.empty{text-align:center;padding:60px 20px;color:var(--muted)}
.empty-icon{font-size:48px;margin-bottom:12px;opacity:.4}

/* LOADING */
.spinner{text-align:center;padding:40px;color:var(--muted)}
.spinner svg{animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<nav>
  <div class="nav-inner">
    <a class="logo" href="#">Tube<span>Stream</span></a>
    <div class="search-box">
      <span class="search-icon">&#128269;</span>
      <input type="search" id="searchInput" placeholder="খুঁজুন..." oninput="debounceSearch(this.value)">
    </div>
    <div class="nav-stats" id="navStats">লোড হচ্ছে...</div>
  </div>
</nav>

<div class="tabs">
  <button class="tab active" onclick="switchTab('all',this)">সব</button>
  <button class="tab" onclick="switchTab('video',this)">&#127916; ভিডিও</button>
  <button class="tab" onclick="switchTab('image',this)">&#128247; ছবি</button>
  <button class="tab" onclick="switchTab('reel',this)">&#127908; রিলস</button>
  <button class="tab" onclick="switchTab('admin',this)">&#9881; অ্যাডমিন</button>
</div>

<main id="mainContent">
  <div id="feedSection">
    <div class="grid" id="mediaGrid"></div>
    <div class="load-more-wrap" id="loadMoreWrap" style="display:none">
      <button class="btn-load" id="loadMoreBtn" onclick="loadMore()">আরো দেখুন</button>
    </div>
  </div>
  <div id="adminSection" style="display:none"></div>
</main>

<!-- MODAL -->
<div class="modal-overlay" id="modal" onclick="closeModal(event)">
  <div class="modal" id="modalBox">
    <button class="modal-close" onclick="closeModal()">&#10005;</button>
    <div class="modal-media" id="modalMedia"></div>
    <div class="modal-info">
      <div class="modal-caption" id="modalCaption"></div>
      <div class="modal-meta" id="modalMeta"></div>
      <div class="modal-actions" id="modalActions"></div>
    </div>
  </div>
</div>

<script>
const API = '';
let currentTab = 'all';
let currentPage = 1;
let totalPages = 1;
let allItems = [];
let searchQuery = '';
let searchTimer;
let currentModalItem = null;

function debounceSearch(val){
  clearTimeout(searchTimer);
  searchTimer = setTimeout(()=>{
    searchQuery = val.trim();
    resetFeed();
    loadFeed();
  },400);
}

function switchTab(tab, el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  currentTab = tab;
  document.getElementById('feedSection').style.display = tab==='admin'?'none':'block';
  document.getElementById('adminSection').style.display = tab==='admin'?'block':'none';
  if(tab==='admin') loadAdmin();
  else { resetFeed(); loadFeed(); }
}

function resetFeed(){
  currentPage=1; totalPages=1; allItems=[];
  document.getElementById('mediaGrid').innerHTML='';
  document.getElementById('loadMoreWrap').style.display='none';
}

async function loadFeed(){
  const grid = document.getElementById('mediaGrid');
  if(currentPage===1) grid.innerHTML='<div class="spinner"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></div>';
  
  const type = currentTab==='all'?'':currentTab;
  const url = \`\${API}/api/media?page=\${currentPage}&limit=24\${type?'&type='+type:''}\${searchQuery?'&search='+encodeURIComponent(searchQuery):''}\`;
  const r = await fetch(url);
  const d = await r.json();
  
  if(currentPage===1) grid.innerHTML='';
  totalPages = d.totalPages||1;
  allItems = [...allItems, ...(d.items||[])];
  
  (d.items||[]).forEach(item => grid.appendChild(makeCard(item)));
  
  if(d.items?.length===0 && currentPage===1){
    grid.innerHTML='<div class="empty"><div class="empty-icon">📭</div><p>কোনো মিডিয়া নেই</p></div>';
  }
  
  const loadWrap = document.getElementById('loadMoreWrap');
  if(currentPage < totalPages){
    loadWrap.style.display='block';
    document.getElementById('loadMoreBtn').disabled=false;
  } else {
    loadWrap.style.display='none';
  }
  
  updateStats(d.total||0);
}

function loadMore(){
  const btn = document.getElementById('loadMoreBtn');
  btn.disabled=true;
  btn.textContent='লোড হচ্ছে...';
  currentPage++;
  loadFeed();
}

function updateStats(total){
  document.getElementById('navStats').textContent = total + ' মিডিয়া';
}

function makeCard(item){
  const div = document.createElement('div');
  const isReel = item.type==='reel';
  div.className = 'card';
  
  const thumbUrl = \`\${API}/api/media/\${item.id}/thumbnail\`;
  const typeLabel = item.type==='video'?'VIDEO':item.type==='image'?'IMAGE':'REEL';
  const dur = item.duration ? fmtDur(item.duration) : '';
  const date = new Date(item.createdAt).toLocaleDateString('bn-BD');
  
  div.innerHTML = \`
    <div class="thumb">
      <img src="\${thumbUrl}" alt="" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
      <div class="no-thumb" style="display:none">\${item.type==='image'?'🖼️':'🎬'}</div>
      \${item.type!=='image'?'<div class="play-icon"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></div>':''}
      <span class="type-badge \${item.type}">\${typeLabel}</span>
      \${dur?'<span class="dur">'+dur+'</span>':''}
    </div>
    <div class="card-body">
      <div class="card-caption">\${item.caption||'—'}</div>
      <div class="card-meta">
        <span class="group-name">\${item.groupName||''}</span>
        <span>\${date}</span>
      </div>
    </div>
  \`;
  
  div.onclick = () => openModal(item);
  return div;
}

function fmtDur(s){
  const m=Math.floor(s/60),sec=s%60;
  return m+':'+(sec<10?'0':'')+sec;
}

function openModal(item){
  currentModalItem = item;
  const mediaEl = document.getElementById('modalMedia');
  const streamUrl = \`\${API}/api/media/\${item.id}/stream\`;
  const thumbUrl = \`\${API}/api/media/\${item.id}/thumbnail\`;
  
  if(item.type==='image'){
    mediaEl.innerHTML = \`<img src="\${streamUrl}" alt="" style="max-width:100%;max-height:65vh;object-fit:contain">\`;
  } else {
    mediaEl.innerHTML = \`<video controls autoplay playsinline src="\${streamUrl}" poster="\${thumbUrl}" style="max-width:100%;max-height:65vh;width:100%"></video>\`;
  }
  
  document.getElementById('modalCaption').textContent = item.caption||'(কোনো ক্যাপশন নেই)';
  
  const sz = item.fileSize ? (item.fileSize/1024/1024).toFixed(1)+'MB' : '';
  document.getElementById('modalMeta').innerHTML = \`
    \${item.groupName?'<span>📌 '+item.groupName+'</span>':''}
    \${item.duration?'<span>⏱ '+fmtDur(item.duration)+'</span>':''}
    \${sz?'<span>💾 '+sz+'</span>':''}
    <span>📅 \${new Date(item.createdAt).toLocaleString('bn-BD')}</span>
  \`;
  
  document.getElementById('modalActions').innerHTML = \`
    <a class="btn btn-primary" href="\${streamUrl}" download target="_blank">⬇ ডাউনলোড</a>
    <button class="btn btn-danger" onclick="deleteItem(\${item.id})">🗑 মুছুন</button>
    <button class="btn btn-secondary" onclick="closeModal()">বন্ধ</button>
  \`;
  
  document.getElementById('modal').classList.add('open');
}

function closeModal(e){
  if(e && e.target !== document.getElementById('modal')) return;
  document.getElementById('modal').classList.remove('open');
  const v = document.getElementById('modalMedia').querySelector('video');
  if(v) v.pause();
}

async function deleteItem(id){
  if(!confirm('মুছে ফেলবেন?')) return;
  await fetch(\`\${API}/api/media/\${id}\`,{method:'DELETE'});
  closeModal();
  resetFeed();
  loadFeed();
}

async function loadAdmin(){
  const sec = document.getElementById('adminSection');
  sec.innerHTML='<div class="spinner"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></div>';
  
  const [statsR, botR, mediaR] = await Promise.all([
    fetch(\`\${API}/api/stats\`).then(r=>r.json()),
    fetch(\`\${API}/api/bot/status\`).then(r=>r.json()),
    fetch(\`\${API}/api/media?page=1&limit=50\`).then(r=>r.json()),
  ]);
  
  sec.innerHTML = \`
    <div class="bot-status">
      <div class="dot \${botR.connected?'':'off'}"></div>
      <div>
        <b>বট স্ট্যাটাস:</b> \${botR.connected?'সংযুক্ত ✅':'সংযুক্ত নয় ❌'}<br>
        <span style="font-size:12px;color:var(--muted)">\${botR.botUsername?'@'+botR.botUsername:''} &nbsp;|&nbsp; \${botR.groupCount} গ্রুপ &nbsp;|&nbsp; শেষ আপডেট: \${botR.lastActivity?new Date(botR.lastActivity).toLocaleString('bn-BD'):'-'}</span>
      </div>
    </div>
    <div class="admin-grid">
      <div class="stat-card"><div class="stat-num">\${statsR.totalMedia||0}</div><div class="stat-label">মোট মিডিয়া</div></div>
      <div class="stat-card"><div class="stat-num">\${statsR.totalVideos||0}</div><div class="stat-label">ভিডিও</div></div>
      <div class="stat-card"><div class="stat-num">\${statsR.totalImages||0}</div><div class="stat-label">ছবি</div></div>
      <div class="stat-card"><div class="stat-num">\${statsR.totalReels||0}</div><div class="stat-label">রিলস</div></div>
      <div class="stat-card"><div class="stat-num">\${statsR.totalGroups||0}</div><div class="stat-label">গ্রুপ</div></div>
      <div class="stat-card"><div class="stat-num">\${statsR.recentCount||0}</div><div class="stat-label">আজকের (২৪ ঘণ্টা)</div></div>
    </div>
    <div style="overflow-x:auto">
      <table class="admin-table">
        <thead><tr><th>ID</th><th>ধরন</th><th>ক্যাপশন</th><th>গ্রুপ</th><th>তারিখ</th><th>মুছুন</th></tr></thead>
        <tbody>
          \${(mediaR.items||[]).map(i=>\`
            <tr>
              <td>\${i.id}</td>
              <td><span class="type-badge \${i.type}" style="position:relative;top:0;left:0">\${i.type.toUpperCase()}</span></td>
              <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">\${i.caption||'—'}</td>
              <td style="color:var(--accent);font-size:11px">\${i.groupName||'—'}</td>
              <td style="white-space:nowrap">\${new Date(i.createdAt).toLocaleDateString('bn-BD')}</td>
              <td><button class="btn btn-danger" style="padding:4px 10px" onclick="adminDelete(\${i.id})">🗑</button></td>
            </tr>
          \`).join('')}
        </tbody>
      </table>
    </div>
  \`;
}

async function adminDelete(id){
  if(!confirm('মুছে ফেলবেন?')) return;
  await fetch(\`\${API}/api/media/\${id}\`,{method:'DELETE'});
  loadAdmin();
}

// INIT
document.addEventListener('DOMContentLoaded', () => {
  resetFeed();
  loadFeed();
});
</script>
</body>
</html>`;

// ─── CORS HEADERS ─────────────────────────────────────────────
function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-API-Secret",
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}

// ─── DB HELPERS ───────────────────────────────────────────────
async function initDB(db) {
  await db.exec(`
    CREATE TABLE IF NOT EXISTS media (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      file_unique_id TEXT UNIQUE NOT NULL,
      file_id TEXT NOT NULL,
      type TEXT NOT NULL DEFAULT 'video',
      caption TEXT,
      mime_type TEXT,
      file_size INTEGER,
      duration INTEGER,
      width INTEGER,
      height INTEGER,
      group_id TEXT,
      group_name TEXT,
      message_id INTEGER,
      sender_id TEXT,
      thumbnail_file_id TEXT,
      created_at DATETIME DEFAULT (datetime('now')),
      updated_at DATETIME DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS bot_status (
      id INTEGER PRIMARY KEY,
      connected INTEGER DEFAULT 0,
      bot_username TEXT,
      group_count INTEGER DEFAULT 0,
      last_activity DATETIME,
      groups_json TEXT DEFAULT '[]'
    );
    INSERT OR IGNORE INTO bot_status (id) VALUES (1);
  `);
}

async function getTelegramFileUrl(token, fileId) {
  const r = await fetch(`${BOT_API}/bot${token}/getFile?file_id=${fileId}`);
  const d = await r.json();
  if (!d.ok || !d.result?.file_path) return null;
  return `${BOT_API}/file/bot${token}/${d.result.file_path}`;
}

// ─── MAIN HANDLER ─────────────────────────────────────────────
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    if (method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    // Init DB on every request (idempotent)
    try { await initDB(env.DB); } catch (e) {}

    // ── Serve frontend ────────────────────────────
    if (path === "/" || path === "") {
      return new Response(HTML, {
        headers: { "Content-Type": "text/html;charset=UTF-8" },
      });
    }

    // ── API Routes ────────────────────────────────
    const secret = request.headers.get("X-API-Secret");
    const isBot = secret === env.API_SECRET;

    // GET /api/media — list with pagination
    if (path === "/api/media" && method === "GET") {
      const page = parseInt(url.searchParams.get("page") || "1");
      const limit = Math.min(parseInt(url.searchParams.get("limit") || "24"), 100);
      const type = url.searchParams.get("type") || "";
      const search = url.searchParams.get("search") || "";
      const groupId = url.searchParams.get("groupId") || "";
      const offset = (page - 1) * limit;

      let where = "WHERE 1=1";
      const params = [];
      if (type) { where += " AND type=?"; params.push(type); }
      if (search) { where += " AND caption LIKE ?"; params.push(`%${search}%`); }
      if (groupId) { where += " AND group_id=?"; params.push(groupId); }

      const countStmt = env.DB.prepare(`SELECT COUNT(*) as cnt FROM media ${where}`);
      const dataStmt = env.DB.prepare(
        `SELECT * FROM media ${where} ORDER BY created_at DESC LIMIT ? OFFSET ?`
      );

      const [countR, dataR] = await Promise.all([
        countStmt.bind(...params).first(),
        dataStmt.bind(...params, limit, offset).all(),
      ]);

      const total = countR?.cnt || 0;

      const items = (dataR.results || []).map(row => ({
        id: row.id,
        fileUniqueId: row.file_unique_id,
        fileId: row.file_id,
        type: row.type,
        caption: row.caption,
        mimeType: row.mime_type,
        fileSize: row.file_size,
        duration: row.duration,
        width: row.width,
        height: row.height,
        groupId: row.group_id,
        groupName: row.group_name,
        messageId: row.message_id,
        senderId: row.sender_id,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      }));

      return json({ items, total, page, limit, totalPages: Math.ceil(total / limit) });
    }

    // POST /api/media — add media (from bot)
    if (path === "/api/media" && method === "POST") {
      let body;
      try { body = await request.json(); } catch { return json({ error: "Invalid JSON" }, 400); }

      if (!body.fileUniqueId || !body.fileId || !body.type) {
        return json({ error: "Missing required fields" }, 400);
      }

      // Check duplicate
      const existing = await env.DB.prepare(
        "SELECT id FROM media WHERE file_unique_id=?"
      ).bind(body.fileUniqueId).first();

      if (existing) {
        return json({ id: existing.id, duplicate: true });
      }

      const r = await env.DB.prepare(`
        INSERT INTO media (file_unique_id, file_id, type, caption, mime_type, file_size, duration, width, height, group_id, group_name, message_id, sender_id, thumbnail_file_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      `).bind(
        body.fileUniqueId, body.fileId, body.type,
        body.caption || null, body.mimeType || null,
        body.fileSize || null, body.duration || null,
        body.width || null, body.height || null,
        body.groupId || null, body.groupName || null,
        body.messageId || null, body.senderId || null,
        body.thumbnailFileId || null,
      ).run();

      return json({ id: r.meta?.last_row_id, created: true }, 201);
    }

    // GET /api/media/:id
    if (path.match(/^\/api\/media\/\d+$/) && method === "GET") {
      const id = parseInt(path.split("/").pop());
      const row = await env.DB.prepare("SELECT * FROM media WHERE id=?").bind(id).first();
      if (!row) return json({ error: "Not found" }, 404);
      return json({
        id: row.id, fileUniqueId: row.file_unique_id, fileId: row.file_id,
        type: row.type, caption: row.caption, mimeType: row.mime_type,
        fileSize: row.file_size, duration: row.duration, width: row.width,
        height: row.height, groupId: row.group_id, groupName: row.group_name,
        createdAt: row.created_at, updatedAt: row.updated_at,
      });
    }

    // DELETE /api/media/:id
    if (path.match(/^\/api\/media\/\d+$/) && method === "DELETE") {
      const id = parseInt(path.split("/").pop());
      await env.DB.prepare("DELETE FROM media WHERE id=?").bind(id).run();
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    // GET /api/media/:id/stream — proxy from Telegram
    if (path.match(/^\/api\/media\/\d+\/stream$/)) {
      const id = parseInt(path.split("/")[3]);
      const row = await env.DB.prepare("SELECT * FROM media WHERE id=?").bind(id).first();
      if (!row) return json({ error: "Not found" }, 404);

      const fileUrl = await getTelegramFileUrl(env.BOT_TOKEN, row.file_id);
      if (!fileUrl) return json({ error: "Could not get file from Telegram" }, 502);

      const range = request.headers.get("Range");
      const telegramResp = await fetch(fileUrl, {
        headers: range ? { Range: range } : {},
      });

      return new Response(telegramResp.body, {
        status: range ? 206 : telegramResp.status,
        headers: {
          "Content-Type": row.mime_type || (row.type === "image" ? "image/jpeg" : "video/mp4"),
          "Accept-Ranges": "bytes",
          "Content-Range": telegramResp.headers.get("Content-Range") || "",
          "Content-Length": telegramResp.headers.get("Content-Length") || "",
          "Cache-Control": "public, max-age=3600",
          ...corsHeaders(),
        },
      });
    }

    // GET /api/media/:id/thumbnail — proxy thumbnail from Telegram
    if (path.match(/^\/api\/media\/\d+\/thumbnail$/)) {
      const id = parseInt(path.split("/")[3]);
      const row = await env.DB.prepare("SELECT * FROM media WHERE id=?").bind(id).first();
      if (!row) return json({ error: "Not found" }, 404);

      const thumbFileId = row.thumbnail_file_id || (row.type === "image" ? row.file_id : null);
      if (!thumbFileId) return json({ error: "No thumbnail" }, 404);

      const fileUrl = await getTelegramFileUrl(env.BOT_TOKEN, thumbFileId);
      if (!fileUrl) return json({ error: "Could not get thumbnail" }, 502);

      const resp = await fetch(fileUrl);
      return new Response(resp.body, {
        status: resp.status,
        headers: {
          "Content-Type": "image/jpeg",
          "Cache-Control": "public, max-age=86400",
          ...corsHeaders(),
        },
      });
    }

    // GET /api/stats
    if (path === "/api/stats") {
      const [total, vid, img, reel, grp, recent] = await Promise.all([
        env.DB.prepare("SELECT COUNT(*) as c FROM media").first(),
        env.DB.prepare("SELECT COUNT(*) as c FROM media WHERE type='video'").first(),
        env.DB.prepare("SELECT COUNT(*) as c FROM media WHERE type='image'").first(),
        env.DB.prepare("SELECT COUNT(*) as c FROM media WHERE type='reel'").first(),
        env.DB.prepare("SELECT COUNT(DISTINCT group_id) as c FROM media WHERE group_id IS NOT NULL").first(),
        env.DB.prepare("SELECT COUNT(*) as c FROM media WHERE created_at > datetime('now','-1 day')").first(),
      ]);
      return json({
        totalMedia: total?.c || 0,
        totalVideos: vid?.c || 0,
        totalImages: img?.c || 0,
        totalReels: reel?.c || 0,
        totalGroups: grp?.c || 0,
        recentCount: recent?.c || 0,
      });
    }

    // GET /api/groups
    if (path === "/api/groups") {
      const r = await env.DB.prepare(
        "SELECT group_id, group_name, COUNT(*) as cnt FROM media WHERE group_id IS NOT NULL GROUP BY group_id ORDER BY cnt DESC"
      ).all();
      return json({ groups: (r.results||[]).map(g=>({groupId:g.group_id,groupName:g.group_name,mediaCount:g.cnt})) });
    }

    // GET /api/bot/status
    if (path === "/api/bot/status") {
      const row = await env.DB.prepare("SELECT * FROM bot_status WHERE id=1").first();
      return json({
        connected: row?.connected === 1,
        botUsername: row?.bot_username || null,
        groupCount: row?.group_count || 0,
        lastActivity: row?.last_activity || null,
      });
    }

    // POST /api/bot/heartbeat — bot updates its status
    if (path === "/api/bot/heartbeat" && method === "POST") {
      let body = {};
      try { body = await request.json(); } catch {}
      await env.DB.prepare(`
        UPDATE bot_status SET connected=1, bot_username=?, group_count=?, last_activity=datetime('now'), groups_json=? WHERE id=1
      `).bind(body.botUsername||null, body.groupCount||0, JSON.stringify(body.groups||[])).run();
      return json({ ok: true });
    }

    // POST /api/bot/sync
    if (path === "/api/bot/sync" && method === "POST") {
      return json({ message: "Sync triggered", triggered: true });
    }

    // 404
    return json({ error: "Not found" }, 404);
  },
};
