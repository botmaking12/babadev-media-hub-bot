import logging
from telegram import Update
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ContextTypes,filters
from config import BOT_TOKEN,BRAND_STYLE,ADMIN_IDS
from downloader import extract_url,platform_name,download,cleanup
from ui import start_text,media_keyboard
logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(message)s')
log=logging.getLogger('babadev'); jobs={}
async def start(update,context): await update.message.reply_text(start_text(BRAND_STYLE),disable_web_page_preview=True)
async def help_cmd(update,context): await update.message.reply_text('🔱 Babadev Media Hub\n\nSend a public YouTube, Instagram or Facebook URL.\n\n🎬 Video • 🎵 Music • 🖼️ Thumbnail • 📦 Download All\n\nUse only content you are allowed to download.')
async def status(update,context): await update.message.reply_text('🟢 Babadev Media Hub is online.\nSend a public media URL to begin.')
async def admin(update,context):
 if update.effective_user.id in ADMIN_IDS: await update.message.reply_text(f'🔐 Active jobs: {len(jobs)}')
async def url_msg(update,context):
 url=extract_url(update.message.text)
 if not url: return await update.message.reply_text('🔗 Please send a valid http/https media URL.')
 jobs[update.effective_user.id]={'url':url,'cancel':False}
 await update.message.reply_text(f'🔗 Link Detected\n\n🌐 Platform: {platform_name(url)}\n\nChoose what you want:',reply_markup=media_keyboard(BRAND_STYLE),disable_web_page_preview=True)
async def callbacks(update,context):
 q=update.callback_query; data=q.data or ''; uid=q.from_user.id
 if data=='cancel': jobs.get(uid,{}).update(cancel=True); await q.answer('Cancelled.'); return await q.message.reply_text('❌ Current download cancelled.')
 if data=='more': await q.answer(); return await q.message.reply_text('⚙️ More Options\n\nQuality selector • History • Favorites • Language • Settings')
 if not data.startswith('media:'): return
 state=jobs.get(uid)
 if not state: return await q.answer('Send a link first.',show_alert=True)
 await q.answer(); mode=data.split(':',1)[1]
 try:
  modes=['video','audio','thumb'] if mode=='all' else [mode]
  await q.message.reply_text('⏳ Preparing download...')
  for m in modes:
   if jobs.get(uid,{}).get('cancel'): return
   jid,info,files=await download(state['url'],m); title=info.get('title') or 'Babadev Media'
   for f in files:
    if f.stat().st_size>49*1024*1024:
     await q.message.reply_text(f'⚠️ {f.name} is larger than 49 MB. Try a smaller quality.'); continue
    with f.open('rb') as fh:
     if m=='audio' or f.suffix.lower() in ('.mp3','.m4a','.opus','.wav'): await q.message.reply_audio(fh,title=title[:64],caption='🎵 '+title+'\n\n🔱 Jai Babadev')
     elif m in ('thumb','image') or f.suffix.lower() in ('.jpg','.jpeg','.png','.webp'): await q.message.reply_photo(fh,caption='🖼️ '+title+'\n\n🔱 Jai Babadev')
     else: await q.message.reply_document(fh,caption='🎬 '+title+'\n\n🔱 Jai Babadev')
   cleanup(jid)
  await q.message.reply_text('✅ Download complete!\n\n🔱 𝐉𝐀𝐈 𝐁𝐀𝐁𝐀𝐃𝐄𝐕 🔱')
 except Exception as e:
  log.exception('download failed'); await q.message.reply_text(f'❌ Download failed: {type(e).__name__}\n\nTry another public URL.')
def main():
 if not BOT_TOKEN or 'PUT_YOUR' in BOT_TOKEN: raise SystemExit('BOT_TOKEN is missing. Put your real BotFather token in .env')
 app=Application.builder().token(BOT_TOKEN).build()
 app.add_handler(CommandHandler('start',start)); app.add_handler(CommandHandler('help',help_cmd)); app.add_handler(CommandHandler('status',status)); app.add_handler(CommandHandler('admin',admin)); app.add_handler(CallbackQueryHandler(callbacks)); app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,url_msg))
 print('================================\n🔱 BABADEV MEDIA HUB\n================================\nBot is running...\n================================')
 app.run_polling(allowed_updates=Update.ALL_TYPES)
if __name__=='__main__': main()
