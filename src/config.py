from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] 
DATA_DIR = ROOT / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_PROCESSED = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "legislation.db"
DOCS = ROOT / "docs"
PARQUET_PATH = DATA_PROCESSED / "acts.parquet"

REPO_ID = "Arailym-tleubayeva/KazakhLawCorpus-clean"
CSV_FILENAME = "data/kazakhlawcorpus_kk_only.csv"
CSV_PATH = DATA_RAW / CSV_FILENAME
CSV_SIZE_BYTES = 336_764_115

ENCODING = "utf-8"

for folder in (DATA_RAW, DATA_PROCESSED, DOCS):
    folder.mkdir(parents=True, exist_ok=True)