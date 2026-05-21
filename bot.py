#!/usr/bin/env python3
import logging
import random
import aiohttp
import asyncio
from urllib.parse import urlparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# ─── AYARLAR ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8890222792:AAEU9MoI504nLuVzAVQfuAKa2tVY-SbAA10"
WEBSHARE_API_KEY = "zhyv0i0y40vpqh1c8ou8hvd42jj435belu3615z2"
RAILWAY_API_TOKEN = "8708f4a7-0dbb-466b-af4d-e904287fdcb6"

BTK_BLOCK_KEYWORDS = ["Bilgi Teknolojileri ve İletişim Kurumu", "erişime engellenmiştir", "ihbarweb.org.tr"]
WEBSHARE_PROXY_LIST = [
    "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.18:5163",
    "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.215:5360"
]

user_state = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── YARDIMCI FONKSİYONLAR ──────────────────────────────────────────────────
def domain(url): return urlparse(url if "://" in url else "https://" + url).netloc

def get_status_label(s):
    if s["accessible"]: return "✅ Erişilebilir"
    if s["btk_blocked"]: return "🚫 BTK Engelli"
    return "❌ Erişilemez"

async def check_site_with_retries(url):
    proxy = random.choice(WEBSHARE_PROXY_LIST)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=15) as resp:
                text = await resp.text()
                is_btk = any(kw.lower() in text.lower() for kw in BTK_BLOCK_KEYWORDS)
                return {"accessible": resp.status < 400, "btk_blocked": is_btk}
    except: return {"accessible": False, "btk_blocked": False}

# ─── OTOMATİK KONTROL DÖNGÜSÜ ───────────────────────────────────────────────
async def run_periodic_check(app):
    while True:
        await asyncio.sleep(300) # 5 Dakika bekle
        for chat_id, data in list(user_state.items()):
            for url, s in list(data["sites"].items()):
                res = await check_site_with_retries(url)
                if s["last_status"] != res["accessible"] or s["btk_blocked"] != res["btk_blocked"]:
                    status_text = get_status_label(res)
                    await app.bot.send_message(chat_id, f"🔄 *{domain(url)}* durum güncellendi:\n📊 {status_text}", parse_mode="Markdown")
                data["sites"][url].update({"last_status": res["accessible"], "btk_blocked": res["btk_blocked"]})

# ─── PANEL VE HANDLERLAR ────────────────────────────────────────────────────
def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Site Listesi", callback_data="site:list")],
        [InlineKeyboardButton("📦 Bant Genişliği", callback_data="admin:bandwidth"), InlineKeyboardButton("💳 Railway Kredi", callback_data="admin:railway")]
    ])

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    
    if data == "admin:main": await query.edit_message_text("🛠 *Admin Paneli*", parse_mode="Markdown", reply_markup=admin_main_keyboard())
    
    elif data == "site:list":
        sites = user_state.get(chat_id, {}).get("sites", {})
        if not sites: text = "📋 *Listenizde hiç site yok.*"
        else:
            text = "📋 *İzlenen Siteler:*\n\n"
            for url, s in sites.items():
                text += f"{get_status_label(s)} | `{domain(url)}`\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))
    
    elif data == "admin:bandwidth":
        async with aiohttp.ClientSession(headers={"Authorization": f"Token {WEBSHARE_API_KEY}"}) as s:
            async with s.get("https://proxy.webshare.io/api/v2/subscription/") as r:
                ws = await r.json()
        await query.edit_message_text(f"📦 *Bant Genişliği*\nKullanılan: {ws.get('bandwidth_used_gb', 'N/A')} GB", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))
    
    elif data == "admin:railway":
        query_gql = "{ me { workspaces { customer { creditBalance } } } }"
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}"}) as s:
            async with s.post("https://backboard.railway.com/graphql/v2", json={"query": query_gql}) as r:
                res = await r.json()
                bal = res.get("data", {}).get("me", {}).get("workspaces", [{}])[0].get("customer", {}).get("creditBalance", "N/A")
        await query.edit_message_text(f"💳 *Railway Bakiye:* ${bal}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))

async def message_handler(update, context):
    text = update.message.text.strip()
    if "." in text:
        url = "https://" + text if not text.startswith("http") else text
        chat_id = update.effective_chat.id
        if chat_id not in user_state: user_state[chat_id] = {"sites": {}}
        res = await check_site_with_retries(url)
        user_state[chat_id]["sites"][url] = {"last_status": res["accessible"], "btk_blocked": res["btk_blocked"]}
        await update.message.reply_text(f"🌐 *{domain(url)}* listeye eklendi.\n📊 Durum: {get_status_label(res)}", parse_mode="Markdown")
    else: await update.message.reply_text("❌ Geçerli bir domain girin.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    loop = asyncio.get_event_loop()
