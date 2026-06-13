import os
import asyncio
import subprocess
import math
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading

# --- আপনার দেওয়া আসল ক্রেডেনশিয়ালস ---
API_ID = 30904664
API_HASH = "723baa6fc4211fe0e73c79be091844f4"
BOT_TOKEN = "8658096412:AAFEKv2qaJmkpbxdz5Lb_M09xBe2yC5l4Fw"
# -----------------------------------------------

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
    output_files = []

    base, ext = os.path.splitext(file_path)

    for i in range(num_parts):
        start_time = i * part_duration
        output_file = f"{base}_part{i+1}{ext}"
        
        split_cmd = (
            f'ffmpeg -y -ss {start_time} -t {part_duration} -i "{file_path}" '
            f'-c copy -map 0 "{output_file}"'
        )
        subprocess.run(split_cmd, shell=True)
        output_files.append(output_file)

    return output_files

def get_video_formats(url):
    import yt_dlp
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None, "ভিডিওর তথ্য পাওয়া যায়নি।"
            
            title = info.get('title', 'Unknown Title')
            video_formats = []
            audio_format = None
            seen_resolutions = set()
            
            if 'formats' in info:
                for f in info['formats']:
                    if isinstance(f, dict):
                        height = f.get('height')
                        if not height:
                            continue
                            
                        # স্ট্যান্ডার্ড ফরম্যাটে কনভার্ট করা (4K সহ)
                        if height <= 144: res_clean = '144p'
                        elif height <= 240: res_clean = '240p'
                        elif height <= 360: res_clean = '360p'
                        elif height <= 480: res_clean = '480p'
                        elif height <= 720: res_clean = '720p'
                        elif height <= 1080: res_clean = '1080p'
                        elif height <= 1440: res_clean = '1440p'
                        elif height <= 2160: res_clean = '2160p (4K)'
                        else: res_clean = f"{height}p"
                        
                        if res_clean not in seen_resolutions and f.get('vcodec') != 'none':
                            size = f.get('filesize') or f.get('filesize_approx')
                            size_mb = round(size / (1024 * 1024), 2) if size else 0
                            
                            # কম রেজোলিউশনে অডিও মার্জ করার দরকার নেই, ১০৮০পি বা তার উপরে বেস্ট অডিও মার্জ হবে
                            f_id = f.get('format_id')
                            if height >= 720:
                                f_id = f"{f_id}+bestaudio/best"

                            seen_resolutions.add(res_clean)
                            video_formats.append({
                                'type': 'video',
                                'format_id': f_id,
                                'res': f"🎬 {res_clean}",
                                'size_str': f"{size_mb} MB" if size_mb else "Best",
                                'res_num': height
                            })
                        
                        if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                            asize = f.get('filesize') or f.get('filesize_approx')
                            if asize:
                                asize_mb = round(asize / (1024 * 1024), 2)
                                audio_format = f"{asize_mb} MB"

            # রেজোলিউশন ছোট থেকে বড় সাজানো
            video_formats.sort(key=lambda x: x['res_num'])
            
            # MP3 অডিও অপশন যোগ করা
            audio_size_str = audio_format if audio_format else "High Quality"
            video_formats.append({
                'type': 'audio',
                'format_id': 'bestaudio',
                'res': '🎵 Audio (MP3)',
                'size_str': audio_size_str
            })
            
            return title, video_formats
    except Exception as e:
        return None, str(e)

@app.on_message(filters.private & filters.text)
async def handle_message(client, message):
    url = message.text
    if not url.startswith(("http://", "https://")):
        await message.reply_text("দয়া করে একটি সঠিক ভিডিও লিংক পাঠান।")
        return

    msg = await message.reply_text("⚡ স্পীড চেকিং চালু হচ্ছে...")
    title, formats = get_video_formats(url)
    
    if isinstance(formats, str) or not formats:
        error_msg = formats if isinstance(formats, str) else "ভিডিওর তথ্য পাওয়া যায়নি বা লিংকটি সমর্থিত নয়।"
        if "Sign in to confirm" in error_msg or "429" in error_msg:
            await msg.edit_text("⚠️ ইউটিউব এই মুহূর্তে রেন্ডার সার্ভারকে ব্লক করেছে। অনুগ্রহ করে একটু পর আবার চেষ্টা করুন।")
        else:
            await msg.edit_text(f"❌ এরর: {error_msg}")
        return

    buttons = []
    row = []
    
    for f in formats:
        callback_data = f"{f['type']}|{f['format_id']}|{url}"
        if len(callback_data) > 64:
            callback_data = f"{f['type']}|best|{url}"
            
        button_text = f"{f['res']} - {f['size_str']}"
        btn = InlineKeyboardButton(button_text, callback_data=callback_data)
        
        if f['type'] == 'audio':
            if row:
                buttons.append(row)
                row = []
            buttons.append([btn])
        else:
            row.append(btn)
            if len(row) == 2:
                buttons.append(row)
                row = []
                
    if row:
        buttons.append(row)

    reply_markup = InlineKeyboardMarkup(buttons)
    await msg.edit_text(f"🎬 **{title}**\n\nFormats to download ↓", reply_markup=reply_markup)

@app.on_callback_query(filters.regex("^(video|audio)\|"))
async def handle_download(client, callback_query):
    data = callback_query.data.split("|")
    download_type = data[0]
    format_id = data[1]
    url = data[2]

    await callback_query.message.edit_text("📥 ফাইলটি সার্ভারে ডাউনলোড হচ্ছে, দয়া করে অপেক্ষা করুন...")

    import yt_dlp
    
    if download_type == "audio":
        output_template = "downloads/%(title)s.%(ext)s"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            'format': format_id if format_id != 'best' else 'bestvideo+bestaudio/best',
            'outtmpl': "downloads/%(title)s_video.%(ext)s",
            'quiet': True,
            'merge_output_format': 'mp4'
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            if download_type == "audio":
                file_path = os.path.splitext(file_path)[0] + ".mp3"
            else:
                if not os.path.exists(file_path):
                    file_path = os.path.splitext(file_path)[0] + ".mp4"

        await callback_query.message.edit_text("⚡ ফাইল প্রসেসিং এবং আপলোডিং চালু হচ্ছে...")

        if download_type == "audio":
            await callback_query.message.reply_audio(audio=file_path, caption="Here is your audio (MP3)!")
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            video_files = split_video(file_path)
            for f in video_files:
                await callback_query.message.reply_video(video=f, caption="Here is your video!")
                if f != file_path and os.path.exists(f):
                    os.remove(f)
            if os.path.exists(file_path):
                os.remove(file_path)

        await callback_query.message.delete()

    except Exception as e:
        await callback_query.message.edit_text(f"❌ ডাউনলোড ব্যর্থ হয়েছে!\nএরর: {str(e)}")

# --- ফ্লাস্ক সার্ভার সেটআপ ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

def start_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    app.run()
