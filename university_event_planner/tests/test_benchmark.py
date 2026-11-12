from app.services.evaluation import run_benchmark


def test_run_benchmark_light_scenario():
    report = run_benchmark("light")
    assert report.total_events == 4
    assert len(report.evaluations) == 4
    names = [e.algorithm_name for e in report.evaluations]
    assert any("Greedy" in n for n in names)
    assert any("CSP" in n for n in names)
    assert any("A*" in n for n in names)
    assert any("Min-Conflicts" in n for n in names)
    # Light scenario should be solved by all or most algorithms
    assert any(e.success for e in report.evaluations)
    assert report.recommendation != ""


def test_run_benchmark_fest_scenario():
    report = run_benchmark("fest")
    assert report.total_events == 12
    assert len(report.evaluations) == 4

