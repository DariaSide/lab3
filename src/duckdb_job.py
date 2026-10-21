from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

import duckdb

from .common import dump_json, empty_accumulator, serialize_accumulator
from .config import ACCESS_KEY, BUCKET, ENDPOINT, OBJECT_KEY, REGION, RESULTS_DIR, SECRET_KEY


def configure(con) -> None:
    endpoint = ENDPOINT.removeprefix("http://").removeprefix("https://")
    con.execute("INSTALL httpfs; LOAD httpfs")
    con.execute(f"SET s3_endpoint='{endpoint}'")
    con.execute(f"SET s3_access_key_id='{ACCESS_KEY}'")
    con.execute(f"SET s3_secret_access_key='{SECRET_KEY}'")
    con.execute(f"SET s3_region='{REGION}'")
    con.execute("SET s3_url_style='path'")
    con.execute(f"SET s3_use_ssl={'true' if ENDPOINT.startswith('https://') else 'false'}")


def run() -> dict:
    con = duckdb.connect(); configure(con)
    uri = f"s3://{BUCKET}/{OBJECT_KEY}"
    con.execute(f"CREATE VIEW vacancies AS SELECT * FROM read_ndjson_auto('{uri}', maximum_object_size=10485760)")
    con.execute("CREATE VIEW expanded AS SELECT vacancy_id, area, salary_rur, skill, pos FROM vacancies, UNNEST(skills) WITH ORDINALITY AS t(skill, pos)")
    acc = empty_accumulator()
    acc["rows"] = con.execute("SELECT count(*) FROM vacancies").fetchone()[0]
    acc["rows_with_skills"] = con.execute("SELECT count(*) FROM vacancies WHERE len(skills)>0").fetchone()[0]
    for size, table in ((1, "skills"), (2, "pairs"), (3, "triples")):
        aliases = [chr(ord('a') + i) for i in range(size)]
        select_skills = ", ".join(f"{a}.skill" for a in aliases)
        joins = "\n".join(f"JOIN expanded {a} ON {a}.vacancy_id=a.vacancy_id AND {prev}.pos < {a}.pos" for a, prev in zip(aliases[1:], aliases[:-1]))
        query = f"""SELECT {select_skills}, count(*) AS n, median(a.salary_rur) FILTER (WHERE a.salary_rur IS NOT NULL) AS med, count(a.salary_rur) AS salary_n
                    FROM expanded a {joins} GROUP BY {select_skills} ORDER BY n DESC, {select_skills}"""
        rows = con.execute(query).fetchall()
        for row in rows:
            combo = tuple(row[:size]); acc["counts"][size][combo] = row[size]
            if row[size + 2]:
                # serialize_accumulator only needs median; repeat the median salary_n times.
                acc["salaries"][size][combo] = [float(row[size + 1])] * int(row[size + 2])
    region_rows = con.execute("SELECT area, count(*), median(salary_rur), count(salary_rur) FROM vacancies GROUP BY area").fetchall()
    for area, n, med, salary_n in region_rows:
        reg = acc["regions"][area]; reg["vacancies"] = n
        if salary_n: reg["salary"] = [float(med)] * salary_n
    for size, key in ((1, "skills"), (2, "pairs"), (3, "triples")):
        aliases = [chr(ord('a') + i) for i in range(size)]
        select_skills = ", ".join(f"{a}.skill" for a in aliases)
        joins = "\n".join(f"JOIN expanded {a} ON {a}.vacancy_id=a.vacancy_id AND {prev}.pos < {a}.pos" for a, prev in zip(aliases[1:], aliases[:-1]))
        q = f"SELECT a.area, {select_skills}, count(*) n FROM expanded a {joins} GROUP BY a.area, {select_skills}"
        for row in con.execute(q).fetchall():
            area, combo, n = row[0], tuple(row[1:1+size]), row[-1]
            acc["regions"][area][key][combo] = n
    result = serialize_accumulator(acc); result["engine"] = "duckdb-sql"; result["source"] = uri
    dump_json(RESULTS_DIR / "duckdb.json", result)
    print(json.dumps({k: result[k] for k in ("rows", "rows_with_skills", "unique_combinations")}, ensure_ascii=False, indent=2)); return result


def main() -> None: run()
if __name__ == "__main__": main()
