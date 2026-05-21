#!/usr/bin/env python3
import asyncio
import logging
import random
import aiohttp
from telegram import Update
from telegram.ext import (Application, CommandHandler, MessageHandler, ContextTypes, filters)

# ─── AYARLAR ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8890222792:AAEU9MoI504nLuVzAVQfuAKa2tVY-SbAA10"
WEBSHARE_USERNAME = "rozhkpzn"
WEBSHARE_PASSWORD = "9u4t6jpvz0hj"

# Residential Proxy (Cloudflare engeli aşımı için)
RESIDENTIAL_PROXY = f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@p.webshare.io:80"

# ESKİ DATACENTER PROXY LİSTEN (KORUNDU)
WEBSHARE_PROXY_LIST = [
    f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@166.88.110.18:5163",
    f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@166.88.110.215:5360",
    f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@142.111.216.225:6370",
    f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@166.88.110.135:5280",
    f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@142.111.216.102:6247",
    f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@142.111.90.88:7233",
    f"http://{WEBSHARE_USERNAME}:{WEBSHARE_PASSWORD}@142.111.216.112:6257",
]

# ─── BAĞLANTI VE KONTROL MANTIĞI ──────────────────────────────────────────

async def check_with_proxy(url: str, proxy: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, proxy=proxy, timeout=10, ssl=False) as response:
                return response.status < 400
        except:
            return False

async def check_site_with_retries(url: str):
    # 1. Önce Residential dene
    if await check_with_proxy(url, RESIDENTIAL_PROXY):
        return True, "Residential (Cloudflare Aşıldı)"
    
    # 2. Olmazsa Datacenter listesini dene
    for proxy in random.sample(WEBSHARE_PROXY_LIST, min(len(WEBSHARE_PROXY_LIST), 5)):
        if await check_with_proxy(url, proxy):
            return True, "Datacenter"
            
    return False, "None"

# ─── TELEGRAM HANDLER'LAR ──────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot aktif! Link gönder, kontrol edeyim.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): url = "https://" + url
    
    msg = await update.message.reply_text("🔍 Kontrol ediliyor...")
    success, source = await check_site_with_retries(url)
    
    if success:
        await msg.edit_text(f"✅ Site Erişilebilir!\nBağlantı Türü: {source}")
    else:
        await msg.edit_text("❌ Siteye erişilemedi veya BTK engeli var.")

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot tüm özellikleri ile çalışıyor...")
    app.run_polling()


if __name__== "__main__":
    main()
