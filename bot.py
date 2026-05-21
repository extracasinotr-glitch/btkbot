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
WEBSHARE_PROXY = "http://rozhkpzn:9u4t6jpvz0hj@166.88.110.18:5163"

user_state = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── FONKSİYONLAR ──────────────────────────────────────────────────────────
def domain(url): return urlparse(url if "://" in url else "https://" + url).netloc

def get_status_label(s):
    if s["accessible"]: return "✅"
    if s["btk_blocked"]: return "🚫"
    return "❌"

async def check_site(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=WEBSHARE_PROXY, timeout=10) as resp:
                text = await resp.text()
                is_btk = any(kw.lower() in text.lower() for kw in BTK_BLOCK_KEYWORDS)
                return {"accessible": resp.status < 400, "btk_blocked": is_btk}
    except: return {"accessible": False, "btk_blocked": False}

# ─── HANDLERLAR ────────────────────────────────────────────────────────────
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Site Listesi", callback_data="site_list")],
        [InlineKeyboardButton("📦 Bant Genişliği", callback_data="bandwidth"), InlineKeyboardButton("💳 Railway Kredi", callback_data="railway")]
    ])

async def start(update, context):
    await update.message.reply_text("👋 Bot aktif. Site eklemek için domain girin.", reply_markup=get_main_keyboard())

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    
    if query.data == "back":
        await query.edit_message_text("🛠 *Admin Paneli*", parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    elif query.data == "site_list":
        sites = user_state.get(chat_id, {}).get("sites", {})
        if not sites:
            text = "📋 Liste boş."
        else:
            text = "📋 *İzlenenler:*\n" + "\n".join([f"{get_status_label(s)} `{domain(u)}`" for u, s in sites.items()])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="back")]]))
    
    elif query.data == "bandwidth":
        try:
            async with aiohttp.ClientSession(headers={"Authorization": f"Token {WEBSHARE_API_KEY}"}) as s:
                async with s.get("https://proxy.webshare.io/api/v2/subscription/") as r:
                    ws = await r.json()
                    gb = ws.get('bandwidth_used_gb', '0')
                    await query.edit_message_text(f"📦 *Kullanılan:* {gb} GB", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="back")]]))
        except Exception as e:
            await query.edit_message_text(f"⚠️ Hata: {str(e)[:20]}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="back")]]))

    elif query.data == "railway":
        query_gql = "{ me { workspaces { customer { creditBalance } } } }"
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}"}) as s:
            async with s.post("https://backboard.railway.com/graphql/v2", json={"query": query_gql}) as r:
                res = await r.json()
                bal = res.get("data", {}).get("me", {}).get("workspaces", [{}])[0].get("customer", {}).get("creditBalance", "0")
                await query.edit_message_text(f"💳 *Bakiye:* ${bal}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="back")]]))

async def msg_handler(update, context):
    text = update.message.text.strip()
    if "." in text:
        url = "https://" + text if not text.startswith("http") else text
        chat_id = update.effective_chat.id
        if chat_id not in user_state: user_state[chat_id] = {"sites": {}}
        res = await check_site(url)
        user_state[chat_id]["sites"][url] = {"last_status": res["accessible"], "btk_blocked": res["btk_blocked"]}
        await update.message.reply_text(f"🌐 Eklendi: {domain(url)}")
    else: await update.message.reply_text("❌ Geçersiz domain.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    app.run_polling()
