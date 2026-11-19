import pandas as pd

# заглушки вместо пустых значений
PLACEHOLDERS = ["ЖОҚ", "НЕТ", "нет", "undefined"]
# делим: запятая + заглавная буква
SEP = r",\s+(?=[A-ZА-ЯЁӘҒҚҢӨҰҮҺІ])"
# справка в скобках
BRACKETS = r"\s*\([^()]*\)"

def clean_placeholders(df: pd.DataFrame) -> pd.DataFrame:
    """Заменяа заглушек на NaN."""
    # копия, исходник не меняем
    df = df.copy()

    # заглушки в NaN
    for col in df.columns:
        df[col] = df[col].where(~df[col].isin(PLACEHOLDERS))

    return df

def strip_brackets(series: pd.Series) -> pd.Series:
    """Убирает справку в скобках: 'Министрлігі (бұрынғы атауы...)' -> 'Министрлігі'."""

    s = series.astype(str)

    # пока есть скобки, удаляем
    while s.str.contains("(", regex=False).any():
        s = s.str.replace(BRACKETS, "", regex=True)

    # возвращаем настоящий NaN
    return s.where(series.notna())

def split_values(df: pd.DataFrame, col: str, id_col: str = "source_id") -> pd.DataFrame:
    """Делит неатомарное поле: одна строка = одна пара (id акта, значение)."""
    # id и поле, без пустых
    out = df[[id_col, col]].dropna()

    # ячейка в список значений
    out[col] = out[col].astype(str).str.split(SEP, regex=True)

    # каждое значение — отдельная строка
    out = out.explode(col)
    out[col] = out[col].str.strip()

    return out.rename(columns={col: "name"}).drop_duplicates()
