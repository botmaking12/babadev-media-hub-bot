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

try:
    from google import genai
except ImportError:
    genai = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ai_sessions = {}


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
# 🎨 PREMIUM BRANDING / UI
# ============================================================

def title_text():
    return (
        "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "      🔱 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 🔱\n"
        "      𝐌𝐄𝐃𝐈𝐀 𝐇𝐔𝐁 𝐏𝐑𝐎\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "✨ 𝙈𝙚𝙙𝙞𝙖 • 𝘼𝙄 • 𝘾𝙧𝙚𝙖𝙩𝙤𝙧 𝙏𝙤𝙤𝙡𝙨 ✨"
    )


def help_text():
    return (
        "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "       🔱 𝐇𝐄𝐋𝐏 𝐂𝐄𝐍𝐓𝐄𝐑\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "🎬 <b>MEDIA</b>\n"
        "• Send a video directly\n"
        "• Send a video as document\n"
        "• Send a public media URL\n\n"
        "🛠️ <b>VIDEO TOOLS</b>\n"
        "✏️ Rename  •  📝 Caption\n"
        "🖼️ Thumbnail  •  🎵 Audio\n"
        "📦 Compress  •  ℹ️ Info\n"
        "💧 Watermark\n\n"
        "🤖 <b>AI STUDIO</b>\n"
        "Captions • Titles • SEO • Scripts\n"
        "Hooks • Hashtags • Ideas • CTA\n"
        "Translation • Rewrite • Summary\n"
        "Prompt Enhancement • AI Prompts\n\n"
        "⚠️ Use only media you have permission to process/download."
    )


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 𝐀𝐈 𝐒𝐓𝐔𝐃𝐈𝐎", callback_data="ai:home")],
        [
            InlineKeyboardButton("🎬 𝐕𝐈𝐃𝐄𝐎", callback_data="menu:video"),
            InlineKeyboardButton("🔗 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃", callback_data="menu:url"),
        ],
        [
            InlineKeyboardButton("🛠️ 𝐓𝐎𝐎𝐋𝐒", callback_data="menu:tools"),
            InlineKeyboardButton("ℹ️ 𝐇𝐄𝐋𝐏", callback_data="menu:help"),
        ],
    ])


def url_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 𝐕𝐈𝐃𝐄𝐎", callback_data="url:video"),
            InlineKeyboardButton("🎵 𝐀𝐔𝐃𝐈𝐎", callback_data="url:audio"),
        ],
        [
            InlineKeyboardButton("🖼️ 𝐓𝐇𝐔𝐌𝐁", callback_data="url:thumb"),
            InlineKeyboardButton("📦 𝐀𝐋𝐋", callback_data="url:all"),
        ],
        [
            InlineKeyboardButton("⚙️ 𝐌𝐎𝐑𝐄", callback_data="more"),
            InlineKeyboardButton("❌ 𝐂𝐀𝐍𝐂𝐄𝐋", callback_data="cancel"),
        ],
    ])


def video_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ 𝐑𝐄𝐍𝐀𝐌𝐄", callback_data="video:rename"),
            InlineKeyboardButton("📝 𝐂𝐀𝐏𝐓𝐈𝐎𝐍", callback_data="video:caption"),
        ],
        [
            InlineKeyboardButton("🖼️ 𝐓𝐇𝐔𝐌𝐁", callback_data="video:thumb"),
            InlineKeyboardButton("🎵 𝐀𝐔𝐃𝐈𝐎", callback_data="video:audio"),
        ],
        [
            InlineKeyboardButton("📦 𝐂𝐎𝐌𝐏𝐑𝐄𝐒𝐒", callback_data="video:compress"),
            InlineKeyboardButton("ℹ️ 𝐈𝐍𝐅𝐎", callback_data="video:info"),
        ],
        [InlineKeyboardButton("💧 𝐖𝐀𝐓𝐄𝐑𝐌𝐀𝐑𝐊", callback_data="video:watermark")],
        [
            InlineKeyboardButton("🤖 𝐀𝐈 𝐒𝐓𝐔𝐃𝐈𝐎", callback_data="ai:home"),
            InlineKeyboardButton("❌ 𝐂𝐀𝐍𝐂𝐄𝐋", callback_data="cancel"),
        ],
    ])


def watermark_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔱 𝐁𝐀𝐁𝐀𝐃𝐄𝐕", callback_data="watermark:babadev")],
        [InlineKeyboardButton("✍️ 𝐂𝐔𝐒𝐓𝐎𝐌", callback_data="watermark:custom")],
        [InlineKeyboardButton("❌ 𝐂𝐀𝐍𝐂𝐄𝐋", callback_data="cancel")],
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 𝐒𝐓𝐀𝐓𝐒", callback_data="admin:stats"),
            InlineKeyboardButton("👥 𝐉𝐎𝐁𝐒", callback_data="admin:jobs"),
        ],
    ])


# ============================================================
# 🤖 AI STUDIO UI
# ============================================================

AI_TOOLS = {
    "caption": "✍️ 𝐂𝐀𝐏𝐓𝐈𝐎𝐍",
    "title": "🎬 𝐓𝐈𝐓𝐋𝐄",
    "description": "📝 𝐃𝐄𝐒𝐂𝐑𝐈𝐏𝐓𝐈𝐎𝐍",
    "hashtags": "#️⃣ 𝐇𝐀𝐒𝐇𝐓𝐀𝐆𝐒",
    "hook": "🎯 𝐇𝐎𝐎𝐊",
    "script": "🎥 𝐒𝐂𝐑𝐈𝐏𝐓",
    "seo": "📈 𝐒𝐄𝐎",
    "ideas": "💡 𝐈𝐃𝐄𝐀𝐒",
    "cta": "🚀 𝐂𝐓𝐀",
    "enhance": "🪄 𝐄𝐍𝐇𝐀𝐍𝐂𝐄 𝐏𝐀𝐑𝐀𝐌",
    "rewrite": "✏️ 𝐑𝐄𝐖𝐑𝐈𝐓𝐄",
    "translate": "🌐 𝐓𝐑𝐀𝐍𝐒𝐋𝐀𝐓𝐄",
    "summarize": "📌 𝐒𝐔𝐌𝐌𝐀𝐑𝐘",
    "grammar": "📝 𝐆𝐑𝐀𝐌𝐌𝐀𝐑",
    "thumbnail": "🖼️ 𝐓𝐇𝐔𝐌𝐁 𝐏𝐑𝐎𝐌𝐏𝐓",
    "videoprompt": "🎞️ 𝐕𝐈𝐃𝐄𝐎 𝐏𝐑𝐎𝐌𝐏𝐓",
}


def ai_home_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ 𝐂𝐀𝐏𝐓𝐈𝐎𝐍", callback_data="ai:tool:caption"),
            InlineKeyboardButton("🎬 𝐓𝐈𝐓𝐋𝐄", callback_data="ai:tool:title"),
        ],
        [
            InlineKeyboardButton("📝 𝐃𝐄𝐒𝐂", callback_data="ai:tool:description"),
            InlineKeyboardButton("#️⃣ 𝐓𝐀𝐆𝐒", callback_data="ai:tool:hashtags"),
        ],
        [
            InlineKeyboardButton("🎯 𝐇𝐎𝐎𝐊", callback_data="ai:tool:hook"),
            InlineKeyboardButton("🚀 𝐂𝐓𝐀", callback_data="ai:tool:cta"),
        ],
        [
            InlineKeyboardButton("🎥 𝐒𝐂𝐑𝐈𝐏𝐓", callback_data="ai:tool:script"),
            InlineKeyboardButton("💡 𝐈𝐃𝐄𝐀𝐒", callback_data="ai:tool:ideas"),
        ],
        [
            InlineKeyboardButton("📈 𝐒𝐄𝐎", callback_data="ai:tool:seo"),
            InlineKeyboardButton("🪄 𝐄𝐍𝐇𝐀𝐍𝐂𝐄", callback_data="ai:tool:enhance"),
        ],
        [
            InlineKeyboardButton("✏️ 𝐑𝐄𝐖𝐑𝐈𝐓𝐄", callback_data="ai:tool:rewrite"),
            InlineKeyboardButton("🌐 𝐓𝐑𝐀𝐍𝐒𝐋𝐀𝐓𝐄", callback_data="ai:tool:translate"),
        ],
        [
            InlineKeyboardButton("📌 𝐒𝐔𝐌𝐌𝐀𝐑𝐘", callback_data="ai:tool:summarize"),
            InlineKeyboardButton("📝 𝐆𝐑𝐀𝐌𝐌𝐀𝐑", callback_data="ai:tool:grammar"),
        ],
        [
            InlineKeyboardButton("🖼️ 𝐓𝐇𝐔𝐌𝐁 𝐏𝐑𝐎𝐌𝐏𝐓", callback_data="ai:tool:thumbnail"),
            InlineKeyboardButton("🎞️ 𝐕𝐈𝐃𝐄𝐎 𝐏𝐑𝐎𝐌𝐏𝐓", callback_data="ai:tool:videoprompt"),
        ],
        [
            InlineKeyboardButton("🌐 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄", callback_data="ai:language"),
            InlineKeyboardButton("🎨 𝐒𝐓𝐘𝐋𝐄", callback_data="ai:style"),
        ],
        [InlineKeyboardButton("❌ 𝐂𝐋𝐎𝐒𝐄", callback_data="ai:close")],
    ])


def language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇸 English", callback_data="ai:lang:English"),
            InlineKeyboardButton("🇮🇳 Hindi", callback_data="ai:lang:Hindi"),
        ],
        [
            InlineKeyboardButton("🇮🇳 Gujarati", callback_data="ai:lang:Gujarati"),
            InlineKeyboardButton("🇮🇳 Hinglish", callback_data="ai:lang:Hinglish"),
        ],
        [
            InlineKeyboardButton("🇮🇳 Marathi", callback_data="ai:lang:Marathi"),
            InlineKeyboardButton("🇮🇳 Bengali", callback_data="ai:lang:Bengali"),
        ],
        [InlineKeyboardButton("⬅️ 𝐁𝐀𝐂𝐊", callback_data="ai:home")],
    ])


def style_keyboard():
    styles = [
        ("🔥 Viral", "Viral"), ("💎 Premium", "Premium"),
        ("🎬 Cinematic", "Cinematic"), ("❤️ Emotional", "Emotional"),
        ("😂 Funny", "Funny"), ("📈 SEO", "SEO"),
        ("📖 Storytelling", "Storytelling"), ("👔 Professional", "Professional"),
    ]
    rows = []
    for i in range(0, len(styles), 2):
        rows.append([
            InlineKeyboardButton(styles[i][0], callback_data=f"ai:style:{styles[i][1]}"),
            InlineKeyboardButton(styles[i+1][0], callback_data=f"ai:style:{styles[i+1][1]}"),
        ])
    rows.append([InlineKeyboardButton("⬅️ 𝐁𝐀𝐂𝐊", callback_data="ai:home")])
    return InlineKeyboardMarkup(rows)


def ai_result_keyboard(kind):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 𝐑𝐄𝐆𝐄𝐍𝐄𝐑𝐀𝐓𝐄", callback_data=f"ai:regen:{kind}"),
            InlineKeyboardButton("✏️ 𝐍𝐄𝐖", callback_data=f"ai:new:{kind}"),
        ],
        [InlineKeyboardButton("⬅️ 𝐀𝐈 𝐇𝐎𝐌𝐄", callback_data="ai:home")],
    ])


AI_INSTRUCTIONS = {
    "caption": "Create 5 engaging social-media captions.",
    "title": "Create 10 strong, accurate titles with curiosity but no misleading clickbait.",
    "description": "Write a polished video/social description with useful context, keywords and a natural CTA.",
    "hashtags": "Generate relevant broad + niche hashtags. Avoid spam and irrelevant tags.",
    "hook": "Create 15 concise scroll-stopping hooks.",
    "script": "Create a short-form script with Hook, Visual/Scene, Voiceover and CTA.",
    "seo": "Create an SEO package: primary keyword, secondary keywords, 10 titles, description and tags.",
    "ideas": "Generate 20 original content ideas with a short hook for each.",
    "cta": "Generate 15 natural calls-to-action suitable for the topic.",
    "enhance": "Turn the user's prompt into a detailed, structured, production-ready AI prompt without changing intent.",
    "rewrite": "Rewrite the text professionally while preserving meaning and tone.",
    "translate": "Translate the text into the selected language while preserving meaning and formatting.",
    "summarize": "Summarize the text into concise, useful bullet points without inventing facts.",
    "grammar": "Fix grammar, spelling and clarity while preserving meaning.",
    "thumbnail": "Create 5 detailed image-generation prompts for a premium thumbnail, including subject, composition, lighting, camera, mood and text placement.",
    "videoprompt": "Create 5 detailed video-generation prompts including scene, movement, camera, lighting, mood, environment, realism/style and duration guidance.",
}


async def gemini_generate(prompt):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    if genai is None:
        raise RuntimeError("google-genai is not installed.")
    client = genai.Client(api_key=GEMINI_API_KEY)

    def task():
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text.strip()

    return await asyncio.to_thread(task)


def ai_prompt(kind, user_input, language, style):
    return f"""You are Babadev Media Hub's premium creator assistant.
Be accurate, practical and original. Never invent factual claims.
Task: {AI_INSTRUCTIONS[kind]}

Target language: {language}
Writing style: {style}

User topic/text:
{user_input}
"""


async def ai_run(uid, message):
    session = ai_sessions.get(uid, {})
    kind = session.get("tool")
    user_input = session.get("input")

    if not kind or not user_input:
        return await message.reply_text("⚠️ Select an AI tool and send your input first.")

    await message.reply_text(
        f"⏳ <b>{AI_TOOLS.get(kind, '🤖 AI')}</b>\n\n"
        "🧠 Generating premium result...",
        parse_mode="HTML",
    )

    try:
        language = session.get("language", "English")
        style = session.get("style", "Viral")
        result = await gemini_generate(
            ai_prompt(kind, user_input, language, style)
        )

        footer = (
            "\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 {language}  •  🎨 {style}\n"
            "🔱 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 𝐀𝐈"
        )

        text = f"{AI_TOOLS.get(kind, '🤖 AI')}\n\n{result}{footer}"
        chunks = [text[i:i+3900] for i in range(0, len(text), 3900)]

        for index, chunk in enumerate(chunks):
            await message.reply_text(
                chunk,
                parse_mode="HTML" if index == 0 else None,
                reply_markup=ai_result_keyboard(kind) if index == len(chunks)-1 else None,
            )
    except Exception as e:
        log.exception("AI generation failed")
        await message.reply_text(
            "❌ <b>AI generation failed</b>\n\n"
            f"<code>{type(e).__name__}</code>\n\n"
            "Check GEMINI_API_KEY and google-genai installation.",
            parse_mode="HTML",
        )


# ============================================================
# 🧹 FILE HELPERS
# ============================================================

def safe_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\-. ()\[\]]+", "_", name, flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name)
    return name[:180] or "Babadev_Media"


def new_job(uid: int):
    cleanup_job(uid)
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
        "🔗 <b>Or send a media URL</b>\n"
        "🤖 <b>Or open AI Studio</b>\n\n"
        "✨ 𝐑𝐄𝐀𝐃𝐘 𝐓𝐎 𝐂𝐑𝐄𝐀𝐓𝐄 ✨",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
        disable_web_page_preview=True,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        help_text(),
        parse_mode="HTML",
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "     🟢 𝐒𝐘𝐒𝐓𝐄𝐌 𝐒𝐓𝐀𝐓𝐔𝐒\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "⚡ Bot: <b>ONLINE</b>\n"
        f"📊 Active Jobs: <b>{len(jobs)}</b>\n"
        f"🎬 FFmpeg: <b>{'READY' if shutil.which('ffmpeg') else 'MISSING'}</b>\n"
        f"📥 yt-dlp: <b>{'READY' if yt_dlp else 'MISSING'}</b>\n"
        f"🤖 Gemini: <b>{'READY' if GEMINI_API_KEY and genai else 'NOT CONFIGURED'}</b>",
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
        else f"Babadev_
