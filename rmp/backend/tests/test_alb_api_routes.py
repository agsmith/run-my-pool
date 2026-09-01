from pathlib import Path


def test_survivor_planner_api_is_routed_to_backend():
    """New API paths must not fall through to the frontend target group."""
    alb_config = (
        Path(__file__).resolve().parents[3] / "terraform" / "alb.tf"
    ).read_text(encoding="utf-8")

    assert '"/survivor-planner/*"' in alb_config
