// ============================================================
// TubeStream — Cloudflare Worker (Fully Fixed)
// Deploy: Create Worker → Paste this → Deploy → D1 Database "tubestream" bind as "DB"
// ============================================================

const BOT_TOKEN = "8517198376:AAEy6hjWJfuFtoi-BtAFXLV8yHFVtvm3z18";
const API_SECRET = "tubestream-secret-2024";
const BOT_API = "https://api.telegram.org";

const HTML = `<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TubeStream</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d0d0d;--card:#1a1a1a;--accent:#7c3aed;--text:#f1f1f1;--muted:#888;--border:#2a2a2a}
body{background:var(--bg);color:var(--text);font-family:sans-serif}
nav{background:#111;border-bottom:1px solid var(--border);padding:0 16px}
.nav-inner{max-width:1400px;margin:0 auto;display:flex;align-items:center;gap:12px;height:56px}
.logo{font-size:20px;font-weight:800;color:var(--accent)}
.search-box{flex:1}
.search-box input{width:100%;background:#222;border:1px solid var(--border);border-radius:8px;padding:8px 14px;color:var(--text)}
.tabs{display:flex;gap:4px;padding:12px 16px 0;max-width:1400px;margin:0 auto}
.tab{padding:8px 20px;border-radius:8px 8px 0 0;cursor:pointer;background:transparent;color:var(--muted)}
.tab.active{background:var(--card);color:var(--text);border-bottom:2px solid var(--accent)}
main{max-width:1400px;margin:0 auto;padding:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.card{background:var(--card);border-radius:12px;overflow:hidden;cursor:pointer;border:1px solid var(--border)}
.card:hover{border-color:var(--accent)}
.thumb{position:relative;background:#111;aspect-ratio:16/9}
.thumb img{width:100%;height:100%;object-fit:cover}
.type-badge{position:absolute;top:6px;left:6px;background:rgba(0,0,0,.7);border-radius:5px;padding:2px 7px;font-size:11px}
.dur{position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,.75);border-radius:4px;padding:2px 6px;font-size:11px}
.card-body{padding:8px 10px}
.card-caption{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden}
.card-meta{font-size:11px;color:#555;margin-top:4px}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:200;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal{background:var(--card);border-radius:14px;max-width:900px;width:100%;max-height:90vh}
.modal-media{background:#000;display:flex;align-items:center;justify-content:center;min-height:200px}
.modal-media video,.modal-media img{max-width:100%;max-height:65vh}
.modal-info{padding:14px 16px}
.btn{padding:7px 16px;border-radius:8px;border:none;cursor:pointer;display:inline-block;text-decoration:none}
.btn-primary{background:var(--accent);color:#fff}
.btn-danger{background:#7f1d1d;color:#fca5a5}
.load-more-wrap{text-align:center;padding:24px 0}
.btn-load{padding:10px 30px;background:var(--accent);color:#fff;border-radius:10px;cursor:pointer}
.empty{text-align:center;padding:60px 20px;color:var(--muted)}
</style>
</head>
<body>
<nav><div class="nav-inner"><a class="logo">Tube<span style="color:#3b82f6">Stream</span></a>
<div class="search-box"><input type="search" id="searchInput" placeholder="খুঁজুন..."></div></div></nav>
<div class="tabs"><button class="tab active" onclick="switchTab('all',this)">সব</button>
<button class="tab" onclick="switchTab('video',this)">ভিডিও</button>
<button class="tab" onclick="switchTab('image',this)">ছবি</button>
<button class="tab" onclick="switchTab('reel',this)">রিলস</button>
<button class="tab" onclick="switchTab('admin',this)">অ্যাডমিন</button></div>
<main><div id="feedSection"><div class="grid" id="mediaGrid"></div><div class="load-more-wrap" id="loadMoreWrap" style="display:none"><button class="btn-load" id="loadMoreBtn">আরো দেখুন</button></div></div>
<div id="adminSection" style="display:none"></div></main>
<div class="modal-overlay" id="modal"><div class="modal"><button onclick="closeModal()" style="float:right;background:none;border:none;color:#fff;font-size:20px;cursor:pointer">✕</button>
<div class="modal-media" id="modalMedia"></div><div class="modal-info" id="modalInfo"></div></div></div>
<script>
var API='';
var currentTab='all';
var currentPage=1;
var totalPages=1;
var searchQuery='';
var searchTimer;

function debounceSearch(val){
    clearTimeout(searchTimer);
    searchTimer=setTimeout(function(){
        searchQuery=val.trim();
        resetFeed();
        loadFeed();
    },400);
}

document.getElementById('searchInput').oninput=function(e){
    debounceSearch(e.target.value);
};

function switchTab(tab,el){
    var tabs=document.querySelectorAll('.tab');
    for(var i=0;i<tabs.length;i++) tabs[i].classList.remove('active');
    el.classList.add('active');
    currentTab=tab;
    var feedSec=document.getElementById('feedSection');
    var adminSec=document.getElementById('adminSection');
    if(tab==='admin'){
        feedSec.style.display='none';
        adminSec.style.display='block';
        loadAdmin();
    }else{
        feedSec.style.display='block';
        adminSec.style.display='none';
        resetFeed();
        loadFeed();
    }
}

function resetFeed(){
    currentPage=1;
    totalPages=1;
    document.getElementById('mediaGrid').innerHTML='';
    document.getElementById('loadMoreWrap').style.display='none';
}

function loadFeed(){
    var grid=document.getElementById('mediaGrid');
    if(currentPage===1) grid.innerHTML='<div class="empty">লোড হচ্ছে...</div>';
    var type=(currentTab==='all')?'':currentTab;
    var url=API+'/api/media?page='+currentPage+'&limit=24'+(type?'&type='+type:'')+(searchQuery?'&search='+encodeURIComponent(searchQuery):'');
    fetch(url).then(function(r){return r.json();}).then(function(d){
        if(currentPage===1) grid.innerHTML='';
        totalPages=d.totalPages||1;
        var items=d.items||[];
        for(var i=0;i<items.length;i++){
            grid.appendChild(makeCard(items[i]));
        }
        if(items.length===0 && currentPage===1){
            grid.innerHTML='<div class="empty"><div>📭 কোনো মিডিয়া নেই</div></div>';
        }
        var wrap=document.getElementById('loadMoreWrap');
        if(currentPage<totalPages){
            wrap.style.display='block';
        }else{
            wrap.style.display='none';
        }
    });
}

function loadMore(){
    currentPage++;
    loadFeed();
}

function makeCard(item){
    var div=document.createElement('div');
    div.className='card';
    var thumbUrl=API+'/api/media/'+item.id+'/thumbnail';
    var typeLabel=(item.type==='video')?'VIDEO':((item.type==='image')?'IMAGE':'REEL');
    var dur='';
    if(item.duration){
        var mins=Math.floor(item.duration/60);
        var secs=item.duration%60;
        dur=mins+':'+(secs<10?'0':'')+secs;
    }
    var captionText=item.caption||'—';
    var groupNameText=item.groupName||'';
    div.innerHTML='<div class="thumb"><img src="'+thumbUrl+'" onerror="this.style.display=\'none\'"><span class="type-badge '+item.type+'">'+typeLabel+'</span>'+(dur?'<span class="dur">'+dur+'</span>':'')+'</div><div class="card-body"><div class="card-caption">'+captionText+'</div><div class="card-meta">'+groupNameText+'</div></div>';
    div.onclick=function(){openModal(item);};
    return div;
}

function openModal(item){
    var mediaEl=document.getElementById('modalMedia');
    var streamUrl=API+'/api/media/'+item.id+'/stream';
    var thumbUrl=API+'/api/media/'+item.id+'/thumbnail';
    if(item.type==='image'){
        mediaEl.innerHTML='<img src="'+streamUrl+'">';
    }else{
        mediaEl.innerHTML='<video controls autoplay src="'+streamUrl+'" poster="'+thumbUrl+'" style="max-width:100%;max-height:65vh"></video>';
    }
    var durText='';
    if(item.duration){
        var mins=Math.floor(item.duration/60);
        var secs=item.duration%60;
        durText='⏱ '+mins+':'+(secs<10?'0':'')+secs;
    }
    document.getElementById('modalInfo').innerHTML='<div><strong>'+(item.caption||'কোনো ক্যাপশন নেই')+'</strong><br><span>📌 '+(item.groupName||'')+'</span> '+durText+'<br><a class="btn btn-primary" href="'+streamUrl+'" download>ডাউনলোড</a> <button class="btn btn-danger" onclick="deleteItem('+item.id+')">মুছুন</button></div>';
    document.getElementById('modal').classList.add('open');
}

function closeModal(){
    document.getElementById('modal').classList.remove('open');
    var v=document.getElementById('modalMedia').querySelector('video');
    if(v) v.pause();
}

function deleteItem(id){
    if(!confirm('মুছে ফেলবেন?')) return;
    fetch(API+'/api/media/'+id,{method:'DELETE'}).then(function(){
        closeModal();
        resetFeed();
        loadFeed();
    });
}

function loadAdmin(){
    var sec=document.getElementById('adminSection');
    sec.innerHTML='<div class="empty">লোড হচ্ছে...</div>';
    fetch(API+'/api/stats').then(function(r){return r.json();}).then(function(stats){
        fetch(API+'/api/bot/status').then(function(r){return r.json();}).then(function(status){
            sec.innerHTML='<div><strong>বট স্ট্যাটাস:</strong> '+(status.connected?'✅ সংযুক্ত':'❌ সংযুক্ত নয়')+'<br>গ্রুপ: '+(status.groupCount||0)+'</div><div class="grid" style="margin-top:16px"><div class="card"><div class="card-body"><div style="font-size:32px;color:var(--accent)">'+(stats.totalMedia||0)+'</div><div>মোট মিডিয়া</div></div></div><div class="card"><div class="card-body"><div style="font-size:32px;color:var(--accent)">'+(stats.totalVideos||0)+'</div><div>ভিডিও</div></div></div><div class="card"><div class="card-body"><div style="font-size:32px;color:var(--accent)">'+(stats.totalImages||0)+'</div><div>ছবি</div></div></div><div class="card"><div class="card-body"><div style="font-size:32px;color:var(--accent)">'+(stats.totalReels||0)+'</div><div>রিলস</div></div></div></div>';
        });
    });
}

loadFeed();
document.getElementById('loadMoreBtn').onclick=loadMore;
</script>
</body>
</html>`;

function corsHeaders() {
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-API-Secret",
    };
}

function json(data, status) {
    status = status || 200;
    return new Response(JSON.stringify(data), {
        status: status,
        headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
}

async function getTelegramFileUrl(fileId) {
    var url = BOT_API + "/bot" + BOT_TOKEN + "/getFile?file_id=" + fileId;
    var r = await fetch(url);
    var d = await r.json();
    if (!d.ok || !d.result || !d.result.file_path) return null;
    return BOT_API + "/file/bot" + BOT_TOKEN + "/" + d.result.file_path;
}

export default {
    async fetch(request, env) {
        var url = new URL(request.url);
        var path = url.pathname;
        var method = request.method;

        if (method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders() });
        }

        // DB init
        try {
            await env.DB.exec(`CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_unique_id TEXT UNIQUE,
                file_id TEXT,
                type TEXT,
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
                created_at DATETIME DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS bot_status (
                id INTEGER PRIMARY KEY,
                connected INTEGER DEFAULT 0,
                bot_username TEXT,
                group_count INTEGER DEFAULT 0,
                last_activity DATETIME,
                groups_json TEXT DEFAULT '[]'
            );
            INSERT OR IGNORE INTO bot_status (id) VALUES (1);`);
        } catch(e) {}

        // Frontend
        if (path === "/" || path === "") {
            return new Response(HTML, {
                headers: { "Content-Type": "text/html;charset=UTF-8" }
            });
        }

        var secret = request.headers.get("X-API-Secret");
        var isBot = (secret === API_SECRET);

        // GET /api/media
        if (path === "/api/media" && method === "GET") {
            var page = parseInt(url.searchParams.get("page") || "1");
            var limit = Math.min(parseInt(url.searchParams.get("limit") || "24"), 100);
            var type = url.searchParams.get("type") || "";
            var search = url.searchParams.get("search") || "";
            var offset = (page - 1) * limit;
            
            var where = "WHERE 1=1";
            var params = [];
            if (type) { where += " AND type=?"; params.push(type); }
            if (search) { where += " AND caption LIKE ?"; params.push("%" + search + "%"); }
            
            var countStmt = env.DB.prepare("SELECT COUNT(*) as cnt FROM media " + where);
            for (var i = 0; i < params.length; i++) countStmt = countStmt.bind(params[i]);
            var count = await countStmt.first();
            
            var dataStmt = env.DB.prepare("SELECT * FROM media " + where + " ORDER BY created_at DESC LIMIT ? OFFSET ?");
            for (var i = 0; i < params.length; i++) dataStmt = dataStmt.bind(params[i]);
            dataStmt = dataStmt.bind(limit).bind(offset);
            var rows = await dataStmt.all();
            
            var items = [];
            var results = rows.results || [];
            for (var i = 0; i < results.length; i++) {
                var r = results[i];
                items.push({
                    id: r.id,
                    type: r.type,
                    caption: r.caption,
                    duration: r.duration,
                    groupId: r.group_id,
                    groupName: r.group_name,
                    createdAt: r.created_at
                });
            }
            
            return json({
                items: items,
                total: count?.cnt || 0,
                page: page,
                limit: limit,
                totalPages: Math.ceil((count?.cnt || 0) / limit)
            });
        }

        // POST /api/media
        if (path === "/api/media" && method === "POST" && isBot) {
            var body;
            try { body = await request.json(); } catch(e) { return json({ error: "Invalid JSON" }, 400); }
            if (!body.fileUniqueId || !body.fileId) return json({ error: "Missing fields" }, 400);
            
            var existing = await env.DB.prepare("SELECT id FROM media WHERE file_unique_id=?").bind(body.fileUniqueId).first();
            if (existing) return json({ id: existing.id, duplicate: true });
            
            await env.DB.prepare(`INSERT INTO media (file_unique_id, file_id, type, caption, mime_type, file_size, duration, width, height, group_id, group_name, message_id, sender_id, thumbnail_file_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(
                body.fileUniqueId, body.fileId, body.type,
                body.caption || null, body.mimeType || null,
                body.fileSize || null, body.duration || null,
                body.width || null, body.height || null,
                body.groupId || null, body.groupName || null,
                body.messageId || null, body.senderId || null,
                body.thumbnailFileId || null
            ).run();
            
            return json({ created: true }, 201);
        }

        // DELETE /api/media/:id
        if (path.match(/^\/api\/media\/\d+$/) && method === "DELETE") {
            var id = parseInt(path.split("/").pop());
            await env.DB.prepare("DELETE FROM media WHERE id=?").bind(id).run();
            return new Response(null, { status: 204, headers: corsHeaders() });
        }

        // GET /api/media/:id/stream
        if (path.match(/^\/api\/media\/\d+\/stream$/)) {
            var id = parseInt(path.split("/")[3]);
            var row = await env.DB.prepare("SELECT * FROM media WHERE id=?").bind(id).first();
            if (!row) return json({ error: "Not found" }, 404);
            
            var fileUrl = await getTelegramFileUrl(row.file_id);
            if (!fileUrl) return json({ error: "File not found" }, 502);
            
            var range = request.headers.get("Range");
            var headers = {};
            if (range) headers["Range"] = range;
            
            var resp = await fetch(fileUrl, { headers: headers });
            return new Response(resp.body, {
                status: resp.status,
                headers: {
                    "Content-Type": row.mime_type || "video/mp4",
                    "Accept-Ranges": "bytes",
                    ...corsHeaders()
                }
            });
        }

        // GET /api/media/:id/thumbnail
        if (path.match(/^\/api\/media\/\d+\/thumbnail$/)) {
            var id = parseInt(path.split("/")[3]);
            var row = await env.DB.prepare("SELECT * FROM media WHERE id=?").bind(id).first();
            if (!row) return json({ error: "Not found" }, 404);
            
            var thumbId = row.thumbnail_file_id || (row.type === "image" ? row.file_id : null);
            if (!thumbId) return json({ error: "No thumbnail" }, 404);
            
            var fileUrl = await getTelegramFileUrl(thumbId);
            if (!fileUrl) return json({ error: "Thumb not found" }, 502);
            
            var resp = await fetch(fileUrl);
            return new Response(resp.body, {
                headers: {
                    "Content-Type": "image/jpeg",
                    "Cache-Control": "public, max-age=86400",
                    ...corsHeaders()
                }
            });
        }

        // GET /api/stats
        if (path === "/api/stats") {
            var total = await env.DB.prepare("SELECT COUNT(*) as c FROM media").first();
            var vid = await env.DB.prepare("SELECT COUNT(*) as c FROM media WHERE type='video'").first();
            var img = await env.DB.prepare("SELECT COUNT(*) as c FROM media WHERE type='image'").first();
            var reel = await env.DB.prepare("SELECT COUNT(*) as c FROM media WHERE type='reel'").first();
            return json({
                totalMedia: total?.c || 0,
                totalVideos: vid?.c || 0,
                totalImages: img?.c || 0,
                totalReels: reel?.c || 0
            });
        }

        // GET /api/bot/status
        if (path === "/api/bot/status") {
            var row = await env.DB.prepare("SELECT * FROM bot_status WHERE id=1").first();
            return json({
                connected: row?.connected === 1,
                botUsername: row?.bot_username,
                groupCount: row?.group_count || 0,
                lastActivity: row?.last_activity
            });
        }

        // POST /api/bot/heartbeat
        if (path === "/api/bot/heartbeat" && method === "POST" && isBot) {
            var body;
            try { body = await request.json(); } catch(e) { body = {}; }
            await env.DB.prepare(`UPDATE bot_status SET connected=1, bot_username=?, group_count=?, last_activity=datetime('now'), groups_json=? WHERE id=1`).bind(
                body.botUsername || null,
                body.groupCount || 0,
                JSON.stringify(body.groups || [])
            ).run();
            return json({ ok: true });
        }

        return json({ error: "Not found" }, 404);
    }
};
