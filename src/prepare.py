from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .common import normalize_skills, salary_rur
from .config import DATA_DIR, ROLE


def prepare(source: Path, destination: Path) -> dict:
    total = selected = with_skills = with_salary = 0
    areas: dict[str, int] = {}
    with source.open("r", encoding="utf-8-sig", newline="") as inp, destination.open("w", encoding="utf-8") as out:
        for row in csv.DictReader(inp):
            total += 1
            if row.get("role") != ROLE:
                continue
            selected += 1
            skills = normalize_skills(row.get("key_skills"))
            salary = salary_rur(row)
            with_skills += bool(skills)
            with_salary += salary is not None
            area = row.get("area") or "Не указан"
            areas[area] = areas.get(area, 0) + 1
            record = {
                "vacancy_id": row.get("vacancy_id"),
                "published_at": row.get("published_at"),
                "area": area,
                "name": row.get("name"),
                "role": row.get("role"),
                "skills": skills,
                "salary_rur": salary,
                "salary_from": row.get("salary_from"),
                "salary_to": row.get("salary_to"),
                "currency": row.get("currency"),
                "gross": row.get("gross"),
            }
            out.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {
        "source": str(source), "source_rows": total, "filter": f"role = {ROLE!r}",
        "selected_rows": selected, "rows_with_skills": with_skills,
        "rows_with_salary": with_salary, "output_bytes": destination.stat().st_size,
        "top_areas": sorted(areas.items(), key=lambda x: (-x[1], x[0]))[:10],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DATA_DIR / "devops_vacancies.ndjson")
    args = parser.parse_args()
    metadata = prepare(args.input, args.output)
    meta_path = DATA_DIR / "prepare_metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

