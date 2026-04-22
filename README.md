# TubeStream Setup Guide

## ধাপ ১: Cloudflare Worker Setup

### ১.১ D1 Database তৈরি করো
1. https://dash.cloudflare.com/ → Workers & Pages → D1
2. "Create database" ক্লিক করো
3. নাম দাও: **tubestream**
4. Create ক্লিক করো

### ১.২ Worker তৈরি করো
1. Workers & Pages → Overview → Create application → Create Worker
2. নাম দাও বা আগেরটা ব্যবহার করো
3. "Edit code" ক্লিক করো
4. **worker.js** ফাইলের সব কোড কপি করে paste করো
5. "Save and deploy" ক্লিক করো

### ১.৩ D1 Database bind করো
1. তোমার Worker → Settings → Bindings
2. "+ Add binding" → D1 Database
3. Variable name: **DB**
4. Database: **tubestream** (আগে তৈরি করা)
5. Save করো

### ১.৪ Environment Variables যোগ করো
Worker Settings → Variables → Environment Variables → Edit variables:

| Variable | Value |
|----------|-------|
| BOT_TOKEN | `8517198376:AAEgXxDt6qsKAHwadqhMHjhc-ss39vCbMa4` |
| API_SECRET | `tubestream-secret-2024` (নিজে কিছু লিখতে পারো) |

### ১.৫ Custom Domain (ঐচ্ছিক)
Workers → তোমার worker → Settings → Triggers → Custom domains → Add
তোমার ডোমেইন: Televideoimage.hasanahmed.workers.dev (এটা ইতোমধ্যে আছে)

---

## ধাপ ২: GitHub এ Bot Push করো

### ২.১ GitHub Repository তৈরি করো
1. github.com → New repository → নাম: **tubestream-bot**
2. Public করো

### ২.২ ফাইলগুলো Upload করো
GitHub repository → Add file → Upload files:
- **bot.py**
- **requirements.txt**

---

## ধাপ ৩: Render-এ Deploy করো

### ৩.১ Render Account
1. https://render.com/ → Sign up (GitHub দিয়ে)
2. New → Web Service
3. GitHub Repository connect করো → **tubestream-bot** সিলেক্ট করো

### ৩.২ Settings
| Setting | Value |
|---------|-------|
| Name | tubestream-bot |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python bot.py` |
| Instance Type | Free |

### ৩.৩ Environment Variables
Render → Environment → Add Environment Variable:

| Key | Value |
|-----|-------|
| BOT_TOKEN | `8517198376:AAEgXxDt6qsKAHwadqhMHjhc-ss39vCbMa4` |
| WORKER_URL | `https://Televideoimage.hasanahmed.workers.dev` |
| API_SECRET | `tubestream-secret-2024` (Worker-এ যা দিয়েছো) |

4. **Create Web Service** ক্লিক করো

---

## গুরুত্বপূর্ণ নোট

- ✅ Render FREE তে bot সারাদিন চলবে (sleep হয় কিন্তু polling বট-এ সমস্যা নেই)
- ✅ Cloudflare D1 FREE তে ৫GB পর্যন্ত ডেটা রাখতে পারবে
- ✅ ভিডিও Telegram server থেকে সরাসরি stream হবে, কোনো স্টোরেজ লাগবে না
- ✅ file_unique_id দিয়ে ডুপ্লিকেট চেক হবে
- ⚠️ Render FREE-তে প্রথম request-এ ৩০ সেকেন্ড দেরি হতে পারে, কিন্তু bot polling-এ এটা সমস্যা করে না
