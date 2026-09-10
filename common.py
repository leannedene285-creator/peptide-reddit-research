"""三个脚本共用的配置、路径与日志设置。"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
RAW_CSV = DATA_DIR / "raw-posts.csv"
LABELED_CSV = DATA_DIR / "labeled-posts.csv"
REPORT_MD = DATA_DIR / "report.md"

SUBREDDITS = ["Biohacking", "Peptides", "Semaglutide", "Tirzepatide"]

# 搜索关键词：既用于 Reddit 站内搜索，也用于本地二次过滤
KEYWORDS = [
    "peptide", "peptides", "BPC-157", "BPC157", "TB-500", "TB500",
    "semaglutide", "tirzepatide", "retatrutide", "GLP-1",
    "reconstitute", "reconstitution", "bacteriostatic",
    "vendor", "source", "COA", "HPLC", "purity",
]

LOOKBACK_DAYS = 365
MIN_TEXT_LENGTH = 40


def load_config() -> None:
    """从项目目录下的 .env 读取凭证，缺失时不报错，由调用方逐项校验。"""
    load_dotenv(PROJECT_DIR / ".env")
    DATA_DIR.mkdir(exist_ok=True)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"环境变量 {name} 未设置，请在 .env 中填写")
    return value


def setup_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger(name)


def contains_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in KEYWORDS)
