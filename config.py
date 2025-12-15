# ==========================================
# 📁 CONFIGURATION FILE (news_verification/config.py)
# ==========================================
from pathlib import Path
import os

# ===============================
# 📂 DIRECTORY CONFIGURATION
# ===============================

# Base directory (this file's folder)
BASE_DIR = Path(__file__).resolve().parent

# Subdirectories
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"
LOG_DIR = BASE_DIR / "logs"

# Ensure directories exist
for d in [STATIC_DIR, UPLOAD_DIR, RESULT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Output files (used by app.py and fighter.py)
OUTPUT_JSON_PATH = RESULT_DIR / "output.json"
PROCESSED_JSON_PATH = RESULT_DIR / "processed_output.json"

# ===============================
# 🔐 API KEYS (load from environment)
# ===============================
import os
from dotenv import load_dotenv

# Load variables from the .env file in the same folder
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
API_KEY=os.getenv("API_KEY")
# Optional: print or check keys (for debugging)
if not all([GEMINI_API_KEY, GROQ_API_KEY, TAVILY_API_KEY]):
    raise ValueError("Missing required API keys. Please set them in .env or environment variables.")


# ===============================
# ⚙️ FLASK CONFIG
# ===============================
FLASK_UPLOAD_FOLDER = str(UPLOAD_DIR)
FLASK_STATIC_FOLDER = str(STATIC_DIR)
