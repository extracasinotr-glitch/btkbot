#!/usr/bin/env python3
import logging
import random
import aiohttp
import asyncio
from urllib.parse import urlparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

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

# ─── FONKSİYONLAR ──────────────────────────────────────────────────────────
def domain(url): return urlparse(url if "://" in url else "https://" + url).netloc

def get_status_label(s):
    if s["accessible"]: return "✅"
    if s["btk_blocked"]: return "🚫"
    return "❌"

async def check_site_with_retries(url):
    proxy = random.choice(WEBSHARE_PROXY_LIST)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=10) as resp:
                text = await resp.text()
                is_btk = any(kw.lower() in text.lower() for kw in BTK_BLOCK_KEYWORDS)
                return {"accessible": resp.status < 400, "btk_blocked": is_btk}
    except: return {"accessible": False, "btk_blocked": False}

# ─── OTOMATİK KONTROL ──────────────────────────────────────────────────────
async def run_periodic_check(app):
    while True:
        await asyncio.sleep(300)
        for chat_id, data in list(user_state.items()):
            for url, s in list(data["sites"].items()):
                res = await check_site_with_retries(url)
                if s["last_status"] != res["accessible"] or s["btk_blocked"] != res["btk_blocked"]:
                    await app.bot.send_message(chat_id, f"🔄 {domain(url)} durumu güncellendi.")
                data["sites"][url].update({"last_status": res["accessible"], "btk_blocked": res["btk_blocked"]})

# ─── HANDLERLAR ────────────────────────────────────────────────────────────
def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Site Listesi", callback_data="site:list")],
        [InlineKeyboardButton("📦 Bant Genişliği", callback_data="admin:bandwidth"), InlineKeyboardButton("💳 Railway", callback_data="admin:railway")]
    ])

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    
    try:
        if query.data == "admin:main":
            await query.edit_message_text("🛠 *Admin Paneli*", parse_mode="Markdown", reply_markup=admin_main_keyboard())
        
        elif query.data == "site:list":
            sites = user_state.get(chat_id, {}).get("sites", {})
            if not sites:
                text = "📋 *Listenizde hiç site yok.*"
            else:
                text = "📋 *İzlenenler:*\n\n" + "\n".join([f"{get_status_label(s)} `{domain(u)}`" for u, s in sites.items()])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))
        
        elif query.data == "admin:bandwidth":
            async with aiohttp.ClientSession(headers={"Authorization": f"Token {WEBSHARE_API_KEY}"}) as s:
                async with s.get("https://proxy.webshare.io/api/v2/subscription/") as r:
                    ws = await r.json()
            await query.edit_message_text(f"📦 *Bant Genişliği:* {ws.get('bandwidth_used_gb', '0')} GB", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))
    except Exception as e:
        logger.error(f"Callback Hatası: {e}")
        await query.edit_message_text("⚠️ Bir hata oluştu, tekrar deneyin.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))

async def message_handler(update, context):
    text = update.message.text.strip()
    if "." in text:
        url = "https://" + text if not text.startswith("http") else text
        chat_id = update.effective_chat.id
        if chat_id not in user_state: user_state[chat_id] = {"sites": {}}
        res = await check_site_with_retries(url)
        user_state[chat_id]["sites"][url] = {"last_status": res["accessible"], "btk_blocked": res["btk_blocked"]}
        await update.message.reply_text(f"🌐 *{domain(url)}* eklendi.", parse_mode="Markdown")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("👋 BTK İzleme Botu.", reply_markup=admin_main_keyboard())))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    loop = asyncio.get_event_loop()
    loop.create_task(run_periodic_check(app))
    app.run_polling()
