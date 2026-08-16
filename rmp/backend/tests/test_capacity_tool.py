import importlib.util
from pathlib import Path


def _load_capacity_tool():
    path = Path(__file__).parents[3] / "tools" / "capacity_test.py"
    spec = importlib.util.spec_from_file_location("capacity_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capacity_percentile_handles_empty_and_order_independent_values():
    tool = _load_capacity_tool()
    assert tool.percentile([], 95) == 0
    assert tool.percentile([100, 10, 50, 25, 75], 50) == 50
    assert tool.percentile([100, 10, 50, 25, 75], 95) == 100


def test_capacity_user_is_rate_limited(monkeypatch):
    tool = _load_capacity_tool()
    clock = [0.0]
    sleeps = []
    monkeypatch.setattr(tool.time, "monotonic", lambda: clock[0])
    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(tool.time, "sleep", sleep)
    monkeypatch.setattr(tool, "request_once", lambda *args: (200, 25.0))

    assert tool.run_user(1.5, 1, "http://example", ["/health"], None, 1) == [
        ("/health", 200, 25.0), ("/health", 200, 25.0)
    ]
    assert sleeps == [1.0, 1.0]
