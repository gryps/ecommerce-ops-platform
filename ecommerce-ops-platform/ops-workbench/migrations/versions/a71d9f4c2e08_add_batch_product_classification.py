"""add batch product classification configuration

Revision ID: a71d9f4c2e08
Revises: f3a9c7d21b46
Create Date: 2026-07-25 20:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a71d9f4c2e08"
down_revision: Union[str, Sequence[str], None] = "f3a9c7d21b46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("wb_material_batches") as batch_op:
        batch_op.add_column(
            sa.Column(
                "classification_mode",
                sa.String(length=40),
                nullable=False,
                server_default="object",
            )
        )
        batch_op.add_column(
            sa.Column(
                "classification_prompt",
                sa.Text(),
                nullable=False,
                server_default="",
            )
        )
        batch_op.add_column(
            sa.Column(
                "classification_review_mode",
                sa.String(length=30),
                nullable=False,
                server_default="manual",
            )
        )
        batch_op.add_column(
            sa.Column(
                "classification_status",
                sa.String(length=40),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(
            sa.Column(
                "classification_config",
                sa.JSON(),
                nullable=False,
                server_default="{}",
            )
        )
        batch_op.add_column(sa.Column("selected_product_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("classification_job_id", sa.String(length=32), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_wb_material_batches_selected_product",
            "wb_products",
            ["selected_product_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_wb_material_batches_classification_job",
            "wb_jobs",
            ["classification_job_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("wb_material_batches") as batch_op:
        batch_op.drop_constraint(
            "fk_wb_material_batches_classification_job", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_wb_material_batches_selected_product", type_="foreignkey"
        )
        batch_op.drop_column("classification_job_id")
        batch_op.drop_column("selected_product_id")
        batch_op.drop_column("classification_config")
        batch_op.drop_column("classification_status")
        batch_op.drop_column("classification_review_mode")
        batch_op.drop_column("classification_prompt")
        batch_op.drop_column("classification_mode")
