from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

from .common import dump_json
from .config import LOG_DIR, RESULTS_DIR, ROOT


def measure(label: str, command: list[str], attempt: int) -> dict:
    started = time.perf_counter(); proc = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    peak = 0
    while proc.poll() is None:
        try:
            parent = psutil.Process(proc.pid); rss = parent.memory_info().rss + sum((c.memory_info().rss for c in parent.children(recursive=True)), 0)
            peak = max(peak, rss)
        except psutil.Error: pass
        time.sleep(0.02)
    output = proc.stdout.read() if proc.stdout else ""
    log = LOG_DIR / f"{label}-{attempt}.log"; log.write_text(output, encoding="utf-8")
    row = {"engine": label, "attempt": attempt, "seconds": round(time.perf_counter()-started, 4), "peak_rss_mb": round(peak/1024/1024, 2), "exit_code": proc.returncode, "log": str(log.relative_to(ROOT))}
    if proc.returncode: raise RuntimeError(f"{label} failed: {output[-2000:]}")
    return row


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--runs", type=int, default=3); a=p.parse_args(); rows=[]
    for i in range(1,a.runs+1): rows.append(measure("mapreduce", [sys.executable,"-m","src.mapreduce_job"], i))
    for i in range(1,a.runs+1): rows.append(measure("duckdb", [sys.executable,"-m","src.duckdb_job"], i))
    subprocess.run([sys.executable,"-m","src.verify"], cwd=ROOT, check=True)
    dump_json(RESULTS_DIR / "profiling.json", {"runs": rows}); print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()

