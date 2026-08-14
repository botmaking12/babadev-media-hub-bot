import asyncio,re,shutil,uuid
from pathlib import Path
import yt_dlp
from config import TMP_DIR
URL_RE=re.compile(r'https?://\S+')
def extract_url(text):
 m=URL_RE.search(text or '')
 return m.group(0).rstrip(').,]}>') if m else None
def platform_name(url):
 u=url.lower()
 if 'youtube.com' in u or 'youtu.be' in u:return 'YouTube'
 if 'instagram.com' in u:return 'Instagram'
 if 'facebook.com' in u or 'fb.watch' in u:return 'Facebook'
 return 'Supported/Unknown'
def _download(url,mode,job_dir):
 job_dir.mkdir(parents=True,exist_ok=True)
 opts={'outtmpl':str(job_dir/'%(title).100B [%(id)s].%(ext)s'),'noplaylist':True,'quiet':True,'no_warnings':True,'restrictfilenames':True}
 if mode=='audio': opts.update(format='bestaudio/best',postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}])
 elif mode in ('thumb','image'): opts.update(skip_download=True,writethumbnail=True)
 else: opts.update(format='bv*+ba/b',merge_output_format='mp4')
 with yt_dlp.YoutubeDL(opts) as ydl:
  info=ydl.extract_info(url,download=True)
 return info,[p for p in job_dir.iterdir() if p.is_file()]
async def download(url,mode):
 jid=uuid.uuid4().hex[:10]; d=Path(TMP_DIR)/jid
 info,files=await asyncio.to_thread(_download,url,mode,d); return jid,info,files
def cleanup(jid): shutil.rmtree(Path(TMP_DIR)/jid,ignore_errors=True)
