import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config" / "config.env"
load_dotenv(CONFIG_PATH)

def bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = int(os.getenv("IBKR_PORT", "7497"))
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "11"))

PAPER_TRADING_ONLY = bool_env("PAPER_TRADING_ONLY", True)
MANUAL_APPROVAL_REQUIRED = bool_env("MANUAL_APPROVAL_REQUIRED", True)
AUTO_SUBMIT_PAPER_ORDERS = bool_env("AUTO_SUBMIT_PAPER_ORDERS", False)

MIN_AI_SCORE = int(os.getenv("MIN_AI_SCORE", "80"))
MAX_SHARES_PER_TRADE = int(os.getenv("MAX_SHARES_PER_TRADE", "25"))
MAX_RISK_PER_TRADE_PCT = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "1.0"))
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "3.0"))

DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/trading_platform_v4.db")
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
