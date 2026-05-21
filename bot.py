#!/usr/bin/env python3
import logging
import random
import aiohttp
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ─── Ayarlar ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8890222792:AAEU9MoI504nLuVzAVQfuAKa2tVY-SbAA10"
WEBSHARE_API_KEY = "zhyv0i0y40vpqh1c8ou8hvd42jj435belu3615z2"
RAILWAY_API_TOKEN = "8708f4a7-0dbb-466b-af4d-e904287fdcb6"

# ─── Global State ──────────────────────────────────────────────────────────
user_state = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── API Fonksiyonları ──────────────────────────────────────────────────────
async def get_webshare_stats():
    headers = {"Authorization": f"Token {WEBSHARE_API_KEY}"}
    try:
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.get("https://proxy.webshare.io/api/v2/subscription/") as r:
                data = await r.json()
                logger.info(f"Webshare Yanıtı: {data}") # Hata ayıklama için
                return data
    except Exception as e:
        return {"error": str(e)}

async def get_railway_credits():
    query = "{ me { workspaces { customer { creditBalance remainingUsageCreditBalance } } } }"
    headers = {"Authorization": f"Bearer {RAILWAY_API_TOKEN}"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://backboard.railway.com/graphql/v2", json={"query": query}, headers=headers) as r:
                data = await r.json()
                return data.get("data", {}).get("me", {}).get("workspaces", [{}])[0].get("customer", {})
    except Exception as e:
        return {"error": str(e)}

# ─── UI / Handlerlar ────────────────────────────────────────────────────────
def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Site Listesi", callback_data="site:list"), InlineKeyboardButton("📊 Bot Durumu", callback_data="admin:status")],
        [InlineKeyboardButton("📦 Bant Genişliği", callback_data="admin:bandwidth"), InlineKeyboardButton("💳 Railway Kredi", callback_data="admin:railway")]
    ])

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "admin:main":
        await query.edit_message_text("🛠 *Admin Paneli*", parse_mode="Markdown", reply_markup=admin_main_keyboard())
    
    elif data == "admin:bandwidth":
        ws = await get_webshare_stats()
        # Esnek veri çekme: Hem GB hem de byte formatı kontrolü
        used = ws.get('bandwidth_used_gb') or (ws.get('bandwidth_used', 0) / (1024**3))
        rem = ws.get('bandwidth_remaining_gb') or (ws.get('bandwidth_remaining', 0) / (1024**3))
        text = f"📦 *Bant Genişliği*\n\nKullanılan: {used:.2f} GB\nKalan: {rem:.2f} GB"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))

    elif data == "admin:railway":
        ry = await get_railway_credits()
        text = f"💳 *Railway Kredi*\n\nBakiye: ${ry.get('creditBalance', '0.00')}\nKullanılabilir: ${ry.get('remainingUsageCreditBalance', '0.00')}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))

    elif data == "admin:status":
        await query.edit_message_text("🤖 *Bot Aktif.*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="admin:main")]]))

async def start_command(update, context):
    await update.message.reply_text("👋 *BTK İzleme Botu*\n\nSite eklemek için URL gönder veya paneli kullan:", parse_mode="Markdown", reply_markup=admin_main_keyboard())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", start_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
