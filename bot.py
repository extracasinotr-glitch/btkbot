#!/usr/bin/env python3
import asyncio
import logging
import random
import time
import aiohttp
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ─── Ayarlar ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8890222792:AAEU9MoI504nLuVzAVQfuAKa2tVY-SbAA10"
WEBSHARE_API_KEY = "zhyv0i0y40vpqh1c8ou8hvd42jj435belu3615z2"
RAILWAY_API_TOKEN = "8708f4a7-0dbb-466b-af4d-e904287fdcb6"

MAX_SITES_PER_USER = 20
TZ_TR = timezone(timedelta(hours=3))

WEBSHARE_PROXY_LIST = [
    "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.18:5163",
    "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.215:5360",
    "http://rozhkpzn:9u4t6jpvz0hj@142.111.216.225:6370",
    "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.135:5280"
]

BTK_BLOCK_KEYWORDS = ["Bilgi Teknolojileri ve İletişim Kurumu", "erişime engellenmiştir", "ihbarweb.org.tr"]

# Global Durum
user_state = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────
def domain(url): return urlparse(url).netloc
def normalize_url(url): return "https://" + url.strip().replace("https://", "").replace("http://", "")
def status_emoji(status, btk): return "✅" if status is True else ("🚫" if btk else "❌")

async def check_site_with_retries(url):
    proxy = random.choice(WEBSHARE_PROXY_LIST)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=15) as resp:
                text = await resp.text()
                btk_blocked = any(kw.lower() in text.lower() for kw in BTK_BLOCK_KEYWORDS)
                return {"accessible": resp.status < 400, "btk_blocked": btk_blocked}
    except:
        return {"accessible": False, "btk_blocked": False}

# ─── Handler'lar ────────────────────────────────────────────────────────────
async def start_command(update, context):
    await update.message.reply_text("BTK İzleme Botu aktif. Takip etmek istediğin siteyi gönder.")

async def message_handler(update, context):
    chat_id = update.effective_chat.id
    if chat_id not in user_state: user_state[chat_id] = {"sites": {}}
    url = normalize_url(update.message.text)
    
    msg = await update.message.reply_text(f"🔍 {domain(url)} kontrol ediliyor...")
    res = await check_site_with_retries(url)
    
    user_state[chat_id]["sites"][url] = {"last_status": res["accessible"], "last_check": time.time(), "btk_blocked": res["btk_blocked"]}
    await msg.edit_text(f"🌐 {domain(url)}\n📊 Durum: {status_emoji(res['accessible'], res['btk_blocked'])}")

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "admin:main":
        await query.edit_message_text("🛠 Admin Paneli", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Site Listesi", callback_data="site:list"), InlineKeyboardButton("📊 Bot Durumu", callback_data="admin:status")]
        ]))
    elif data == "site:list":
        chat_id = update.effective_chat.id
        sites = user_state.get(chat_id, {}).get("sites", {})
        text = "📋 İzlenen Siteler:\n" + "\n".join([f"{status_emoji(s['last_status'], s['btk_blocked'])} {domain(u)}" for u, s in sites.items()])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))
    elif data == "admin:status":
        await query.edit_message_text("🤖 Bot çalışıyor. Proxy: Aktif. Veri: Güncel.")

# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", lambda u, c: u.message.reply_text("Panel:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Aç", callback_data="admin:main")]]))))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info("Bot başarıyla başlatıldı.")
    app.run_polling()

if __name__ == "__main__":
    main()
