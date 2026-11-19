import sqlite3
import pandas as pd
from src.config import DB_PATH, DOCS

QUERIES = {
    # 1. Сколько актов и сколько отменено по годам (только полные годы — из аудита)
    "acts_per_year": """
        SELECT year, COUNT(*) as acts, SUM(is_repealed) as repealed,
               ROUND(100.0 * SUM(is_repealed) / COUNT(*), 1) as repealed_pct
        FROM acts
        WHERE year BETWEEN 1992 AND 2025
        GROUP BY year
        ORDER BY year
    """,
    # 2. Топ-10 органов по числу актов (через таблицу связи многие-ко-многим)
    "top_bodies": """
        SELECT b.name as body, COUNT(*) as acts
        FROM act_bodies ab
        join bodies b on b.body_id = ab.body_id
        GROUP BY b.name
        ORDER BY acts DESC
        LIMIT 10
    """,
    # 3. Самые частые сферы регулирования (только где больше 5000 актов)
    "top_areas": """
        select ar.name as area, count(*) as acts
        from act_areas aa
        join areas ar on ar.area_id = aa.area_id
        GROUP BY ar.name
        HAVING COUNT(*) > 5000
        ORDER BY acts DESC        
    """,
    # 4. Доля отменённых по юридической силе (AVG от 0/1 = доля единиц)
    "repeal_by_force": """
        select lf.name as legal_force,
               count(*) as acts,
               round(100.0 * avg(a.is_repealed), 1) as repealed_pct
        from acts a
        join legal_forces lf on lf.legal_force_id = a.legal_force_id
        group by lf.name
        having count(*) >= 1000
        order by repealed_pct desc
    """,
    # 5. Регионы, где актов больше среднего по всем регионам (подзапрос в HAVING)
    "regions_above_avg": """
        select r.name as region, count(*) as acts
        from acts a
        join regions r on r.region_id = a.region_id
        group by r.name
        having count(*) > (
            select avg(cnt)
            from (select count(*) as cnt from acts group by region_id)
        )
        order by acts desc
    """,
    # 6. Динамика по годам: изменение к прошлому году, скользящее среднее, накопительно
    "yearly_growth": """
        with yearly as (
            select year, count(*) as acts
            from acts
            where year between 1992 and 2025
            group by year
        )
        select year, acts, 
            acts - lag(acts) over (order by year) as change,
            round(avg(acts) over (order by year rows between 2 preceding 
                and current row), 0) as avg_3y,
            sum(acts) over (order by year) as cumulative
        from yearly 
        order by year
    """,
    # 7. Самый активный орган в каждом году (2016–2025)
    "top_body_per_year": """
        with body_year as (
            select a.year, b.name as body, count(*) as acts
            from acts a
            join act_bodies ab on ab.act_id = a.act_id
            join bodies b      on b.body_id = ab.body_id
            where a.year between 2016 and 2025
            group by a.year, b.name
        ),
        ranked as (
            select year, body, acts,
                   row_number() over (partition by year order by acts desc) as rn
            from body_year
        )
        select year, body, acts
        from ranked
        where rn = 1
        order by year
    """,

    # 8. Формы актов: место (RANK) и доля от всех (SUM() OVER () — сумма по ВСЕЙ таблице)
    "form_share": """
        with form_counts as (
            select f.name as form, count(*) as acts
            from act_forms af
            join forms f on f.form_id = af.form_id
            group by f.name
        )
        select form, acts,
               rank() over (order by acts desc) as rnk,
               round(100.0 * acts / sum(acts) over (), 1) as share_pct
        from form_counts
        order by rnk
        limit 10
    """,

    # 9. Сферы с самой большой долей отменённых актов
    "area_repeal_rank": """
        with area_stats as (
            select ar.name as area, count(*) as acts, avg(a.is_repealed) as rate
            from acts a
            join act_areas aa on aa.act_id = a.act_id
            join areas ar     on ar.area_id = aa.area_id
            group by ar.name
            having count(*) >= 1000
        )
        select area, acts,
               round(100.0 * rate, 1) as repealed_pct,
               dense_rank() over (order by rate desc) as rnk
        from area_stats
        order by rnk
        limit 10
    """,
}

def run_query(name: str) -> pd.DataFrame:
    """Выполняет запрос по имени и возвращает результат как таблицу pandas."""

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Нет базы {DB_PATH}. Сначала запусти: python -m src.db")

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(QUERIES[name], conn)


def main():
    out_dir = DOCS / "queries"
    out_dir.mkdir(exist_ok=True)

    for name in QUERIES.keys():
        result = run_query(name)

        result.to_csv(out_dir / f"{name}.csv", index=False, encoding="utf-8-sig")

        print(f"\n-{name} {result.shape}-")
        print(result.head(3).to_string(index=False))

if __name__ == "__main__":
    main()