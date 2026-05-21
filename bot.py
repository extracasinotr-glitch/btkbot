#!/usr/bin/env python3
import logging
import random
import aiohttp
from urllib.parse import urlparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# ─── 1. AYARLAR & API KEYS ──────────────────────────────────────────────────
BOT_TOKEN = "8890222792:AAEU9MoI504nLuVzAVQfuAKa2tVY-SbAA10"
WEBSHARE_API_KEY = "zhyv0i0y40vpqh1c8ou8hvd42jj435belu3615z2"
RAILWAY_API_TOKEN = "8708f4a7-0dbb-466b-af4d-e904287fdcb6"

BTK_BLOCK_KEYWORDS = ["Bilgi Teknolojileri ve İletişim Kurumu", "erişime engellenmiştir", "ihbarweb.org.tr"]
WEBSHARE_PROXY_LIST = [
    "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.18:5163",
    "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.215:5360",
    "http://rozhkpzn:9u4t6jpvz0hj@142.111.216.225:6370",
    "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.135:5280"
]

user_state = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── 2. YARDIMCI FONKSİYONLAR ──────────────────────────────────────────────
def domain(url): return urlparse(url if "://" in url else "https://" + url).netloc

async def check_site_with_retries(url):
    proxy = random.choice(WEBSHARE_PROXY_LIST)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=15) as resp:
                text = await resp.text()
                is_btk = any(kw.lower() in text.lower() for kw in BTK_BLOCK_KEYWORDS)
                return {"accessible": resp.status < 400, "btk_blocked": is_btk}
    except: return {"accessible": False, "btk_blocked": False}

async def get_webshare_stats():
    try:
        async with aiohttp.ClientSession(headers={"Authorization": f"Token {WEBSHARE_API_KEY}"}) as s:
            async with s.get("https://proxy.webshare.io/api/v2/subscription/") as r:
                return await r.json()
    except: return {}

async def get_railway_credits():
    query = "{ me { workspaces { customer { creditBalance remainingUsageCreditBalance } } } }"
    try:
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}"}) as s:
            async with s.post("https://backboard.railway.com/graphql/v2", json={"query": query}) as r:
                res = await r.json()
                return res.get("data", {}).get("me", {}).get("workspaces", [{}])[0].get("customer", {})
    except: return {}

# ─── 3. HANDLER & UI ────────────────────────────────────────────────────────
async def message_handler(update, context):
    text = update.message.text.strip()
    if "." in text:
        url = "https://" + text if not text.startswith("http") else text
        msg = await update.message.reply_text(f"🔍 {domain(url)} kontrol ediliyor...")
        res = await check_site_with_retries(url)
        
        status = "✅ Erişilebilir" if res["accessible"] else ("🚫 BTK Engelli" if res["btk_blocked"] else "❌ Erişilemez")
        await msg.edit_text(f"🌐 *{domain(url)}*\n📊 Durum: {status}", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Geçerli bir domain girin (örn: google.com)")

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "admin:main": await query.edit_message_text("🛠 *Admin Paneli*", parse_mode="Markdown", reply_markup=admin_main_keyboard())
    elif data == "admin:bandwidth":
        ws = await get_webshare_stats()
        text = f"📦 *Bant Genişliği*\nKullanılan: {ws.get('bandwidth_used_gb', 'N/A')} GB\nKalan: {ws.get('bandwidth_remaining_gb', 'N/A')} GB"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))
    elif data == "admin:railway":
        ry = await get_railway_credits()
        text = f"💳 *Railway Kredi*\nBakiye: ${ry.get('creditBalance', 'N/A')}\nKullanılabilir: ${ry.get('remainingUsageCreditBalance', 'N/A')}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))

def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Bant Genişliği", callback_data="admin:bandwidth"), InlineKeyboardButton("💳 Railway Kredi", callback_data="admin:railway")]
    ])

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("👋 BTK İzleme Botu aktif.", reply_markup=admin_main_keyboard())))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
