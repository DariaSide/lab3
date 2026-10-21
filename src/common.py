from __future__ import annotations

import itertools
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


def normalize_skills(raw: str | None) -> list[str]:
    """Split HH skills, deduplicate case-insensitively and sort deterministically."""
    seen: dict[str, str] = {}
    for part in (raw or "").split(";"):
        skill = " ".join(part.strip().split())
        if skill:
            seen.setdefault(skill.casefold(), skill)
    return [seen[key] for key in sorted(seen)]


def salary_rur(row: dict) -> float | None:
    """Monthly RUR midpoint; open bounds use the available bound, net is grossed up."""
    if row.get("currency") != "RUR":
        return None
    values = []
    for key in ("salary_from", "salary_to"):
        try:
            if row.get(key) not in (None, ""):
                values.append(float(row[key]))
        except (TypeError, ValueError):
            pass
    if not values:
        return None
    midpoint = sum(values) / len(values)
    gross = str(row.get("gross", "")).lower()
    return midpoint / 0.87 if gross == "false" else midpoint


def combinations(skills: list[str], size: int) -> Iterable[tuple[str, ...]]:
    return itertools.combinations(skills, size)


def empty_accumulator() -> dict:
    return {
        "rows": 0,
        "rows_with_skills": 0,
        "counts": {1: Counter(), 2: Counter(), 3: Counter()},
        "salaries": {1: defaultdict(list), 2: defaultdict(list), 3: defaultdict(list)},
        "regions": defaultdict(lambda: {"vacancies": 0, "salary": [], "skills": Counter(), "pairs": Counter(), "triples": Counter()}),
    }


def consume(acc: dict, row: dict) -> None:
    acc["rows"] += 1
    skills = row.get("skills") or normalize_skills(row.get("key_skills"))
    salary = row.get("salary_rur")
    if salary is None:
        salary = salary_rur(row)
    if skills:
        acc["rows_with_skills"] += 1
    for size in (1, 2, 3):
        for combo in combinations(skills, size):
            acc["counts"][size][combo] += 1
            if salary is not None:
                acc["salaries"][size][combo].append(float(salary))
    region = row.get("area") or "Не указан"
    reg = acc["regions"][region]
    reg["vacancies"] += 1
    if salary is not None:
        reg["salary"].append(float(salary))
    reg["skills"].update(combinations(skills, 1))
    reg["pairs"].update(combinations(skills, 2))
    reg["triples"].update(combinations(skills, 3))


def merge(left: dict, right: dict) -> dict:
    left["rows"] += right["rows"]
    left["rows_with_skills"] += right["rows_with_skills"]
    for size in (1, 2, 3):
        left["counts"][size].update(right["counts"][size])
        for combo, vals in right["salaries"][size].items():
            left["salaries"][size][combo].extend(vals)
    for region, src in right["regions"].items():
        dst = left["regions"][region]
        dst["vacancies"] += src["vacancies"]
        dst["salary"].extend(src["salary"])
        for key in ("skills", "pairs", "triples"):
            dst[key].update(src[key])
    return left


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 2) if values else None


def serialize_accumulator(acc: dict) -> dict:
    def rows_for(size: int) -> list[dict]:
        return [
            {
                "skills": list(combo),
                "count": count,
                "salary_n": len(acc["salaries"][size].get(combo, [])),
                "median_salary_rur": median(acc["salaries"][size].get(combo, [])),
            }
            for combo, count in sorted(acc["counts"][size].items(), key=lambda x: (-x[1], x[0]))
        ]

    regions = []
    for name, values in sorted(acc["regions"].items(), key=lambda x: (-x[1]["vacancies"], x[0])):
        regions.append({
            "region": name,
            "vacancies": values["vacancies"],
            "salary_n": len(values["salary"]),
            "median_salary_rur": median(values["salary"]),
            "top_skills": [{"skills": list(k), "count": v} for k, v in values["skills"].most_common(10)],
            "top_pairs": [{"skills": list(k), "count": v} for k, v in values["pairs"].most_common(10)],
            "top_triples": [{"skills": list(k), "count": v} for k, v in values["triples"].most_common(10)],
        })
    return {
        "rows": acc["rows"],
        "rows_with_skills": acc["rows_with_skills"],
        "unique_combinations": {str(size): len(acc["counts"][size]) for size in (1, 2, 3)},
        "skills": rows_for(1),
        "pairs": rows_for(2),
        "triples": rows_for(3),
        "regions": regions,
    }


def dump_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

