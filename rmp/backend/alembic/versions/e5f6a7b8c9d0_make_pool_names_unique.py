"""make pool names unique

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, name FROM pools ORDER BY created_at, id")
    ).mappings()
    used_names = set()
    for row in rows:
        original_name = (row["name"] or "League").strip() or "League"
        unique_name = original_name
        suffix_number = 2
        while unique_name.casefold() in used_names:
            suffix = f" ({suffix_number})"
            unique_name = f"{original_name[:255 - len(suffix)]}{suffix}"
            suffix_number += 1
        used_names.add(unique_name.casefold())
        if unique_name != row["name"]:
            connection.execute(
                sa.text("UPDATE pools SET name = :name WHERE id = :pool_id"),
                {"name": unique_name, "pool_id": row["id"]},
            )
    op.create_unique_constraint("uq_pools_name", "pools", ["name"])


def downgrade():
    op.drop_constraint("uq_pools_name", "pools", type_="unique")
