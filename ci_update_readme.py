"""Generate a markdown results table and optionally update README.md.

Usage:
    python ci_update_readme.py                # print markdown to stdout (for GITHUB_STEP_SUMMARY)
    python ci_update_readme.py --update-readme  # replace markers in README.md in-place
"""
import json
import argparse
import datetime
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
README      = Path(__file__).parent / "README.md"

START = "<!-- BENCH_RESULTS_START -->"
END   = "<!-- BENCH_RESULTS_END -->"


def load_results(msg_size: int) -> list[dict]:
    rows = []
    for f in sorted(RESULTS_DIR.glob(f"*_{msg_size}b.json")):
        rows.append(json.loads(f.read_text()))
    rows.sort(key=lambda r: r.get("p50_us", float("inf")))
    return rows


def make_table(rows: list[dict], msg_size: int) -> str:
    if not rows:
        return ""
    n = rows[0].get("iterations", "?")
    lines = [
        f"### {msg_size} B messages &nbsp; (n = {n:,} round-trips)",
        "",
        "| Transport | p50 μs | p95 μs | p99 μs | p99.9 μs | msg/s |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['transport']} "
            f"| {r['p50_us']:.1f} "
            f"| {r['p95_us']:.1f} "
            f"| {r['p99_us']:.1f} "
            f"| {r['p999_us']:.1f} "
            f"| {r['throughput_msg_s']:,.0f} |"
        )
    return "\n".join(lines) + "\n"


def build_report() -> str:
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    parts = [f"_Last updated: {now} · runner: `ubuntu-latest`_\n"]
    for size in [64, 256, 1024]:
        table = make_table(load_results(size), size)
        if table:
            parts.append(table)
    if len(parts) == 1:
        parts.append("_No results yet — run `python run_all.py` first._\n")
    return "\n".join(parts)


def update_readme(report: str) -> None:
    text = README.read_text()
    s = text.find(START)
    e = text.find(END)
    if s == -1 or e == -1:
        raise SystemExit(f"ERROR: markers not found in README.md\n  expected: {START!r} … {END!r}")
    README.write_text(text[: s + len(START)] + "\n" + report + text[e:])
    print("README.md updated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-readme", action="store_true",
                        help="Replace content between markers in README.md")
    args = parser.parse_args()

    report = build_report()
    if args.update_readme:
        update_readme(report)
    else:
        print(report)
