import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
API_KEY = os.getenv("MINI_API_KEY", "")
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
PROJECT_PATH = "/Users/matthewmacosko/Documents/Vision Builder"
