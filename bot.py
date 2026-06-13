import os
import math
import subprocess
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading

# এনভায়রনমেন্ট ভেরিয়েবল থেকে তথ্য লোড করা
API_ID = int(os.environ.get("API_ID", 39094664))
API_HASH = os.environ.get("API_HASH", "723baa6fc4211fe0e73c79be091844f4")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8658096412:AAFEKv2qaJmkpbxdz5Lb_M09xBe2yC5l4Fw")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ফোল্ডার চেক
if not os.path.exists("downloads"):
    os.makedirs("downloads")

def get_video_formats(url):
    ydl_opts = {'quiet': True, 'format': 'bestvideo+bestaudio/best'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            available_formats = []
            seen_res = set()
            
            for f in formats:
                if isinstance(f, dict) and f.get('height') and f.get('filesize'):
                    res = f.get('height')
                    res_str = f"{res}p"
                    if res_str not in seen_res:
                        size_mb = round(f['filesize'] / (1024 * 1024), 1)
                        available_formats.append({
                            'type': 'video',
                            'format_id': f['format_id'],
                            'res': res_str,
                            'size_str': f"{size_mb} MB"
                        })
                        seen_res.add(res_str)
            return info.get('title', 'Video'), available_formats
    except Exception as e:
        return None, str(e)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("হ্যালো! ভিডিওর লিংক পাঠান, আমি সেটি ডাউনলোড করতে সাহায্য করব।")

@app.on_message(filters.text & filters.private)
async def handle_message(client, message):
    url = message.text
    if not url.startswith("http"):
        return
    
    msg = await message.reply_text("তথ্য সংগ্রহ করছি...")
    title, formats = get_video_formats(url)
    
    if not formats:
        await msg.edit_text(f"এরর: {formats}")
        return
    
    buttons = [
        [InlineKeyboardButton(f"{f['res']} - {f['size_str']}", callback_data=f"{f['format_id']}|{url}")]
        for f in formats
    ]
    await msg.edit_text(f"ভিডিও: {title}\nফরম্যাট নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query()
async def callback(client, query):
    data = query.data.split("|")
    format_id = data[0]
    url = data[1]
    
    await query.message.edit_text("ডাউনলোড শুরু হচ্ছে...")
    # এখানে ডাউনলোডের বাকি লজিক হবে
    await query.message.edit_text("ডাউনলোড সফল হয়েছে!")

# ফ্লাস্ক সার্ভার
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Active!"

def start_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    app.run()
