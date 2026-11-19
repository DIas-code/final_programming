import sqlite3
from src.config import DB_PATH
import pandas as pd
from src.data_loader import load_parquet
from src.cleaning import clean_placeholders, strip_brackets, split_values

SCHEMA = """
CREATE TABLE legal_forces (
    legal_force_id INTEGER PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE
);

CREATE TABLE regions (
    region_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE
);

CREATE TABLE acts (
    act_id         INTEGER PRIMARY KEY,
    law_id         TEXT    NOT NULL UNIQUE,
    title          TEXT    NOT NULL,
    date_adopted   TEXT    NOT NULL,
    year           INTEGER NOT NULL,
    is_repealed    INTEGER NOT NULL,
    legal_force_id INTEGER REFERENCES legal_forces(legal_force_id),
    region_id      INTEGER REFERENCES regions(region_id)
);

CREATE TABLE forms (
    form_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

CREATE TABLE areas (
    area_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

CREATE TABLE bodies (
    body_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

CREATE TABLE act_forms (
    act_id  INTEGER NOT NULL REFERENCES acts(act_id),
    form_id INTEGER NOT NULL REFERENCES forms(form_id),
    PRIMARY KEY (act_id, form_id)
);

CREATE TABLE act_areas (
    act_id  INTEGER NOT NULL REFERENCES acts(act_id),
    area_id INTEGER NOT NULL REFERENCES areas(area_id),
    PRIMARY KEY (act_id, area_id)
);

CREATE TABLE act_bodies (
    act_id  INTEGER NOT NULL REFERENCES acts(act_id),
    body_id INTEGER NOT NULL REFERENCES bodies(body_id),
    PRIMARY KEY (act_id, body_id)
);
"""

def create_schema() -> sqlite3.Connection:
    """Создаёт пустую базу с таблицами и возвращает подключение."""
    DB_PATH.unlink(missing_ok=True) #удалить старый файл базы, если он есть
    conn = sqlite3.connect(DB_PATH)
    # создаём все таблицы
    conn.executescript(SCHEMA)
    return conn

def prepare_for_load(df: pd.DataFrame) -> pd.DataFrame:
    """Очистка перед загрузкой: заглушки, category -> текст, скобки."""
    # заглушки в NaN
    df = clean_placeholders(df)

    # category в обычный текст
    for col in ["legal_force", "region", "act_form", "legal_relation_area", "adopting_body"]:
        df[col] = df[col].astype(str).where(df[col].notna())

    # убираем справку в скобках
    df["adopting_body"] = strip_brackets(df["adopting_body"])
    return df

def load_lookup(conn, names: pd.Series, table: str, id_col: str) -> dict:
    """Заполняет справочник и возвращает словарь {название: id}."""
    # уникальные названия по алфавиту
    unique = sorted(names.dropna().unique())

    # id и название
    lookup = pd.DataFrame({id_col: range(1, len(unique) + 1), "name": unique})

    # записываем в базу
    lookup.to_sql(table, conn, if_exists="append", index=False)

    # словарь название → id
    return dict(zip(lookup["name"], lookup[id_col]))

def load_acts(conn, df: pd.DataFrame) -> None:
    """Заполняет legal_forces, regions и главную таблицу acts."""

    # сначала справочники — их id нужны для acts
    forces = load_lookup(conn, df["legal_force"], "legal_forces", "legal_force_id")
    regions = load_lookup(conn, df["region"], "regions", "region_id")

    # собираем таблицу acts: ключ словаря = имя колонки в базе
    acts = pd.DataFrame({
        "act_id": df["source_id"],
        "law_id": df["law_id"],
        "title": df["title"],
        "date_adopted": df["date_adopted"].dt.strftime("%Y-%m-%d"),
        "year": df["date_adopted"].dt.year,
        "is_repealed": df["is_repealed"].astype(int),
        "legal_force_id": df["legal_force"].map(forces),
        "region_id": df["region"].map(regions),
    })
    # записываем в базу
    acts.to_sql("acts", conn, if_exists="append", index=False)

def load_links(conn, df, col: str, table: str, link_table: str, id_col: str) -> None:
    """Неатомарное поле -> справочник + таблица связи многие-ко-многим."""
    # пары (акт, значение)
    pairs = split_values(df, col)

    # справочник значений
    lookup = load_lookup(conn, pairs["name"], table, id_col)

    # название → id
    pairs[id_col] = pairs["name"].map(lookup)
    pairs = pairs.rename(columns={"source_id": "act_id"})

    # записываем таблицу связи
    pairs[["act_id", id_col]].drop_duplicates().to_sql(
        link_table, conn, if_exists="append", index=False
    )

def main() -> None:
    # данные и пустая база
    df = prepare_for_load(load_parquet())

    conn = create_schema()

    # заполняем все таблицы
    load_acts(conn, df)
    load_links(conn, df, "act_form", "forms", "act_forms", "form_id")
    load_links(conn, df, "legal_relation_area", "areas", "act_areas", "area_id")
    load_links(conn, df, "adopting_body", "bodies", "act_bodies", "body_id")

    # .commit() — сохранить изменения в файл базы (без этого данные пропадут)
    conn.commit()

    # проверка: строк в таблицах
    for t in ["legal_forces", "regions", "acts", "forms", "areas", "bodies",
              "act_forms", "act_areas", "act_bodies"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {count}")

    conn.close()

if __name__ == "__main__":
    main()