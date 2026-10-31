from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()
ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv('DATA_DIR', str(ROOT / 'data')))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SAM_CHECKPOINT = Path(os.getenv('SAM_CHECKPOINT', str(ROOT / 'sam_vit_b_01ec64.pth')))
SAM_TYPE = os.getenv('SAM_TYPE', 'vit_b')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
PORT = int(os.getenv('PORT', '8080'))
MAX_IMAGE_MB = int(os.getenv('MAX_IMAGE_MB', '15'))
MIN_ALIGNMENT_MATCHES = int(os.getenv('MIN_ALIGNMENT_MATCHES', '15'))
WEBHOOK_URL = os.getenv('MES_WEBHOOK_URL', '')
WEBHOOK_TOKEN = os.getenv('MES_WEBHOOK_TOKEN', '')
PIXELS_PER_MM = float(os.getenv('PIXELS_PER_MM', '0'))
