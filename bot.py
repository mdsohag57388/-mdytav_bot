import os
import threading
import yt_dlp
from pyrogram import Client, filters
from flask import Flask

# এনভায়রনমেন্ট ভেরিয়েবল লোড
API_ID = int(os.environ.get("API_ID", 39094664))
API_HASH = os.environ.get("API_HASH", "723baa6fc4211fe0e73c79be091844f4")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8658096412:AAFEKv2qaJmkpbxdz5Lb_M09xBe2yC5l4Fw")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ফ্লাস্ক সার্ভার
def start_flask():
    app_flask = Flask(__name__)
    @app_flask.route('/')
    def home(): return "Bot is Active!"
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ভিডিও ফরমেট ফাংশন
def get_video_formats(url):
    ydl_opts = {'quiet': True, 'format': 'bestvideo+bestaudio/best'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'Video'), []
    except Exception as e:
        return None, str(e)

# মেইন ব্লক
if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    app.run()
