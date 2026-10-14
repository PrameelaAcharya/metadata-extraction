from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
TRAIN_DIR = DATA_DIR / "train"
TEST_DIR = DATA_DIR / "test"
TRAIN_CSV = DATA_DIR / "train.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

OLLAMA_URL = "http://localhost:11434/api/chat"
#MODEL_NAME = "qwen2.5:3b"
MODEL_NAME = "llama3:latest"
OLLAMA_TIMEOUT = 180

SCHEMA_FIELDS = [
    "Agreement Value",
    "Agreement Start Date",
    "Agreement End Date",
    "Renewal Notice (Days)",
    "Party One",
    "Party Two",
]

SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt"}
