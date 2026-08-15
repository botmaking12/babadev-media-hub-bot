import asyncio
import logging
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

try:
    from config import BOT_TOKEN, BRAND_STYLE, ADMIN_IDS
except Exception:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    BRAND_STYLE = os.getenv("BRAND_STYLE", "gold")
    ADMIN_IDS = []

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


# ============================================================
# 🔱 BABADEV MEDIA HUB
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

log = logging.getLogger("babadev")

BASE_DIR = Path.home() / "babadev-media-hub-bot"
WORK_DIR = BASE_DIR / "media_jobs"
WORK_DIR.mkdir(parents=True, exist_ok=True)

MAX_TELEGRAM_SIZE = 49 * 1024 * 1024

jobs = {}


# ============================================================
# 🎨 TEXT / BRANDING
# ============================================================

def title_text():
    return (
        "🔱 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐌𝐄𝐃𝐈𝐀 𝐇𝐔𝐁 🔱\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✨ 𝙈𝙚𝙙𝙞𝙖 𝙏𝙤𝙤𝙡𝙠𝙞𝙩 • 𝟮𝟰/𝟳 ✨\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def help_text():
    return (
        "╔══════════════════════╗\n"
        "   🔱 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐇𝐄𝐋𝐏\n"
        "╚══════════════════════╝\n\n"
        "🎬 <b>VIDEO FILE</b>\n"
        "Send a video directly to the bot.\n\n"
        "🔗 <b>MEDIA URL</b>\n"
        "Send a public YouTube / Instagram / Facebook URL.\n\n"
        "🛠️ <b>TOOLS</b>\n"
        "✏️ Rename\n"
        "📝 Custom Caption\n"
        "🖼️ Thumbnail\n"
        "🎵 Extract Audio\n"
        "📦 Compress\n"
        "💧 Watermark\n"
        "ℹ️ Video Info\n\n"
        "⚠️ Use only media you have permission to process/download."
    )


# ============================================================
# 🔘 KEYBOARDS
# ============================================================

def url_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 𝐕𝐢𝐝𝐞𝐨", callback_data="url:video"),
            InlineKeyboardButton("🎵 𝑨𝒖𝒅𝒊𝒐", callback_data="url:audio"),
        ],
        [
            InlineKeyboardButton("🖼️ 𝙏𝙝𝙪𝙢𝙗𝙣𝙖𝙞𝙡", callback_data="url:thumb"),
            InlineKeyboardButton("📦 𝐀𝐥𝐥", callback_data="url:all"),
        ],
        [
            InlineKeyboardButton("⚙️ 𝑴𝒐𝒓𝒆", callback_data="more"),
            InlineKeyboardButton("❌ 𝐂𝐚𝐧𝐜𝐞𝐥", callback_data="cancel"),
        ],
    ])


def video_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ 𝐑𝐞𝐧𝐚𝐦𝐞", callback_data="video:rename"),
            InlineKeyboardButton("📝 𝑪𝒂𝒑𝒕𝒊𝒐𝒏", callback_data="video:caption"),
        ],
        [
            InlineKeyboardButton("🖼️ 𝐓𝐡𝐮𝐦𝐛𝐧𝐚𝐢𝐥", callback_data="video:thumb"),
            InlineKeyboardButton("🎵 𝑨𝒖𝒅𝒊𝒐", callback_data="video:audio"),
        ],
        [
            InlineKeyboardButton("📦 𝐂𝐨𝐦𝐩𝐫𝐞𝐬𝐬", callback_data="video:compress"),
            InlineKeyboardButton("ℹ️ 𝑰𝒏𝒇𝒐", callback_data="video:info"),
        ],
        [
            InlineKeyboardButton("💧 𝐖𝐚𝐭𝐞𝐫𝐦𝐚𝐫𝐤", callback_data="video:watermark"),
        ],
        [
            InlineKeyboardButton("❌ 𝐂𝐚𝐧𝐜𝐞𝐥", callback_data="cancel"),
        ],
    ])


def watermark_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔱 𝐁𝐀𝐁𝐀𝐃𝐄𝐕",
                callback_data="watermark:babadev",
            )
        ],
        [
            InlineKeyboardButton(
                "✍️ 𝘾𝙪𝙨𝙩𝙤𝙢 𝙏𝙚𝙭𝙩",
                callback_data="watermark:custom",
            )
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ],
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 𝐒𝐭𝐚𝐭𝐬", callback_data="admin:stats"),
            InlineKeyboardButton("👥 𝑱𝒐𝒃𝒔", callback_data="admin:jobs"),
        ],
    ])


# ============================================================
# 🧹 FILE HELPERS
# ============================================================

def safe_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\-. ()\[\]]+", "_", name, flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name)
    return name[:180] or "Babadev_Media"


def new_job(uid: int):
    jid = uuid.uuid4().hex[:12]
    folder = WORK_DIR / f"{uid}_{jid}"
    folder.mkdir(parents=True, exist_ok=True)

    jobs[uid] = {
        "id": jid,
        "dir": folder,
        "file": None,
        "title": "Babadev Media",
        "caption": None,
        "cancel": False,
        "waiting": None,
    }

    return jobs[uid]


def get_job(uid):
    return jobs.get(uid)


def cleanup_job(uid):
    job = jobs.pop(uid, None)

    if job:
        try:
            shutil.rmtree(job["dir"], ignore_errors=True)
        except Exception:
            pass


def run_ffmpeg(args):
    command = ["ffmpeg", "-y"] + args

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1500:])

    return result


def run_ffprobe(path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size:stream=codec_name,width,height,r_frame_rate",
        "-of",
        "default=noprint_wrappers=1",
        str(path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        return "Information unavailable."

    return result.stdout.strip() or "Information unavailable."


# ============================================================
# 📥 DOWNLOAD URL
# ============================================================

async def download_url(url, mode, output_dir):

    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed.")

    output_template = str(output_dir / "%(title).150s.%(ext)s")

    if mode == "audio":
        fmt = "bestaudio/best"
    else:
        fmt = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"

    options = {
        "outtmpl": output_template,
        "format": fmt,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    if mode == "audio":
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    def task():
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            return info

    info = await asyncio.to_thread(task)

    files = list(output_dir.glob("*"))

    if not files:
        raise RuntimeError("Downloaded file was not found.")

    media_file = max(files, key=lambda x: x.stat().st_mtime)

    return media_file, info


# ============================================================
# 🚀 START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        title_text()
        + "\n\n"
        "🎬 <b>Send a video file</b>\n"
        "🔗 <b>Or send a media URL</b>\n\n"
        "✨ 𝑹𝒆𝒂𝒅𝒚 𝒕𝒐 𝒑𝒓𝒐𝒄𝒆𝒔𝒔 ✨",
        parse_mode="HTML",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        help_text(),
        parse_mode="HTML",
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🟢 <b>𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐌𝐄𝐃𝐈𝐀 𝐇𝐔𝐁</b>\n\n"
        "⚡ Status: <b>ONLINE</b>\n"
        f"📊 Active Jobs: <b>{len(jobs)}</b>",
        parse_mode="HTML",
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid not in ADMIN_IDS:
        return await update.message.reply_text(
            "⛔ 𝐀𝐝𝐦𝐢𝐧 𝐎𝐧𝐥𝐲"
        )

    await update.message.reply_text(
        "🔐 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐀𝐃𝐌𝐈𝐍\n\n"
        f"👥 Active Jobs: {len(jobs)}",
        reply_markup=admin_keyboard(),
    )


# ============================================================
# 🔗 URL MESSAGE
# ============================================================

def extract_url(text):

    if not text:
        return None

    match = re.search(
        r"https?://[^\s]+",
        text,
        flags=re.IGNORECASE,
    )

    return match.group(0) if match else None


def platform_name(url):

    u = url.lower()

    if "youtube.com" in u or "youtu.be" in u:
        return "YouTube"

    if "instagram.com" in u:
        return "Instagram"

    if "facebook.com" in u or "fb.watch" in u:
        return "Facebook"

    return "Web"


async def url_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = extract_url(update.message.text)

    if not url:
        return await update.message.reply_text(
            "🔗 Please send a valid <b>http/https</b> URL.",
            parse_mode="HTML",
        )

    uid = update.effective_user.id

    job = new_job(uid)
    job["url"] = url

    await update.message.reply_text(
        "╔════════════════════╗\n"
        "   🔗 𝐋𝐈𝐍𝐊 𝐃𝐄𝐓𝐄𝐂𝐓𝐄𝐃\n"
        "╚════════════════════╝\n\n"
        f"🌐 Platform: <b>{platform_name(url)}</b>\n\n"
        "👇 Choose your option:",
        parse_mode="HTML",
        reply_markup=url_keyboard(),
        disable_web_page_preview=True,
    )


# ============================================================
# 🎬 DIRECT VIDEO FILE
# ============================================================

async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    job = new_job(uid)

    video = update.message.video

    filename = (
        update.message.caption
        if update.message.caption
        else f"Babadev_Video_{uuid.uuid4().hex[:6]}.mp4"
    )

    filename = safe_name(filename)

    if not filename.lower().endswith(".mp4"):
        filename += ".mp4"

    target = job["dir"] / filename

    await update.message.reply_text(
        "⏳ <b>𝐕𝐢𝐝𝐞𝐨 𝐑𝐞𝐜𝐞𝐢𝐯𝐞𝐝</b>\n\n"
        "📥 Downloading file from Telegram...\n"
        "⚙️ Please wait...",
        parse_mode="HTML",
    )

    try:
        tg_file = await video.get_file()
        await tg_file.download_to_drive(custom_path=str(target))

        job["file"] = target
        job["title"] = target.stem

        await update.message.reply_text(
            "╔════════════════════╗\n"
            "   🎬 𝐕𝐈𝐃𝐄𝐎 𝐑𝐄𝐀𝐃𝐘\n"
            "╚════════════════════╝\n\n"
            f"📁 <b>{target.name}</b>\n"
            f"📦 Size: <b>{target.stat().st_size / 1024 / 1024:.2f} MB</b>\n\n"
            "✨ Choose what you want to do:",
            parse_mode="HTML",
            reply_markup=video_keyboard(),
        )

    except Exception as e:
        log.exception("Video receive failed")
        cleanup_job(uid)

        await update.message.reply_text(
            f"❌ <b>Upload failed</b>\n\n<code>{type(e).__name__}</code>",
            parse_mode="HTML",
        )


# ============================================================
# 📄 VIDEO AS DOCUMENT
# ============================================================

async def receive_document(update: Update, context: ContextTypes.DEFAULT_TYPE):

    document = update.message.document

    if not document:
        return

    mime = document.mime_type or ""

    filename = document.file_name or "video"

    video_extensions = (
        ".mp4",
        ".mkv",
        ".mov",
        ".avi",
        ".webm",
        ".m4v",
        ".3gp",
    )

    if not (
        mime.startswith("video/")
        or filename.lower().endswith(video_extensions)
    ):
        return

    uid = update.effective_user.id

    job = new_job(uid)

    filename = safe_name(filename)

    target = job["dir"] / filename

    await update.message.reply_text(
        "⏳ <b>𝐕𝐢𝐝𝐞𝐨 𝐃𝐨𝐜𝐮𝐦𝐞𝐧𝐭 𝐃𝐞𝐭𝐞𝐜𝐭𝐞𝐝</b>\n\n"
        "📥 Receiving file...\n"
        "⚙️ Processing...",
        parse_mode="HTML",
    )

    try:
        tg_file = await document.get_file()

        await tg_file.download_to_drive(
            custom_path=str(target)
        )

        job["file"] = target
        job["title"] = target.stem

        await update.message.reply_text(
            "✅ <b>𝐕𝐢𝐝𝐞𝐨 𝐑𝐞𝐚𝐝𝐲</b>\n\n"
            f"📁 {target.name}\n"
            f"📦 {target.stat().st_size / 1024 / 1024:.2f} MB\n\n"
            "👇 Select an action:",
            parse_mode="HTML",
            reply_markup=video_keyboard(),
        )

    except Exception as e:
        log.exception("Document receive failed")
        cleanup_job(uid)

        await update.message.reply_text(
            f"❌ Upload failed: <code>{type(e).__name__}</code>",
            parse_mode="HTML",
        )


# ============================================================
# ✏️ RENAME
# ============================================================

async def do_rename(update, context):

    uid = update.effective_user.id
    job = get_job(uid)

    if not job or not job.get("file"):
        return await update.effective_message.reply_text(
            "❌ No video available."
        )

    job["waiting"] = "rename"

    await update.effective_message.reply_text(
        "✏️ <b>𝐑𝐄𝐍𝐀𝐌𝐄 𝐅𝐈𝐋𝐄</b>\n\n"
        "Send the new filename.\n\n"
        "Example:\n"
        "<code>My_New_Video</code>",
        parse_mode="HTML",
    )


# ============================================================
# 📝 CAPTION
# ============================================================

async def do_caption(update, context):

    uid = update.effective_user.id
    job = get_job(uid)

    if not job or not job.get("file"):
        return await update.effective_message.reply_text(
            "❌ No video available."
        )

    job["waiting"] = "caption"

    await update.effective_message.reply_text(
        "📝 <b>𝐂𝐔𝐒𝐓𝐎𝐌 𝐂𝐀𝐏𝐓𝐈𝐎𝐍</b>\n\n"
        "Send the caption you want with the video.",
        parse_mode="HTML",
    )


# ============================================================
# 🖼️ THUMBNAIL
# ============================================================

async def make_thumbnail(update, context):

    uid = update.effective_user.id
    job = get_job(uid)

    if not job or not job.get("file"):
        return await update.effective_message.reply_text(
            "❌ No video available."
        )

    src = job["file"]
    thumb = job["dir"] / "thumbnail.jpg"

    await update.effective_message.reply_text(
        "🖼️ <b>𝐂𝐑𝐄𝐀𝐓𝐈𝐍𝐆 𝐓𝐇𝐔𝐌𝐁𝐍𝐀𝐈𝐋...</b>",
        parse_mode="HTML",
    )

    try:
        run_ffmpeg([
            "-ss",
            "00:00:01",
            "-i",
            str(src),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(thumb),
        ])

        if thumb.stat().st_size > MAX_TELEGRAM_SIZE:
            raise RuntimeError("Thumbnail is too large.")

        with thumb.open("rb") as f:
            await update.effective_message.reply_photo(
                photo=f,
                caption="🖼️ 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐓𝐇𝐔𝐌𝐁𝐍𝐀𝐈𝐋",
            )

    except Exception as e:
        log.exception("Thumbnail failed")

        await update.effective_message.reply_text(
            f"❌ Thumbnail failed: <code>{type(e).__name__}</code>",
            parse_mode="HTML",
        )


# ============================================================
# 🎵 EXTRACT AUDIO
# ============================================================

async def extract_audio(update, context):

    uid = update.effective_user.id
    job = get_job(uid)

    if not job or not job.get("file"):
        return await update.effective_message.reply_text(
            "❌ No video available."
        )

    src = job["file"]
    audio = job["dir"] / f"{src.stem}.mp3"

    await update.effective_message.reply_text(
        "🎵 <b>𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐈𝐍𝐆 𝐀𝐔𝐃𝐈𝐎...</b>\n\n"
        "⏳ Please wait...",
        parse_mode="HTML",
    )

    try:
        run_ffmpeg([
            "-i",
            str(src),
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(audio),
        ])

        if audio.stat().st_size > MAX_TELEGRAM_SIZE:
            return await update.effective_message.reply_text(
                "⚠️ Audio file is larger than Telegram's configured limit."
            )

        with audio.open("rb") as f:
            await update.effective_message.reply_audio(
                audio=InputFile(f, filename=audio.name),
                title=src.stem[:64],
                caption="🎵 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐀𝐔𝐃𝐈𝐎",
            )

    except Exception as e:
        log.exception("Audio extraction failed")

        await update.effective_message.reply_text(
            f"❌ Audio extraction failed: <code>{type(e).__name__}</code>",
            parse_mode="HTML",
        )


# ============================================================
# 📦 COMPRESS
# ============================================================

async def compress_video(update, context):

    uid = update.effective_user.id
    job = get_job(uid)

    if not job or not job.get("file"):
        return await update.effective_message.reply_text(
            "❌ No video available."
        )

    src = job["file"]
    output = job["dir"] / f"{src.stem}_compressed.mp4"

    await update.effective_message.reply_text(
        "📦 <b>𝐂𝐎𝐌𝐏𝐑𝐄𝐒𝐒𝐈𝐍𝐆 𝐕𝐈𝐃𝐄𝐎...</b>\n\n"
        "⚙️ This may take some time.",
        parse_mode="HTML",
    )

    try:
        run_ffmpeg([
            "-i",
            str(src),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output),
        ])

        size = output.stat().st_size

        if size > MAX_TELEGRAM_SIZE:
            return await update.effective_message.reply_text(
                "⚠️ Compressed video is still larger than 49 MB."
            )

        with output.open("rb") as f:
            await update.effective_message.reply_video(
                video=InputFile(f, filename=output.name),
                caption="📦 𝐂𝐎𝐌𝐏𝐑𝐄𝐒𝐒𝐄𝐃 • 🔱 𝐁𝐀𝐁𝐀𝐃𝐄𝐕",
            )

    except Exception as e:
        log.exception("Compression failed")

        await update.effective_message.reply_text(
            f"❌ Compression failed: <code>{type(e).__name__}</code>",
            parse_mode="HTML",
        )


# ============================================================
# ℹ️ VIDEO INFO
# ============================================================

async def video_info(update, context):

    uid = update.effective_user.id
    job = get_job(uid)

    if not job or not job.get("file"):
        return await update.effective_message.reply_text(
            "❌ No video available."
        )

    src = job["file"]

    info = await asyncio.to_thread(
        run_ffprobe,
        src,
    )

    await update.effective_message.reply_text(
        "╔══════════════════════╗\n"
        "   ℹ️ 𝐕𝐈𝐃𝐄𝐎 𝐈𝐍𝐅𝐎\n"
        "╚══════════════════════╝\n\n"
        f"📁 <b>{src.name}</b>\n"
        f"📦 <b>{src.stat().st_size / 1024 / 1024:.2f} MB</b>\n\n"
        f"<pre>{info}</pre>",
        parse_mode="HTML",
    )


# ============================================================
# 💧 WATERMARK
# ============================================================

async def watermark_video(update, context, text="🔱 BABADEV"):

    uid = update.effective_user.id
    job = get_job(uid)

    if not job or not job.get("file"):
        return await update.effective_message.reply_text(
            "❌ No video available."
        )

    src = job["file"]
    output = job["dir"] / f"{src.stem}_watermarked.mp4"

    await update.effective_message.reply_text(
        "💧 <b>𝐀𝐃𝐃𝐈𝐍𝐆 𝐖𝐀𝐓𝐄𝐑𝐌𝐀𝐑𝐊...</b>",
        parse_mode="HTML",
    )

    try:
        # Simple bottom-right watermark.
        vf = (
            "drawtext="
            "text='BABADEV':"
            "x=w-tw-25:"
            "y=h-th-25:"
            "fontsize=28:"
            "fontcolor=white:"
            "borderw=2:"
            "bordercolor=black@0.7"
        )

        run_ffmpeg([
            "-i",
            str(src),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "copy",
            str(output),
        ])

        if output.stat().st_size > MAX_TELEGRAM_SIZE:
            return await update.effective_message.reply_text(
                "⚠️ Watermarked video is larger than 49 MB."
            )

        with output.open("rb") as f:
            await update.effective_message.reply_video(
                video=InputFile(f, filename=output.name),
                caption="💧 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐖𝐀𝐓𝐄𝐑𝐌𝐀𝐑𝐊",
            )

    except Exception as e:
        log.exception("Watermark failed")

        await update.effective_message.reply_text(
            f"❌ Watermark failed: <code>{type(e).__name__}</code>",
            parse_mode="HTML",
        )


# ============================================================
# 🔘 CALLBACKS
# ============================================================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    data = q.data or ""
    uid = q.from_user.id

    await q.answer()

    # ----------------------------
    # Cancel
    # ----------------------------

    if data == "cancel":
        cleanup_job(uid)

        return await q.message.reply_text(
            "❌ <b>𝐉𝐨𝐛 𝐂𝐚𝐧𝐜𝐞𝐥𝐥𝐞𝐝</b>\n\n"
            "Send another video or URL to start again.",
            parse_mode="HTML",
        )

    # ----------------------------
    # More
    # ----------------------------

    if data == "more":
        return await q.message.reply_text(
            "⚙️ <b>𝐌𝐎𝐑𝐄 𝐎𝐏𝐓𝐈𝐎𝐍𝐒</b>\n\n"
            "🎬 Video\n"
            "🎵 Audio\n"
            "🖼️ Thumbnail\n"
            "📦 Download All\n\n"
            "✨ More tools are available for direct video files.",
            parse_mode="HTML",
        )

    # ----------------------------
    # URL
    # ----------------------------

    if data.startswith("url:"):

        job = get_job(uid)

        if not job or not job.get("url"):
            return await q.message.reply_text(
                "❌ URL session expired. Send the URL again."
            )

        mode = data.split(":", 1)[1]

        await q.message.reply_text(
            "⏳ <b>𝐏𝐑𝐄𝐏𝐀𝐑𝐈𝐍𝐆 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃...</b>\n\n"
            "🌐 Please wait...",
            parse_mode="HTML",
        )

        try:

            modes = ["video", "audio", "thumb"] if mode == "all" else [mode]

            for current_mode in modes:

                if job.get("cancel"):
                    return

                file_path, info = await download_url(
                    job["url"],
                    current_mode,
                    job["dir"],
                )

                if current_mode == "thumb":

                    thumb = job["dir"] / "thumbnail.jpg"

                    run_ffmpeg([
                        "-i",
                        str(file_path),
                        "-frames:v",
                        "1",
                        "-q:v",
                        "2",
                        str(thumb),
                    ])

                    with thumb.open("rb") as f:
                        await q.message.reply_photo(
                            photo=f,
                            caption="🖼️ 𝐓𝐇𝐔𝐌𝐁𝐍𝐀𝐈𝐋\n\n🔱 𝐁𝐀𝐁𝐀𝐃𝐄𝐕",
                        )

                    continue

                if file_path.stat().st_size > MAX_TELEGRAM_SIZE:

                    await q.message.reply_text(
                        f"⚠️ <b>{file_path.name}</b>\n\n"
                        "File is larger than 49 MB.\n"
                        "Try a lower-quality/smaller source.",
                        parse_mode="HTML",
                    )

                    continue

                with file_path.open("rb") as f:

                    if current_mode == "audio":

                        await q.message.reply_audio(
                            audio=InputFile(
                                f,
                                filename=file_path.name,
                            ),
                            title=str(
                                info.get("title", "Babadev Audio")
                            )[:64],
                            caption="🎵 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐀𝐔𝐃𝐈𝐎 🔱",
                        )

                    else:

                        await q.message.reply_video(
                            video=InputFile(
                                f,
                                filename=file_path.name,
                            ),
                            caption="🎬 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐌𝐄𝐃𝐈𝐀 🔱",
                            supports_streaming=True,
                        )

            await q.message.reply_text(
                "✅ <b>𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄</b>\n\n"
                "🔱 𝐉𝐀𝐈 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 🔱",
                parse_mode="HTML",
            )

        except Exception as e:

            log.exception("URL download failed")

            await q.message.reply_text(
                "❌ <b>Download failed</b>\n\n"
                f"<code>{type(e).__name__}</code>\n\n"
                "Try another public URL.",
                parse_mode="HTML",
            )

        return

    # ----------------------------
    # Video Tools
    # ----------------------------

    if data.startswith("video:"):

        action = data.split(":", 1)[1]

        if action == "rename":
            return await do_rename(update, context)

        if action == "caption":
            return await do_caption(update, context)

        if action == "thumb":
            return await make_thumbnail(update, context)

        if action == "audio":
            return await extract_audio(update, context)

        if action == "compress":
            return await compress_video(update, context)

        if action == "info":
            return await video_info(update, context)

        if action == "watermark":
            return await q.message.reply_text(
                "💧 <b>𝐖𝐀𝐓𝐄𝐑𝐌𝐀𝐑𝐊</b>\n\n"
                "Choose watermark:",
                parse_mode="HTML",
                reply_markup=watermark_keyboard(),
            )

    # ----------------------------
    # Watermark
    # ----------------------------

    if data.startswith("watermark:"):

        mode = data.split(":", 1)[1]

        if mode == "babadev":
            return await watermark_video(
                update,
                context,
                "🔱 BABADEV",
            )

        if mode == "custom":

            job = get_job(uid)

            if not job:
                return await q.message.reply_text(
                    "❌ No active video."
                )

            job["waiting"] = "watermark"

            return await q.message.reply_text(
                "✍️ <b>𝘾𝙐𝙎𝙏𝙊𝙈 𝙒𝘼𝙏𝙀𝙍𝙈𝘼𝙍𝙆</b>\n\n"
                "Send the watermark text.",
                parse_mode="HTML",
            )

    # ----------------------------
    # Admin
    # ----------------------------

    if data.startswith("admin:"):

        if uid not in ADMIN_IDS:
            return await q.message.reply_text(
                "⛔ 𝐀𝐃𝐌𝐈𝐍 𝐎𝐍𝐋𝐘"
            )

        action = data.split(":", 1)[1]

        if action == "stats":

            return await q.message.reply_text(
                "📊 <b>𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐒</b>\n\n"
                f"⚡ Active jobs: <b>{len(jobs)}</b>\n"
                f"🖥️ FFmpeg: <b>{'YES' if shutil.which('ffmpeg') else 'NO'}</b>\n"
                f"📥 yt-dlp: <b>{'YES' if yt_dlp else 'NO'}</b>",
                parse_mode="HTML",
            )

        if action == "jobs":

            if not jobs:
                return await q.message.reply_text(
                    "👥 No active jobs."
                )

            text = "👥 <b>𝐀𝐂𝐓𝐈𝐕𝐄 𝐉𝐎𝐁𝐒</b>\n\n"

            for user_id, job in jobs.items():
                text += f"• <code>{user_id}</code> — {job.get('title')}\n"

            return await q.message.reply_text(
                text,
                parse_mode="HTML",
            )


# ============================================================
# 💬 TEXT INPUT AFTER BUTTON
# ============================================================

async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id
    job = get_job(uid)

    if not job:
        return await url_message(update, context)

    waiting = job.get("waiting")

    if waiting == "rename":

        new_name = safe_name(update.message.text)

        old_file = job["file"]

        extension = old_file.suffix

        if not new_name.lower().endswith(extension.lower()):
            new_name += extension

        new_file = old_file.parent / new_name

        old_file.rename(new_file)

        job["file"] = new_file
        job["title"] = new_file.stem
        job["waiting"] = None

        await update.message.reply_text(
            "✅ <b>𝐑𝐄𝐍𝐀𝐌𝐄𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘</b>\n\n"
            f"📁 <code>{new_file.name}</code>",
            parse_mode="HTML",
            reply_markup=video_keyboard(),
        )

        return

    if waiting == "caption":

        job["caption"] = update.message.text
        job["waiting"] = None

        await update.message.reply_text(
            "✅ <b>𝐂𝐀𝐏𝐓𝐈𝐎𝐍 𝐒𝐀𝐕𝐄𝐃</b>\n\n"
            f"📝 {job['caption']}",
            parse_mode="HTML",
            reply_markup=video_keyboard(),
        )

        return

    if waiting == "watermark":

        text = update.message.text.strip()[:80]

        job["waiting"] = None

        await watermark_video(
            update,
            context,
            text,
        )

        return

    # Otherwise treat as URL.
    return await url_message(update, context)


# ============================================================
# 🧠 ERROR HANDLER
# ============================================================

async def error_handler(update, context):

    log.exception(
        "Unhandled exception",
        exc_info=context.error,
    )


# ============================================================
# 🚀 MAIN
# ============================================================

def main():

    if not BOT_TOKEN or "PUT_YOUR" in BOT_TOKEN:

        raise SystemExit(
            "BOT_TOKEN is missing. Configure it in config.py/.env."
        )

    if not shutil.which("ffmpeg"):
        log.warning("FFmpeg is not installed.")

    if yt_dlp is None:
        log.warning("yt-dlp Python module is not installed.")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_cmd)
    )

    app.add_handler(
        CommandHandler("status", status)
    )

    app.add_handler(
        CommandHandler("admin", admin)
    )

    # Callback buttons
    app.add_handler(
        CallbackQueryHandler(callbacks)
    )

    # Direct Telegram video
    app.add_handler(
        MessageHandler(
            filters.VIDEO,
            receive_video,
        )
    )

    # Video sent as document
    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            receive_document,
        )
    )

    # Text / URLs
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_input,
        )
    )

    app.add_error_handler(error_handler)

    print(
        "========================================\n"
        "🔱 BABADEV MEDIA HUB\n"
        "========================================\n"
        "🎬 Video File Handler : ENABLED\n"
        "🔗 URL Downloader     : ENABLED\n"
        "🖼️ Thumbnail          : ENABLED\n"
        "🎵 Audio Extractor    : ENABLED\n"
        "📦 Compressor         : ENABLED\n"
        "💧 Watermark          : ENABLED\n"
        "✏️ Rename             : ENABLED\n"
        "📝 Caption            : ENABLED\n"
        "========================================\n"
        "🚀 Bot is running...\n"
        "========================================"
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
