"""
Entry point for running all benchmarks.

Usage:
    cd example_project
    uv run python -m benchmarks [--iterations N] [--json] [--tier TIER] [--no-diagrams] [--db-label LABEL]
"""

import argparse
import asyncio
import gc
import os
from pathlib import Path

# Ensure Django is set up before importing models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

import django
django.setup()

from benchmarks import bench_hierarchy, bench_small, bench_wide
from benchmarks.runner import print_results, results_to_json


async def main(iterations: int, output_json: bool, tier: str | None, diagrams: bool, db_label: str):
    from django_tortoise import init, close

    gc.disable()
    await init()

    all_results = []
    tiers = [tier] if tier else ["small", "wide", "hierarchy"]

    print(f"Running benchmarks ({iterations} iterations each, db={db_label})...\n")

    tier_map = {
        "small": ("Small model (Tag)", bench_small),
        "wide": ("Wide model (WideModel)", bench_wide),
        "hierarchy": ("Hierarchy models (Department/Team/Employee)", bench_hierarchy),
    }

    for i, t in enumerate(tiers, 1):
        label, module = tier_map[t]
        print(f"  [{i}/{len(tiers)}] {label}...")
        all_results.extend(await module.run_all(iterations=iterations))

    await close()
    gc.enable()

    if output_json:
        print(results_to_json(all_results))
    else:
        print_results(all_results)

    # Save results JSON
    results_dir = Path(__file__).resolve().parent.parent / "diagrams"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / f"bench_{db_label}.json"
    results_path.write_text(results_to_json(all_results))
    print(f"Results saved: {results_path}")

    if diagrams:
        from benchmarks.diagrams import generate_diagrams
        paths = generate_diagrams(all_results, db_label=db_label)
        print(f"Diagrams generated ({len(paths)} files):")
        for p in paths:
            print(f"  {p}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run django-tortoise-objects benchmarks")
    parser.add_argument("--iterations", "-n", type=int, default=50, help="Iterations per benchmark")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--tier", choices=["small", "wide", "hierarchy"], help="Run only a specific tier")
    parser.add_argument("--no-diagrams", action="store_true", help="Skip diagram generation")
    parser.add_argument("--db-label", default="sqlite", help="Label for diagram filenames (e.g. sqlite, postgres)")
    args = parser.parse_args()

    asyncio.run(main(args.iterations, args.json, args.tier, diagrams=not args.no_diagrams, db_label=args.db_label))
