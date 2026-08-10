"""Regression tests for public ALB route ownership."""

from pathlib import Path


ALB_TERRAFORM = Path(__file__).resolve().parents[3] / "terraform" / "alb.tf"


def test_frontend_admin_pages_are_not_forwarded_to_fastapi():
    """Next.js owns /admin/league/*; only /admin/pools/* is a backend API."""
    config = ALB_TERRAFORM.read_text()

    assert '"/admin/pools/*"' in config
    assert '"/admin/*"' not in config
