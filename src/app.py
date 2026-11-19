import sqlite3
import sys
from pathlib import Path
# корень проекта в пути
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pandas as pd
import plotly.express as px
import streamlit as st
from src.config import DB_PATH

st.set_page_config(page_title="Законодательство Казахстана", layout="wide")


@st.cache_data
def load_data():
    """Читает из базы акты, органы и сферы (один раз, потом из кеша)."""
    # нет базы — пустой результат
    if not DB_PATH.exists():
        return None, None, None

    with sqlite3.connect(DB_PATH) as conn:
        # акты с регионом и силой
        acts = pd.read_sql("""
            SELECT a.act_id, a.year, a.is_repealed,
                   r.name AS region, lf.name AS legal_force
            FROM acts a
            LEFT JOIN regions r       ON r.region_id = a.region_id
            LEFT JOIN legal_forces lf ON lf.legal_force_id = a.legal_force_id
            WHERE a.year BETWEEN 1992 AND 2025
        """, conn)
        # пары акт — орган
        bodies = pd.read_sql("""
            SELECT ab.act_id, b.name AS body
            FROM act_bodies ab JOIN bodies b ON b.body_id = ab.body_id
        """, conn)
        # пары акт — сфера
        areas = pd.read_sql("""
            SELECT aa.act_id, ar.name AS area
            FROM act_areas aa JOIN areas ar ON ar.area_id = aa.area_id
        """, conn)
    return acts, bodies, areas


def apply_filters(acts, years, region, force, status):
    """Оставляет только акты, подходящие под фильтры."""
    # фильтр по годам
    df = acts[acts["year"].between(years[0], years[1])]

    # регион и юр. сила
    if region != "Все":
        df = df[df["region"] == region]
    if force != "Все":
        df = df[df["legal_force"] == force]

    # фильтр по статусу
    if status == "Действующие":
        df = df[df["is_repealed"] == 0]
    elif status == "Отменённые":
        df = df[df["is_repealed"] == 1]
    else:
        pass

    return df


def top_names(pairs, act_ids, col, n=10):
    """Топ-n названий (органов или сфер) среди выбранных актов."""
    return (pairs[pairs["act_id"].isin(act_ids)][col]
            .value_counts().head(n)
            .rename_axis(col).reset_index(name="acts"))


def main():
    st.title("Законодательство Казахстана, 1992–2025")

    acts, bodies, areas = load_data()
    if acts is None:
        st.error("Нет базы. Запусти: python -m src.data_loader, затем python -m src.db")
        return

    # фильтры в боковой панели
    st.sidebar.header("Фильтры")
    years = st.sidebar.slider("Годы", 1992, 2025, (2010, 2025))
    regions = ["Все"] + acts["region"].value_counts().index.tolist()
    region = st.sidebar.selectbox("Регион", regions)
    forces = ["Все"] + sorted(acts["legal_force"].dropna().unique())
    force = st.sidebar.selectbox("Юридическая сила", forces)
    status = st.sidebar.radio("Статус", ["Все", "Действующие", "Отменённые"])

    df = apply_filters(acts, years, region, force, status)
    if df.empty:
        st.warning("По выбранным фильтрам актов нет.")
        return

    # карточки с цифрами
    c1, c2, c3 = st.columns(3)
    c1.metric("Актов", f"{len(df):,}".replace(",", " "))
    c2.metric("Отменено, %", f"{df['is_repealed'].mean() * 100:.1f}")
    c3.metric("Лет в выборке", df["year"].nunique())

    # акты по годам
    per_year = df.groupby("year").agg(
        acts=("act_id", "size"),
        repealed_pct=("is_repealed", "mean"),
    ).reset_index()
    per_year["repealed_pct"] = (per_year["repealed_pct"] * 100).round(1)
    fig = px.bar(per_year, x="year", y="acts", color="repealed_pct",
                 labels={"year": "Год", "acts": "Актов", "repealed_pct": "Отменено, %"},
                 title="Актов по годам")
    st.plotly_chart(fig, width="stretch")

    # топ органов и сфер
    left, right = st.columns(2)
    tb = top_names(bodies, df["act_id"], "body")
    left.plotly_chart(px.bar(tb[::-1], x="acts", y="body", orientation="h",
                             labels={"acts": "Актов", "body": ""},
                             title="Топ-10 органов"), width="stretch")
    ta = top_names(areas, df["act_id"], "area")
    right.plotly_chart(px.bar(ta[::-1], x="acts", y="area", orientation="h",
                              labels={"acts": "Актов", "area": ""},
                              title="Топ-10 сфер регулирования"), width="stretch")


main()
