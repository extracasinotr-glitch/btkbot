#!/usr/bin/env python3
import logging
import aiohttp
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ─── Ayarlar ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8890222792:AAEU9MoI504nLuVzAVQfuAKa2tVY-SbAA10"
WEBSHARE_API_KEY = "zhyv0i0y40vpqh1c8ou8hvd42jj435belu3615z2"
RAILWAY_API_TOKEN = "8708f4a7-0dbb-466b-af4d-e904287fdcb6"

user_state = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Fonksiyonlar ──────────────────────────────────────────────────────────
def domain(url): return urlparse(url if "://" in url else "https://" + url).netloc

async def get_webshare_stats():
    try:
        async with aiohttp.ClientSession(headers={"Authorization": f"Token {WEBSHARE_API_KEY}"}) as s:
            async with s.get("https://proxy.webshare.io/api/v2/subscription/") as r:
                return await r.json()
    except: return {"error": "API Hatası"}

async def get_railway_credits():
    query = "{ me { workspaces { customer { creditBalance remainingUsageCreditBalance } } } }"
    try:
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}"}) as s:
            async with s.post("https://backboard.railway.com/graphql/v2", json={"query": query}) as r:
                res = await r.json()
                return res.get("data", {}).get("me", {}).get("workspaces", [{}])[0].get("customer", {})
    except: return {"error": "API Hatası"}

# ─── Handlerlar ─────────────────────────────────────────────────────────────
async def message_handler(update, context):
    text = update.message.text.strip()
    # İçinde nokta varsa domain kabul et
    if "." in text:
        chat_id = update.effective_chat.id
        if chat_id not in user_state: user_state[chat_id] = {"sites": {}}
        user_state[chat_id]["sites"][text] = {"last_status": True}
        await update.message.reply_text(f"✅ *{text}* izleme listesine eklendi.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Geçerli bir domain girin (örn: google.com)")

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "admin:main": await query.edit_message_text("🛠 *Admin Paneli*", parse_mode="Markdown", reply_markup=admin_main_keyboard())
    elif data == "admin:bandwidth":
        ws = await get_webshare_stats()
        text = f"📦 *Bant Genişliği*\nKullanılan: {ws.get('bandwidth_used_gb', 'N/A')} GB"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))
    elif data == "admin:railway":
        ry = await get_railway_credits()
        text = f"💳 *Railway Kredi*\nBakiye: ${ry.get('creditBalance', 'N/A')}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))
    elif data == "site:list":
        chat_id = update.effective_chat.id
        sites = user_state.get(chat_id, {}).get("sites", {})
        text = "📋 *İzlenenler:*\n" + "\n".join(sites.keys()) if sites else "Liste boş."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))

def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Site Listesi", callback_data="site:list")],
        [InlineKeyboardButton("📦 Bant Genişliği", callback_data="admin:bandwidth"), InlineKeyboardButton("💳 Railway Kredi", callback_data="admin:railway")]
    ])

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("👋 BTK Botu", reply_markup=admin_main_keyboard())))
    app.add_handler(CallbackQueryHandler(callback_handler))
    # Burası eksikti, domainleri artık burası yakalayacak:
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
