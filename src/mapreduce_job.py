from __future__ import annotations

import argparse
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .common import consume, dump_json, empty_accumulator, merge, serialize_accumulator
from .config import BUCKET, OBJECT_KEY, RESULTS_DIR
from .storage import client


def ranges(size: int, chunk_size: int) -> list[tuple[int, int, int]]:
    return [(i, start, min(size - 1, start + chunk_size - 1)) for i, start in enumerate(range(0, size, chunk_size))]


def map_chunk(task: tuple[int, int, int, int]) -> tuple[int, dict]:
    index, start, end, total = task
    s3 = client()
    fetch_start = max(0, start - 1)
    fetch_end = min(total - 1, end + 65536)
    body = s3.get_object(Bucket=BUCKET, Key=OBJECT_KEY, Range=f"bytes={fetch_start}-{fetch_end}")["Body"].read()
    # A record belongs to the chunk containing its first byte.  Looking one byte
    # behind start distinguishes a true line boundary from the middle of a line.
    if start == 0:
        begin = 0
    elif body[start - fetch_start - 1:start - fetch_start] == b"\n":
        begin = start - fetch_start
    else:
        cut = body.find(b"\n", start - fetch_start)
        begin = len(body) if cut < 0 else cut + 1
    if end >= total - 1:
        finish = len(body)
    else:
        end_pos = end - fetch_start
        if body[end_pos:end_pos + 1] == b"\n":
            finish = end_pos + 1
        else:
            cut = body.find(b"\n", end_pos + 1)
            finish = len(body) if cut < 0 else cut + 1
    body = body[begin:finish]
    acc = empty_accumulator()
    for line in body.splitlines():
        if line.strip(): consume(acc, json.loads(line))
    return index, acc


def simulated_failure(task):
    raise RuntimeError(f"simulated mapper failure for chunk {task[0]}")


def run(chunk_size: int, workers: int, simulate_failure: bool = False) -> dict:
    s3 = client(); size = s3.head_object(Bucket=BUCKET, Key=OBJECT_KEY)["ContentLength"]
    tasks = [(i, start, end, size) for i, start, end in ranges(size, chunk_size)]
    mapped: dict[int, dict] = {}
    # Threaded mappers avoid copying large combination counters between processes;
    # network Range GETs still run concurrently and each mapper owns its accumulator.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(simulated_failure if simulate_failure and task[0] == 0 else map_chunk, task): task for task in tasks}
        retried = 0
        for future in as_completed(futures):
            task = futures[future]
            try:
                index, acc = future.result()
            except Exception:
                retried += 1
                index, acc = map_chunk(task)  # one deterministic retry
            mapped[index] = acc
    reduced = empty_accumulator()
    for index in sorted(mapped): merge(reduced, mapped[index])
    result = serialize_accumulator(reduced)
    result["engine"] = "custom-mapreduce"
    result["source"] = f"s3://{BUCKET}/{OBJECT_KEY}"
    result["chunk_size_bytes"] = chunk_size
    result["chunks"] = len(tasks)
    result["workers"] = workers
    result["retried_chunks"] = retried
    dump_json(RESULTS_DIR / "mapreduce.json", result)
    for key, name in (("skills", "skills"), ("pairs", "pairs"), ("triples", "triples")):
        dump_json(RESULTS_DIR / f"mapreduce_{name}.json", {key: result[key]})
    print(json.dumps({k: result[k] for k in ("rows", "rows_with_skills", "unique_combinations", "chunks", "workers", "retried_chunks")}, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--chunk-size", type=int, default=256*1024); p.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1)); p.add_argument("--simulate-failure", action="store_true")
    a = p.parse_args(); run(a.chunk_size, a.workers, a.simulate_failure)


if __name__ == "__main__": main()
