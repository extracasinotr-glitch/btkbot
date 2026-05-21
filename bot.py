#!/usr/bin/env python3
import logging
import random
import aiohttp
from urllib.parse import urlparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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

async def check_site_with_retries(url):
    proxy = random.choice(WEBSHARE_PROXY_LIST)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=15) as resp:
                text = await resp.text()
                is_btk = any(kw.lower() in text.lower() for kw in BTK_BLOCK_KEYWORDS)
                return {"accessible": resp.status < 400, "btk_blocked": is_btk}
    except: return {"accessible": False, "btk_blocked": False}

# 5 DAKİKADA BİR ÇALIŞACAK OTOMATİK KONTROL
async def auto_check_job(context: ContextTypes.DEFAULT_TYPE):
    for chat_id, data in user_state.items():
        for url in list(data["sites"].keys()):
            res = await check_site_with_retries(url)
            # Eğer önceki durumu "Erişilebilir" ise ve şimdi "Engellendiyse" bildirim at
            if data["sites"][url]["last_status"] == True and res["btk_blocked"]:
                await context.bot.send_message(chat_id, f"⚠️ UYARI: *{domain(url)}* BTK tarafından engellendi!", parse_mode="Markdown")
            
            data["sites"][url]["last_status"] = res["accessible"]
            data["sites"][url]["btk_blocked"] = res["btk_blocked"]

# ─── HANDLERLAR ─────────────────────────────────────────────────────────────
async def message_handler(update, context):
    text = update.message.text.strip()
    if "." in text:
        chat_id = update.effective_chat.id
        if chat_id not in user_state: user_state[chat_id] = {"sites": {}}
        
        url = "https://" + text if not text.startswith("http") else text
        res = await check_site_with_retries(url)
        user_state[chat_id]["sites"][url] = {"last_status": res["accessible"], "btk_blocked": res["btk_blocked"]}
        
        status = "✅ Erişilebilir" if res["accessible"] else ("🚫 BTK Engelli" if res["btk_blocked"] else "❌ Erişilemez")
        await update.message.reply_text(f"🌐 *{domain(url)}* eklendi.\n📊 Durum: {status}", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Geçerli bir domain girin.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # 5 dakikada bir (300 saniye) otomatik kontrolü başlat
    job_queue = app.job_queue
    job_queue.run_repeating(auto_check_job, interval=300, first=10)
    
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("👋 BTK İzleme Botu 5dk'da bir tarama yapıyor.")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info("Bot 5 dakikalık periyotla başlatıldı.")
    app.run_polling()

if __name__ == "__main__":
    main()
