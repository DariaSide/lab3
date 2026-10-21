from __future__ import annotations

import json
from .common import dump_json, load_json
from .config import RESULTS_DIR


def canonical(rows):
    return {(tuple(x["skills"]), x["count"], x["salary_n"], x["median_salary_rur"]) for x in rows}


def run() -> dict:
    mr = load_json(RESULTS_DIR / "mapreduce.json"); db = load_json(RESULTS_DIR / "duckdb.json")
    checks = {"rows": mr["rows"] == db["rows"], "rows_with_skills": mr["rows_with_skills"] == db["rows_with_skills"]}
    for key in ("skills", "pairs", "triples"):
        checks[key] = canonical(mr[key]) == canonical(db[key])
    result = {"passed": all(checks.values()), "checks": checks, "mapreduce_rows": mr["rows"], "duckdb_rows": db["rows"]}
    dump_json(RESULTS_DIR / "verification.json", result); print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]: raise SystemExit(1)
    return result


if __name__ == "__main__": run()

