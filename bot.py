import os
import asyncio
import tempfile
import subprocess
from threading import Thread
from flask import Flask, request
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp


BOT_TOKEN = os.environ.get("8314604269:AAHqjwpIZbd15ahRZo2srHVqnSLNP3dNbzQ")
API_ID = int(os.environ.get("24526311", "0"))
API_HASH = os.environ.get("717d5df262e474f88d86c537a787c98d")
CHANNEL_ID = os.environ.get("-1003015338091")  
OWNER_ID = int(os.environ.get("8327095733", "0"))
AUTO_UPLOAD = os.environ.get("AUTO_UPLOAD", "false").lower() in ("1", "true", "yes")

if not BOT_TOKEN or not API_ID or not API_HASH:
    raise RuntimeError("Missing BOT_TOKEN or API_ID or API_HASH in environment variables")

app = Flask(__name__)

# Simple keepalive endpoint for health checks
@app.route("/", methods=["GET"])
def index():
    return "OK", 200

# optional ping route for external services
@app.route("/ping", methods=["POST"])
def ping():
    return {"status": "pong"}, 200

# start Flask in a thread so Pyrogram can run in main thread loop
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ---------- yt-dlp downloader helpers ----------
YTDLP_OPTS = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': '%(id)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}

async def download_instagram(url: str) -> str:
    """Download video and return path to saved file."""
    # Use a temporary directory
    tmpdir = tempfile.mkdtemp()
    opts = YTDLP_OPTS.copy()
    opts['outtmpl'] = os.path.join(tmpdir, '%(id)s.%(ext)s')

    loop = asyncio.get_event_loop()

    def run():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # pick the downloaded filename
            filename = ydl.prepare_filename(info)
            return filename, info

    filename, info = await loop.run_in_executor(None, run)
    return filename, info

def reencode_to_mp4(src_path: str) -> str:
    """Ensure output is mp4 (some files may be webm), return new path."""
    base = os.path.splitext(src_path)[0]
    out = base + "_out.mp4"
    cmd = [
        'ffmpeg', '-y', '-i', src_path,
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k', out
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

# ---------- Pyrogram Bot ----------
bot = Client("insta_reposter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text("Hi — send /reel <instagram_url> to download and repost reels (no guarantee of watermark removal). Use responsibly.")

@bot.on_message(filters.command("reel") & filters.private | filters.group)
async def reel_handler(client: Client, message: Message):
    text = message.text or message.caption or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /reel <instagram_url>")
        return
    url = parts[1].strip()
    processing = await message.reply_text("🔄 Processing... this may take a few seconds")
    try:
        downloaded_path, info = await download_instagram(url)
    except Exception as e:
        await processing.edit(f"❌ Download failed: {e}")
        return

    # re-encode to mp4 for compatibility
    try:
        out_path = reencode_to_mp4(downloaded_path)
    except Exception:
        out_path = downloaded_path

    caption = ''
    # try to get uploader's username from info
    try:
        uploader = info.get('uploader') or info.get('channel') or info.get('creator') or ''
        caption_text = info.get('description') or ''
        credit = f"\n\n📌 Credit: @{uploader}" if uploader else ""
        caption = (caption_text[:900] + '...') if len(caption_text) > 900 else caption_text
        caption = caption + credit
    except Exception:
        caption = '📌 Credit: (source)'

    try:
        # reply with video
        await message.reply_video(out_path, caption=caption)

        # optionally auto-upload to channel
        if AUTO_UPLOAD and CHANNEL_ID:
            try:
                await client.send_video(CHANNEL_ID, out_path, caption=caption)
            except Exception as e:
                # log but don't break
                print('Auto upload failed:', e)

        await processing.delete()
    except Exception as e:
        await processing.edit(f"❌ Failed to send video: {e}")
    finally:
        # cleanup
        try:
            os.remove(downloaded_path)
        except Exception:
            pass
        try:
            if out_path != downloaded_path:
                os.remove(out_path)
        except Exception:
            pass

@bot.on_message(filters.command("mp3"))
async def mp3_handler(client: Client, message: Message):
    text = message.text or message.caption or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /mp3 <instagram_url>")
        return
    url = parts[1].strip()
    m = await message.reply_text("🔄 Downloading and extracting audio...")
    try:
        downloaded_path, info = await download_instagram(url)
    except Exception as e:
        await m.edit(f"❌ Download failed: {e}")
        return

    base = os.path.splitext(downloaded_path)[0]
    mp3_path = base + ".mp3"
    cmd = ['ffmpeg', '-y', '-i', downloaded_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '3', mp3_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        await message.reply_audio(mp3_path, title=info.get('title') or 'Audio')
        await m.delete()
    except Exception as e:
        await m.edit(f"❌ Sending audio failed: {e}")
    finally:
        try:
            os.remove(downloaded_path)
            os.remove(mp3_path)
        except Exception:
            pass

# admin-only command to set auto-upload
@bot.on_message(filters.command("setchannel") & filters.user(OWNER_ID))
async def set_channel(client: Client, message: Message):
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /setchannel <@channelusername_or_id>")
        return
    cid = parts[1].strip()
    # store in environment (Heroku: change config var manually) - here we just echo
    await message.reply_text(f"Channel set to {cid}. Please update CHANNEL_ID in Heroku config vars to persist.")

# ---------- Start everything ----------
if __name__ == '__main__':
    # start flask in a thread
    t = Thread(target=run_flask, daemon=True)
    t.start()

    # run pyrogram
    bot.run()
