"""
Benchmark framework: timing utilities and result reporting.

Provides:
  - BenchmarkResult dataclass for storing timing data
  - run_benchmark() coroutine that times an async callable N times
  - print_results() for formatted console output
  - results_to_json() for machine-readable output
"""

import json
import statistics
import time
from dataclasses import dataclass, field


@dataclass
class BenchmarkResult:
    """Stores timing results for a single benchmark."""
    name: str
    backend: str  # "tortoise_objects" or "django_native"
    operation: str
    model_tier: str  # "small", "wide", "hierarchy"
    times_ms: list[float] = field(default_factory=list)
    iterations: int = 0

    @property
    def min_ms(self) -> float:
        return min(self.times_ms) if self.times_ms else 0.0

    @property
    def max_ms(self) -> float:
        return max(self.times_ms) if self.times_ms else 0.0

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.times_ms) if self.times_ms else 0.0

    @property
    def median_ms(self) -> float:
        return statistics.median(self.times_ms) if self.times_ms else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.times_ms:
            return 0.0
        sorted_times = sorted(self.times_ms)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]


async def run_benchmark(
    name: str,
    backend: str,
    operation: str,
    model_tier: str,
    func,
    iterations: int = 50,
    warmup: int = 1,
) -> BenchmarkResult:
    """
    Run an async benchmark function N times, collecting wall-clock timings.

    Args:
        name: Human-readable benchmark name.
        backend: "tortoise_objects" or "django_native".
        operation: Operation type (e.g., "get", "filter", "create").
        model_tier: "small", "wide", or "hierarchy".
        func: Async callable (no args) to benchmark.
        iterations: Number of timed iterations.
        warmup: Number of warmup iterations (not timed).

    Returns:
        BenchmarkResult with timing data.
    """
    # Warmup
    for _ in range(warmup):
        await func()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await func()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    return BenchmarkResult(
        name=name,
        backend=backend,
        operation=operation,
        model_tier=model_tier,
        times_ms=times,
        iterations=iterations,
    )


def print_results(results: list[BenchmarkResult]) -> None:
    """Print benchmark results as a formatted table."""
    # Group by model_tier, then operation
    header = f"{'Benchmark':<50} {'Backend':<20} {'Min':>8} {'Mean':>8} {'Median':>8} {'P95':>8} {'Max':>8} {'N':>5}"
    sep = "-" * len(header)

    print("\n" + sep)
    print("BENCHMARK RESULTS")
    print(sep)
    print(header)
    print(sep)

    current_tier = None
    for r in sorted(results, key=lambda x: (x.model_tier, x.operation, x.backend)):
        if r.model_tier != current_tier:
            current_tier = r.model_tier
            print(f"\n  [{current_tier.upper()}]")
        print(
            f"  {r.name:<48} {r.backend:<20} "
            f"{r.min_ms:>7.2f} {r.mean_ms:>7.2f} {r.median_ms:>7.2f} "
            f"{r.p95_ms:>7.2f} {r.max_ms:>7.2f} {r.iterations:>5}"
        )

    print(sep + "\n")


def results_to_json(results: list[BenchmarkResult]) -> str:
    """Serialize results to JSON."""
    data = []
    for r in results:
        data.append({
            "name": r.name,
            "backend": r.backend,
            "operation": r.operation,
            "model_tier": r.model_tier,
            "iterations": r.iterations,
            "min_ms": round(r.min_ms, 4),
            "max_ms": round(r.max_ms, 4),
            "mean_ms": round(r.mean_ms, 4),
            "median_ms": round(r.median_ms, 4),
            "p95_ms": round(r.p95_ms, 4),
        })
    return json.dumps(data, indent=2)
