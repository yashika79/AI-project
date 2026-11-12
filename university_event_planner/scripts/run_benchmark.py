import argparse
from app.services.evaluation import run_benchmark


def main():
    parser = argparse.ArgumentParser(description="Run AI Algorithm Scheduling Benchmark")
    parser.add_argument(
        "--scenario",
        default="medium",
        choices=["light", "contested", "medium", "stress"],
        help="Scenario to evaluate (default: medium)",
    )
    args = parser.parse_args()

    print(f"\n{'='*75}")
    print(f"  AI-BASED UNIVERSITY EVENT SCHEDULER & ALLOCATION BENCHMARK")
    print(f"  Scenario: {args.scenario.upper()}")
    print(f"{'='*75}\n")

    report = run_benchmark(scenario_name=args.scenario)

    header = f"{'Algorithm':<32} | {'Solved':<10} | {'Time (ms)':<10} | {'Expansions':<11} | {'Waste (seats)':<13}"
    print(header)
    print("-" * len(header))

    for e in report.evaluations:
        status_str = f"{e.solve_rate_percent}% ({e.assigned_count}/{e.total_events})"
        print(
            f"{e.algorithm_name:<32} | {status_str:<10} | {e.execution_time_ms:<10.2f} | {e.nodes_expanded:<11} | {e.total_capacity_waste:<13}"
        )

    print("\n" + "-" * len(header))
    print(f"\n💡 Finding & Recommendation:\n{report.recommendation}\n")


if __name__ == "__main__":
    main()

