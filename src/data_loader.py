from pathlib import Path
from huggingface_hub import hf_hub_download
import pandas as pd
from src.config import CSV_FILENAME, CSV_PATH, DATA_RAW, REPO_ID, ENCODING, PARQUET_PATH

def download_csv() -> Path:
    """Скачивает CSV в data/raw/, если файла там ещё нет."""
    if CSV_PATH.exists():
        print(f"Csv уже скачан: {CSV_PATH}")
        return CSV_PATH

    print("CSV скачивается...")

    try:
        path = hf_hub_download(
            repo_id=REPO_ID, #чей датасет
            repo_type="dataset",
            filename=CSV_FILENAME,
            local_dir=DATA_RAW #то куда скачивается
        )
    except Exception as exc:
        raise RuntimeError(f"Не удалось скачать датасет: {exc}") from exc

    print(f"Скачан в: {path}")
    return Path(path)

CHUNK_SIZE= 50000

DROP_COLS = ["is_archive"] #все f бесполезная колонна
#Date columns
DATE_COLS = ["date_adopted", "date_modified", "date_published", "ministry_registration_date"]

# текст, где одни и те же значения повторяются много раз
# (например, legal_force: 43 разных названия на 215 тыс. строк)
CATEGORY_COLS = [
    "database_section", "legal_force", "regulatory_body", "act_form",
    "developer_body", "place_of_adoption", "region", "adopting_body",
    "legal_relation_area",
]

def read_csv_chunks(chunk_size = CHUNK_SIZE) -> pd.DataFrame:
    """Читает CSV по частям(50000) и склеивает в одну таблицу."""
    chunks = []

    for chunk in pd.read_csv(CSV_PATH, encoding=ENCODING, dtype=str, chunksize=chunk_size):
        chunks.append(chunk)
        print(f"прочитан чанк {len(chunks)}: {len(chunk)} строк")

    return pd.concat(chunks, ignore_index=True) #соединяем чанки

def memory_mb(df: pd.DataFrame) -> float:
    """Сколько МБ оперативной памяти занимает таблица."""
    # deep=True — считать реальный размер текста в ячейках, без счиате ссылку

    return df.memory_usage(deep=True).sum() / 1024**2

def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    # удаляем бесполезные колонки
    df = df.drop(columns=DROP_COLS)

    # текст в даты
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d")

    # t/f в True/False
    df["is_repealed"] = df["is_repealed"] == "t"

    # id в маленькое число
    df["source_id"] = pd.to_numeric(df["source_id"], downcast="integer")

    # повторяющийся текст в category
    for col in CATEGORY_COLS:
        df[col] = df[col].astype("category")
    
    return df

def save_parquet(df: pd.DataFrame) -> None:
    """Сохраняет таблицу в Parquet."""
    df.to_parquet(PARQUET_PATH, index=False, compression="zstd")
    print(f"Сохранено: {PARQUET_PATH} ({PARQUET_PATH.stat().st_size / 1024**2:.1f} МБ)")

def load_parquet() -> pd.DataFrame:
    """Читает Parquet; если его нет — сначала создаёт."""
    # если файла нет — делаем всю згрузку
    if not PARQUET_PATH.exists():
        main()
    return pd.read_parquet(PARQUET_PATH)

def main() -> None:
    download_csv()

    print("CSV by chunks")
    df = read_csv_chunks()

    print(f"Загружено: {df.shape[0]} строк, {df.shape[1]} колонок")


    # замер до
    before = memory_mb(df)
    print(f"Память до оптимизации: {before:.1f} МБ")

    df = optimize_dtypes(df)

    # замер после
    after = memory_mb(df)
    print(f"Память после оптимизации: {after:.1f} МБ")

    print(f"Экономия: {(before - after) / before * 100:.0f} %")
    
    save_parquet(df)

if __name__ == "__main__":
    main()