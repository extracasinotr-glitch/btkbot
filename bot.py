#!/usr/bin/env python3
import logging
import aiohttp
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8890222792:AAEU9MoI504nLuVzAVQfuAKa2tVY-SbAA10"
WEBSHARE_API_KEY = "zhyv0i0y40vpqh1c8ou8hvd42jj435belu3615z2"
RAILWAY_API_TOKEN = "8708f4a7-0dbb-466b-af4d-e904287fdcb6"
BTK_KEYWORDS = ["Bilgi Teknolojileri ve İletişim Kurumu", "erişime engellenmiştir"]

user_data = {} # {chat_id: {"sites": []}}

async def check_btk(url):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://{url}", timeout=5) as r:
                text = await r.text()
                return any(k in text for k in BTK_KEYWORDS)
    except: return False

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Site Listesi", callback_data="menu_list")],
        [InlineKeyboardButton("📦 Bant Genişliği", callback_data="menu_bw"), InlineKeyboardButton("💳 Kredi", callback_data="menu_bal")]
    ])

async def start(update, context):
    await update.message.reply_text("👋 BTK İzleme Botu aktif.", reply_markup=get_main_menu())

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    if query.data == "menu_list":
        sites = user_data.get(chat_id, {}).get("sites", [])
        text = "📋 *İzlenenler:*\n" + "\n".join([f"- {s}" for s in sites]) if sites else "Liste boş."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="menu_back")]]))

    elif query.data == "menu_bw":
        async with aiohttp.ClientSession(headers={"Authorization": f"Token {WEBSHARE_API_KEY}"}) as s:
            async with s.get("https://proxy.webshare.io/api/v2/subscription/") as r:
                res = await r.json()
                await query.edit_message_text(f"📦 Bant: {res.get('bandwidth_used_gb', 0)} GB", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="menu_back")]]))

    elif query.data == "menu_bal":
        query_gql = "{ me { workspaces { customer { creditBalance } } } }"
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {RAILWAY_API_TOKEN}"}) as s:
            async with s.post("https://backboard.railway.com/graphql/v2", json={"query": query_gql}) as r:
                res = await r.json()
                bal = res.get("data", {}).get("me", {}).get("workspaces", [{}])[0].get("customer", {}).get("creditBalance", 0)
                await query.edit_message_text(f"💳 Bakiye: ${bal}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="menu_back")]]))

    elif query.data == "menu_back":
        await query.edit_message_text("🛠 Menü:", reply_markup=get_main_menu())

async def msg_handler(update, context):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    if chat_id not in user_data: user_data[chat_id] = {"sites": []}
    
    is_blocked = await check_btk(text)
    status = "🚫 BTK'lı" if is_blocked else "✅ Temiz"
    user_data[chat_id]["sites"].append(f"{text} ({status})")
    await update.message.reply_text(f"🌐 Eklendi: {text} | Durum: {status}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    app.run_polling()
