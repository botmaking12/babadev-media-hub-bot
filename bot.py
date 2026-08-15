import logging
from pathlib import Path

from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import BOT_TOKEN, BRAND_STYLE, ADMIN_IDS
from downloader import extract_url, platform_name, download, cleanup
from ui import start_text, media_keyboard, custom_keyboard


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

log = logging.getLogger('babadev')

jobs = {}


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        start_text(BRAND_STYLE),
        disable_web_page_preview=True
    )


# =========================
# HELP
# =========================

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🔱 Babadev Media Hub\n\n'
        'Send a public YouTube, Instagram or Facebook URL.\n\n'
        '🎬 Video • 🎵 Music • 🖼️ Thumbnail • 📦 Download All\n\n'
        '📝 Custom Caption\n'
        '✏️ Rename File\n\n'
        'Use only content you are allowed to download.'
    )


# =========================
# STATUS
# =========================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🟢 Babadev Media Hub is online.\n'
        'Send a public media URL to begin.'
    )


# =========================
# ADMIN
# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in ADMIN_IDS:
        await update.message.reply_text(
            f'🔐 Active jobs: {len(jobs)}'
        )


# =========================
# URL MESSAGE
# =========================

async def url_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id
    text = update.message.text or ''

    # If user is entering custom data
    state = jobs.get(uid)

    if state and state.get('waiting_for'):

        waiting = state.get('waiting_for')

        # ---------- CUSTOM CAPTION ----------
        if waiting == 'caption':

            caption = text.strip()

            if not caption:
                return await update.message.reply_text(
                    '❌ Caption cannot be empty.\n\n'
                    'Please send your caption again.'
                )

            state['custom_caption'] = caption
            state['waiting_for'] = None

            await update.message.reply_text(
                '✅ Custom caption saved.\n\n'
                'Your custom caption will be added above the default '
                'Babadev caption.',
                reply_markup=custom_keyboard()
            )

            return

        # ---------- RENAME ----------
        if waiting == 'rename':

            filename = text.strip()

            if not filename:
                return await update.message.reply_text(
                    '❌ Filename cannot be empty.'
                )

            # Remove unsafe path characters
            filename = Path(filename).name

            # Remove extension if user entered one.
            # Original extension will be preserved.
            if '.' in filename:
                filename = filename.rsplit('.', 1)[0]

            if not filename:
                return await update.message.reply_text(
                    '❌ Invalid filename.'
                )

            state['custom_filename'] = filename
            state['waiting_for'] = None

            await update.message.reply_text(
                f'✅ Filename saved:\n\n'
                f'📄 `{filename}`\n\n'
                f'Original file extension will be preserved.',
                parse_mode='Markdown',
                reply_markup=custom_keyboard()
            )

            return

    # ---------- NORMAL URL ----------
    url = extract_url(text)

    if not url:
        return await update.message.reply_text(
            '🔗 Please send a valid http/https media URL.'
        )

    jobs[uid] = {
        'url': url,
        'cancel': False,
        'custom_caption': None,
        'custom_filename': None,
        'waiting_for': None
    }

    await update.message.reply_text(
        f'🔗 Link Detected\n\n'
        f'🌐 Platform: {platform_name(url)}\n\n'
        f'Choose what you want:',
        reply_markup=media_keyboard(BRAND_STYLE),
        disable_web_page_preview=True
    )


# =========================
# BUILD CAPTION
# =========================

def build_caption(
    mode,
    title,
    custom_caption=None
):
    if mode == 'audio':
        default_caption = (
            f'🎵 {title}\n\n'
            f'🔱 Jai Babadev'
        )

    elif mode in ('thumb', 'image'):
        default_caption = (
            f'🖼️ {title}\n\n'
            f'🔱 Jai Babadev'
        )

    else:
        default_caption = (
            f'🎬 {title}\n\n'
            f'🔱 Jai Babadev'
        )

    if custom_caption:
        final_caption = (
            f'{custom_caption}\n\n'
            f'{default_caption}'
        )
    else:
        final_caption = default_caption

    # Telegram caption limit
    return final_caption[:1024]


# =========================
# CALLBACKS
# =========================

async def callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    q = update.callback_query
    data = q.data or ''
    uid = q.from_user.id

    # =====================
    # CANCEL
    # =====================

    if data == 'cancel':

        if uid in jobs:
            jobs[uid]['cancel'] = True
            jobs[uid]['waiting_for'] = None

        await q.answer('Cancelled.')

        return await q.message.reply_text(
            '❌ Current operation cancelled.'
        )

    # =====================
    # MORE
    # =====================

    if data == 'more':

        await q.answer()

        return await q.message.reply_text(
            '⚙️ More Options\n\n'
            '• Quality selector\n'
            '• History\n'
            '• Favorites\n'
            '• Language\n'
            '• Settings'
        )

    # =====================
    # CUSTOM CAPTION
    # =====================

    if data == 'custom:caption':

        state = jobs.get(uid)

        if not state:
            return await q.answer(
                'Send a link first.',
                show_alert=True
            )

        state['waiting_for'] = 'caption'

        await q.answer()

        return await q.message.reply_text(
            '📝 **Custom Caption**\n\n'
            'Ab jo caption aap video ke saath chahte ho '
            'wo message me send karo.\n\n'
            'Example:\n'
            '🔥 New Video\n'
            '❤️ Follow for more updates',
            parse_mode='Markdown'
        )

    # =====================
    # RENAME
    # =====================

    if data == 'custom:rename':

        state = jobs.get(uid)

        if not state:
            return await q.answer(
                'Send a link first.',
                show_alert=True
            )

        state['waiting_for'] = 'rename'

        await q.answer()

        return await q.message.reply_text(
            '✏️ **Rename File**\n\n'
            'New filename send karo.\n\n'
            'Example:\n'
            '`Babadev_Video_01`\n\n'
            'Extension automatically preserve hogi.',
            parse_mode='Markdown'
        )

    # =====================
    # RESET CUSTOM OPTIONS
    # =====================

    if data == 'custom:reset':

        state = jobs.get(uid)

        if state:
            state['custom_caption'] = None
            state['custom_filename'] = None
            state['waiting_for'] = None

        await q.answer('Reset complete.')

        return await q.message.reply_text(
            '🔄 Custom caption and filename reset.',
            reply_markup=media_keyboard(BRAND_STYLE)
        )

    # =====================
    # MEDIA
    # =====================

    if not data.startswith('media:'):
        return

    state = jobs.get(uid)

    if not state:
        return await q.answer(
            'Send a link first.',
            show_alert=True
        )

    await q.answer()

    mode = data.split(':', 1)[1]

    try:

        modes = (
            ['video', 'audio', 'thumb']
            if mode == 'all'
            else [mode]
        )

        await q.message.reply_text(
            '⏳ Preparing download...'
        )

        for m in modes:

            if jobs.get(uid, {}).get('cancel'):
                return

            jid, info, files = await download(
                state['url'],
                m
            )

            title = info.get('title') or 'Babadev Media'

            custom_caption = state.get(
                'custom_caption'
            )

            custom_filename = state.get(
                'custom_filename'
            )

            for f in files:

                if f.stat().st_size > 49 * 1024 * 1024:

                    await q.message.reply_text(
                        f'⚠️ {f.name} is larger than 49 MB.\n'
                        f'Try a smaller quality.'
                    )

                    continue

                suffix = f.suffix.lower()

                caption = build_caption(
                    m,
                    title,
                    custom_caption
                )

                # =====================
                # AUDIO
                # =====================

                if (
                    m == 'audio'
                    or suffix in (
                        '.mp3',
                        '.m4a',
                        '.opus',
                        '.wav'
                    )
                ):

                    with f.open('rb') as fh:

                        audio_filename = (
                            custom_filename
                            + suffix
                            if custom_filename
                            else f.name
                        )

                        audio_file = InputFile(
                            fh,
                            filename=audio_filename
                        )

                        await q.message.reply_audio(
                            audio_file,
                            title=title[:64],
                            caption=caption
                        )

                # =====================
                # IMAGE
                # =====================

                elif (
                    m in ('thumb', 'image')
                    or suffix in (
                        '.jpg',
                        '.jpeg',
                        '.png',
                        '.webp'
                    )
                ):

                    with f.open('rb') as fh:

                        await q.message.reply_photo(
                            fh,
                            caption=caption
                        )

                # =====================
                # VIDEO / DOCUMENT
                # =====================

                else:

                    with f.open('rb') as fh:

                        document_filename = (
                            custom_filename
                            + suffix
                            if custom_filename
                            else f.name
                        )

                        document_file = InputFile(
                            fh,
                            filename=document_filename
                        )

                        await q.message.reply_document(
                            document_file,
                            caption=caption
                        )

                # Cleanup
                cleanup(jid)

        await q.message.reply_text(
            '✅ Download complete!\n\n'
            '🔱 𝐉𝐀𝐈 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 🔱'
        )

        # Keep custom settings for current job,
        # but reset cancellation/waiting state.
        state['cancel'] = False
        state['waiting_for'] = None

    except Exception as e:

        log.exception('download failed')

        await q.message.reply_text(
            f'❌ Download failed: '
            f'{type(e).__name__}\n\n'
            f'Try another public URL.'
        )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN or 'PUT_YOUR' in BOT_TOKEN:

        raise SystemExit(
            'BOT_TOKEN is missing. '
            'Put your real BotFather token in .env'
        )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler('start', start)
    )

    app.add_handler(
        CommandHandler('help', help_cmd)
    )

    app.add_handler(
        CommandHandler('status', status)
    )

    app.add_handler(
        CommandHandler('admin', admin)
    )

    app.add_handler(
        CallbackQueryHandler(callbacks)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            url_msg
        )
    )

    print(
        '================================\n'
        '🔱 BABADEV MEDIA HUB\n'
        '================================\n'
        'Bot is running...\n'
        '================================'
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == '__main__':
    main()
