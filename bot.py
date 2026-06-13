import os
import asyncio
import subprocess
import math
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# --- আপনার টেলিগ্রাম এপিআই ডিটেইলস ---
API_ID = 39094664                    
API_HASH = "723baa6fc4211fe0e73c79be091844f4"     
BOT_TOKEN = "8658096412:AAFEKV2qaJmkpbxdz5Lb_MO9xBe2yC5l4Fw"
# -----------------------------------------------------------

app = Client("downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

if not os.path.exists("downloads"):
    os.makedirs("downloads")

def split_video(file_path, target_size_bytes=1900 * 1024 * 1024):
    file_size = os.path.getsize(file_path)
    if file_size <= target_size_bytes:
        return [file_path]

    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    duration = float(subprocess.check_output(cmd, shell=True).decode().strip())
    
    num_parts = math.ceil(file_size / target_size_bytes)
    part_duration = duration / num_parts
    
    base_name, ext = os.path.splitext(file_path)
    split_files = []
    
    for i in range(num_parts):
        start_time = i * part_duration
        output_part = f"{base_name}_part{i+1}{ext}"
        split_cmd = f'ffmpeg -y -ss {start_time} -i "{file_path}" -t {part_duration} -c copy -map 0 -loglevel panic "{output_part}"'
        subprocess.run(split_cmd, shell=True)
        
        if os.path.exists(output_part):
            split_files.append(output_part)
            
    return split_files

def get_video_formats(url):
    ydl_opts = {'quiet': True, 'extract_flat': False, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            title = info.get('title', 'Video')
            
            available_formats = []
            target_resolutions = ['144', '240', '360', '480', '720', '1080', '1440', '2160']
            seen_res = set()
            
            for f in formats:
                res = f.get('height')
                if res and str(res) in target_resolutions and f.get('filesize'):
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
            
            return title, available_formats
        except Exception as e:
            return None, str(e)

@app.on_message(filters.private & filters.text)
async def handle_message(client, message):
    url = message.text
    if not url.startswith(("http://", "https://")):
        await message.reply_text("দয়া করে একটি সঠিক ভিডিও লিংক পাঠান।")
        return

    msg = await message.reply_text("⚡ স্পীড চেকিং চালু হচ্ছে...")
    title, formats = get_video_formats(url)

    if not formats:
        await msg.edit_text("ভিডিওর তথ্য পাওয়া যায়নি বা লিংকটি সমর্থিত নয়।")
        return

    buttons = []
    row = []
    
    for f in formats:
        if f['type'] == 'video':
            button_text = f"🎬 {f['res']} - {f['size_str']}"
            callback_data = f"dl|{f['format_id']}|video|{url}"
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)

    await msg.delete()
    await message.reply_text(
        f"**🎥 {title}**\n\nকোয়ালিটি সিলেক্ট করুন (সার্ভার স্পীড একটিভেটেড):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex(r"^dl\|"))
async def handle_download(client, callback_query):
    _, format_id, f_type, url = callback_query.data.split("|")
    await callback_query.answer()
    
    status_msg = await callback_query.message.reply_text("🚀 সার্ভারে সুপারফাস্ট ডাউনলোড হচ্ছে...")

    output_template = "downloads/%(title)s.%(ext)s"
    ydl_opts = {
        'format': format_id,
        'outtmpl': output_template,
        'quiet': True,
        'n_threads': 8
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await status_msg.edit_text("⚙️ সাইজ চেক করে পার্ট করা হচ্ছে...")
        video_parts = split_video(filename)

        for index, part in enumerate(video_parts):
            part_name = os.path.basename(part)
            await status_msg.edit_text(f"⚡ 🚀 হাই-স্পীড আপলোড হচ্ছে: {index+1}/{len(video_parts)}...")
            
            await client.send_video(chat_id=callback_query.message.chat.id, video=part)
            
            if part != filename and os.path.exists(part):
                os.remove(part)

        if os.path.exists(filename):
            os.remove(filename)
            
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ একটি ভুল হয়েছে: {str(e)}")

print("বটটি সুপারফাস্ট মোডে চালু হয়েছে...")

from flask import Flask
import threading
import os

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"
def run_bot_in_background():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    print("টেলিগ্রাম বট সফলভাবে ব্যাকগ্রাউন্ডে কানেক্টেড হচ্ছে...")
    loop.run_until_complete(app.start())
    
    from pyrogram.methods.utilities.idle import idle
    loop.run_until_complete(idle())

if __name__ == "__main__":
    # ১. প্রথমে টেলিগ্রাম বটকে সম্পূর্ণ আলাদা একটি ব্যাকগ্রাউন্ড থ্রেডে স্টার্ট করে দেওয়া হলো
    import threading
    bot_thread = threading.Thread(target=run_bot_in_background)
    bot_thread.daemon = True
    bot_thread.start()
    
    # ২. এবার মেইন থ্রেডে ফ্লাস্ক রান করবে, যাতে রেন্ডার সার্ভার কখনো ব্লক বা ক্র্যাশ না হয়
    print("রেন্ডার পোর্ট সচল করার জন্য ফ্লাস্ক সার্ভার চালু হচ্ছে...")
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)
