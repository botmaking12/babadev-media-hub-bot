import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN=os.getenv('BOT_TOKEN','').strip()
BRAND_STYLE=os.getenv('BRAND_STYLE','gold').strip().lower()
try: MAX_DOWNLOAD_MB=int(os.getenv('MAX_DOWNLOAD_MB','180'))
except ValueError: MAX_DOWNLOAD_MB=180
ADMIN_IDS={int(x.strip()) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip().isdigit()}
TMP_DIR='tmp'
os.makedirs(TMP_DIR,exist_ok=True)
