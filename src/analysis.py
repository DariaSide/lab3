from __future__ import annotations

import itertools
import json
import statistics

from .common import dump_json, load_json
from .config import RESULTS_DIR


def salary_effects(result: dict, size: int, min_salary_n: int = 10) -> list[dict]:
    key = {1:"skills",2:"pairs",3:"triples"}[size]
    rows = {tuple(x["skills"]): x for x in result[key]}
    baseline_key = {2:"skills",3:"pairs"}[size]
    baseline_rows = {tuple(x["skills"]): x for x in result[baseline_key]}
    effects=[]
    for combo,row in rows.items():
        if size == 1 or row["salary_n"] < min_salary_n or row["median_salary_rur"] is None: continue
        subsets = list(itertools.combinations(combo,size-1))
        valid = [baseline_rows[s] for s in subsets if s in baseline_rows and baseline_rows[s]["salary_n"] >= min_salary_n and baseline_rows[s]["median_salary_rur"] is not None]
        if not valid: continue
        baseline=max(valid,key=lambda x:x["count"])
        delta=round(row["median_salary_rur"]-baseline["median_salary_rur"],2)
        effects.append({"skills":list(combo),"count":row["count"],"salary_n":row["salary_n"],"median_salary_rur":row["median_salary_rur"],"baseline_skills":baseline["skills"],"baseline_count":baseline["count"],"baseline_median_salary_rur":baseline["median_salary_rur"],"delta_rur":delta})
    return sorted(effects,key=lambda x:(-x["delta_rur"],-x["salary_n"],x["skills"]))


def main() -> None:
    data=load_json(RESULTS_DIR/"mapreduce.json"); profile=load_json(RESULTS_DIR/"profiling.json")
    regions=data["regions"][:3]
    effects2=salary_effects(data,2); effects3=salary_effects(data,3)
    by_engine={}
    for engine in ("mapreduce","duckdb"):
        rows=[x for x in profile["runs"] if x["engine"]==engine]
        by_engine[engine]={"median_seconds":round(statistics.median(x["seconds"] for x in rows),4),"median_peak_rss_mb":round(statistics.median(x["peak_rss_mb"] for x in rows),2)}
    result={"top_regions":regions,"pair_increase":effects2[:10],"pair_decrease":list(reversed(effects2[-10:])),"triple_increase":effects3[:10],"triple_decrease":list(reversed(effects3[-10:])),"profile_summary":by_engine,"top_skills":data["skills"][:20],"combination_growth":data["unique_combinations"]}
    dump_json(RESULTS_DIR/"analysis.json",result); print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
